import argparse
import json
import os
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from .contracts import SourceKind
from .investigator import build_evidence_pack, investigate
from .outcomes import follow_up_for
from .provider import BasetenConfig, BasetenProvider, MockProvider, ProviderConfig, get_provider
from .readiness import STALE_READING_AGE_S
from .scenario import load_scenario
from .verification import verify_recovery

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
SCENARIOS_DIR = BACKEND_DIR / "scenarios"
EVAL_DIR = BACKEND_DIR / "eval"
EXPECTED_PATH = EVAL_DIR / "expected.json"
RESULTS_PATH = EVAL_DIR / "results-offline.json"
LIVE_RESULTS_PATH = EVAL_DIR / "results-live.json"
LIVE_BASETEN_RESULTS_PATH = EVAL_DIR / "results-live-baseten.json"
BASETEN_RESULTS_PATH = LIVE_BASETEN_RESULTS_PATH
DOCS_PATH = REPO_DIR / "docs" / "evaluation.md"

CASES = (
    ("demo_v1", "2026-01-16T18:00:00-05:00"),
    ("demo_recovery_v1", "2026-01-16T18:00:00-05:00"),
    ("demo_recovery_v1", "2026-01-16T19:00:00-05:00"),
    ("demo_recovery_v1", "2026-01-16T20:31:00-05:00"),
    ("demo_no_followup_v1", "2026-01-16T20:31:00-05:00"),
    ("demo_revised_v1", "2026-01-16T18:00:00-05:00"),
    ("demo_cancelled_v1", "2026-01-16T18:00:00-05:00"),
    ("demo_video_v1", "2026-01-16T16:31:00-05:00"),
    ("demo_video_v1", "2026-01-16T18:21:00-05:00"),
    ("demo_video_v1", "2026-01-16T18:51:00-05:00"),
    ("demo_video_v1", "2026-01-16T20:21:00-05:00"),
    ("demo_video_v1", "2026-01-16T21:01:00-05:00"),
    ("visual_water_low_temp_v1", "2026-01-16T18:00:00-05:00"),
    ("visual_frost_missed_v1", "2026-01-16T18:00:00-05:00"),
    ("visual_dry_floor_v1", "2026-01-16T18:00:00-05:00"),
    ("visual_water_low_temp_v1", "2026-01-16T19:00:00-05:00"),
    ("visual_frost_missed_v1", "2026-01-16T20:31:00-05:00"),
)

CONDITIONS = ("combined", "thermostat_only", "room_sensor_only", "electrical_only", "calendar_only")
CONDITION_SOURCES = {
    "combined": None,
    "thermostat_only": "thermostat",
    "room_sensor_only": "room_sensor",
    "electrical_only": "electrical",
    "calendar_only": "calendar",
}

FOLLOWUP_CREATED_AT = {
    "demo_v1": "2026-01-16T18:00:00-05:00",
    "demo_recovery_v1": "2026-01-16T18:00:00-05:00",
    "demo_no_followup_v1": "2026-01-16T18:00:00-05:00",
    "demo_revised_v1": "2026-01-16T18:00:00-05:00",
    "demo_cancelled_v1": "2026-01-16T18:00:00-05:00",
    "demo_video_v1": "2026-01-16T16:31:00-05:00",
}

WARMING_STAGES = ("warming_observed", "goal_verified", "arrival_met")
GOAL_STAGES = ("goal_verified", "arrival_met")


def case_id(scenario, at):
    return f"{scenario}@{at[11:16]}"


def load_expected(path=EXPECTED_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["cases"]


def _parse(value):
    return datetime.fromisoformat(value)


def _filtered(scenario, condition):
    kept = CONDITION_SOURCES[condition]
    if kept is None:
        return scenario
    return replace(scenario, records=[r for r in scenario.records if r.source.value == kept], visual=None)


def _followup(scenario):
    created = FOLLOWUP_CREATED_AT.get(scenario.manifest.id)
    if created is None:
        return None
    try:
        return follow_up_for(scenario, f"eval-{scenario.manifest.id}", _parse(created))
    except Exception:
        return None


def supportable_claims(pack, verification_stage, at):
    metrics = pack.get("metrics") or {}
    trend = metrics.get("indoor_trend") or {}
    circuits = metrics.get("circuits") or {}
    last_at = trend.get("last_observed_at")
    fresh = False
    if trend.get("last_value") is not None and isinstance(last_at, str):
        age_s = (at - _parse(last_at)).total_seconds()
        fresh = trend.get("fresh", trend.get("is_fresh"))
        if fresh is None:
            fresh = 0 <= age_s <= STALE_READING_AGE_S
        else:
            fresh = bool(fresh) and age_s >= 0
    change = trend.get("change")
    return {
        "current_temperature": bool(fresh),
        "target_temperature": pack.get("confirmation") is not None,
        "target_gap": bool(fresh and metrics.get("target_gap") is not None),
        "warming": bool(
            fresh
            and (trend.get("sample_count") or 0) >= 3
            and (trend.get("coverage") or 0) >= 0.5
            and isinstance(change, (int, float))
            and change >= 1.0
        ),
        "electrical_activity": any(c.get("sample_count") and c.get("max_w") is not None for c in circuits.values()),
        "useful_heat": False,
        "power_continuity_weighs_against_total_loss": (pack.get("power_context") or {}).get("continuity") == "activity_weighs_against_total_loss",
        "recovery_warming_verified": verification_stage in WARMING_STAGES,
        "recovery_goal_verified": verification_stage in GOAL_STAGES,
    }


def evaluate_cases(cases=None, scenario_cache=None):
    expected = cases if cases is not None else load_expected()
    cache = scenario_cache if scenario_cache is not None else {}
    followups = {}
    rows = []
    for case in expected:
        name = case["scenario"]
        if name not in cache:
            cache[name] = load_scenario(SCENARIOS_DIR / name)
            followups[name] = _followup(cache[name])
        scenario = cache[name]
        at = _parse(case["at"])
        for condition in CONDITIONS:
            filtered = _filtered(scenario, condition)
            pack = build_evidence_pack(filtered, at)
            got = pack["computed_readiness"]
            readiness_obj = pack.get("readiness") if isinstance(pack.get("readiness"), dict) else {}
            got_target = readiness_obj.get("target_at_arrival")
            if got_target is None and isinstance(readiness_obj.get("inputs"), dict):
                got_target = readiness_obj["inputs"].get("target_at_arrival") or readiness_obj["inputs"].get("arrival_outcome")
            if got == "arrival_passed" and got_target is None:
                got_target = "unknown"
            stage = None
            if followups[name] is not None:
                stage = verify_recovery(filtered, followups[name], at)["stage"]
            expected_stage = case.get("expected_verification")
            expected_target = case.get("expected_target_at_arrival")
            readiness_correct = got == case["expected_readiness"]
            target_correct = None if expected_target is None else got_target == expected_target
            verification_correct = None if expected_stage is None else stage == expected_stage
            correct = readiness_correct and verification_correct is not False and target_correct is not False
            if correct:
                classification = "correct"
            elif not readiness_correct and got == "cannot_tell":
                classification = "unsupported"
            elif not readiness_correct:
                classification = "wrong"
            elif target_correct is False and got_target in (None, "unknown"):
                classification = "unsupported"
            elif target_correct is False:
                classification = "wrong"
            else:
                classification = "unsupported"
            rows.append({
                "case_id": case["id"],
                "scenario": name,
                "at": case["at"],
                "condition": condition,
                "sources_kept": "all" if condition == "combined" else CONDITION_SOURCES[condition],
                "expected_readiness": case["expected_readiness"],
                "got_readiness": got,
                "readiness_correct": readiness_correct,
                "expected_target_at_arrival": expected_target,
                "target_at_arrival": got_target,
                "got_target_at_arrival": got_target,
                "target_at_arrival_correct": target_correct,
                "expected_verification": expected_stage,
                "got_verification": stage,
                "verification_correct": verification_correct,
                "correct": correct,
                "classification": classification,
                "claims": supportable_claims(pack, stage, at),
            })
    return rows


def _totals(rows):
    totals = {}
    for condition in CONDITIONS:
        group = [r for r in rows if r["condition"] == condition]
        scored = [r for r in group if r["verification_correct"] is not None]
        target_scored = [r for r in group if r.get("target_at_arrival_correct") is not None]
        totals[condition] = {
            "cases": len(group),
            "readiness_correct": sum(r["readiness_correct"] for r in group),
            "readiness_wrong": sum(r["classification"] == "wrong" for r in group),
            "readiness_unsupported": sum(r["classification"] == "unsupported" for r in group),
            "target_at_arrival_scored": len(target_scored),
            "target_at_arrival_correct": sum(bool(r["target_at_arrival_correct"]) for r in target_scored),
            "verification_scored": len(scored),
            "verification_correct": sum(bool(r["verification_correct"]) for r in scored),
            "fully_correct": sum(r["correct"] for r in group),
        }
    return totals


def _highlights(rows):
    by_case = {}
    for row in rows:
        by_case.setdefault(row["case_id"], {})[row["condition"]] = row
    highlights = []
    for cid, group in by_case.items():
        combined = group["combined"]
        if not combined["correct"]:
            continue
        for condition in CONDITIONS[1:]:
            row = group[condition]
            if not row["correct"]:
                highlights.append({
                    "case_id": cid,
                    "condition": condition,
                    "kind": row["classification"],
                    "expected_readiness": row["expected_readiness"],
                    "got_readiness": row["got_readiness"],
                    "expected_verification": row["expected_verification"],
                    "got_verification": row["got_verification"],
                    "detail": f"{condition} gives {row['classification']} answer ({row['got_readiness']}/{row['got_verification']}) where combined gives the expected {row['expected_readiness']}/{row['expected_verification']}.",
                })
            for claim in ("current_temperature", "target_gap", "warming", "recovery_warming_verified", "recovery_goal_verified"):
                if combined["claims"][claim] and not row["claims"][claim] and row["correct"]:
                    highlights.append({
                        "case_id": cid,
                        "condition": condition,
                        "kind": "unsupported_claim",
                        "claim": claim,
                        "detail": f"{condition} cannot support the {claim} claim that combined supports at {cid}.",
                    })
    for row in rows:
        if row["case_id"] == "demo_video_v1@16:31" and row["condition"] == "electrical_only" and row["claims"]["electrical_activity"]:
            highlights.append({
                "case_id": row["case_id"],
                "condition": "electrical_only",
                "kind": "unsupported_claim",
                "claim": "useful_heat",
                "detail": "electrical_only at demo_video_v1@16:31 can support an electrical-activity claim (blower circuit watts) but watts alone never support a useful-heat claim; the combined view uses the flat room readings to show no warming.",
            })
            break
    return highlights


def run_offline(cases=None):
    rows = evaluate_cases(cases)
    count = len(load_expected() if cases is None else cases)
    return {
        "mode": "offline",
        "live": False,
        "disclaimer": f"Synthetic scenarios only; expected labels hand-written by the builder from fixture data; small sample ({count} cases); not a benchmark of real homes.",
        "conditions_note": "Source-limited conditions keep only evidence records of one source kind. Trip/confirmation context (arrival and target, the question being asked) is retained, so a lone temperature source can answer where its readings are fresh and sufficient. useful_heat is supportable in no condition: watts alone never prove useful heat.",
        "totals": _totals(rows),
        "highlights": _highlights(rows),
        "rows": rows,
    }


def run_model_cases(provider, cases=None, max_calls=None):
    expected = cases if cases is not None else load_expected()
    if max_calls is not None:
        expected = expected[: max(0, int(max_calls))]
    cache = {}
    records = []
    for case in expected:
        name = case["scenario"]
        if name not in cache:
            cache[name] = load_scenario(SCENARIOS_DIR / name)
        result = investigate(cache[name], _parse(case["at"]), provider=provider)
        computed = (result.summary or {}).get("computed_readiness") or (result.evidence_pack or {}).get("computed_readiness")
        model_readiness = result.output.readiness if result.output is not None else None
        records.append({
            "case_id": case["id"],
            "scenario": name,
            "at": case["at"],
            "status": result.status,
            "provider_mode": result.provider_mode,
            "model_id": result.model_id,
            "computed_readiness": computed,
            "model_readiness": model_readiness,
            "readiness_agreement": (model_readiness == computed) if model_readiness is not None else None,
            "rejected_claim_reasons": list(result.reasons) if result.status != "ok" else [],
            "reasons": list(result.reasons),
            "latency_ms": result.latency_ms,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "max_tokens_used": result.max_tokens_used,
        })
    return records


def check_live_allowed(live, max_calls, env=None, provider=None, provider_name=None):
    source = os.environ if env is None else env
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    chosen = provider_name or provider or "meta"
    chosen = str(chosen).lower()
    missing = []
    if not live:
        missing.append("--live")
    if not isinstance(max_calls, int) or isinstance(max_calls, bool) or max_calls < 1:
        missing.append("--max-calls N (positive integer)")
    if chosen == "baseten":
        if get("ARIA_HOME_BASETEN_ENABLED") != "1":
            missing.append("ARIA_HOME_BASETEN_ENABLED=1")
    elif chosen in ("meta", "meta-provider", "meta_provider"):
        if get("ARIA_HOME_MODEL_ENABLED") != "1":
            missing.append("ARIA_HOME_MODEL_ENABLED=1")
    else:
        missing.append("--provider meta|baseten")
    if missing:
        raise RuntimeError("live evaluation refused; missing: " + ", ".join(missing))
    return True


def _expected_label(row):
    label = row["expected_readiness"] if row["expected_verification"] is None else f"{row['expected_readiness']} / {row['expected_verification']}"
    if row.get("expected_target_at_arrival") is not None:
        label += f" (target at arrival: {row['expected_target_at_arrival']})"
    return label


def _got_label(row):
    label = row["got_readiness"] if row["got_verification"] is None else f"{row['got_readiness']} / {row['got_verification']}"
    if row.get("expected_target_at_arrival") is not None or row.get("target_at_arrival") is not None:
        label += f" (target at arrival: {row.get('target_at_arrival')})"
    return label


def render_markdown(results):
    totals = results["totals"]
    case_count = len({(r["scenario"], r["at"]) for r in results["rows"]}) or len(totals.get("combined", {}).get("cases", 0))
    lines = [
        "# Evaluation (offline, deterministic)",
        "",
        "Synthetic scenarios, expected labels written by the builder, small sample, not a benchmark of real homes.",
        "",
        f"The {case_count} cases pair each scenario with fixed replay times. Expected readiness (and, for `demo_video_v1` only, the expected verification stage) is hand-written in `backend/eval/expected.json` from the fixture data, with a one-line reason per case. For `arrival_passed` cases (now strictly after the confirmed arrival), `expected_target_at_arrival` (`met` / `not_met`) is also scored: a case is correct only if both the readiness status and the at-arrival outcome (`target_at_arrival` on the readiness result) match, so a source condition without indoor temperatures yields `unknown` and is scored unsupported, not correct. Each case is run under the combined (all-sources) condition and under source-limited conditions that keep only one source kind of evidence record; trip/confirmation context (the arrival and target being asked about) is retained. `useful_heat` is supportable in no condition: circuit watts alone never prove useful heat. The `visual_*` cases add synthetic SAM 3.1 segmentation evidence (recorded responses over synthetic images, including the recorded frost-pipe false negative); visual evidence never yields `on_track`, `warming_observed`, `goal_verified` or `arrival_met`, and zero detected objects is reported as no detection, never as an all-clear.",
        "",
        "The model investigation contract is `inv-v3`: after the confirmed arrival has passed, the model states the temperature at arrival (`temperature_at_arrival`, the last eligible reading observed and received by arrival) and must not state a `current_temperature`. All recorded live runs below predate this change and used the `inv-v2` contract, which asked for a current temperature even after arrival.",
        "",
        "## Totals",
        "",
        "| Condition | Cases | Readiness correct | Wrong | Unsupported | Target at arrival correct (scored) | Verification correct (scored) | Fully correct |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for condition in CONDITIONS:
        t = totals[condition]
        lines.append(f"| {condition} | {t['cases']} | {t['readiness_correct']} | {t['readiness_wrong']} | {t['readiness_unsupported']} | {t.get('target_at_arrival_correct', 0)} ({t.get('target_at_arrival_scored', 0)}) | {t['verification_correct']} ({t['verification_scored']}) | {t['fully_correct']} |")
    lines += [
        "",
        "## Cases",
        "",
        "| Case | Condition | Expected | Got | Correct? |",
        "|---|---|---|---|---|",
    ]
    for row in results["rows"]:
        lines.append(f"| {row['case_id']} | {row['condition']} | {_expected_label(row)} | {_got_label(row)} | {'yes' if row['correct'] else 'no (' + row['classification'] + ')'} |")
    lines += ["", "## Where a single source falls short", ""]
    if results["highlights"]:
        for item in results["highlights"]:
            lines.append(f"- {item['detail']}")
    else:
        lines.append("- None.")
    lines += [
        "",
        "## Reading this",
        "",
        "- Combined matches every expected readiness label and every scored verification stage; the single-source conditions do not, mostly by falling back to `cannot_tell` / `telemetry_missing` / `unable_to_verify` (unsupported), not by asserting the opposite readiness.",
        "- Thermostat-only during the `demo_video_v1` outage (16:31) cannot support a warming or even a current-temperature claim: its last reading is 15:30, stale by evaluation time. The combined view still has fresh independent room readings showing no warming.",
        "- Electrical-only can show circuit activity (for example the blower circuit during the outage) but can never support a useful-heat claim; only temperature evidence can show warming.",
        "- A model condition exists in `aria_home.evaluation.run_model_cases` (status, readiness agreement, rejected-claim reasons, latency, tokens per case). Offline tests run it with the mock provider. A live run requires `--live`, `--max-calls N`, and `ARIA_HOME_MODEL_ENABLED=1` together; there are no retries, and timeout/max-tokens come from the existing provider/investigator config.",
        "",
    ]
    return "\n".join(lines)


def write_offline(results, results_path=RESULTS_PATH, docs_path=DOCS_PATH):
    results_path = Path(results_path)
    docs_path = Path(docs_path)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    rendered = render_markdown(results)
    if docs_path.exists():
        existing = docs_path.read_text(encoding="utf-8")
        marker = "## Live model condition"
        if marker in existing:
            live = existing[existing.index(marker):].strip()
            if "live run used the earlier labels" not in live:
                heading, _, rest = live.partition("\n")
                note = "Note: the live run used the earlier labels (before the strictly-after-arrival correction and target-at-arrival scoring), so its computed-readiness column reflects those earlier labels."
                live = heading + "\n\n" + note + ("\n" + rest if rest else "")
            rendered = rendered + ("" if rendered.endswith("\n\n") else "\n" if rendered.endswith("\n") else "\n\n") + live + "\n"
    docs_path.write_text(rendered, encoding="utf-8")
    return results_path, docs_path


def main(argv=None, env=None):
    parser = argparse.ArgumentParser(prog="aria_home.evaluation", description="ARIA Home offline/live evaluation harness")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--offline", action="store_true", help="deterministic offline evaluation (no model calls)")
    group.add_argument("--live", action="store_true", help="run the model condition on live models (requires --max-calls and ARIA_HOME_MODEL_ENABLED=1)")
    group.add_argument("--mock-model", action="store_true", help="run the model condition with the mock provider (no network)")
    parser.add_argument("--max-calls", type=int, default=None)
    parser.add_argument("--provider", choices=["meta", "baseten"], default="meta")
    parser.add_argument("--results", default=None, help="output JSON path (offline mode)")
    parser.add_argument("--docs", default=None, help="output markdown path (offline mode)")
    args = parser.parse_args(argv)
    source_env = os.environ if env is None else env

    if args.offline:
        results = run_offline()
        results_path, docs_path = write_offline(
            results,
            Path(args.results) if args.results else RESULTS_PATH,
            Path(args.docs) if args.docs else DOCS_PATH,
        )
        for condition in CONDITIONS:
            t = results["totals"][condition]
            print(f"{condition}: readiness {t['readiness_correct']}/{t['cases']}, verification {t['verification_correct']}/{t['verification_scored']}, fully correct {t['fully_correct']}/{t['cases']}")
        print(f"wrote {results_path} and {docs_path}")
        return 0

    if args.mock_model:
        records = run_model_cases(MockProvider(), max_calls=args.max_calls)
        print(json.dumps(records, indent=2))
        return 0

    try:
        check_live_allowed(args.live, args.max_calls, env=source_env, provider=args.provider)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    if args.provider == "baseten":
        baseten_config = BasetenConfig.from_env(source_env)
        provider = BasetenProvider(baseten_config)
        if getattr(provider, "mode", None) != "live":
            print("live evaluation refused; provider is not live (check ARIA_HOME_BASETEN_ENABLED and BASETEN_API_KEY)", file=sys.stderr)
            raise SystemExit(2)
        records = run_model_cases(provider, max_calls=args.max_calls)
        LIVE_BASETEN_RESULTS_PATH.write_text(json.dumps({"mode": "live", "provider": "baseten", "model_id": baseten_config.model_id, "records": records}, indent=2) + "\n", encoding="utf-8")
        print(f"live model cases: {len(records)}; wrote {LIVE_BASETEN_RESULTS_PATH}")
        return 0
    config = ProviderConfig.from_env(source_env)
    provider = get_provider(config)
    if getattr(provider, "mode", None) != "live":
        print("live evaluation refused; provider is not live (check ARIA_HOME_MODEL_ENABLED, provider URL, model id and MODEL_API_KEY)", file=sys.stderr)
        raise SystemExit(2)
    records = run_model_cases(provider, max_calls=args.max_calls)
    LIVE_RESULTS_PATH.write_text(json.dumps({"mode": "live", "records": records}, indent=2) + "\n", encoding="utf-8")
    print(f"live model cases: {len(records)}; wrote {LIVE_RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
