"""ARIA's Laws: code-enforced checks over every model output.

Each law in backend/laws/laws.json names the enforcement check function in
this module. check_output() runs every ACTIVE law against a model output
(investigation, watcher or review) and returns the violations; a violation
rejects the output and names the law. Proposed laws never enforce: they are
listed for people to read, and only a person editing laws.json can activate
one. There is no route that activates a law.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

LAWS_PATH = Path(__file__).resolve().parent.parent / "laws" / "laws.json"

LAWS_VERSION = "laws-v1"

_CIRCUIT_PREFIX = "metric:circuit_activity:"
_HUMAN_PREFIX = "human-report:"
_TEMP_QUANTITIES = frozenset({"indoor_temp", "outdoor_temp", "setpoint", "target_temp"})
_TEMP_METRICS = frozenset({"metric:indoor_trend", "metric:target_gap"})

PERSONAL_KEY_PARTS = ("image", "photo", "picture", "camera", "visual", "face")


def load_laws(path=None):
    raw = json.loads(Path(path or LAWS_PATH).read_text(encoding="utf-8"))
    return {
        "version": raw.get("version", LAWS_VERSION),
        "model_laws": list(raw.get("model_laws") or []),
        "process_laws": list(raw.get("process_laws") or []),
    }


def active_model_laws(registry=None):
    registry = registry if registry is not None else load_laws()
    return [law for law in registry["model_laws"] if law.get("status") == "active"]


def _parse_time(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _negated(text, index):
    window = text[max(0, index - 14):index].lower()
    return any(token in window for token in ("not ", "n't", "never ", "no ", "cannot", "can't", "without "))


def _phrase_hit(text, phrases):
    lowered = text.lower()
    for phrase in phrases:
        start = lowered.find(phrase)
        if start >= 0 and not _negated(lowered, start):
            return phrase
    return None


def _word_hit(text, phrases):
    lowered = text.lower()
    for phrase in phrases:
        start = lowered.find(phrase)
        while start >= 0:
            before = lowered[start - 1] if start > 0 else " "
            if before not in "abcdefghijklmnopqrstuvwxyz" and not _negated(lowered, start):
                return phrase
            start = lowered.find(phrase, start + 1)
    return None


def _prose_parts(output):
    if not isinstance(output, dict):
        return
    for key in ("interpretation", "clarification", "unknowns", "limitations"):
        value = output.get(key)
        if isinstance(value, str) and value.strip():
            yield key, value
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    yield key, item
    follow_up = output.get("follow_up")
    if isinstance(follow_up, dict) and isinstance(follow_up.get("observation"), str):
        yield "follow_up.observation", follow_up["observation"]
    for index, hyp in enumerate(output.get("hypotheses") or []):
        if isinstance(hyp, dict) and isinstance(hyp.get("text"), str):
            yield f"hypotheses[{index}]", hyp["text"]
    for index, obs in enumerate(output.get("observations") or []):
        if isinstance(obs, dict) and isinstance(obs.get("claim"), str):
            yield f"observations[{index}]", obs["claim"]
    for index, issue in enumerate(output.get("issues") or []):
        if isinstance(issue, dict) and isinstance(issue.get("note"), str) and issue["note"].strip():
            yield f"issues[{index}]", issue["note"]


def _hypotheses(output):
    items = output.get("hypotheses") if isinstance(output, dict) else None
    return [h for h in items if isinstance(h, dict)] if isinstance(items, list) else []


def _observations(output):
    items = output.get("observations") if isinstance(output, dict) else None
    return [o for o in items if isinstance(o, dict)] if isinstance(items, list) else []


def _evidence_by_id(pack):
    items = {}
    for item in (pack.get("evidence") or []) if isinstance(pack, dict) else []:
        if isinstance(item, dict) and item.get("id"):
            items[item["id"]] = item
    return items


def _is_circuit_evidence(evidence_id, by_id):
    if str(evidence_id).startswith(_CIRCUIT_PREFIX):
        return True
    item = by_id.get(evidence_id)
    return isinstance(item, dict) and "data" not in item and item.get("quantity") == "circuit_power"


def _is_temp_evidence(evidence_id, by_id):
    if str(evidence_id) in _TEMP_METRICS:
        return True
    item = by_id.get(evidence_id)
    return isinstance(item, dict) and "data" not in item and item.get("quantity") in _TEMP_QUANTITIES


def _is_human_evidence(evidence_id, by_id):
    if str(evidence_id).startswith(_HUMAN_PREFIX):
        return True
    item = by_id.get(evidence_id)
    return isinstance(item, dict) and (item.get("source") == "human_report" or item.get("quantity") == "technician_note")


_HEAT_PHRASES = ("warming", "useful heat", "is heating", "heating the", "heat output", "producing heat", "generating heat")


def check_no_heat_from_watts(output, pack=None, at=None):
    by_id = _evidence_by_id(pack or {})
    for hyp in _hypotheses(output):
        cited = [str(i) for i in (list(hyp.get("supporting_ids") or []) + list(hyp.get("conflicting_ids") or []))]
        if cited and _phrase_hit(hyp.get("text") or "", _HEAT_PHRASES) and all(_is_circuit_evidence(i, by_id) for i in cited):
            return "electrical activity alone is never heat: a warming claim cites only circuit evidence"
    for obs in _observations(output):
        cited = [str(i) for i in (obs.get("evidence_ids") or [])]
        if cited and _phrase_hit(obs.get("claim") or "", _HEAT_PHRASES) and all(_is_circuit_evidence(i, by_id) for i in cited):
            return "electrical activity alone is never heat: a warming claim cites only circuit evidence"
    return None


def check_ack_not_resolution(output, pack=None, at=None):
    for where, text in _prose_parts(output):
        if "acknowledg" in text.lower() and _phrase_hit(text, ("resolv", "fixed", "closed the", "no further action", "stands resolved")):
            return f"acknowledgement is not resolution ({where} treats an acknowledgement as resolved)"
    return None


def check_reconnect_proves_nothing(output, pack=None, at=None):
    for where, text in _prose_parts(output):
        if _phrase_hit(text, ("reconnect", "back online", "reporting restored", "telemetry restored")) and _word_hit(
            text, ("verified", "verify", "recovered", "working again", "fixed", "resolved", "back on track", "on track", "prove")
        ):
            return f"thermostat reconnection alone proves nothing ({where} treats reconnection as recovery)"
    return None


def check_human_report_not_measurement(output, pack=None, at=None):
    by_id = _evidence_by_id(pack or {})
    if isinstance(output, dict):
        for fact in output.get("facts") or []:
            if not isinstance(fact, dict):
                continue
            if fact.get("claim_type") in ("current_temperature", "temperature_at_arrival", "target_temperature", "target_gap", "electrical_activity", "equipment_function") and _is_human_evidence(fact.get("evidence_id"), by_id):
                return f"a human report never counts as a sensor measurement (fact cites {fact.get('evidence_id')})"
    for obs in _observations(output):
        cited = [str(i) for i in (obs.get("evidence_ids") or [])]
        if any(_is_human_evidence(i, by_id) for i in cited) and str(obs.get("kind")) in ("temperature_drop", "telemetry_gap", "equipment_quiet"):
            return "a human report never counts as a sensor measurement (observation cites a human report as sensor evidence)"
    return None


_ALL_CLEAR_PHRASES = ("all clear", "all-clear", "confirmed safe", "proven safe", "definitely safe", "no danger")


def check_no_detection_not_safe(output, pack=None, at=None):
    for where, text in _prose_parts(output):
        if _phrase_hit(text, _ALL_CLEAR_PHRASES):
            return f"no detection never means safe ({where} states an all-clear)"
    return None


def check_stale_not_current(output, pack=None, at=None):
    if not isinstance(pack, dict):
        return None
    moment = _parse_time(at if at is not None else pack.get("at"))
    if moment is None:
        return None
    from .eligibility import freshness_limit_s

    by_id = _evidence_by_id(pack)
    window_start = moment.timestamp() - 3 * 3600
    if isinstance(output, dict):
        for fact in output.get("facts") or []:
            if not isinstance(fact, dict) or fact.get("claim_type") != "current_temperature":
                continue
            item = by_id.get(fact.get("evidence_id"))
            if not isinstance(item, dict):
                continue
            observed = _parse_time(item.get("observed_at") or (item.get("data") or {}).get("last_observed_at") if isinstance(item.get("data"), dict) else item.get("observed_at"))
            if observed is None:
                continue
            age_s = (moment - observed).total_seconds()
            limit = freshness_limit_s(item if "data" not in item else {"value": 1, "observed_at": item.get("data", {}).get("last_observed_at"), "expected_cadence_s": None})
            if age_s < 0 or age_s > limit or observed.timestamp() < window_start:
                return f"an old or superseded reading is never current (fact cites {fact.get('evidence_id')} observed {observed.isoformat()})"
    for obs in _observations(output):
        if "current" not in str(obs.get("claim") or "").lower() and "now " not in str(obs.get("claim") or "").lower():
            continue
        for evidence_id in obs.get("evidence_ids") or []:
            item = by_id.get(evidence_id)
            if not isinstance(item, dict) or "data" in item:
                continue
            observed = _parse_time(item.get("observed_at"))
            if observed is None:
                continue
            if (moment - observed).total_seconds() > freshness_limit_s(item):
                return f"an old or superseded reading is never current (observation cites stale {evidence_id})"
    return None


_SUCCESS_PHRASES = ("goal met", "goal verified", "fully recovered", "arrival_met", "back on track", "is on track", "will be ready", "is ready for arrival", "success")


def _pack_has_unresolved_conflicts(pack):
    try:
        from .eligibility import measurement_conflict_groups
    except Exception:
        return False
    evidence = [e for e in pack.get("evidence", []) if isinstance(e, dict) and "data" not in e]
    try:
        return bool(
            measurement_conflict_groups(evidence, quantity="indoor_temp")
            or measurement_conflict_groups(evidence, quantity="circuit_power")
        )
    except Exception:
        return False


def check_conflicts_block_success(output, pack=None, at=None):
    if not isinstance(pack, dict) or not _pack_has_unresolved_conflicts(pack):
        return None
    for where, text in _prose_parts(output):
        if _phrase_hit(text, _SUCCESS_PHRASES):
            return f"unresolved contradictory readings block success ({where} claims success while readings conflict)"
    return None


def check_no_images_or_personal_in_hvac(output, pack=None, at=None):
    from .notifications import FORBIDDEN_KEY_PARTS

    payload = None
    if isinstance(output, dict):
        if isinstance(output.get("payload"), dict) and output.get("audience") == "hvac_company":
            payload = output["payload"]
        elif isinstance(output.get("notification"), dict):
            nested = output["notification"]
            if isinstance(nested.get("payload"), dict) and nested.get("audience") == "hvac_company":
                payload = nested["payload"]

        def _scan(value, trail="payload"):
            if isinstance(value, dict):
                for key, item in value.items():
                    lowered = str(key).lower()
                    if any(part in lowered for part in FORBIDDEN_KEY_PARTS) or any(part in lowered for part in PERSONAL_KEY_PARTS):
                        return f"images and personal details never enter HVAC payloads (forbidden key {trail}.{key})"
                    hit = _scan(item, f"{trail}.{key}")
                    if hit:
                        return hit
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    hit = _scan(item, f"{trail}[{index}]")
                    if hit:
                        return hit
            return None

        if payload is not None:
            return _scan(payload)
    return None


def _is_forecast_evidence(evidence_id, by_id):
    if str(evidence_id).startswith("weather"):
        return True
    item = by_id.get(evidence_id)
    if not isinstance(item, dict):
        return False
    if item.get("kind") == "forecast" or item.get("quantity") == "outdoor_temp_forecast":
        return True
    return "data" not in item and item.get("quantity") == "outdoor_temp"


def check_weather_never_decides(output, pack=None, at=None):
    by_id = _evidence_by_id(pack or {})
    for hyp in _hypotheses(output):
        cited = [str(i) for i in (list(hyp.get("supporting_ids") or []) + list(hyp.get("conflicting_ids") or []))]
        if cited and _word_hit(hyp.get("text") or "", ("on track", "at risk", "will be ready", "ready on arrival")) and all(
            _is_forecast_evidence(i, by_id) for i in cited
        ):
            return "weather forecast context never decides readiness on its own: a readiness claim cites only forecast evidence"
    return None


CHECKS = {
    "check_no_heat_from_watts": check_no_heat_from_watts,
    "check_ack_not_resolution": check_ack_not_resolution,
    "check_reconnect_proves_nothing": check_reconnect_proves_nothing,
    "check_human_report_not_measurement": check_human_report_not_measurement,
    "check_no_detection_not_safe": check_no_detection_not_safe,
    "check_stale_not_current": check_stale_not_current,
    "check_conflicts_block_success": check_conflicts_block_success,
    "check_no_images_or_personal_in_hvac": check_no_images_or_personal_in_hvac,
    "check_weather_never_decides": check_weather_never_decides,
}


def check_output(output, pack=None, at=None, registry=None):
    violations = []
    data = output.model_dump(mode="json") if hasattr(output, "model_dump") else output
    for law in active_model_laws(registry):
        func = CHECKS.get(law.get("check"))
        if func is None:
            continue
        try:
            reason = func(data, pack, at)
        except Exception:
            continue
        if reason:
            violations.append({"law": law["id"], "reason": reason})
    return violations


__all__ = [
    "CHECKS",
    "LAWS_PATH",
    "LAWS_VERSION",
    "active_model_laws",
    "check_output",
    "load_laws",
]
