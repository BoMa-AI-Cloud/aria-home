"""Model-value evaluation: dry run by default; live only with approval flags.

Dry run lists the 12 unseen variants and the exact planned calls (no model
call). Live runs the three comparisons from docs/model-value-eval-plan.md
using the existing provider, review and watcher code, then writes raw
results to backend/eval/model-value/ and a scored report to
docs/model-value-eval.md.

    python backend/scripts/run_model_value_eval.py
    python backend/scripts/run_model_value_eval.py --live --max-calls 60 --code-snapshot <git-HEAD>
"""
import argparse
import copy
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from aria_home.investigator import build_evidence_pack, investigate, validate  # noqa: E402
from aria_home.scenario import load_scenario  # noqa: E402

SPARK_MODEL_ID = "muse-spark-1.3"
RECORDING_TIMEOUT_S = 180.0
WATCHER_MAX_TOKENS = 16000
VARIANTS_SUBDIR = "eval_variants"

PLANTED_CLAIMS = (
    {"id": "wrong-temperature", "sentence": "The indoor temperature reads about 6 F higher than every cited reading shows."},
    {"id": "invented-repair-cause", "sentence": "The blower circuit activity proves the furnace itself has failed."},
    {"id": "report-proves-warmth", "sentence": "The technician completion report alone proves the house is warm again."},
    {"id": "wrong-time", "sentence": "The key temperature reading was observed three hours earlier than cited."},
)


def _env_dict(env):
    return os.environ if env is None else env


def _redact(text, env):
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    source = _env_dict(env)
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    secret = get("MODEL_API_KEY")
    if isinstance(secret, str) and secret.strip():
        text = text.replace(secret.strip(), "[redacted]").replace(secret, "[redacted]")
    return text


def _utc_now(now):
    return now if now is not None else datetime.now(timezone.utc)


def _stamp(now):
    return _utc_now(now).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def variants_dir(base=None):
    return Path(base) if base else BACKEND_DIR / "scenarios" / VARIANTS_SUBDIR


def eval_out_dir(base=None):
    return Path(base) if base else BACKEND_DIR / "eval" / "model-value"


def load_variants(base=None):
    root = variants_dir(base)
    variants = []
    for path in sorted(root.iterdir()):
        meta = path / "variant.json"
        if path.is_dir() and meta.is_file():
            variants.append(json.loads(meta.read_text(encoding="utf-8")))
    return variants


def plan_calls(variants):
    calls = []
    for index, variant in enumerate(variants):
        vid = variant["id"]
        calls.append({"variant": vid, "kind": "spark", "detail": "muse-spark-1.3 explanation"})
        calls.append({"variant": vid, "kind": "wonder-genuine", "detail": "muse-wonder-1.0 review of the genuine answer"})
        calls.append({
            "variant": vid, "kind": "wonder-planted", "detail": "muse-wonder-1.0 review of the planted-claim copy",
            "planted_claim": PLANTED_CLAIMS[index % len(PLANTED_CLAIMS)]["id"],
        })
        calls.append({"variant": vid, "kind": "watcher-first", "detail": "watcher first attempt"})
        calls.append({"variant": vid, "kind": "watcher-revision", "detail": "watcher revision iff the first attempt is rejected"})
    return calls


def _unique_path(path):
    candidate = Path(path)
    if not candidate.exists():
        return candidate
    index = 1
    while True:
        alt = candidate.with_name(f"{candidate.stem}-{index}{candidate.suffix}")
        if not alt.exists():
            return alt
        index += 1


class _CountingProvider:
    def __init__(self, inner):
        self._inner = inner
        self.calls = 0

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def generate(self, prompt=None, **kwargs):
        self.calls += 1
        return self._inner.generate(prompt, **kwargs)


class _LiveWatcherProvider:
    mode = "live"
    model_id = SPARK_MODEL_ID

    def __init__(self, env, timeout_s, max_tokens):
        from aria_home.watcher import WATCHER_MODEL_ID

        self._env = env
        self.timeout_s = timeout_s
        self.max_tokens = max_tokens
        self.model_id = WATCHER_MODEL_ID
        self.calls = 0

    def generate(self, prompt=None, **kwargs):
        from aria_home.watcher import request_live_watcher

        self.calls += 1
        live = request_live_watcher(
            prompt if isinstance(prompt, str) else str(prompt),
            env=self._env,
            max_tokens=self.max_tokens,
            timeout_s=self.timeout_s,
        )
        return {
            "text": live.get("text"),
            "error": live.get("error"),
            "status": live.get("status"),
            "model": live.get("model"),
            "answered_model": live.get("model") or self.model_id,
            "mode": "live",
        }


def _spark_provider(env, timeout_s):
    from aria_home.provider import MetaProvider, ProviderConfig

    source = _env_dict(env)
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    config = ProviderConfig(
        provider_url=(get("ARIA_HOME_PROVIDER_URL") or "").strip() or None,
        model_id=SPARK_MODEL_ID,
        api_key=get("MODEL_API_KEY"),
        enabled=get("ARIA_HOME_MODEL_ENABLED") == "1",
        timeout_s=timeout_s,
    )
    return MetaProvider(config)


def _check_live_env(env):
    source = _env_dict(env)
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    missing = []
    if get("ARIA_HOME_MODEL_ENABLED") != "1":
        missing.append("ARIA_HOME_MODEL_ENABLED=1")
    if not (get("ARIA_HOME_PROVIDER_URL") or "").strip():
        missing.append("ARIA_HOME_PROVIDER_URL")
    if not (get("MODEL_API_KEY") or "").strip():
        missing.append("MODEL_API_KEY")
    return missing


def _plant_claim(output, claim):
    planted = copy.deepcopy(output)
    interpretation = planted.get("interpretation", "")
    planted["interpretation"] = f"{interpretation} {claim['sentence']}".strip()
    return planted


def _review_result(entry_output, pack, env, http_post, timeout_s):
    from aria_home.review import request_live_review

    if entry_output is None:
        return {"status": "skipped", "reason": "no accepted spark answer to review"}
    result = request_live_review(entry_output, pack, env=env, http_post=http_post, timeout_s=timeout_s)
    body = {
        "status": "ok" if result.get("ok") else "error",
        "error": result.get("error"),
        "review": result.get("review"),
        "validation": result.get("validation"),
    }
    if result.get("detail"):
        body["detail"] = _redact(result["detail"], env)
    return body


def run_variant(variant, scenarios_root, env, http_post, timeout_s,
                spark_provider=None, watcher_provider=None):
    from aria_home.watcher import run_watcher

    scenario = load_scenario(Path(scenarios_root) / variant["id"])
    at = datetime.fromisoformat(variant["eval_at"])
    pack = build_evidence_pack(scenario, at)
    provider = spark_provider if spark_provider is not None else _spark_provider(env, timeout_s)
    investigation = investigate(scenario, at, provider=provider)
    spark = {"status": investigation.status, "reasons": [_redact(r, env) for r in investigation.reasons]}
    output = None
    if investigation.status == "ok" and investigation.output is not None:
        output = investigation.output.model_dump(mode="json")
        spark["output"] = output
        spark["model_id"] = investigation.model_id
    genuine = _review_result(output, pack, env, http_post, timeout_s)
    claim = next(c for c in PLANTED_CLAIMS if c["id"] == variant.get("planted_claim", PLANTED_CLAIMS[0]["id"]))
    planted_output = _plant_claim(output, claim) if output is not None else None
    planted = _review_result(planted_output, pack, env, http_post, timeout_s)
    planted["planted_claim"] = claim["id"]
    watcher_source = watcher_provider if watcher_provider is not None else _LiveWatcherProvider(env, timeout_s, WATCHER_MAX_TOKENS)
    counting = _CountingProvider(watcher_source)
    watched = run_watcher(scenario, at, counting)
    watcher = {
        "final_result": watched["final_result"],
        "failed_checks": watched["failed_checks"],
        "observations": watched["observations"],
        "code_detections": watched["code_detections"],
        "model_triggered": watched["model_triggered"],
        "code_triggered": watched["code_triggered"],
        "provider_calls": counting.calls,
        "correction_record": watched["correction_record"],
    }
    return {
        "variant": variant["id"],
        "eval_at": variant["eval_at"],
        "expected_readiness": variant["expected_readiness"],
        "expected_verification": variant["expected_verification"],
        "spark": spark,
        "wonder_genuine": genuine,
        "wonder_planted": planted,
        "watcher": watcher,
    }


def score_spark(item):
    spark = item.get("spark", {})
    if spark.get("status") != "ok" or not isinstance(spark.get("output"), dict):
        return {"verdict": "rejected", "reasons": spark.get("reasons", []), "needs_human": []}
    output = spark["output"]
    deterministic = []
    if output.get("readiness") != item.get("expected_readiness"):
        deterministic.append(f"readiness {output.get('readiness')!r} != code label {item.get('expected_readiness')!r}")
    return {
        "verdict": "pass" if not deterministic else "fail",
        "reasons": deterministic,
        "needs_human": ["problem_named", "next_action_right"],
    }


def score_spark_validate(item, pack):
    spark = item.get("spark", {})
    if spark.get("status") != "ok" or not isinstance(spark.get("output"), dict):
        return ["no accepted spark answer"]
    return validate(spark["output"], pack)


def score_wonder(results):
    genuine = [r for r in results if isinstance(r.get("wonder_genuine"), dict) and r["wonder_genuine"].get("status") == "ok"]
    planted = [r for r in results if isinstance(r.get("wonder_planted"), dict) and r["wonder_planted"].get("status") == "ok"]
    genuine_flagged = [r["variant"] for r in genuine if (r["wonder_genuine"].get("review") or {}).get("verdict") == "issues_found"]
    planted_flagged = [r["variant"] for r in planted if (r["wonder_planted"].get("review") or {}).get("verdict") == "issues_found"]
    return {
        "genuine_total": len(genuine),
        "genuine_flagged": genuine_flagged,
        "planted_total": len(planted),
        "planted_flagged": planted_flagged,
    }


def score_watcher(results):
    first_verified = {}
    first_rejected = {}
    revised_ok = []
    missed_proxy = []
    for item in results:
        watcher = item.get("watcher", {}) or {}
        record = watcher.get("correction_record")
        observations = watcher.get("observations", []) or []
        if record is None and watcher.get("final_result") == "confirmed":
            first_verified[item["variant"]] = len(observations)
        else:
            failed = (record or {}).get("failed_checks", watcher.get("failed_checks", []))
            first_rejected[item["variant"]] = failed
            if watcher.get("final_result") == "corrected and verified":
                revised_ok.append(item["variant"])
        if not observations and watcher.get("code_triggered"):
            missed_proxy.append(item["variant"])
    attempted = [v for v in first_rejected if any(
        item["variant"] == v and (item.get("watcher", {}) or {}).get("provider_calls", 0) > 1
        for item in results
    )]
    return {
        "first_verified": first_verified,
        "first_rejected": first_rejected,
        "revisions_attempted": attempted,
        "revised_ok": revised_ok,
        "missed_proxy": missed_proxy,
    }


def _rate(flagged, total):
    if not total:
        return "n/a (0 denominator)"
    return f"{len(flagged)}/{total}"


def render_report(results, spark_scores, wonder, watcher_scores, snapshot, stamp, failures_only=False):
    lines = [
        "# Model-Value Evaluation Report",
        "",
        f"Code snapshot: {snapshot}; generated {stamp}; live variants n={len(results)}.",
        "",
        "## A — Spark vs deterministic summary",
        "",
    ]
    passed = sum(1 for s in spark_scores if s["verdict"] == "pass")
    lines.append(f"Deterministic checks passing: {passed}/{len(spark_scores)}.")
    for item, score in zip(results, spark_scores):
        if score["verdict"] != "pass":
            lines.append(f"- FAIL {item['variant']}: {score['verdict']}; {'; '.join(score['reasons']) or 'no accepted answer'}")
    lines.append("Needs human scoring per variant (never guessed): problem_named, next_action_right.")
    for item in results:
        lines.append(f"- HUMAN {item['variant']}: problem_named=?, next_action_right=?")
    lines += [
        "",
        "## B — Spark vs Spark+Wonder",
        "",
        f"Catch rate on planted claims: {_rate(wonder['planted_flagged'], wonder['planted_total'])} flagged.",
        f"False-alarm rate on genuine answers: {_rate(wonder['genuine_flagged'], wonder['genuine_total'])} flagged.",
    ]
    for item in results:
        planted = item.get("wonder_planted", {})
        review = (planted.get("review") or {})
        lines.append(f"- {item['variant']}: planted={planted.get('planted_claim')}; verdict={review.get('verdict')}; status={planted.get('status')}")
    lines += [
        "",
        "## C — watcher first attempt vs revised attempt",
        "",
        f"Verified first attempt: {len(watcher_scores['first_verified'])}/{len(results)}.",
        f"Revisions corrected: {len(watcher_scores['revised_ok'])}/{len(watcher_scores['revisions_attempted'])} attempted.",
        f"Missed-problem proxy (empty model answer while code detections fire): {len(watcher_scores['missed_proxy'])}/{len(results)}.",
    ]
    for variant, failed in watcher_scores["first_rejected"].items():
        lines.append(f"- REJECTED {variant}: {'; '.join(failed) or 'no checks recorded'}")
    for variant in watcher_scores["missed_proxy"]:
        lines.append(f"- MISSED-PROXY {variant}: model empty, code detections fired")
    lines += [
        "Needs human scoring per variant (never guessed): observation_correct.",
        "",
        "## Limitations",
        "",
        "- Models interpret only; readiness and verification stay in code.",
        "- Rubric parts needing judgement are listed above as needs-human, not scored.",
        "- Twelve synthetic variants cannot represent real homes; results do not generalize.",
        "- A Wonder non-flag is not proof the answer is true; a flag is bounded to the pack.",
    ]
    if failures_only:
        return "\n".join(line for line in lines if line.startswith(("#", "- FAIL", "- REJECTED", "- MISSED")))
    return "\n".join(lines) + "\n"


def main(argv=None, *, env=None, http_post=None, out=None, now=None,
         spark_provider=None, watcher_provider=None):
    out = out or print
    source_env = _env_dict(env)
    parser = argparse.ArgumentParser(prog="run_model_value_eval", description="Model-value evaluation")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--max-calls", type=int, default=None)
    parser.add_argument("--code-snapshot", default=None)
    parser.add_argument("--variants-dir", default=None)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--report", default=None)
    parser.add_argument("--timeout-s", type=float, default=RECORDING_TIMEOUT_S)
    args = parser.parse_args(argv)

    scenarios_root = variants_dir(args.variants_dir)
    variants = load_variants(scenarios_root)
    for index, variant in enumerate(variants):
        variant.setdefault("planted_claim", PLANTED_CLAIMS[index % len(PLANTED_CLAIMS)]["id"])
    calls = plan_calls(variants)
    if not args.live:
        out(f"variants: {len(variants)}")
        for variant in variants:
            out(f"- {variant['id']}: eval_at={variant['eval_at']} readiness={variant['expected_readiness']} verification={variant['expected_verification']}")
        out(f"planned calls: {len(calls)} (spark={sum(1 for c in calls if c['kind']=='spark')}, wonder={sum(1 for c in calls if c['kind'].startswith('wonder'))}, watcher up to {sum(1 for c in calls if c['kind'].startswith('watcher'))})")
        out("dry run: zero model calls made")
        return 0

    if args.max_calls is None or not args.code_snapshot:
        out("live run requires --live --max-calls N --code-snapshot SHA")
        return 2
    if len(calls) > args.max_calls:
        out(f"refusing: planned {len(calls)} calls exceed --max-calls {args.max_calls}; zero model calls made")
        return 2
    needs_env = spark_provider is None or watcher_provider is None or http_post is None
    if needs_env:
        problems = _check_live_env(source_env)
        if problems:
            out(f"live run not configured ({', '.join(problems)}); zero model calls made")
            return 2
    results = []
    for variant in variants:
        try:
            results.append(run_variant(
                variant, scenarios_root, source_env, http_post, args.timeout_s,
                spark_provider=spark_provider, watcher_provider=watcher_provider,
            ))
        except Exception as exc:
            results.append({"variant": variant["id"], "eval_at": variant["eval_at"], "error": _redact(str(exc), source_env)})
    packs = {}
    for variant in variants:
        try:
            scenario = load_scenario(scenarios_root / variant["id"])
            packs[variant["id"]] = build_evidence_pack(scenario, datetime.fromisoformat(variant["eval_at"]))
        except Exception:
            packs[variant["id"]] = {}
    spark_scores = []
    for item in results:
        score = score_spark(item)
        if score["verdict"] == "pass":
            extra = score_spark_validate(item, packs.get(item["variant"], {}))
            if extra:
                score = {"verdict": "fail", "reasons": extra, "needs_human": score["needs_human"]}
        spark_scores.append(score)
    wonder = score_wonder(results)
    watcher_scores = score_watcher(results)
    stamp = _stamp(now)
    out_base = eval_out_dir(args.out_dir)
    out_base.mkdir(parents=True, exist_ok=True)
    raw_path = _unique_path(out_base / f"model-value-{stamp}.json")
    raw_path.write_text(json.dumps({
        "snapshot": args.code_snapshot,
        "generated_at": _utc_now(now).astimezone(timezone.utc).isoformat(),
        "planned_calls": len(calls),
        "records": results,
    }, indent=2, default=str) + "\n", encoding="utf-8")
    report = render_report(results, spark_scores, wonder, watcher_scores, args.code_snapshot, stamp)
    report_path = Path(args.report) if args.report else BACKEND_DIR.parent / "docs" / "model-value-eval.md"
    report_path.write_text(report, encoding="utf-8")
    out(f"wrote {raw_path} and {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
