"""Recorded model answers for public-demo mode.

A recorded answer is shown only for an exact match on scenario id, replay
time, evidence input revision, model id and contract/policy versions. The
recorded output is re-validated against the current evidence pack at serve
time; anything else (including a stale recording for changed evidence)
falls back to the deterministic code summary.

Recorded-answer file format (JSON, under ARIA_HOME_RECORDED_DIR or
backend/eval/recorded/): an object with an "answers" list, a bare list, or
a single answer object. Each answer carries scenario_id, evaluated_at_utc,
input_revision, model_id, provider_route, prompt_version,
readiness_policy_version, code_snapshot, recorded_at and output (an
InvestigationOutput object). backend/eval/results-live-*.json records that
carry a full "output" object are also picked up, with the run timestamp and
code snapshot taken from the file itself, never invented.
"""

import glob
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .investigator import (
    PROMPT_VERSION,
    Investigation,
    InvestigationOutput,
    _deterministic_summary,
    build_evidence_pack,
    inference_identity,
    render_verified_facts,
    validate,
)
from .provider import ALLOWED_MODEL_IDS
from .readiness import READINESS_POLICY_VERSION

RECORDED_DIR_ENV = "ARIA_HOME_RECORDED_DIR"
NO_RECORDED_LABEL = "No recorded model response for this snapshot"
PREFERRED_MODEL_ID = "muse-spark-1.3"


def recorded_dir(env=None):
    source = os.environ if env is None else env
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    raw = get(RECORDED_DIR_ENV)
    if raw:
        return Path(raw).expanduser()
    return Path(__file__).resolve().parent.parent / "eval" / "recorded"


def _norm_time(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _answer_entries(payload, source):
    if isinstance(payload, dict) and isinstance(payload.get("answers"), list):
        items = payload["answers"]
    elif isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("output"), dict):
        items = [payload]
    else:
        return
    for item in items:
        if isinstance(item, dict):
            yield {"answer": item, "source": source}


def load_recorded_answers(directory=None):
    directory = Path(directory) if directory is not None else recorded_dir()
    entries = []
    if directory.is_dir():
        for path in sorted(directory.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            entries.extend(_answer_entries(payload, str(path)))
    entries.extend(_eval_result_entries())
    return entries


def _eval_result_entries():
    entries = []
    for path in sorted(glob.glob(str(Path(__file__).resolve().parent.parent / "eval" / "results-live-*.json"))):
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        for record in payload.get("records") or []:
            if not isinstance(record, dict) or not isinstance(record.get("output"), dict):
                continue
            entries.append(
                {
                    "answer": {
                        "scenario_id": record.get("scenario"),
                        "evaluated_at_utc": record.get("at"),
                        "input_revision": record.get("input_revision"),
                        "model_id": record.get("model_id"),
                        "provider_route": f"{record.get('provider', 'unknown')} ({record.get('provider_mode', 'unknown')})",
                        "prompt_version": record.get("prompt_version"),
                        "readiness_policy_version": record.get("readiness_policy_version"),
                        "code_snapshot": payload.get("snapshot"),
                        "recorded_at": payload.get("date"),
                        "output": record.get("output"),
                    },
                    "source": path,
                }
            )
    return entries


def _entry_matches(entry, scenario_id, evaluated_at_utc, input_revision, prompt_version, readiness_policy_version):
    try:
        entry_at = _norm_time(entry.get("evaluated_at_utc"))
    except (TypeError, ValueError):
        return False
    return (
        entry.get("scenario_id") == scenario_id
        and entry_at == evaluated_at_utc
        and entry.get("input_revision") == input_revision
        and entry.get("model_id") in ALLOWED_MODEL_IDS
        and entry.get("prompt_version") == prompt_version
        and entry.get("readiness_policy_version") == readiness_policy_version
    )


def find_recorded(entries, scenario_id, evaluated_at_utc, input_revision, prompt_version=PROMPT_VERSION, readiness_policy_version=READINESS_POLICY_VERSION):
    try:
        wanted_at = _norm_time(evaluated_at_utc)
    except (TypeError, ValueError):
        return None
    matches = [
        item for item in entries
        if isinstance(item.get("answer"), dict)
        and _entry_matches(item["answer"], scenario_id, wanted_at, input_revision, prompt_version, readiness_policy_version)
    ]
    if not matches:
        return None
    matches.sort(key=lambda item: (item["answer"].get("model_id") != PREFERRED_MODEL_ID, str(item["answer"].get("model_id"))))
    return matches[0]


def provenance_for(entry, validation_reasons):
    answer = entry["answer"]
    return {
        "model_id": answer.get("model_id"),
        "provider_route": answer.get("provider_route") or answer.get("provider") or "unknown",
        "recorded_at": answer.get("recorded_at"),
        "input_revision": answer.get("input_revision"),
        "code_snapshot": answer.get("code_snapshot"),
        "prompt_version": answer.get("prompt_version"),
        "readiness_policy_version": answer.get("readiness_policy_version"),
        "validation": {"passed": not validation_reasons, "reasons": list(validation_reasons)},
    }


def public_investigation(scenario, at, entries=None):
    pack = build_evidence_pack(scenario, at)
    identity = inference_identity(scenario, at)
    summary = _deterministic_summary(pack)
    if entries is None:
        entries = load_recorded_answers()
    match = find_recorded(
        entries,
        scenario.manifest.id,
        identity["evaluated_at_utc"],
        identity["input_revision"],
    )
    if match is None:
        return _fallback(summary, pack), None
    reasons = validate(match["answer"].get("output"), pack)
    provenance = provenance_for(match, reasons)
    if reasons:
        return _fallback(summary, pack), None
    output = InvestigationOutput.model_validate(match["answer"]["output"])
    output = output.model_copy(update={"verified_facts": render_verified_facts(output, pack)})
    return (
        Investigation(
            status="ok",
            output=output,
            model_id=match["answer"].get("model_id"),
            prompt_version=PROMPT_VERSION,
            provider_mode="recorded",
            summary=summary,
            evidence_pack=pack,
        ),
        provenance,
    )


def annotate_public_result(scenario, at, result, entries=None):
    if result is None or result.status != "ok" or result.output is None:
        return None
    pack = result.evidence_pack if isinstance(result.evidence_pack, dict) and result.evidence_pack else build_evidence_pack(scenario, at)
    identity = inference_identity(scenario, at)
    if entries is None:
        entries = load_recorded_answers()
    match = find_recorded(
        entries,
        scenario.manifest.id,
        identity["evaluated_at_utc"],
        identity["input_revision"],
    )
    if match is None:
        return None
    return provenance_for(match, validate(match["answer"].get("output"), pack))


def _fallback(summary, pack):
    return Investigation(
        status="unavailable",
        reasons=[NO_RECORDED_LABEL],
        prompt_version=PROMPT_VERSION,
        summary=summary,
        evidence_pack=pack,
    )


__all__ = [
    "NO_RECORDED_LABEL",
    "annotate_public_result",
    "find_recorded",
    "load_recorded_answers",
    "provenance_for",
    "public_investigation",
    "recorded_dir",
]
