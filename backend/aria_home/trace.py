"""ARIA's view trace: the ordered replay of how each decision was made.

Built only from the same functions that make the decisions (evidence pack,
freshness/eligibility, readiness, verification, watcher verification, laws,
human-report attachment, notification gates). Never calls a model, never
shows evidence received after the replay moment.
"""

from datetime import datetime, timedelta

from . import laws as laws_module
from .clock import plain_duration, plain_time
from .contracts import Availability, SourceKind
from .eligibility import (
    eligible_records,
    freshness_limit_s,
    normalized_measurement_value,
    unresolved_conflict_groups,
)
from .evidence import freshness, source_status
from .investigator import build_evidence_pack, inference_identity
from .metrics import temperature_trend
from .notifications import ALERT_GAP_F, CAREGIVER_SCENARIOS, _get, caregiver_alert_level, caregiver_is_authorized, caregiver_permission_text, decide_hvac_notification, decide_notifications
from .outcomes import follow_up_for
from .public_demo import parsed_checkpoints
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

SCRIPTED_BASIS = "scripted story, no visitor decisions"


class UnknownInvestigation(ValueError):
    """The trace was asked for an investigation with no stored follow-up."""


def investigation_trace_inputs(store, scenario, investigation_id, at):
    """The follow-up/verification/notice inputs for one stored investigation.

    Shared by the follow-up view and the trace so both use the investigation's
    real follow-up (never a fresh one anchored at the replay time) and the
    effective caregiver decision as of the replay time. Returns None when the
    investigation has no stored follow-up in this store.
    """
    follow_up = store.get_follow_up(investigation_id)
    if follow_up is None:
        return None
    return {
        "follow_up": follow_up,
        "verification": verify_recovery(scenario, follow_up, at),
        "caregiver_decision": store.get_caregiver_decision(investigation_id, at=at),
    }


TEMP_UNITS = frozenset({"F", "C"})
POWER_UNITS = frozenset({"W"})
CONFLICT_QUANTITIES = ("indoor_temp", "circuit_power")
QUANTITY_WORDS = {"indoor_temp": "indoor temperature", "circuit_power": "circuit power"}
CARE_AUDIENCE_WORDS = {"homeowner": "resident", "family_caregiver": "family caregiver", "hvac_company": "HVAC company"}
READINESS_LABELS = {"arrival_passed": "warm-by time passed"}
STAGE_LABELS = {"telemetry_missing": "thermostat not reporting", "arrival_met": "warm-by goal met"}
REFUSAL_WORDS = {
    "homeowner_opted_out": "the resident chose not to get updates",
    "homeowner_preference_missing": "the resident's update preference is not on file",
    "caregiver_not_authorized": "the family caregiver is not on file to be asked",
    "caregiver_hvac_not_authorized": "the family caregiver has not approved contacting HVAC",
    "caregiver_declined": "the family caregiver declined",
}


def _timezone_name(scenario):
    return _get(_get(scenario, "manifest"), "timezone")


def _clock(scenario, value):
    return plain_time(value, _timezone_name(scenario))


def _words(name):
    return str(name).replace("_", " ")


def _sentence(reasons):
    return "; ".join(str(reason).rstrip(".") for reason in reasons or [])


def _is_care_story(scenario):
    return _get(_get(scenario, "manifest"), "id") in CAREGIVER_SCENARIOS


def _audience_words(scenario, audience):
    return CARE_AUDIENCE_WORDS.get(audience, _words(audience)) if _is_care_story(scenario) else _words(audience)


def _stage_label(scenario, stage):
    label = STAGE_LABELS.get(stage, _words(stage))
    return label.replace("goal", "target") if _is_care_story(scenario) else label


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


def _source_trace(status, latest, at, conflicted_ids, scenario=None):
    detail = _record_values(latest) if latest is not None else None
    if latest is None:
        freshness_state, freshness_reason = "missing", "no readings yet at this time"
    elif latest.value is None:
        freshness_state, freshness_reason = "missing", f"{latest.id} has no value"
    else:
        state = freshness(latest, at)
        age_s = (at - latest.observed_at).total_seconds()
        limit = "no age limit applies" if latest.expected_cadence_s is None else f"limit {plain_duration(freshness_limit_s(latest))}"
        if state is Availability.available:
            freshness_state = "fresh"
            freshness_reason = f"{latest.id} observed {_clock(scenario, latest.observed_at)}, {plain_duration(age_s)} old ({limit})"
        elif state is Availability.invalid:
            freshness_state, freshness_reason = "invalid", f"{latest.id} is dated after this moment in the replay"
        elif state is Availability.stale:
            freshness_state, freshness_reason = "stale", f"{latest.id} observed {_clock(scenario, latest.observed_at)}, {plain_duration(age_s)} old ({limit})"
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
            rows.append({"check": "freshness", "target": item["source"], "passed": None, "reason": "no readings yet at this time"})
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
            rows.append({"check": "conflict", "target": quantity, "passed": True, "reason": f"no unresolved {QUANTITY_WORDS.get(quantity, quantity)} conflicts at this time"})
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
            rows.append({"check": "units", "target": source, "passed": True, "reason": f"all {_words(source)} readings use understood units"})
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
            rows.append({"check": f"law:{law.get('id')}", "target": "no model output", "passed": None, "reason": "no model answer at this time; nothing to check"})
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
        {key: record.get(key) for key in ("scenario_id", "evaluated_at_utc", "input_revision", "laws_version", "watcher_prompt_version", "original_claim", "failed_checks", "revision_claim", "final_result")}
        for record in load_correction_records()
        if isinstance(record, dict) and record.get("scenario_id") == wid["scenario_id"] and record.get("evaluated_at_utc") == wid["evaluated_at_utc"] and record.get("input_revision") == wid["input_revision"] and record.get("laws_version", wid["laws_version"]) == wid["laws_version"] and record.get("watcher_prompt_version", wid["watcher_prompt_version"]) == wid["watcher_prompt_version"]
    ]
    if match is not None and parsed is not None and not reasons:
        shown = _jsonable(parsed["observations"])
        for record in load_correction_records():
            if not isinstance(record, dict):
                continue
            if record.get("final_result") != "corrected and verified":
                continue
            if record.get("scenario_id") != wid["scenario_id"]:
                continue
            if record.get("evaluated_at_utc") != wid["evaluated_at_utc"]:
                continue
            if record.get("input_revision") != wid["input_revision"]:
                continue
            if record.get("laws_version") != wid["laws_version"]:
                continue
            if record.get("watcher_prompt_version") != wid["watcher_prompt_version"]:
                continue
            if _jsonable(record.get("revision_claim")) != shown:
                continue
            status = "corrected and verified"
            break
    return {
        "observations": observations,
        "model_note": note,
        "status": status,
        "provenance": provenance if match is not None else None,
        "code_detections": _jsonable(detections),
        "corrections": corrections,
    }


def _alert_created_at(store, investigation_id, at):
    """The moment ARIA asked: the delivered caregiver-alert row creation time."""
    try:
        rows = store.list_notifications(investigation_id, at=at)
    except Exception:
        return None
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if row.get("audience") == "family_caregiver" and row.get("kind") == "caregiver_alert" and row.get("state") == "simulated_delivered":
            try:
                return datetime.fromisoformat(str(row.get("created_at")).replace("Z", "+00:00"))
            except ValueError:
                return None
    return None


def _first_ask_time(scenario, at):
    """The first checkpoint at or before `at` when the caregiver alert is raised, or None."""
    try:
        checkpoints = parsed_checkpoints(scenario.manifest.id)
    except Exception:
        return None
    for checkpoint in checkpoints:
        if checkpoint > at:
            break
        try:
            pack = build_evidence_pack(scenario, checkpoint)
        except Exception:
            continue
        readiness = pack.get("readiness") if isinstance(pack.get("readiness"), dict) else {}
        if caregiver_alert_level(readiness) != "alert":
            continue
        try:
            context = context_as_of(scenario, checkpoint)
        except Exception:
            continue
        try:
            if caregiver_is_authorized(context):
                return checkpoint
        except Exception:
            continue
    return None


def _scripted_ask_time(scenario, at):
    """The moment the scripted trace freezes the request: the same predicate as
    the notification gate, so it matches when the stored flow asks."""
    return _first_ask_time(scenario, at) or at


def _notices_exist(scenario, at, decisions, store=None, investigation_id=None):
    """Whether the House could show a notice at this step.

    `decisions` answers what the gates would allow if a notice were sent. In the
    care story nothing is sent until the caregiver is asked: before that the app
    stores no notification rows, so the trace shows none either.
    """
    if not _is_care_story(scenario):
        return True
    if investigation_id is not None and store is not None:
        return bool(store.list_notifications(investigation_id, at=at))
    if any(d["audience"] == "family_caregiver" for d in decisions):
        return True
    return _first_ask_time(scenario, at) is not None


def _permission_trace(scenario, at, events, decisions, caregiver_decision=None, store=None, investigation_id=None):
    """The caregiver permission step: requested, waiting, then approved or declined by the caregiver.

    The request text is frozen at the moment ARIA asked (the alert creation
    time), never rebuilt at the replay time; before it is raised there is no step.
    """
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
    asked_at = None
    if store is not None and investigation_id is not None:
        asked_at = _alert_created_at(store, investigation_id, at)
    if asked_at is None:
        asked_at = _scripted_ask_time(scenario, at)
    if asked_at is None or asked_at > at:
        return None
    return {
        "status": status,
        "actor": actor,
        "decided_at": decided_at,
        "source": source,
        "requested_at": asked_at.isoformat(),
        "text": caregiver_permission_text(scenario, asked_at),
        "note": "approval only lets ARIA contact the HVAC company; it never changes readiness or verification",
    }


def _decision_as_of(caregiver_decision, at):
    """The effective caregiver choice at the replay time: later decisions do not leak backwards."""
    if caregiver_decision is None:
        return None, None
    get = (lambda name: caregiver_decision.get(name)) if isinstance(caregiver_decision, dict) else (lambda name: getattr(caregiver_decision, name, None))
    if get("decision") not in ("approved", "declined"):
        return None, None
    try:
        decided_at = datetime.fromisoformat(str(get("decided_at")).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None, None
    if decided_at > at:
        return None, None
    return get("decision"), decided_at


def _readiness_lead(status):
    return "Warm-by time passed" if status == "arrival_passed" else f"Readiness {_words(status)}"


def _plain_event_label(label):
    text = label.strip()
    if text.lower().startswith("simulated "):
        text = text[len("simulated "):]
        text = text[:1].upper() + text[1:] if text else text
    return text


def _event_activity_text(scenario, at, event, choice, decided_at, room_text, goal):
    kind = _get(event, "kind")
    try:
        context = context_as_of(scenario, at)
    except Exception:
        context = None
    confirmation = _get(context, "confirmation") if context is not None else None
    trip = _get(context, "trip") if context is not None else None
    if kind == "confirmation_request":
        target = _get(confirmation, "target_temp")
        unit = _get(confirmation, "target_unit") or "F"
        arrival = _get(trip, "planned_arrival")
        when = _clock(scenario, arrival) if isinstance(arrival, datetime) else None
        if target is not None and when is not None:
            plan = f"{target:g} {unit} by {when}"
        elif target is not None:
            plan = f"{target:g} {unit}"
        else:
            plan = "recorded"
        return f"Warm-by plan confirmed ({plan}); room {room_text}"
    if kind == "caregiver_alert":
        try:
            pack = build_evidence_pack(scenario, at)
        except Exception:
            pack = {}
        readiness = pack.get("readiness") if isinstance(pack, dict) else None
        status = readiness.get("status") if isinstance(readiness, dict) else "unknown"
        return f"{_readiness_lead(status)}: room {room_text}{goal}; permission request sent to the family caregiver"
    if kind == "caregiver_hvac_authorized":
        if choice == "approved" and decided_at is not None:
            return f"Family caregiver approved HVAC contact at {_clock(scenario, decided_at)}; HVAC may now be contacted"
        return "Family caregiver authorized contacting the HVAC company on file"
    payload = _get(event, "payload") or {}
    label = payload.get("label") if isinstance(payload, dict) else None
    if isinstance(label, str) and label.strip():
        return _plain_event_label(label)
    return f"{_words(kind)} available at {_clock(scenario, _get(event, 'available_at'))}"


def step_activity(scenario, at, follow_up=None, caregiver_decision=None):
    """One activity line for a replay step, always naming its source.

    The newest scenario event available since the previous checkpoint wins,
    unless the caregiver declined HVAC contact as of the replay time: contact,
    visit and report events then never happened, so they are skipped and the
    line says what is true instead. Otherwise the line is computed from the
    current readiness, thermostat reporting, or verification state. Text comes
    from the event payload or the computed values, never from a label map.
    A decision recorded later than the replay time never changes the line.
    """
    choice, decided_at = _decision_as_of(caregiver_decision, at)
    try:
        checkpoints = sorted(parsed_checkpoints(scenario.manifest.id))
    except Exception:
        checkpoints = []
    prev = scenario.manifest.start
    for checkpoint in checkpoints:
        if checkpoint >= at:
            break
        prev = checkpoint
    window = [e for e in events_as_of(scenario, at) if _get(e, "available_at") is not None and _get(e, "available_at") > prev and _get(e, "available_at") <= at]
    if choice == "declined":
        window = [e for e in window if _get(e, "kind") not in ("caregiver_hvac_authorized", "hvac_request", "technician_arrival", "service_visit", "hvac_completion_report")]
    visible = visible_records(getattr(scenario, "records", None) or [], at)
    room = [r for r in visible if _get(r, "source") is SourceKind.room_sensor and _get(r, "quantity") == "indoor_temp" and isinstance(_get(r, "value"), (int, float))]
    latest_room = max(room, key=lambda r: (_get(r, "observed_at"), _get(r, "received_at"), str(_get(r, "id")))) if room else None
    room_text = f"{_get(latest_room, 'value')} {_get(latest_room, 'unit')}" if latest_room is not None else "no room reading"
    try:
        confirmation = _get(context_as_of(scenario, at), "confirmation")
    except Exception:
        confirmation = None
    target = _get(confirmation, "target_temp")
    goal_word = "target" if _is_care_story(scenario) else "goal"
    goal = f" against the {target:g} F {goal_word}" if isinstance(target, (int, float)) else ""
    if choice == "declined":
        first_after = None
        for checkpoint in checkpoints:
            if decided_at is None or checkpoint >= decided_at:
                first_after = checkpoint
                break
        try:
            declined_pack = build_evidence_pack(scenario, at)
            declined_readiness = declined_pack.get("readiness") if isinstance(declined_pack, dict) else None
            declined_status = declined_readiness.get("status") if isinstance(declined_readiness, dict) else None
        except Exception:
            declined_status = None
        warm_by_passed = declined_status == "arrival_passed" or (checkpoints and at >= checkpoints[-1])
        if first_after is not None and at == first_after:
            when = _clock(scenario, decided_at) if decided_at is not None else "an unknown time"
            return {"text": f"Caregiver declined HVAC contact at {when}; nobody was contacted. Independent room sensor {room_text}", "source": "computed:caregiver_declined"}
        if warm_by_passed:
            return {"text": f"Warm-by time checked: {goal_word} missed; room {room_text}", "source": "computed:arrival_checked"}
        if isinstance(target, (int, float)):
            return {"text": f"No contact made; independent room sensor {room_text}, below the {target:g} F {goal_word}", "source": "computed:telemetry"}
        return {"text": f"No contact made; independent room sensor {room_text}{goal}", "source": "computed:telemetry"}
    if window:
        event = max(window, key=lambda e: (_get(e, "available_at"), _get(e, "event_time"), str(_get(e, "id"))))
        return {"text": _event_activity_text(scenario, at, event, choice, decided_at, room_text, goal), "source": f"event:{_get(event, 'id')}"}
    if follow_up is not None:
        try:
            verification = verify_recovery(scenario, follow_up, at)
        except Exception:
            verification = None
        stage = verification.get("stage") if isinstance(verification, dict) else None
        if stage is not None and stage != "telemetry_missing":
            try:
                entries = list(build_evidence_timeline(scenario, follow_up, at))
            except Exception:
                entries = []
            if choice == "declined":
                entries = [entry for entry in entries if entry["kind"] != "hvac_completion_report"]
            if entries:
                entry = entries[-1]
                return {"text": entry["label"], "source": f"computed:{entry['kind']}"}
            words = {"arrival_met": f"warm-by {goal_word} met", "goal_verified": f"{goal_word} verified", "goal_not_maintained": f"{goal_word} not maintained"}.get(stage, stage.replace("_", " "))
            return {"text": f"Verification {words}; room {room_text}", "source": "computed:verification"}
        return {"text": f"Thermostat not reporting; independent room sensor {room_text}", "source": "computed:telemetry"}
    try:
        pack = build_evidence_pack(scenario, at)
    except Exception:
        pack = {}
    readiness = pack.get("readiness") if isinstance(pack, dict) else None
    status = readiness.get("status") if isinstance(readiness, dict) else "unknown"
    if scenario.manifest.id == "care_home_v1" and caregiver_alert_level(readiness) == "notice" and isinstance(target, (int, float)) and latest_room is not None:
        below = target - _get(latest_room, "value")
        return {"text": f"Noticed: room {room_text} is {below:g} F below the {target:g} F target. No one is asked yet; ARIA asks at {ALERT_GAP_F:g} F below", "source": "computed:notice"}
    trend_clause = ""
    try:
        zones = sorted({r.subject for r in eligible_records(visible, "indoor_temp", now=at, require_value=False)})
    except Exception:
        zones = []
    try:
        trend = temperature_trend(visible, zones[0] if zones else "demo-house/main", at - timedelta(hours=3), at, at)
    except Exception:
        trend = {}
    rate = trend.get("rate_per_hour") if isinstance(trend, dict) else None
    if isinstance(trend, dict) and trend.get("sufficient") and isinstance(rate, (int, float)) and not isinstance(rate, bool):
        if rate < 0:
            trend_clause = f", falling {abs(round(rate * 10) / 10):g} F an hour"
        elif rate > 0:
            trend_clause = f", rising {round(rate * 10) / 10:g} F an hour"
    return {"text": f"{_readiness_lead(status)}: room {room_text}{goal}{trend_clause}", "source": "computed:readiness"}


def build_trace(scenario, at, entries=None, watcher_entries=None, review_entries=None, transcript_entries=None, caregiver_decision=None, investigation_id=None, store=None):
    pack = build_evidence_pack(scenario, at)
    identity = inference_identity(scenario, at)
    visible = visible_records(scenario.records, at)
    conflicted = _conflicted_ids(visible, at)

    statuses = pack.get("source_statuses") or []
    source_traces = [_source_trace(status, _latest_for(visible, status["source"] if isinstance(status, dict) else status.source.value), at, conflicted, scenario) for status in statuses]

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
    basis = SCRIPTED_BASIS
    if investigation_id is not None:
        inputs = investigation_trace_inputs(store, scenario, investigation_id, at) if store is not None else None
        if inputs is None:
            raise UnknownInvestigation(f"no stored follow-up for investigation {investigation_id}")
        followup = inputs["follow_up"]
        caregiver_decision = inputs["caregiver_decision"]
        basis = f"visitor investigation {investigation_id}"
        verification = _serialize_verification(inputs["verification"])
        verification["available"] = True
        timeline = _jsonable(build_evidence_timeline(scenario, followup, at, caregiver_decision))
    else:
        try:
            followup = follow_up_for(scenario, identity["investigation_id"], at)
        except ValueError as exc:
            followup, verification, timeline = None, {"available": False, "reason": str(exc)}, []
        else:
            verification = _serialize_verification(verify_recovery(scenario, followup, at))
            verification["available"] = True
            timeline = _jsonable(build_evidence_timeline(scenario, followup, at, caregiver_decision))

    watcher = _watcher_detail(scenario, at, pack, identity, watcher_entries)
    watcher_summary = public_watcher(scenario, at)

    human = human_report_for(scenario, at, transcript_entries, caregiver_decision)
    if human is None:
        human_trace = None
    else:
        human_trace = {
            "payload": _jsonable(human["payload"]),
            "timeline_entry": _jsonable(human["timeline_entry"]),
            "label": HUMAN_REPORT_LABEL,
            "note": "a person's report, not a sensor reading: a report, not proof",
        }

    investigation, _provenance = public_investigation(scenario, at, entries)
    context = context_as_of(scenario, at)
    events = events_as_of(scenario, at)
    verification_for_notif = {key: value for key, value in verification.items() if key != "available"} if verification.get("available") else None
    decisions = decide_notifications(investigation, readiness, verification_for_notif, context, events, at, scenario, identity["investigation_id"])
    decisions = list(decisions) + [decide_hvac_notification(investigation, readiness, verification_for_notif, context, events, at, scenario, investigation_id or identity["investigation_id"], caregiver_decision=caregiver_decision)]
    permission = _permission_trace(scenario, at, events, decisions, caregiver_decision, store=store, investigation_id=investigation_id)
    shown = decisions if _notices_exist(scenario, at, decisions, store, investigation_id) else []
    notices = [{"audience": item["audience"], "kind": item["kind"], "allowed": item["allowed"], "reason": item.get("reason"), "payload_keys": sorted((item.get("payload") or {}).keys())} for item in shown]

    steps = []
    for index, item in enumerate(source_traces):
        state = "pass" if item["availability"] == "available" and item["freshness"] == "fresh" and not item["conflicted"] else "stale" if item["freshness"] in ("stale", "missing") else "fail"
        steps.append({"seq": len(steps), "kind": "source", "label": f"{_words(item['source'])}: {item['availability']}", "state": state, "detail": item["freshness_reason"], "ref": {"section": "sources", "index": index}})
    for index, row in enumerate(check_rows):
        state = "pass" if row["passed"] is True else "fail" if row["passed"] is False else "stale"
        steps.append({"seq": len(steps), "kind": "check", "label": f"{row['check']} on {_words(row['target'])}", "state": state, "detail": row["reason"], "ref": {"section": "checks", "index": index}})
    steps.append({"seq": len(steps), "kind": "decision", "label": f"readiness: {READINESS_LABELS.get(readiness.get('status'), _words(readiness.get('status')))}", "state": "pass" if readiness.get("status") in ("on_track", "arrival_passed") else "fail" if readiness.get("status") == "at_risk" else "stale", "detail": _sentence(readiness.get("reasons")), "ref": {"section": "readiness", "index": 0}})
    if verification.get("available"):
        steps.append({"seq": len(steps), "kind": "decision", "label": f"verification: {_stage_label(scenario, verification.get('stage'))}", "state": "pass" if verification.get("stage") in ("goal_verified", "arrival_met") else "stale", "detail": _sentence(verification.get("reasons")), "ref": {"section": "verification", "index": 0}})
    else:
        steps.append({"seq": len(steps), "kind": "decision", "label": "verification: not available", "state": "stale", "detail": str(verification.get("reason", "")).split(": ", 1)[-1], "ref": {"section": "verification", "index": 0}})
    for index, obs in enumerate(watcher["observations"]):
        state = "pass" if obs.get("status") == "confirmed" else "fail"
        steps.append({"seq": len(steps), "kind": "model", "label": f"watcher: {obs.get('kind')}", "state": state, "detail": f"{obs.get('claim')} [{obs.get('status')}]", "ref": {"section": "watcher", "index": index}})
    if not watcher["observations"] and not watcher["code_detections"]:
        steps.append({"seq": len(steps), "kind": "model", "label": "no detection, never safe", "state": "quiet", "detail": "no model observation and no code detection at this time; absence of a detection is not an all-clear", "ref": {"section": "watcher", "index": 0}})
    for index, detection in enumerate(watcher["code_detections"]):
        steps.append({"seq": len(steps), "kind": "code", "label": f"code detection: {_words(detection.get('rule'))}", "state": "fail", "detail": detection.get("detail", ""), "ref": {"section": "code_detections", "index": index}})
    if human_trace is not None:
        steps.append({"seq": len(steps), "kind": "human", "label": "human report, not a measurement", "state": "stale", "detail": human_trace["payload"].get("transcript", "")[:200], "ref": {"section": "human", "index": 0}})
    if permission is not None:
        decided = _clock(scenario, permission["decided_at"]) if permission.get("decided_at") else "an unknown time"
        label = {
            "waiting": "caregiver permission: no answer yet — ARIA will not contact HVAC until the caregiver answers",
            "approved": f"caregiver permission: approved by the caregiver at {decided} — HVAC may now be contacted",
            "declined": f"caregiver permission: declined by the caregiver at {decided} — no HVAC request; verification continues from independent readings",
        }[permission["status"]]
        state = {"waiting": "stale", "approved": "pass", "declined": "fail"}[permission["status"]]
        steps.append({"seq": len(steps), "kind": "permission", "label": label, "state": state, "detail": f"{permission['text']} (asked at {_clock(scenario, permission['requested_at'])}; {permission['note']})", "ref": {"section": "permission", "index": 0}})
    for index, notice in enumerate(notices):
        state = "pass" if notice["allowed"] else "stale"
        steps.append({"seq": len(steps), "kind": "notice", "label": f"{_audience_words(scenario, notice['audience'])}: {'raised' if notice['allowed'] else 'refused'}", "state": state, "detail": REFUSAL_WORDS.get(notice["reason"], notice["reason"]) or f"fields: {', '.join(notice['payload_keys'])}", "ref": {"section": "notices", "index": index}})

    return {
        "trace_version": TRACE_VERSION,
        "computed_by": "deterministic code",
        "basis": basis,
        "scenario": scenario.manifest.id,
        "at": at.isoformat(),
        "input_revision": identity["input_revision"],
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "as_of_note": "only evidence received by this time is shown",
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


__all__ = ["TRACE_VERSION", "SCRIPTED_BASIS", "UnknownInvestigation", "build_trace", "investigation_trace_inputs"]
