"""Record the approved care-story anomaly-watcher batch (operator-only).

For 8 care_home_v1 checkpoints (19:20 as a quiet control, then 02:31,
02:45, 04:21, 04:51, 06:21, 06:45 and 07:01), this runs the watcher through
run_watcher exactly as the app does (one-revision correction loop, code
verification, laws named on rejection) and records each run. Verified
corrections are saved through save_correction_record. Inputs and outputs
are synthetic only (the care_home_v1 fixtures).

Dry run by default (no model call). Live only with --live AND --max-calls
N AND --code-snapshot SHA. The key comes only from MODEL_API_KEY and never
appears in output, files or errors.

    python backend/scripts/record_care_watcher.py
    python backend/scripts/record_care_watcher.py --live --max-calls 16 --code-snapshot <git-HEAD>
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from aria_home.provider import ALLOWED_MODEL_IDS  # noqa: E402
from aria_home.public_demo import CHECKPOINTS  # noqa: E402
from aria_home.review import reviews_dir  # noqa: E402
from aria_home.scenario import load_scenario  # noqa: E402
from aria_home.watcher import (  # noqa: E402
    WATCHER_MODEL_ID,
    WATCHER_PROMPT_VERSION,
    corrections_dir,
    find_all_recorded_watchers,
    is_provider_error_rejection,
    is_unreadable_rejection,
    load_correction_records,
    load_recorded_watchers,
    newest_recorded_watcher,
    request_live_watcher,
    run_watcher,
    save_correction_record,
    watcher_identity,
)

CARE_SCENARIO_ID = "care_home_v1"
WATCHER_LABELS = ("19:20", "02:31", "02:45", "04:21", "04:51", "06:21", "06:45", "07:01")
WATCHER_PROVIDER_ROUTE = "meta live via Meta Model API (messages)"
SCENARIOS_DIR = BACKEND_DIR / "scenarios"
RECORDING_TIMEOUT_S = 180.0
RECORDING_MAX_TOKENS = 4096


class _Capture:
    def __init__(self, inner):
        self._inner = inner
        self.calls = 0

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def __setattr__(self, name, value):
        if name in ("_inner", "calls"):
            object.__setattr__(self, name, value)
        else:
            try:
                setattr(self._inner, name, value)
            except (AttributeError, TypeError):
                pass
            try:
                object.__setattr__(self, name, value)
            except (AttributeError, TypeError):
                pass

    def generate(self, prompt=None, **kwargs):
        self.calls += 1
        return self._inner.generate(prompt, **kwargs)


class _LiveWatcherProvider:
    mode = "live"
    model_id = WATCHER_MODEL_ID

    def __init__(self, env, timeout_s, max_tokens):
        self._env = env
        self.timeout_s = timeout_s
        self.max_tokens = max_tokens
        self.calls = 0

    def generate(self, prompt=None, **kwargs):
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
            "requested_model": WATCHER_MODEL_ID,
            "answered_model": live.get("model") or WATCHER_MODEL_ID,
            "mode": "live",
        }


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


def _wanted(at_str):
    return any(f"T{label}:" in at_str for label in WATCHER_LABELS)


def _plan(scenario):
    items = []
    for at_str in CHECKPOINTS[CARE_SCENARIO_ID]:
        if not _wanted(at_str):
            continue
        at = datetime.fromisoformat(at_str)
        items.append({"at_str": at_str, "at": at, "identity": watcher_identity(scenario, at)})
    return items


def _watchers_path(watchers_base, date_str):
    return Path(watchers_base) / f"watchers-care-{date_str}.json"


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


def _recorded_at_str(now):
    return _utc_now(now).astimezone(timezone.utc).isoformat()


def _apply_recording_settings(provider, timeout_s, max_tokens):
    for name, value in (("timeout_s", timeout_s), ("max_tokens", max_tokens)):
        try:
            setattr(provider, name, value)
        except (AttributeError, TypeError):
            pass
    config = getattr(provider, "config", None)
    if config is not None:
        for name, value in (("timeout_s", timeout_s), ("max_tokens", max_tokens)):
            if hasattr(config, name):
                try:
                    object.__setattr__(config, name, value)
                except (AttributeError, TypeError):
                    pass
    return provider


def _missing_plan(plan, watchers_base):
    entries = load_recorded_watchers(watchers_base)
    needed, skipped = [], 0
    for item in plan:
        identity = item["identity"]
        matches = find_all_recorded_watchers(
            entries,
            CARE_SCENARIO_ID,
            identity["evaluated_at_utc"],
            identity["input_revision"],
            identity["laws_version"],
        )
        newest = newest_recorded_watcher(matches)
        if newest is None or is_unreadable_rejection(newest["entry"]) or is_provider_error_rejection(newest["entry"]):
            needed.append(item)
        else:
            skipped += 1
    return needed, skipped


def _entry_for(item, result, code_snapshot, recorded_stamp):
    identity = item["identity"]
    final = result.get("final_result")
    verified = result.get("observations") or []
    if final in ("confirmed", "corrected and verified"):
        output = {"observations": [
            {k: obs[k] for k in ("kind", "claim", "evidence_ids", "values") if k in obs}
            for obs in verified
        ]}
    else:
        record = result.get("correction_record") or {}
        revision = record.get("revision_claim")
        original = record.get("original_claim")
        if isinstance(revision, list):
            output = {"observations": revision}
        elif isinstance(original, list):
            output = {"observations": original}
        else:
            output = {"raw_text": "watcher returned no parseable JSON"}
    mode = result.get("provider_mode")
    return {
        "scenario_id": CARE_SCENARIO_ID,
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "input_revision": identity["input_revision"],
        "laws_version": identity["laws_version"],
        "watcher_prompt_version": WATCHER_PROMPT_VERSION,
        "model_id": result.get("model_id") or WATCHER_MODEL_ID,
        "provider_route": WATCHER_PROVIDER_ROUTE if mode == "live" else "mock",
        "code_snapshot": code_snapshot,
        "recorded_at": recorded_stamp,
        "status": final,
        "final_result": final,
        "failed_checks": list(result.get("failed_checks") or []),
        "output": output,
    }


def main(argv=None, *, provider=None, env=None, out=None, now=None):
    out = out or print
    source_env = _env_dict(env)
    parser = argparse.ArgumentParser(prog="record_care_watcher", description="Record approved care-story watcher runs")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--max-calls", type=int, default=None)
    parser.add_argument("--code-snapshot", default=None)
    parser.add_argument("--date", default=None, help="UTC date override for output file names (YYYY-MM-DD)")
    parser.add_argument("--watchers-dir", default=None)
    parser.add_argument("--corrections-dir", default=None)
    parser.add_argument("--timeout-s", type=float, default=RECORDING_TIMEOUT_S)
    parser.add_argument("--max-tokens", type=int, default=RECORDING_MAX_TOKENS)
    parser.add_argument("--only-missing", action="store_true")
    args = parser.parse_args(argv)

    scenario = load_scenario(SCENARIOS_DIR / CARE_SCENARIO_ID)
    plan = _plan(scenario)
    watchers_base = Path(args.watchers_dir) if args.watchers_dir else reviews_dir(source_env)
    corrections_base = Path(args.corrections_dir) if args.corrections_dir else corrections_dir(source_env)
    date_str = args.date or _utc_now(now).astimezone(timezone.utc).date().isoformat()
    target_path = _watchers_path(watchers_base, date_str)
    if args.only_missing:
        needed, skipped = _missing_plan(plan, watchers_base)
        planned_total = 2 * len(needed)
    else:
        needed, skipped = list(plan), 0
        planned_total = 2 * len(plan)

    def emit(text):
        out(_redact(str(text), source_env))

    if not args.live:
        emit(f"{CARE_SCENARIO_ID} watcher checkpoints ({len(plan)}):")
        for item in plan:
            emit(f"- {item['at_str']}")
        emit(f"planned calls: up to {planned_total} ({len(needed)} first + up to {len(needed)} revisions)")
        if args.only_missing:
            emit(f"only-missing: skipped {skipped} recorded watcher(s); {len(needed)} checkpoint(s) still needed")
        emit(f"watchers output: {target_path}")
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
        if get("ARIA_HOME_MODEL_ENABLED") != "1":
            emit("live recording refused: provider is not live (check ARIA_HOME_MODEL_ENABLED)")
            return 2
        for var in ("ARIA_HOME_PROVIDER_URL", "ARIA_HOME_MODEL_ID"):
            value = get(var)
            if not (isinstance(value, str) and value.strip()):
                emit(f"live recording refused: provider not configured (missing: {var})")
                return 2
        if get("ARIA_HOME_MODEL_ID").strip() not in ALLOWED_MODEL_IDS:
            emit("live recording refused: model_mismatch")
            return 2
        provider = _LiveWatcherProvider(source_env, args.timeout_s, args.max_tokens)
    else:
        _apply_recording_settings(provider, args.timeout_s, args.max_tokens)
    if planned_total > args.max_calls:
        emit(f"live recording refused: planned {planned_total} calls exceed --max-calls {args.max_calls}")
        return 2

    provider = _Capture(provider)
    _apply_recording_settings(provider, args.timeout_s, args.max_tokens)
    recorded_stamp = _recorded_at_str(now)
    corrections = load_correction_records(corrections_base)
    entries = []
    saved_corrections = 0

    for item in needed:
        if provider.calls >= args.max_calls:
            break
        result = run_watcher(scenario, item["at"], provider, corrections=corrections)
        record = result.get("correction_record")
        if record is not None and result.get("final_result") == "corrected and verified":
            try:
                save_correction_record(record, directory=corrections_base)
                saved_corrections += 1
            except OSError as exc:
                emit(f"correction not saved for {item['at_str']}: {exc}")
            corrections = [*corrections, record]
        entries.append(_entry_for(item, result, args.code_snapshot, recorded_stamp))

    target = _unique_path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"watchers": entries}, indent=2) + "\n", encoding="utf-8")
    emit(f"wrote {len(entries)} watchers to {target}")
    if saved_corrections:
        emit(f"saved {saved_corrections} correction(s) to {corrections_base}")
    emit(f"model calls made: {provider.calls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
