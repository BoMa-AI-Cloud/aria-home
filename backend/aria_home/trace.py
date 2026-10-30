"""ARIA's view trace: the ordered replay of how each decision was made.

Built only from the same functions that make the decisions (evidence pack,
freshness/eligibility, readiness, verification, watcher verification, laws,
human-report attachment, notification gates). Never calls a model, never
shows evidence received after the replay moment.
"""

from datetime import datetime

from . import laws as laws_module
from .contracts import Availability, SourceKind
from .eligibility import (
    freshness_limit_s,
    normalized_measurement_value,
    unresolved_conflict_groups,
)
from .evidence import freshness, source_status
from .investigator import build_evidence_pack, inference_identity
from .notifications import _get, caregiver_permission_text, decide_hvac_notification, decide_notifications
from .outcomes import follow_up_for
from .recorded import find_recorded, load_recorded_answers, public_investigation
from .review import find_recorded_review, load_recorded_reviews
from .scenario import context_as_of, events_as_of, visible_records
from .transcribe import HUMAN_REPORT_LABEL, human_report_for
from .verification import build_evidence_timeline, verify_recovery
from .watcher import (
    NO_RECORDED_WATCHER_LABEL,
    code_detections,
    find_recorded_watcher,
    load_correction_records,
    load_recorded_watchers,
    parse_watcher_output,
    public_watcher,
    verify_watcher_output,
    watcher_identity,
    watcher_provenance,
)

TRACE_VERSION = "trace-v1"

TEMP_UNITS = frozenset({"F", "C"})
POWER_UNITS = frozenset({"W"})
CONFLICT_QUANTITIES = ("indoor_temp", "circuit_power")


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _jsonable(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _record_values(record):
    get = (lambda name: record.get(name)) if isinstance(record, dict) else (lambda name: getattr(record, name, None))
    return {
        "id": get("id"),
        "source": get("source").value if isinstance(get("source"), SourceKind) else get("source"),
        "subject": get("subject"),
        "quantity": get("quantity"),
        "value": get("value"),
        "unit": get("unit"),
        "observed_at": _iso(get("observed_at")),
        "received_at": _iso(get("received_at")),
    }


def _latest_for(records, source):
    candidates = [r for r in records if _record_values(r)["source"] == source]
    if not candidates:
        return None
    return max(candidates, key=lambda r: (_record_values(r)["observed_at"], _record_values(r)["received_at"], _record_values(r)["id"]))


def _source_trace(status, latest, at, conflicted_ids):
    detail = _record_values(latest) if latest is not None else None
    if latest is None:
        freshness_state, freshness_reason = "missing", "no records visible as of the replay time"
    elif latest.value is None:
        freshness_state, freshness_reason = "missing", f"{latest.id} has no value"
    else:
        state = freshness(latest, at)
        limit = freshness_limit_s(latest)
        age_s = (at - latest.observed_at).total_seconds()
        if state is Availability.available:
            freshness_state = "fresh"
            freshness_reason = f"{latest.id} observed {latest.observed_at.isoformat()}, {age_s:.0f}s old (limit {limit:.0f}s)"
        elif state is Availability.invalid:
            freshness_state, freshness_reason = "invalid", f"{latest.id} is future-dated beyond the replay time"
        elif state is Availability.stale:
            freshness_state, freshness_reason = "stale", f"{latest.id} observed {latest.observed_at.isoformat()}, {age_s:.0f}s old (limit {limit:.0f}s)"
        else:
            freshness_state, freshness_reason = "missing", f"{latest.id} has no usable value"
    conflicted = detail is not None and detail["id"] in conflicted_ids
    return {
        "source": status["source"] if isinstance(status, dict) else status.source.value,
        "availability": status["availability"] if isinstance(status, dict) else status.availability.value,
        "record_count": status.get("record_count") if isinstance(status, dict) else status.record_count,
        "notes": list(status.get("notes") or []) if isinstance(status, dict) else list(status.notes or []),
        "latest_reading": detail,
        "freshness": freshness_state,
        "freshness_reason": freshness_reason,
        "conflicted": conflicted,
    }


def _conflicted_ids(visible, at):
    out = set()
    for quantity in CONFLICT_QUANTITIES:
        try:
            groups = unresolved_conflict_groups(visible, quantity, at)
        except Exception:
            continue
        for group in groups:
            out.update(group.get("ids") or [])
    return out


def _freshness_checks(source_traces):
    rows = []
    for item in source_traces:
        if item["latest_reading"] is None:
            rows.append({"check": "freshness", "target": item["source"], "passed": None, "reason": "no records visible as of the replay time"})
        elif item["freshness"] == "fresh":
            rows.append({"check": "freshness", "target": item["source"], "passed": True, "reason": item["freshness_reason"]})
        else:
            rows.append({"check": "freshness", "target": item["source"], "passed": False, "reason": item["freshness_reason"]})
    return rows


def _conflict_checks(visible, at):
    rows = []
    for quantity in CONFLICT_QUANTITIES:
        try:
            groups = unresolved_conflict_groups(visible, quantity, at)
        except Exception as exc:
            rows.append({"check": "conflict", "target": quantity, "passed": None, "reason": f"conflict check failed to run: {exc}"})
            continue
        if groups:
            ids = sorted({rid for group in groups for rid in (group.get("ids") or [])})
            rows.append({"check": "conflict", "target": quantity, "passed": False, "reason": f"unresolved contradictory readings block success: {', '.join(ids)}"})
        else:
            rows.append({"check": "conflict", "target": quantity, "passed": True, "reason": f"no unresolved {quantity} conflicts as of the replay time"})
    return rows


def _units_checks(visible):
    by_source = {}
    for record in visible:
        kind = getattr(record, "kind", None)
        kind = kind.value if hasattr(kind, "value") else kind
        if kind != "measurement":
            continue
        by_source.setdefault(_record_values(record)["source"], []).append(record)
    rows = []
    for source in sorted(by_source):
        bad = []
        for record in by_source[source]:
            info = _record_values(record)
            quantity, unit, value = info["quantity"], info["unit"], info["value"]
            if value is None:
                continue
            allowed = TEMP_UNITS if quantity in ("indoor_temp", "outdoor_temp", "setpoint", "target_temp") else POWER_UNITS if quantity == "circuit_power" else None
            if allowed is not None and unit not in allowed:
                bad.append(f"{info['id']} has unit {unit!r}")
            elif not isinstance(value, (int, float)) or isinstance(value, bool):
                bad.append(f"{info['id']} has a non-numeric value")
            elif normalized_measurement_value(record) is None:
                bad.append(f"{info['id']} has a value code cannot use")
        if bad:
            rows.append({"check": "units", "target": source, "passed": False, "reason": "; ".join(bad)})
        else:
            rows.append({"check": "units", "target": source, "passed": True, "reason": f"all {source} readings use understood units"})
    return rows


def _recorded_outputs(scenario_id, evaluated_at_utc, input_revision, prompt_version, readiness_policy_version, entries, watcher_entries, review_entries):
    outputs = []
    match = find_recorded(entries, scenario_id, evaluated_at_utc, input_revision, prompt_version, readiness_policy_version)
    if match is not None and isinstance(match.get("answer", {}).get("output"), dict):
        outputs.append({"target": "investigation", "output": match["answer"]["output"]})
    try:
        laws_version = laws_module.load_laws()["version"]
    except Exception:
        laws_version = None
    watcher_match = find_recorded_watcher(watcher_entries, scenario_id, evaluated_at_utc, input_revision, laws_version)
    if watcher_match is not None and isinstance(watcher_match.get("entry", {}).get("output"), dict):
        outputs.append({"target": "watcher", "output": watcher_match["entry"]["output"]})
    review_match = find_recorded_review(review_entries, scenario_id, evaluated_at_utc, input_revision)
    if review_match is not None and isinstance(review_match.get("entry", {}).get("review"), dict):
        outputs.append({"target": "review", "output": review_match["entry"]["review"]})
    return outputs


def _law_checks(pack, at, recorded_outputs):
    laws = laws_module.active_model_laws()
    rows = []
    if not recorded_outputs:
        for law in laws:
            rows.append({"check": f"law:{law.get('id')}", "target": "no model output", "passed": None, "reason": "no model output at this snapshot; nothing to check"})
        return rows
    for law in laws:
        func = laws_module.CHECKS.get(law.get("check"))
        for item in recorded_outputs:
            if func is None:
                rows.append({"check": f"law:{law.get('id')}", "target": item["target"], "passed": None, "reason": f"no enforcement check named {law.get('check')!r}"})
                continue
            try:
                reason = func(item["output"], pack, at)
            except Exception:
                continue
            if reason:
                rows.append({"check": f"law:{law.get('id')}", "target": item["target"], "passed": False, "reason": reason})
            else:
                rows.append({"check": f"law:{law.get('id')}", "target": item["target"], "passed": True, "reason": f"{law.get('id')} holds on the recorded {item['target']} output"})
    return rows


def _serialize_verification(verification):
    payload = dict(verification)
    for key in ("evaluated_at", "goal_verified_at", "arrival_met_at"):
        payload[key] = _iso(payload.get(key))
    latest = payload.get("latest_reading_used")
    if isinstance(latest, dict):
        payload["latest_reading_used"] = {key: _iso(value) for key, value in latest.items()}
    return payload


def _watcher_detail(scenario, at, pack, identities, watcher_entries):
    wid = watcher_identity(scenario, at)
    detections = code_detections(scenario, at, pack)
    if watcher_entries is None:
        watcher_entries = load_recorded_watchers()
    match = find_recorded_watcher(watcher_entries, wid["scenario_id"], wid["evaluated_at_utc"], wid["input_revision"], wid["laws_version"])
    observations = []
    if match is None:
        note, provenance, status = NO_RECORDED_WATCHER_LABEL, None, "quiet"
    else:
        parsed, reasons = parse_watcher_output(match["entry"].get("output"))
        if parsed is not None:
            reasons.extend(verify_watcher_output(parsed, pack, at))
        provenance = watcher_provenance(match, reasons)
        if reasons or parsed is None:
            note, status = NO_RECORDED_WATCHER_LABEL, "rejected"
            for obs in (parsed or {}).get("observations", []):
                observations.append({**_jsonable(obs), "status": "rejected", "reasons": list(reasons)})
            if not observations:
                observations.append({"kind": None, "claim": None, "evidence_ids": [], "values": {}, "status": "rejected", "reasons": list(reasons)})
        else:
            note, status = None, "confirmed"
            for obs in parsed["observations"]:
                observations.append({**_jsonable(obs), "status": "confirmed", "reasons": []})
    corrections = [
        {key: record.get(key) for key in ("scenario_id", "evaluated_at_utc", "input_revision", "laws_version", "original_claim", "failed_checks", "revision_claim", "final_result")}
        for record in load_correction_records()
        if isinstance(record, dict) and record.get("scenario_id") == wid["scenario_id"] and record.get("evaluated_at_utc") == wid["evaluated_at_utc"]
    ]
    for record in corrections:
        if record.get("final_result") == "corrected and verified":
            status = "corrected and verified"
    return {
        "observations": observations,
        "model_note": note,
        "status": status,
        "provenance": provenance if match is not None else None,
        "code_detections": _jsonable(detections),
        "corrections": corrections,
    }


def _permission_trace(scenario, at, events, decisions, caregiver_decision=None):
    """The caregiver permission step: requested, waiting, then approved or declined by the caregiver."""
    if scenario.manifest.id != "care_home_v1":
        return None
    alert = next((d for d in decisions if d["audience"] == "family_caregiver" and d["kind"] == "caregiver_alert"), None)
    requested_earlier = any(_get(e, "kind") == "caregiver_alert" for e in events)
    if not requested_earlier and (alert is None or not alert["allowed"]):
        return None
    if caregiver_decision is not None:
        status, actor, decided_at, source = caregiver_decision["decision"], caregiver_decision.get("actor", "family_caregiver"), caregiver_decision.get("decided_at"), "in-app decision"
    else:
        approval = next((e for e in events if _get(e, "kind") == "caregiver_hvac_authorized"), None)
        status = "approved" if approval is not None else "waiting"
        actor = "family_caregiver" if approval is not None else None
        decided_at = _iso(_get(approval, "available_at")) if approval is not None else None
        source = "scenario event" if approval is not None else None
    return {
        "status": status,
        "actor": actor,
        "decided_at": decided_at,
        "source": source,
        "text": caregiver_permission_text(scenario, at),
        "note": "approval only lets ARIA contact the HVAC company; it never changes readiness or verification",
    }


def build_trace(scenario, at, entries=None, watcher_entries=None, review_entries=None, transcript_entries=None, caregiver_decision=None):
    pack = build_evidence_pack(scenario, at)
    identity = inference_identity(scenario, at)
    visible = visible_records(scenario.records, at)
    conflicted = _conflicted_ids(visible, at)

    statuses = pack.get("source_statuses") or []
    source_traces = [_source_trace(status, _latest_for(visible, status["source"] if isinstance(status, dict) else status.source.value), at, conflicted) for status in statuses]

    if entries is None:
        entries = load_recorded_answers()
    if review_entries is None:
        review_entries = load_recorded_reviews()
    recorded_outputs = _recorded_outputs(
        identity["scenario_id"], identity["evaluated_at_utc"], identity["input_revision"],
        pack.get("prompt_version"), pack.get("readiness_policy_version"),
        entries, watcher_entries if watcher_entries is not None else load_recorded_watchers(), review_entries,
    )
    check_rows = _freshness_checks(source_traces) + _conflict_checks(visible, at) + _units_checks(visible) + _law_checks(pack, at, recorded_outputs)

    readiness = pack.get("readiness") if isinstance(pack.get("readiness"), dict) else {}
    try:
        followup = follow_up_for(scenario, identity["investigation_id"], at)
    except ValueError as exc:
        followup, verification, timeline = None, {"available": False, "reason": str(exc)}, []
    else:
        verification = _serialize_verification(verify_recovery(scenario, followup, at))
        verification["available"] = True
        timeline = _jsonable(build_evidence_timeline(scenario, followup, at))

    watcher = _watcher_detail(scenario, at, pack, identity, watcher_entries)
    watcher_summary = public_watcher(scenario, at)

    human = human_report_for(scenario, at, transcript_entries)
    if human is None:
        human_trace = None
    else:
        human_trace = {
            "payload": _jsonable(human["payload"]),
            "timeline_entry": _jsonable(human["timeline_entry"]),
            "label": HUMAN_REPORT_LABEL,
            "note": "human report, not a sensor measurement; corroboration only, never a measurement",
        }

    investigation, _provenance = public_investigation(scenario, at, entries)
    context = context_as_of(scenario, at)
    events = events_as_of(scenario, at)
    verification_for_notif = {key: value for key, value in verification.items() if key != "available"} if verification.get("available") else None
    decisions = decide_notifications(investigation, readiness, verification_for_notif, context, events, at, scenario, identity["investigation_id"])
    decisions = list(decisions) + [decide_hvac_notification(investigation, readiness, verification_for_notif, context, events, at, scenario, identity["investigation_id"])]
    permission = _permission_trace(scenario, at, events, decisions, caregiver_decision)
    notices = [{"audience": item["audience"], "kind": item["kind"], "allowed": item["allowed"], "reason": item.get("reason"), "payload_keys": sorted((item.get("payload") or {}).keys())} for item in decisions]

    steps = []
    for index, item in enumerate(source_traces):
        state = "pass" if item["availability"] == "available" and item["freshness"] == "fresh" and not item["conflicted"] else "stale" if item["freshness"] in ("stale", "missing") else "fail"
        steps.append({"seq": len(steps), "kind": "source", "label": f"{item['source']}: {item['availability']}", "state": state, "detail": item["freshness_reason"], "ref": {"section": "sources", "index": index}})
    for index, row in enumerate(check_rows):
        state = "pass" if row["passed"] is True else "fail" if row["passed"] is False else "stale"
        steps.append({"seq": len(steps), "kind": "check", "label": f"{row['check']} on {row['target']}", "state": state, "detail": row["reason"], "ref": {"section": "checks", "index": index}})
    steps.append({"seq": len(steps), "kind": "decision", "label": f"readiness: {readiness.get('status')}", "state": "pass" if readiness.get("status") in ("on_track", "arrival_passed") else "fail" if readiness.get("status") == "at_risk" else "stale", "detail": "; ".join(readiness.get("reasons") or []), "ref": {"section": "readiness", "index": 0}})
    if verification.get("available"):
        steps.append({"seq": len(steps), "kind": "decision", "label": f"verification: {verification.get('stage')}", "state": "pass" if verification.get("stage") in ("goal_verified", "arrival_met") else "stale", "detail": "; ".join(verification.get("reasons") or []), "ref": {"section": "verification", "index": 0}})
    else:
        steps.append({"seq": len(steps), "kind": "decision", "label": "verification: not available", "state": "stale", "detail": verification.get("reason", ""), "ref": {"section": "verification", "index": 0}})
    for index, obs in enumerate(watcher["observations"]):
        state = "pass" if obs.get("status") == "confirmed" else "fail"
        steps.append({"seq": len(steps), "kind": "model", "label": f"watcher: {obs.get('kind')}", "state": state, "detail": f"{obs.get('claim')} [{obs.get('status')}]", "ref": {"section": "watcher", "index": index}})
    if not watcher["observations"] and not watcher["code_detections"]:
        steps.append({"seq": len(steps), "kind": "model", "label": "no detection, never safe", "state": "quiet", "detail": "no model observation and no code detection at this time; absence of a detection is not an all-clear", "ref": {"section": "watcher", "index": 0}})
    for index, detection in enumerate(watcher["code_detections"]):
        steps.append({"seq": len(steps), "kind": "code", "label": f"code detection: {detection.get('rule')}", "state": "fail", "detail": detection.get("detail", ""), "ref": {"section": "code_detections", "index": index}})
    if human_trace is not None:
        steps.append({"seq": len(steps), "kind": "human", "label": "human report, not a measurement", "state": "stale", "detail": human_trace["payload"].get("transcript", "")[:200], "ref": {"section": "human", "index": 0}})
    if permission is not None:
        label = {"waiting": "caregiver permission: requested, waiting", "approved": "caregiver permission: approved by the caregiver", "declined": "caregiver permission: declined by the caregiver"}[permission["status"]]
        state = {"waiting": "stale", "approved": "pass", "declined": "fail"}[permission["status"]]
        steps.append({"seq": len(steps), "kind": "permission", "label": label, "state": state, "detail": permission["text"], "ref": {"section": "permission", "index": 0}})
    for index, notice in enumerate(notices):
        state = "pass" if notice["allowed"] else "stale"
        steps.append({"seq": len(steps), "kind": "notice", "label": f"{notice['audience']}: {'raised' if notice['allowed'] else 'refused'}", "state": state, "detail": notice["reason"] or f"fields: {', '.join(notice['payload_keys'])}", "ref": {"section": "notices", "index": index}})

    return {
        "trace_version": TRACE_VERSION,
        "computed_by": "deterministic code",
        "scenario": scenario.manifest.id,
        "at": at.isoformat(),
        "input_revision": identity["input_revision"],
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "as_of_note": "only evidence with received_at at or before the replay time is shown",
        "sources": source_traces,
        "checks": check_rows,
        "readiness": {"status": readiness.get("status"), "reasons": list(readiness.get("reasons") or [])},
        "verification": verification,
        "verification_timeline": timeline,
        "watcher": watcher,
        "watcher_summary": {key: _jsonable(value) for key, value in watcher_summary.items()},
        "human_report": human_trace,
        "permission": permission,
        "notices": notices,
        "steps": steps,
    }


__all__ = ["TRACE_VERSION", "build_trace"]
