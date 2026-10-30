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
    answer_digest,
    request_live_review,
    reviews_dir,
)
from aria_home.scenario import load_scenario  # noqa: E402

CARE_SCENARIO_ID = "care_home_v1"
ANSWER_MODEL_ID = "muse-spark-1.3"
ANSWER_PROVIDER_ROUTE = "meta live via Meta Model API"
SCENARIOS_DIR = BACKEND_DIR / "scenarios"
RECORDING_TIMEOUT_S = 180.0


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


def _norm_time(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _answer_items(payload):
    if isinstance(payload, dict) and isinstance(payload.get("answers"), list):
        return payload["answers"]
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("output"), dict):
        return [payload]
    return []


def _review_items(payload):
    if isinstance(payload, dict) and isinstance(payload.get("reviews"), list):
        return payload["reviews"]
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("review"), dict):
        return [payload]
    return []


def _load_existing_answers(recorded_base):
    answers = []
    base = Path(recorded_base)
    if base.is_dir():
        for path in sorted(base.glob("care-*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            for item in _answer_items(payload):
                if isinstance(item, dict):
                    answers.append(item)
    return answers


def _load_existing_reviews(reviews_base):
    reviews = []
    base = Path(reviews_base)
    if base.is_dir():
        for path in sorted(base.glob("reviews-*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            for item in _review_items(payload):
                if isinstance(item, dict):
                    reviews.append(item)
    return reviews


def _key_of(entry):
    try:
        at = _norm_time(entry.get("evaluated_at_utc"))
    except (TypeError, ValueError, AttributeError):
        return None
    return (entry.get("scenario_id"), at, entry.get("input_revision"))


def _missing_plan(plan, recorded_base, reviews_base):
    existing = _load_existing_answers(recorded_base)
    accepted = {}
    for answer in existing:
        if answer.get("status") != "accepted":
            continue
        key = _key_of(answer)
        if key is not None and key not in accepted:
            accepted[key] = answer
    reviewed = set()
    for review in _load_existing_reviews(reviews_base):
        if not review.get("answer_digest"):
            continue
        key = _key_of(review)
        if key is not None:
            reviewed.add(key)
    flags = []
    for item in plan:
        key = (CARE_SCENARIO_ID, _norm_time(item["identity"]["evaluated_at_utc"]), item["identity"]["input_revision"])
        has_answer = key in accepted
        has_review = key in reviewed
        if has_answer and has_review:
            flags.append({"item": item, "key": key, "need_answer": False, "need_review": False, "prior": accepted[key]})
        elif has_answer:
            flags.append({"item": item, "key": key, "need_answer": False, "need_review": True, "prior": accepted[key]})
        else:
            flags.append({"item": item, "key": key, "need_answer": True, "need_review": True, "prior": None})
    return flags


def _apply_recording_timeout(inner, timeout_s):
    try:
        inner.timeout_s = timeout_s
    except (AttributeError, TypeError):
        pass
    config = getattr(inner, "config", None)
    if config is not None and hasattr(config, "timeout_s"):
        try:
            object.__setattr__(config, "timeout_s", timeout_s)
        except (AttributeError, TypeError):
            pass
    return inner


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
    parser.add_argument("--timeout-s", type=float, default=RECORDING_TIMEOUT_S)
    parser.add_argument("--only-missing", action="store_true")
    args = parser.parse_args(argv)

    scenario = load_scenario(SCENARIOS_DIR / CARE_SCENARIO_ID)
    plan = _plan(scenario)
    recorded_base = Path(args.recorded_dir) if args.recorded_dir else recorded_dir(source_env)
    reviews_base = Path(args.reviews_dir) if args.reviews_dir else reviews_dir(source_env)
    date_str = args.date or _utc_now(now).astimezone(timezone.utc).date().isoformat()
    answers_path = _answer_paths(plan, recorded_base, date_str)
    reviews_path = _reviews_path(reviews_base, date_str)
    if args.only_missing:
        flags = _missing_plan(plan, recorded_base, reviews_base)
        need_answers = sum(1 for f in flags if f["need_answer"])
        need_reviews = sum(1 for f in flags if f["need_review"])
        skipped = sum(1 for f in flags if not f["need_answer"] and not f["need_review"])
        planned_total = need_answers + need_reviews
    else:
        flags = None
        need_answers = len(plan)
        need_reviews = len(plan)
        skipped = 0
        planned_total = 2 * len(plan)

    def emit(text):
        out(_redact(str(text), source_env))

    if not args.live:
        emit(f"{CARE_SCENARIO_ID} checkpoints ({len(plan)}):")
        for item in plan:
            emit(f"- {item['at_str']}")
        emit(f"planned calls: up to {planned_total} ({need_answers} {ANSWER_MODEL_ID} answers + up to {need_reviews} {REVIEW_MODEL_ID} reviews)")
        if args.only_missing:
            emit(f"only-missing: skipped {skipped} recorded answer(s); {need_answers} answer(s) and {need_reviews} review(s) still needed")
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
        config = replace(ProviderConfig.from_env(source_env), model_id=ANSWER_MODEL_ID, timeout_s=args.timeout_s)
        missing = config.missing_settings()
        if missing:
            emit(f"live recording refused: provider not configured (missing: {', '.join(missing)})")
            return 2
        provider = get_provider(config)
        if getattr(provider, "mode", None) != "live":
            emit("live recording refused: provider is not live (check ARIA_HOME_MODEL_ENABLED)")
            return 2
    else:
        _apply_recording_timeout(provider, args.timeout_s)
    if planned_total > args.max_calls:
        emit(f"live recording refused: planned {planned_total} calls exceed --max-calls {args.max_calls}")
        return 2

    provider = _Capture(provider)
    _apply_recording_timeout(provider, args.timeout_s)
    recorded_stamp = _recorded_at_str(now)
    answers, reviews = [], []
    calls = 0
    skipped_reviews = 0

    def _record_review(item, output):
        live = request_live_review(output, item["pack"], env=source_env, http_post=http_post, timeout_s=args.timeout_s)
        if live.get("ok") and live.get("validation", {}).get("passed") and live.get("review") is not None:
            reviews.append({
                "scenario_id": CARE_SCENARIO_ID,
                "evaluated_at_utc": item["identity"]["evaluated_at_utc"],
                "input_revision": item["identity"]["input_revision"],
                "model_id": REVIEW_MODEL_ID,
                "review_contract_version": REVIEW_CONTRACT_VERSION,
                "reviewed_model_id": ANSWER_MODEL_ID,
                "reviewed_prompt_version": PROMPT_VERSION,
                "reviewed_readiness_policy_version": READINESS_POLICY_VERSION,
                "answer_digest": answer_digest(output),
                "provider_route": REVIEW_PROVIDER_ROUTE,
                "recorded_at": recorded_stamp,
                "review": live["review"],
            })
        else:
            reason = live.get("error") or "; ".join(live.get("validation", {}).get("reasons", ()))
            emit(f"review not recorded for {item['at_str']}: {reason or 'unknown'} (status={live.get('status')}, detail={live.get('detail', '')})")

    def _handle_answer(item, result):
        nonlocal calls, skipped_reviews
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
                return
            _record_review(item, output)
            calls += 1
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

    if flags is not None:
        for flag in flags:
            item = flag["item"]
            if not flag["need_answer"]:
                if not flag["need_review"]:
                    continue
                if calls >= args.max_calls:
                    skipped_reviews += 1
                    continue
                _record_review(item, flag["prior"].get("output"))
                calls += 1
                continue
            if calls >= args.max_calls:
                break
            _handle_answer(item, investigate(scenario, item["at"], provider=provider))
    else:
        for item in plan:
            if calls >= args.max_calls:
                break
            _handle_answer(item, investigate(scenario, item["at"], provider=provider))

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
