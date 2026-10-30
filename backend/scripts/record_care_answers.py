"""Record the approved care-story model answers and reviews (operator-only).

For each of the 10 public-demo checkpoints of care_home_v1, this builds the
evidence pack and identity exactly as the app does, calls muse-spark-1.3
once through the investigation path, validates with the same validation the
app uses, and records the answer. Each accepted answer gets one
muse-wonder-1.0 second review through request_live_review. Inputs and
outputs are synthetic only (the care_home_v1 fixtures).

Dry run by default (no model call). Live only with --live AND --max-calls N
AND --code-snapshot HEAD. The key comes only from MODEL_API_KEY and never
appears in output, files or errors.

    python backend/scripts/record_care_answers.py
    python backend/scripts/record_care_answers.py --live --max-calls 20 --code-snapshot <git-HEAD>
"""
import argparse
import json
import os
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from aria_home.investigator import PROMPT_VERSION, inference_identity, build_evidence_pack, investigate  # noqa: E402
from aria_home.provider import ProviderConfig, get_provider  # noqa: E402
from aria_home.public_demo import CHECKPOINTS  # noqa: E402
from aria_home.readiness import READINESS_POLICY_VERSION  # noqa: E402
from aria_home.recorded import recorded_dir  # noqa: E402
from aria_home.review import (  # noqa: E402
    REVIEW_CONTRACT_VERSION,
    REVIEW_MODEL_ID,
    REVIEW_PROVIDER_ROUTE,
    request_live_review,
    reviews_dir,
)
from aria_home.scenario import load_scenario  # noqa: E402

CARE_SCENARIO_ID = "care_home_v1"
ANSWER_MODEL_ID = "muse-spark-1.3"
ANSWER_PROVIDER_ROUTE = "meta live via Meta Model API"
SCENARIOS_DIR = BACKEND_DIR / "scenarios"


class _Capture:
    def __init__(self, inner):
        self._inner = inner
        self.last_text = None

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def generate(self, prompt=None, **kwargs):
        result = self._inner.generate(prompt, **kwargs)
        if isinstance(result, dict):
            self.last_text = result.get("text")
        else:
            self.last_text = getattr(result, "text", None)
        return result


def _env_dict(env):
    return os.environ if env is None else env


def _redact(text, env):
    source = _env_dict(env)
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    secret = get("MODEL_API_KEY")
    if isinstance(secret, str) and secret.strip():
        text = text.replace(secret.strip(), "[redacted]").replace(secret, "[redacted]")
    return text


def _utc_now(now):
    return now if now is not None else datetime.now(timezone.utc)


def _plan(scenario):
    items = []
    for at_str in CHECKPOINTS[CARE_SCENARIO_ID]:
        at = datetime.fromisoformat(at_str)
        pack = build_evidence_pack(scenario, at)
        identity = inference_identity(scenario, at)
        items.append({"at_str": at_str, "at": at, "pack": pack, "identity": identity})
    return items


def _answer_paths(plan, recorded_base, date_str):
    return recorded_base / f"care-{date_str}.json"


def _reviews_path(reviews_base, date_str):
    return reviews_base / f"reviews-care-{date_str}.json"


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


def _rejected_output(text):
    if isinstance(text, str):
        try:
            data = json.loads(text)
        except ValueError:
            return {"raw_text": text[:4000]}
        if isinstance(data, dict):
            return data
    return {"raw_text": "" if text is None else str(text)[:4000]}


def _recorded_at_str(now):
    return _utc_now(now).astimezone(timezone.utc).isoformat()


def main(argv=None, *, provider=None, http_post=None, env=None, out=None, now=None):
    out = out or print
    source_env = _env_dict(env)
    parser = argparse.ArgumentParser(prog="record_care_answers", description="Record approved care-story answers and reviews")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--max-calls", type=int, default=None)
    parser.add_argument("--code-snapshot", default=None)
    parser.add_argument("--date", default=None, help="UTC date override for output file names (YYYY-MM-DD)")
    parser.add_argument("--recorded-dir", default=None)
    parser.add_argument("--reviews-dir", default=None)
    args = parser.parse_args(argv)

    scenario = load_scenario(SCENARIOS_DIR / CARE_SCENARIO_ID)
    plan = _plan(scenario)
    recorded_base = Path(args.recorded_dir) if args.recorded_dir else recorded_dir(source_env)
    reviews_base = Path(args.reviews_dir) if args.reviews_dir else reviews_dir(source_env)
    date_str = args.date or _utc_now(now).astimezone(timezone.utc).date().isoformat()
    answers_path = _answer_paths(plan, recorded_base, date_str)
    reviews_path = _reviews_path(reviews_base, date_str)
    planned_total = 2 * len(plan)

    def emit(text):
        out(_redact(str(text), source_env))

    if not args.live:
        emit(f"{CARE_SCENARIO_ID} checkpoints ({len(plan)}):")
        for item in plan:
            emit(f"- {item['at_str']}")
        emit(f"planned calls: up to {planned_total} ({len(plan)} {ANSWER_MODEL_ID} answers + up to {len(plan)} {REVIEW_MODEL_ID} reviews)")
        emit(f"answers output: {answers_path}")
        emit(f"reviews output: {reviews_path}")
        emit("dry run: no model calls made (use --live --max-calls N --code-snapshot HEAD to record)")
        return 0

    if not isinstance(args.max_calls, int) or isinstance(args.max_calls, bool) or args.max_calls < 1:
        emit("live recording refused: --live requires --max-calls N (positive integer)")
        return 2
    if not args.code_snapshot:
        emit("live recording refused: --live requires --code-snapshot HEAD")
        return 2
    get = source_env.get if hasattr(source_env, "get") else lambda k, d=None: getattr(source_env, k, d)
    if not (isinstance(get("MODEL_API_KEY"), str) and get("MODEL_API_KEY").strip()):
        emit("live recording refused: MODEL_API_KEY is not set")
        return 2
    if provider is None:
        config = replace(ProviderConfig.from_env(source_env), model_id=ANSWER_MODEL_ID)
        missing = config.missing_settings()
        if missing:
            emit(f"live recording refused: provider not configured (missing: {', '.join(missing)})")
            return 2
        provider = get_provider(config)
        if getattr(provider, "mode", None) != "live":
            emit("live recording refused: provider is not live (check ARIA_HOME_MODEL_ENABLED)")
            return 2
    if planned_total > args.max_calls:
        emit(f"live recording refused: planned {planned_total} calls exceed --max-calls {args.max_calls}")
        return 2

    provider = _Capture(provider)
    recorded_stamp = _recorded_at_str(now)
    answers, reviews = [], []
    calls = 0
    skipped_reviews = 0
    for item in plan:
        if calls >= args.max_calls:
            break
        result = investigate(scenario, item["at"], provider=provider)
        calls += 1
        identity = item["identity"]
        if result.status == "ok" and result.output is not None:
            output = result.output.model_dump(mode="json")
            answers.append({
                "scenario_id": CARE_SCENARIO_ID,
                "evaluated_at_utc": identity["evaluated_at_utc"],
                "input_revision": identity["input_revision"],
                "model_id": ANSWER_MODEL_ID,
                "provider_route": ANSWER_PROVIDER_ROUTE,
                "prompt_version": PROMPT_VERSION,
                "readiness_policy_version": READINESS_POLICY_VERSION,
                "code_snapshot": args.code_snapshot,
                "recorded_at": recorded_stamp,
                "status": "accepted",
                "output": output,
            })
            if calls >= args.max_calls:
                skipped_reviews += 1
                continue
            live = request_live_review(output, item["pack"], env=source_env, http_post=http_post)
            calls += 1
            if live.get("ok") and live.get("validation", {}).get("passed") and live.get("review") is not None:
                reviews.append({
                    "scenario_id": CARE_SCENARIO_ID,
                    "evaluated_at_utc": identity["evaluated_at_utc"],
                    "input_revision": identity["input_revision"],
                    "model_id": REVIEW_MODEL_ID,
                    "review_contract_version": REVIEW_CONTRACT_VERSION,
                    "reviewed_model_id": ANSWER_MODEL_ID,
                    "provider_route": REVIEW_PROVIDER_ROUTE,
                    "recorded_at": recorded_stamp,
                    "review": live["review"],
                })
            else:
                reason = live.get("error") or "; ".join(live.get("validation", {}).get("reasons", ()))
                emit(f"review not recorded for {item['at_str']}: {reason or 'unknown'}")
        else:
            answers.append({
                "scenario_id": CARE_SCENARIO_ID,
                "evaluated_at_utc": identity["evaluated_at_utc"],
                "input_revision": identity["input_revision"],
                "model_id": ANSWER_MODEL_ID,
                "provider_route": ANSWER_PROVIDER_ROUTE,
                "prompt_version": PROMPT_VERSION,
                "readiness_policy_version": READINESS_POLICY_VERSION,
                "code_snapshot": args.code_snapshot,
                "recorded_at": recorded_stamp,
                "status": "rejected",
                "rejection_reasons": list(result.reasons),
                "output": _rejected_output(provider.last_text),
            })

    answers_target = _unique_path(answers_path)
    answers_target.parent.mkdir(parents=True, exist_ok=True)
    answers_target.write_text(json.dumps({"answers": answers}, indent=2) + "\n", encoding="utf-8")
    emit(f"wrote {len(answers)} answers to {answers_target}")
    if reviews:
        reviews_target = _unique_path(reviews_path)
        reviews_target.parent.mkdir(parents=True, exist_ok=True)
        reviews_target.write_text(json.dumps({"reviews": reviews}, indent=2) + "\n", encoding="utf-8")
        emit(f"wrote {len(reviews)} reviews to {reviews_target}")
    else:
        emit("wrote 0 reviews (no accepted answer with a passing review)")
    if skipped_reviews:
        emit(f"skipped {skipped_reviews} review(s): call budget exhausted")
    emit(f"model calls made: {calls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
