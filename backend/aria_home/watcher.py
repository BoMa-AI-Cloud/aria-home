"""Anomaly watcher: a model pass over an as-of evidence window, checked by code.

The watcher gets no question about any specific problem. It returns JSON:
{"observations": [{"kind", "claim", "evidence_ids", "values"}]} or an empty
list. Code verifies each observation against the evidence (ids exist and are
visible as of the time, values match the readings within tolerance, window
and freshness hold, no conflict) and against all active laws. Verified
observations are labelled "noticed by the model, confirmed by the evidence
check" and may raise the caregiver notice. The code's own detection rules
run independently and still raise the notice if the model misses. An empty
or failed watcher result never lowers risk.

Correction loop: a rejected observation batch gets exactly one revision call
carrying the specific failed checks. The revision is re-verified the same
way; pass means "corrected and verified", fail means rejected for good.
Every rejection and correction is written to a correction record
(backend/eval/corrections-*.json shape).

The watcher prompt includes the active laws and up to five recent verified
corrections as examples. That is prompt-level (in-context) improvement: the
examples steer this call only; the model itself is not retrained.

The live call (request_live_watcher) is operator-only: it is never called
from a route, a GET handler, or public-demo mode. Recorded watcher runs
replay with provenance (model, provider route, recorded timestamp from the
file, input revision, laws version).
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from . import laws as laws_module
from .investigator import build_evidence_pack, inference_identity
from .provider import ALLOWED_MODEL_IDS, build_request

WATCHER_PROMPT_VERSION = "watch-v1"
WATCHER_MODEL_ID = "muse-spark-1.3"
WATCHER_BASE_URL = "https://api.meta.ai"
WATCHER_MAX_TOKENS = 512
WATCHER_TIMEOUT_S = 20.0

WATCHER_KINDS = ("temperature_drop", "telemetry_gap", "equipment_quiet", "visual_detection", "other")
MAX_CLAIM_CHARS = 200
VALUE_TOLERANCE = 0.15
WINDOW_HOURS = 3
MAX_LEDGER_EXAMPLES = 5
CORRECTIONS_GLOB = "corrections-*.json"
NO_RECORDED_WATCHER_LABEL = "No recorded watcher run for this snapshot"

WATCHER_SYSTEM_PROMPT = """You are the ARIA Home anomaly watcher (prompt version watch-v1).
You receive an as-of window of all visible evidence for one home (room, thermostat, circuits, weather, visual).
No question is being asked about any specific problem: report only what looks anomalous, or nothing.
Reply with JSON only, matching this schema exactly (no extra fields):
{"observations": [{"kind": "temperature_drop" | "telemetry_gap" | "equipment_quiet" | "visual_detection" | "other", "claim": "<= 200 characters", "evidence_ids": ["<ids from the pack only>"], "values": {"value": number | str | bool, "unit": str | null, "at": ISO-8601 datetime str | null}}]}.
An empty list is an acceptable answer when nothing looks anomalous. Cite only evidence ids from the pack.
Copy values from the cited readings; do not invent numbers. Do not state an all-clear and do not claim safety.
The examples below are prompt-level context only; the model itself is not retrained."""


def corrections_dir(env=None):
    source = os.environ if env is None else env
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    raw = get("ARIA_HOME_CORRECTIONS_DIR")
    if raw:
        return Path(raw).expanduser()
    return Path(__file__).resolve().parent.parent / "eval"


def watcher_identity(scenario, at):
    identity = inference_identity(scenario, at)
    return {
        "scenario_id": identity["scenario_id"],
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "input_revision": identity["input_revision"],
        "watcher_prompt_version": WATCHER_PROMPT_VERSION,
        "laws_version": laws_module.load_laws()["version"],
    }


def load_correction_records(directory=None):
    directory = Path(directory) if directory is not None else corrections_dir()
    records = []
    if directory.is_dir():
        for path in sorted(directory.glob(CORRECTIONS_GLOB)):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(payload, dict) and isinstance(payload.get("records"), list):
                records.extend(r for r in payload["records"] if isinstance(r, dict))
            elif isinstance(payload, dict):
                records.append(payload)
    return records


def save_correction_record(record, directory=None):
    directory = Path(directory) if directory is not None else corrections_dir()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"corrections-{stamp}.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def build_watcher_prompt(pack, registry=None, corrections=()):
    registry = registry if registry is not None else laws_module.load_laws()
    lines = [WATCHER_SYSTEM_PROMPT, "", "Active laws (code-enforced; a violating observation is rejected):"]
    for law in laws_module.active_model_laws(registry):
        lines.append(f"- {law['id']}: {law.get('statement')}")
    verified = [c for c in corrections if isinstance(c, dict) and c.get("final_result") in ("confirmed", "corrected and verified")]
    verified = verified[-MAX_LEDGER_EXAMPLES:]
    if verified:
        lines += ["", "Recent verified corrections (in-context examples only; the model itself is not retrained):"]
        for item in verified:
            lines.append(
                f"- rejected claim: {item.get('original_claim')}; failed checks: {item.get('failed_checks')}; "
                f"accepted revision: {item.get('revision_claim')}"
            )
    lines += ["", "Evidence pack (JSON):", json.dumps(pack, default=str)]
    return "\n".join(lines)


def build_revision_prompt(original_text, failed_checks, pack):
    lines = [
        "Your previous watcher answer was rejected. Revise it once: fix every failed check below, keep the same JSON schema, and cite only evidence ids from the pack.",
        "",
        "Failed checks:",
    ]
    for check in failed_checks:
        lines.append(f"- {check}")
    lines += ["", "Your rejected answer:", original_text, "", "Evidence pack (JSON):", json.dumps(pack, default=str)]
    return "\n".join(lines)


def parse_watcher_output(data):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError as exc:
            return None, [f"invalid JSON: {exc}"]
    if not isinstance(data, dict):
        return None, ["watcher output must be a JSON object"]
    observations = data.get("observations")
    if not isinstance(observations, list):
        return None, ["watcher observations must be a list"]
    reasons = []
    normalized = []
    for index, obs in enumerate(observations):
        where = f"observation {index}"
        if not isinstance(obs, dict):
            reasons.append(f"{where} must be an object")
            continue
        kind = obs.get("kind")
        if kind not in WATCHER_KINDS:
            reasons.append(f"{where} has unknown kind: {kind!r}")
            continue
        claim = obs.get("claim")
        if not isinstance(claim, str) or not claim.strip():
            reasons.append(f"{where} claim must be a non-empty string")
            continue
        if len(claim) > MAX_CLAIM_CHARS:
            reasons.append(f"{where} claim is {len(claim)} characters (max {MAX_CLAIM_CHARS})")
            continue
        ids = obs.get("evidence_ids")
        if not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids):
            reasons.append(f"{where} evidence_ids must be a non-empty list of strings")
            continue
        values = obs.get("values")
        if not isinstance(values, dict):
            reasons.append(f"{where} values must be an object")
            continue
        normalized.append({"kind": kind, "claim": claim, "evidence_ids": list(ids), "values": dict(values)})
    if reasons:
        return None, reasons
    return {"observations": normalized}, []


def _evidence_by_id(pack):
    items = {}
    for item in pack.get("evidence", []) or []:
        if isinstance(item, dict) and item.get("id"):
            items[item["id"]] = item
    return items


def _numbers_match(given, expected):
    if isinstance(expected, bool) or isinstance(given, bool):
        return given is expected
    if isinstance(expected, (int, float)) and isinstance(given, (int, float)):
        return abs(float(given) - float(expected)) <= VALUE_TOLERANCE
    return given == expected


def _metric_numbers(item):
    data = item.get("data")
    if not isinstance(data, dict):
        return []
    return [v for v in data.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]


def _conflicted_ids(pack, at):
    try:
        from .eligibility import unresolved_conflict_groups
    except Exception:
        return set()
    evidence = [e for e in pack.get("evidence", []) if isinstance(e, dict) and "data" not in e]
    out = set()
    for quantity in ("indoor_temp", "circuit_power"):
        try:
            groups = unresolved_conflict_groups(evidence, quantity, at)
        except Exception:
            continue
        for group in groups:
            out.update(group["ids"])
    return out


def verify_observation(obs, pack, at):
    from .eligibility import freshness_limit_s, is_fresh

    reasons = []
    by_id = _evidence_by_id(pack)
    window_start = at - timedelta(hours=WINDOW_HOURS)
    for evidence_id in obs["evidence_ids"]:
        item = by_id.get(evidence_id)
        if item is None:
            reasons.append(f"unknown evidence id: {evidence_id}")
            continue
        received = laws_module._parse_time(item.get("received_at") or (item.get("data") or {}).get("received_at") if isinstance(item.get("data"), dict) else item.get("received_at"))
        if received is not None and received > at:
            reasons.append(f"evidence {evidence_id} is not visible as of the evaluation time")
            continue
        values = obs["values"]
        if "data" not in item:
            observed = laws_module._parse_time(item.get("observed_at"))
            if observed is not None and (observed < window_start or observed > at):
                reasons.append(f"evidence {evidence_id} is outside the {WINDOW_HOURS}-hour as-of window")
            if not is_fresh(item, at):
                reasons.append(f"evidence {evidence_id} is not fresh at the evaluation time (historical only)")
            if "value" in values and not _numbers_match(values["value"], item.get("value")):
                reasons.append(f"observation value does not match evidence {evidence_id}: {values['value']!r} != {item.get('value')!r} (tolerance {VALUE_TOLERANCE})")
            if "unit" in values and values["unit"] is not None and values["unit"] != item.get("unit"):
                reasons.append(f"observation unit does not match evidence {evidence_id}")
            if "at" in values and values["at"] is not None:
                given_at = laws_module._parse_time(values["at"])
                if given_at != observed:
                    reasons.append(f"observation time does not match evidence {evidence_id}")
        else:
            data = item.get("data") or {}
            last_at = laws_module._parse_time(data.get("last_observed_at") or data.get("latest_observed_at"))
            if last_at is not None and (last_at < window_start or last_at > at):
                reasons.append(f"evidence {evidence_id} is outside the {WINDOW_HOURS}-hour as-of window")
            pseudo = {"value": 1, "observed_at": (last_at or at).isoformat(), "expected_cadence_s": data.get("expected_cadence_s")}
            if last_at is None or not is_fresh(pseudo, at):
                reasons.append(f"evidence {evidence_id} is not fresh at the evaluation time (historical only)")
            if "value" in values and isinstance(values["value"], (int, float)) and not isinstance(values["value"], bool):
                if not any(_numbers_match(values["value"], candidate) for candidate in _metric_numbers(item)):
                    reasons.append(f"observation value does not match evidence {evidence_id} (tolerance {VALUE_TOLERANCE})")
    conflicted = _conflicted_ids(pack, at)
    clashing = [i for i in obs["evidence_ids"] if i in conflicted]
    if clashing:
        reasons.append(f"observation cites contradictory readings {sorted(clashing)}: unresolved conflicts block the claim")
    return reasons


def verify_watcher_output(parsed, pack, at, registry=None):
    reasons = []
    for obs in parsed.get("observations", []):
        reasons.extend(verify_observation(obs, pack, at))
    for violation in laws_module.check_output(parsed, pack, at, registry):
        reasons.append(f"law {violation['law']}: {violation['reason']}")
    return reasons


def _generate_text(provider, prompt):
    result = provider.generate(prompt, max_tokens=WATCHER_MAX_TOKENS)
    if isinstance(result, dict):
        text = result.get("text")
        model_id = result.get("answered_model") or result.get("requested_model")
        mode = result.get("mode")
    else:
        text = getattr(result, "text", None)
        model_id = getattr(result, "answered_model", None) or getattr(result, "requested_model", None)
        mode = getattr(result, "mode", None)
    return text, model_id or WATCHER_MODEL_ID, mode or "mock"


def _availability_of(pack, source):
    for status in pack.get("source_statuses", []) or []:
        if isinstance(status, dict) and status.get("source") == source:
            return status.get("availability")
    return None


def code_detections(scenario, at, pack=None):
    pack = pack if pack is not None else build_evidence_pack(scenario, at)
    detections = []
    readiness = pack.get("readiness") if isinstance(pack.get("readiness"), dict) else {}
    if _availability_of(pack, "thermostat") not in (None, "available"):
        detections.append({"rule": "telemetry_gap", "detail": "thermostat telemetry is missing or stale; independent readings decide"})
    if readiness.get("status") == "at_risk":
        detections.append({"rule": "readiness_at_risk", "detail": "deterministic readiness is at_risk at this time"})
    circuits = (pack.get("metrics") or {}).get("circuits") or {}
    if readiness.get("status") == "at_risk" and any(isinstance(c, dict) and c.get("active") is False for c in circuits.values()):
        detections.append({"rule": "equipment_quiet", "detail": "a heating circuit shows no activity while readiness is at_risk"})
    return detections


def run_watcher(scenario, at, provider, corrections=(), registry=None):
    pack = build_evidence_pack(scenario, at)
    identity = watcher_identity(scenario, at)
    prompt = build_watcher_prompt(pack, registry, corrections)
    first_text, model_id, mode = _generate_text(provider, prompt)
    parsed, reasons = parse_watcher_output(first_text or "")
    failed_checks = list(reasons)
    if parsed is not None:
        failed_checks.extend(verify_watcher_output(parsed, pack, at, registry))
    revision_claim, final_result, verified = None, "rejected", []
    if not failed_checks and parsed is not None:
        final_result, verified = "confirmed", parsed["observations"]
        revision_text = None
    else:
        revision_prompt = build_revision_prompt(first_text or "", failed_checks, pack)
        revision_text, model_id, mode = _generate_text(provider, revision_prompt)
        revised, revision_reasons = parse_watcher_output(revision_text or "")
        revision_checks = list(revision_reasons)
        if revised is not None:
            revision_checks.extend(verify_watcher_output(revised, pack, at, registry))
        revision_claim = (revised or {}).get("observations")
        if not revision_checks and revised is not None:
            final_result, verified = "corrected and verified", revised["observations"]
        else:
            failed_checks = revision_checks
    record = None
    if failed_checks or final_result == "corrected and verified":
        original = (parsed or {}).get("observations")
        record = {
            "scenario_id": identity["scenario_id"],
            "evaluated_at_utc": identity["evaluated_at_utc"],
            "input_revision": identity["input_revision"],
            "laws_version": identity["laws_version"],
            "watcher_prompt_version": WATCHER_PROMPT_VERSION,
            "model_id": model_id,
            "provider_route": f"meta live via Meta Model API (messages)" if mode == "live" else "mock",
            "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "original_claim": original,
            "failed_checks": failed_checks if final_result == "rejected" else (list(reasons) + (verify_watcher_output(parsed, pack, at, registry) if parsed is not None else [])),
            "revision_claim": revision_claim,
            "final_result": final_result,
        }
    detections = code_detections(scenario, at, pack)
    model_triggered = bool(verified)
    code_triggered = bool(detections)
    return {
        "scenario_id": identity["scenario_id"],
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "input_revision": identity["input_revision"],
        "laws_version": identity["laws_version"],
        "model_id": model_id,
        "provider_mode": mode,
        "observations": [
            {**obs, "status": final_result, "notice": "noticed by the model, confirmed by the evidence check"}
            for obs in verified
        ],
        "failed_checks": failed_checks,
        "final_result": final_result,
        "correction_record": record,
        "code_detections": detections,
        "model_triggered": model_triggered,
        "code_triggered": code_triggered,
        "raise_caregiver_notice": model_triggered or code_triggered,
        "lowers_risk": False,
    }


def request_live_watcher(prompt, *, env=None, max_tokens=WATCHER_MAX_TOKENS, timeout_s=WATCHER_TIMEOUT_S):
    """Operator-only live watcher call. Never called from routes or public-demo code."""
    source = os.environ if env is None else env
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    if get("ARIA_HOME_MODEL_ENABLED") != "1":
        return {"ok": False, "error": "disabled", "text": None}
    api_key = get("MODEL_API_KEY")
    if isinstance(api_key, str):
        api_key = api_key.strip() or None
    base_url = get("ARIA_HOME_PROVIDER_URL")
    if isinstance(base_url, str):
        base_url = base_url.strip() or None
    model_id = get("ARIA_HOME_MODEL_ID")
    if isinstance(model_id, str):
        model_id = model_id.strip() or None
    if not api_key or not base_url or not model_id:
        return {"ok": False, "error": "not_configured", "text": None}
    if model_id not in ALLOWED_MODEL_IDS:
        return {"ok": False, "error": "model_mismatch", "text": None}
    from .provider import ProviderConfig

    request = build_request(
        ProviderConfig(provider_url=base_url, model_id=model_id, api_key=api_key, enabled=True, timeout_s=timeout_s, max_tokens=max_tokens),
        [{"role": "user", "content": prompt}],
    )
    try:
        with httpx.Client(timeout=timeout_s) as client:
            response = client.post(request["url"], headers=request["headers"], json=request["json"])
    except httpx.TimeoutException:
        return {"ok": False, "error": "timeout", "text": None}
    except httpx.HTTPError:
        return {"ok": False, "error": "server_error", "text": None}
    if response.status_code in (401, 403):
        return {"ok": False, "error": "auth", "text": None}
    if not 200 <= response.status_code <= 299:
        return {"ok": False, "error": "bad_response", "text": None}
    try:
        body = response.json()
    except ValueError:
        return {"ok": False, "error": "bad_response", "text": None}
    if not isinstance(body, dict) or body.get("model") != model_id:
        return {"ok": False, "error": "model_mismatch", "text": None}
    parts = [
        block["text"]
        for block in body.get("content") or []
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
    ]
    if not parts:
        return {"ok": False, "error": "no_text", "text": None}
    return {"ok": True, "error": None, "text": "".join(parts)}


def _watcher_entries(payload, source):
    if isinstance(payload, dict) and isinstance(payload.get("watchers"), list):
        items = payload["watchers"]
    elif isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict) and isinstance(payload.get("output"), dict):
        items = [payload]
    else:
        return
    for item in items:
        if isinstance(item, dict):
            yield {"entry": item, "source": source}


def load_recorded_watchers(directory=None):
    from .review import reviews_dir

    directory = Path(directory) if directory is not None else reviews_dir()
    entries = []
    if directory.is_dir():
        for path in sorted(directory.glob("watchers-*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            entries.extend(_watcher_entries(payload, str(path)))
    return entries


def find_recorded_watcher(entries, scenario_id, evaluated_at_utc, input_revision, laws_version=None):
    try:
        wanted_at = laws_module._parse_time(evaluated_at_utc).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, AttributeError):
        return None
    for item in entries:
        entry = item.get("entry")
        if not isinstance(entry, dict):
            continue
        try:
            entry_at = laws_module._parse_time(entry.get("evaluated_at_utc") or entry.get("recorded_at"))
            entry_at = entry_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except (TypeError, ValueError, AttributeError):
            continue
        if (
            entry.get("scenario_id") == scenario_id
            and entry_at == wanted_at
            and entry.get("input_revision") == input_revision
            and (laws_version is None or entry.get("laws_version", laws_version) == laws_version)
            and entry.get("watcher_prompt_version", WATCHER_PROMPT_VERSION) == WATCHER_PROMPT_VERSION
        ):
            return item
    return None


def watcher_provenance(entry, validation_reasons):
    record = entry["entry"]
    return {
        "model_id": record.get("model_id"),
        "provider_route": record.get("provider_route") or "unknown",
        "recorded_at": record.get("recorded_at"),
        "input_revision": record.get("input_revision"),
        "laws_version": record.get("laws_version"),
        "watcher_prompt_version": record.get("watcher_prompt_version", WATCHER_PROMPT_VERSION),
        "validation": {"passed": not validation_reasons, "reasons": list(validation_reasons)},
    }


def public_watcher(scenario, at, entries=None):
    """Recorded-only watcher view plus the independent code detections.

    Never calls a provider. When no recorded run matches, the model list is
    empty and labelled; the code detections are still shown.
    """
    pack = build_evidence_pack(scenario, at)
    identity = watcher_identity(scenario, at)
    detections = code_detections(scenario, at, pack)
    if entries is None:
        entries = load_recorded_watchers()
    match = find_recorded_watcher(entries, identity["scenario_id"], identity["evaluated_at_utc"], identity["input_revision"], identity["laws_version"])
    if match is None:
        return {
            "scenario_id": identity["scenario_id"],
            "evaluated_at_utc": identity["evaluated_at_utc"],
            "model_observations": [],
            "model_note": NO_RECORDED_WATCHER_LABEL,
            "provenance": None,
            "code_detections": detections,
            "raise_caregiver_notice": bool(detections),
            "notice_basis": "code" if detections else "none",
        }
    parsed, reasons = parse_watcher_output(match["entry"].get("output"))
    if parsed is not None:
        reasons.extend(verify_watcher_output(parsed, pack, at))
    provenance = watcher_provenance(match, reasons)
    if reasons or parsed is None:
        return {
            "scenario_id": identity["scenario_id"],
            "evaluated_at_utc": identity["evaluated_at_utc"],
            "model_observations": [],
            "model_note": NO_RECORDED_WATCHER_LABEL,
            "provenance": provenance,
            "code_detections": detections,
            "raise_caregiver_notice": bool(detections),
            "notice_basis": "code" if detections else "none",
        }
    observations = [
        {**obs, "status": "confirmed", "notice": "noticed by the model, confirmed by the evidence check"}
        for obs in parsed["observations"]
    ]
    triggered = bool(observations)
    return {
        "scenario_id": identity["scenario_id"],
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "model_observations": observations,
        "model_note": None,
        "provenance": provenance,
        "code_detections": detections,
        "raise_caregiver_notice": triggered or bool(detections),
        "notice_basis": "both" if triggered and detections else ("model" if triggered else ("code" if detections else "none")),
    }


__all__ = [
    "MAX_CLAIM_CHARS",
    "NO_RECORDED_WATCHER_LABEL",
    "VALUE_TOLERANCE",
    "WATCHER_KINDS",
    "WATCHER_MODEL_ID",
    "WATCHER_PROMPT_VERSION",
    "build_revision_prompt",
    "build_watcher_prompt",
    "code_detections",
    "corrections_dir",
    "find_recorded_watcher",
    "load_correction_records",
    "load_recorded_watchers",
    "parse_watcher_output",
    "public_watcher",
    "request_live_watcher",
    "run_watcher",
    "save_correction_record",
    "verify_observation",
    "verify_watcher_output",
    "watcher_identity",
    "watcher_provenance",
]
