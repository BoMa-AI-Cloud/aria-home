from datetime import datetime, timedelta

from .contracts import Availability, SourceKind
from .eligibility import eligible_records
from .evidence import freshness
from .metrics import target_gap, temperature_trend
from .scenario import context_as_of, events_as_of, visible_records
from .scheduling import compute_follow_up_schedule

AUDIENCES = ("homeowner", "property_manager", "family_caregiver", "hvac_company")

ALLOWLISTS = {
    "homeowner": {"audience", "kind", "readiness", "readiness_in_words", "stage", "stage_in_words", "verified_facts", "what_was_done", "evaluated_at", "planned_arrival"},
    "property_manager": {"audience", "kind", "property_label", "verified_facts", "readiness", "requested_action", "access_note"},
    "family_caregiver": {"audience", "kind", "property_label", "verified_facts", "readiness", "requested_action", "access_note"},
    "hvac_company": {"audience", "kind", "property_label", "access_note", "manager_contact_label", "relevant_observations"},
}

CAREGIVER_SCENARIOS = frozenset({"care_home_v1"})

HVAC_AUTH_EVENT_KINDS = ("manager_hvac_authorized", "caregiver_hvac_authorized")

FORBIDDEN_KEY_PARTS = ("trip", "itinerary", "email", "phone", "location", "flight")

READINESS_IN_WORDS = {
    "on_track": "On track: the property is expected to be ready on arrival, based on the verified facts.",
    "at_risk": "At risk: the property may not be ready on arrival, based on the verified facts.",
    "cannot_tell": "Cannot tell yet whether the property will be ready on arrival, based on the verified facts.",
}

STAGE_IN_WORDS = {
    "telemetry_missing": "Thermostat telemetry is missing.",
    "reporting_restored": "Thermostat reporting is restored; recovery is not yet verified.",
    "warming_observed": "Warming has been observed in independent readings.",
    "goal_verified": "The temperature goal has been verified.",
    "goal_not_maintained": "The temperature goal was verified earlier but is no longer being maintained.",
    "arrival_met": "The temperature goal was still met at arrival.",
    "unable_to_verify": "Recovery cannot be verified from the available readings.",
}

MANAGER_REQUESTED_ACTION = "Please review the verified facts and decide whether to contact the HVAC company on file."
CAREGIVER_REQUESTED_ACTION = "Please review the home status and observations and decide whether to contact the HVAC company on file."
DEFAULT_ACCESS_NOTE = "Access arranged through the property manager (synthetic label)"
DEFAULT_MANAGER_CONTACT_LABEL = "property manager on file (synthetic label)"
DEFAULT_CAREGIVER_ACCESS_NOTE = "Access arranged through the family caregiver (synthetic label)"
DEFAULT_CAREGIVER_CONTACT_LABEL = "family caregiver on file (synthetic label)"


def _uses_caregiver(scenario):
    manifest = _get(scenario, "manifest")
    return _get(manifest, "id") in CAREGIVER_SCENARIOS


def _get(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _check_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in FORBIDDEN_KEY_PARTS):
                raise ValueError(f"forbidden notification payload key: {key}")
            _check_keys(item)
    elif isinstance(value, list):
        for item in value:
            _check_keys(item)


def validate_payload(audience, payload):
    if audience not in ALLOWLISTS:
        raise ValueError(f"unknown audience: {audience}")
    extra = set(payload) - ALLOWLISTS[audience]
    if extra:
        raise ValueError(f"payload keys outside {audience} allowlist: {sorted(extra)}")
    _check_keys(payload)
    return payload


def verified_facts_from(investigation=None, readiness=None):
    output = _get(investigation, "output")
    facts = _get(output, "verified_facts") if output is not None else None
    if not facts and isinstance(investigation, dict):
        facts = investigation.get("verified_facts")
        nested = investigation.get("investigation")
        if not facts and isinstance(nested, dict):
            facts = (nested.get("output") or {}).get("verified_facts")
    if facts:
        return [str(item) for item in facts]
    reasons = _get(readiness, "reasons") or []
    return [str(item) for item in reasons]


def _readiness_status(readiness, investigation=None):
    status = _get(readiness, "status")
    if status:
        return str(status)
    pack = _get(investigation, "evidence_pack") or {}
    pack_readiness = pack.get("readiness") if isinstance(pack, dict) else None
    if isinstance(pack_readiness, dict) and pack_readiness.get("status"):
        return str(pack_readiness["status"])
    output = _get(investigation, "output")
    output_readiness = _get(output, "readiness") if output is not None else None
    return str(output_readiness) if output_readiness else "cannot_tell"


def _stage(verification):
    stage = _get(verification, "stage")
    return str(stage) if stage else None


def _property_label(context, scenario=None):
    trip = _get(context, "trip")
    confirmation = _get(context, "confirmation")
    for obj in (trip, confirmation):
        label = _get(obj, "property_id") if obj is not None else None
        if label:
            return str(label)
    trip = _get(scenario, "trip")
    label = _get(trip, "property_id") if trip is not None else None
    return str(label) if label else "demo-house"


def _event_payload(events, kind):
    for event in events or []:
        if _get(event, "kind") == kind:
            payload = _get(event, "payload") or {}
            return payload if isinstance(payload, dict) else {}
    return {}


def _access_and_contact(events, scenario=None):
    payload = _event_payload(events, "hvac_request")
    if _uses_caregiver(scenario):
        access = payload.get("access_note") or DEFAULT_CAREGIVER_ACCESS_NOTE
        contact = payload.get("manager_contact") or payload.get("manager_contact_label") or DEFAULT_CAREGIVER_CONTACT_LABEL
    else:
        access = payload.get("access_note") or DEFAULT_ACCESS_NOTE
        contact = payload.get("manager_contact") or payload.get("manager_contact_label") or DEFAULT_MANAGER_CONTACT_LABEL
    return str(access), str(contact)


def build_payload(audience, investigation=None, readiness=None, verification=None, context=None, events=None, now=None, scenario=None):
    status = _readiness_status(readiness, investigation)
    stage = _stage(verification)
    facts = verified_facts_from(investigation, readiness)
    access_note, manager_contact = _access_and_contact(events, scenario)
    if audience == "homeowner":
        trip = _get(context, "trip")
        payload = {
            "audience": audience,
            "kind": "investigation_update",
            "readiness": status,
            "readiness_in_words": READINESS_IN_WORDS.get(status, READINESS_IN_WORDS["cannot_tell"]),
            "stage": stage,
            "stage_in_words": STAGE_IN_WORDS.get(stage, "Recovery has not been verified yet.") if stage else "Recovery has not been verified yet.",
            "verified_facts": facts,
            "what_was_done": ["Investigation evaluated by deterministic code", "Readiness computed by deterministic code"] + (["Recovery verification evaluated by deterministic code"] if verification else []),
            "evaluated_at": _iso(now),
            "planned_arrival": _iso(_get(trip, "planned_arrival")) if trip is not None else None,
        }
    elif audience == "property_manager":
        payload = {
            "audience": audience,
            "kind": "manager_alert",
            "property_label": _property_label(context, scenario),
            "verified_facts": facts,
            "readiness": status,
            "requested_action": MANAGER_REQUESTED_ACTION,
            "access_note": access_note,
        }
    elif audience == "family_caregiver":
        payload = {
            "audience": audience,
            "kind": "caregiver_alert",
            "property_label": _property_label(context, scenario),
            "verified_facts": facts,
            "readiness": status,
            "requested_action": CAREGIVER_REQUESTED_ACTION,
            "access_note": access_note,
        }
    elif audience == "hvac_company":
        observations = facts or [str(item) for item in (_get(readiness, "reasons") or [])]
        payload = {
            "audience": audience,
            "kind": "hvac_request",
            "property_label": _property_label(context, scenario),
            "access_note": access_note,
            "manager_contact_label": manager_contact,
            "relevant_observations": observations,
        }
    else:
        raise ValueError(f"unknown audience: {audience}")
    return validate_payload(audience, payload)


def homeowner_refusal_reason(context):
    confirmation = _get(context, "confirmation")
    if confirmation is None:
        return "homeowner_preference_missing"
    value = _get(confirmation, "notify_homeowner")
    if value is True:
        return None
    if value is False:
        return "homeowner_opted_out"
    return "homeowner_preference_missing"


def homeowner_is_authorized(context):
    return homeowner_refusal_reason(context) is None


def manager_is_authorized(context):
    confirmation = _get(context, "confirmation")
    return bool(confirmation is not None and _get(confirmation, "manager_authorized"))


def caregiver_is_authorized(context):
    confirmation = _get(context, "confirmation")
    return bool(confirmation is not None and _get(confirmation, "manager_authorized"))


def hvac_is_authorized(events):
    return any(_get(event, "kind") in HVAC_AUTH_EVENT_KINDS for event in (events or []))


def _decision(audience, kind, allowed, reason, payload, investigation_id):
    return {
        "audience": audience,
        "kind": kind,
        "allowed": allowed,
        "reason": reason,
        "payload": payload,
        "idempotency_key": f"{investigation_id}:{audience}:{kind}",
    }


def decide_notifications(investigation=None, readiness=None, verification=None, context=None, events=None, now=None, scenario=None, investigation_id=""):
    """Homeowner: only an as-of confirmation with notify_homeowner is True allows delivery.

    A False preference is refused as homeowner_opted_out; a missing or
    unknown preference is refused as homeowner_preference_missing. There is
    no emergency/status override. This gate is independent of manager
    authorization. Refused decisions are persisted by callers as refused
    audit rows, never delivered.
    """
    status = _readiness_status(readiness, investigation)
    decisions = []
    homeowner = build_payload("homeowner", investigation, readiness, verification, context, events, now, scenario)
    reason = homeowner_refusal_reason(context)
    decisions.append(_decision("homeowner", homeowner["kind"], reason is None, reason, homeowner, investigation_id))
    if status in ("at_risk", "cannot_tell"):
        if _uses_caregiver(scenario):
            caregiver = build_payload("family_caregiver", investigation, readiness, verification, context, events, now, scenario)
            if caregiver_is_authorized(context):
                decisions.append(_decision("family_caregiver", caregiver["kind"], True, None, caregiver, investigation_id))
            else:
                decisions.append(_decision("family_caregiver", caregiver["kind"], False, "caregiver_not_authorized", caregiver, investigation_id))
        else:
            manager = build_payload("property_manager", investigation, readiness, verification, context, events, now, scenario)
            if manager_is_authorized(context):
                decisions.append(_decision("property_manager", manager["kind"], True, None, manager, investigation_id))
            else:
                decisions.append(_decision("property_manager", manager["kind"], False, "manager_not_authorized", manager, investigation_id))
    return decisions


def decide_hvac_notification(investigation=None, readiness=None, verification=None, context=None, events=None, now=None, scenario=None, investigation_id="", caregiver_decision=None):
    """A caregiver decision recorded in the app wins over the scripted authorisation event."""
    payload = build_payload("hvac_company", investigation, readiness, verification, context, events, now, scenario)
    decided = _get(caregiver_decision, "decision") if caregiver_decision is not None else None
    if decided == "declined":
        return _decision("hvac_company", payload["kind"], False, "caregiver_declined", payload, investigation_id)
    if decided == "approved" or hvac_is_authorized(events):
        return _decision("hvac_company", payload["kind"], True, None, payload, investigation_id)
    reason = "caregiver_hvac_not_authorized" if _uses_caregiver(scenario) else "manager_hvac_not_authorized"
    return _decision("hvac_company", payload["kind"], False, reason, payload, investigation_id)


def _deterministic_created_at(store, scenario, investigation_id, gate_at, discovery_at):
    if gate_at is None or discovery_at is None:
        return discovery_at
    follow_up = None
    try:
        follow_up = store.get_follow_up(investigation_id)
    except Exception:
        follow_up = None
    anchor = _get(follow_up, "created_at") if follow_up is not None else None
    if anchor is None:
        try:
            row = store.get_investigation(investigation_id)
        except Exception:
            row = None
        raw_anchor = row.get("evaluated_at") or row.get("created_at") if isinstance(row, dict) else None
        anchor = raw_anchor if isinstance(raw_anchor, datetime) else None
        if anchor is None and isinstance(raw_anchor, str):
            try:
                anchor = datetime.fromisoformat(raw_anchor.replace("Z", "+00:00"))
            except ValueError:
                anchor = None
    if anchor is None:
        return discovery_at
    deadline = _get(follow_up, "deadline") if follow_up is not None else None
    cadence_s = _get(follow_up, "cadence_s") if follow_up is not None else None
    if cadence_s is None and scenario is not None:
        cadence_s = next((r.expected_cadence_s for r in (getattr(scenario, "records", None) or []) if r.quantity == "indoor_temp" and r.expected_cadence_s is not None), None)
    if gate_at <= anchor:
        return min(anchor, discovery_at) if discovery_at >= anchor else anchor
    current = anchor
    for _ in range(10000):
        schedule = compute_follow_up_schedule(current, deadline=deadline, cadence_s=cadence_s)
        nxt = schedule.get("next_check_at") if hasattr(schedule, "get") else None
        if nxt is None or nxt <= current:
            return discovery_at
        if nxt >= gate_at:
            return min(nxt, discovery_at)
        current = nxt
    return discovery_at


def _persist_decisions(store, investigation_id, decisions, created_at):
    rows = []
    for decision in decisions:
        if decision["allowed"]:
            row = store.save_notification(
                investigation_id=investigation_id,
                audience=decision["audience"],
                kind=decision["kind"],
                idempotency_key=decision["idempotency_key"],
                payload=decision["payload"],
                created_at=created_at,
                delivery="simulated",
                state="queued",
            )
            if row and row["state"] == "queued":
                row = store.update_notification_state(row["id"], "simulated_delivered")
            rows.append(row)
        else:
            rows.append(store.save_notification(
                investigation_id=investigation_id,
                audience=decision["audience"],
                kind=decision["kind"],
                idempotency_key=f"{decision['idempotency_key']}:refused:{decision['reason']}",
                payload=decision["payload"],
                created_at=created_at,
                delivery="simulated",
                state="refused",
                refusal_reason=decision["reason"],
            ))
    return rows


def create_investigation_notifications(store, scenario, investigation_id, investigation, readiness, at, verification=None):
    context = context_as_of(scenario, at) if scenario is not None else None
    events = events_as_of(scenario, at) if scenario is not None else []
    decisions = decide_notifications(investigation, readiness, verification, context, events, at, scenario, investigation_id)
    return _persist_decisions(store, investigation_id, decisions, at)


def _as_datetime(value):
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def create_hvac_notification(store, scenario, investigation_id, investigation, readiness, at, verification=None, caregiver_decision=None):
    context = context_as_of(scenario, at) if scenario is not None else None
    events = events_as_of(scenario, at) if scenario is not None else []
    decision = decide_hvac_notification(investigation, readiness, verification, context, events, at, scenario, investigation_id, caregiver_decision=caregiver_decision)
    created_at = at
    if decision["allowed"] and scenario is not None:
        if caregiver_decision is not None and _get(caregiver_decision, "decision") == "approved":
            gate_at = _as_datetime(_get(caregiver_decision, "decided_at"))
        else:
            gate_at = next((_get(e, "available_at") for e in (getattr(scenario, "events", None) or []) if _get(e, "kind") in HVAC_AUTH_EVENT_KINDS), None)
        created_at = _deterministic_created_at(store, scenario, investigation_id, gate_at, at)
    return _persist_decisions(store, investigation_id, [decision], created_at)[0]


def _latest_visible(scenario, at, source, quantity=None):
    visible = [
        r for r in (getattr(scenario, "records", None) or [])
        if r.received_at <= at and r.source.value == source and (quantity is None or r.quantity == quantity)
    ]
    return max(visible, key=lambda r: r.observed_at) if visible else None


NON_HEATING_STATES = frozenset({"idle", "off"})


def _whole(value):
    return str(int(round(float(value))))


def _thermostat_clause(records, at):
    temps = sorted(
        [r for r in eligible_records(records, "indoor_temp", now=at, require_value=False) if _get(r, "source") is SourceKind.thermostat],
        key=lambda r: (_get(r, "observed_at"), _get(r, "received_at"), str(_get(r, "id"))),
    )
    if not temps:
        return "thermostat not reporting"
    latest = temps[-1]
    if freshness(latest, at) is not Availability.available:
        return f"thermostat not reporting since {_get(latest, 'observed_at').strftime('%H:%M')}"
    states = sorted(
        [r for r in records if _get(r, "source") is SourceKind.thermostat and _get(r, "quantity") == "hvac_reported_state"],
        key=lambda r: (_get(r, "observed_at"), _get(r, "received_at"), str(_get(r, "id"))),
    )
    if not states:
        return None
    state = str(_get(states[-1], "value") or "").lower()
    if state not in NON_HEATING_STATES:
        return None
    start = _get(states[-1], "observed_at")
    for record in reversed(states[:-1]):
        if str(_get(record, "value") or "").lower() != state:
            break
        start = _get(record, "observed_at")
    return f"furnace reported {state} since {start.strftime('%H:%M')}"


def caregiver_permission_text(scenario, at):
    """The permission request, built only from readings visible at `at`; a missing reading is said, never invented."""
    records = visible_records(getattr(scenario, "records", None) or [], at) if scenario is not None else []
    room = _latest_visible(scenario, at, "room_sensor", "indoor_temp") if scenario is not None else None
    room_value = _get(room, "value")
    temp = f"{_whole(room_value)} F" if isinstance(room_value, (int, float)) else "temperature unknown"
    zones = sorted({_get(r, "subject") for r in eligible_records(records, "indoor_temp", now=at, require_value=False)})
    zone = zones[0] if zones else "demo-house/main"
    trend = temperature_trend(records, zone, at - timedelta(hours=3), at, at)
    rate = trend.get("rate_per_hour")
    cooling = bool(trend.get("sufficient")) and isinstance(rate, (int, float)) and rate < 0
    parts = [temp]
    try:
        confirmation = _get(context_as_of(scenario, at), "confirmation") if scenario is not None else None
    except Exception:
        confirmation = None
    target = _get(confirmation, "target_temp") if confirmation is not None else None
    if target is not None and isinstance(room_value, (int, float)) and trend.get("last_value") is not None:
        unit = _get(confirmation, "target_unit") or "F"
        gap = target_gap(trend, float(target), unit)
        if gap is not None:
            if gap["gap"] < 0:
                parts.append(f"{_whole(abs(gap['gap']))} F below the {_whole(target)} F target")
            elif gap["gap"] > 0:
                parts.append(f"{_whole(gap['gap'])} F above the {_whole(target)} F target")
            else:
                parts.append(f"at the {_whole(target)} F target")
    clause = _thermostat_clause(records, at)
    if clause is not None:
        parts.append(clause)
    below = target is None or not isinstance(room_value, (int, float)) or float(room_value) < float(target)
    state = "cooling" if cooling else ("below target" if below else "at or above target")
    if not isinstance(room_value, (int, float)):
        state = "at an unknown temperature"
        parts = parts[1:]
    detail = f" ({', '.join(parts)})" if parts else ""
    return f"ARIA Home (synthetic scenario): your mother's home is {state}{detail}. May I contact the HVAC company? Approve or decline in ARIA Home."


CAREGIVER_UPDATES = {
    "caregiver_update_hvac_contacted": "HVAC company contacted with the allowed fields only",
    "caregiver_update_goal_verified": "Temperature goal verified from independent room readings",
}


def create_caregiver_updates(store, scenario, investigation_id, hvac_row, verification, at):
    """Simulated for-your-information updates to the caregiver after the HVAC request and after verification."""
    if hvac_row is None or hvac_row.get("state") != "simulated_delivered":
        return []
    hvac_payload = hvac_row.get("payload") or {}
    due = [("caregiver_update_hvac_contacted", _as_datetime(hvac_row.get("created_at")))]
    if verification and verification.get("stage") in ("goal_verified", "arrival_met") and verification.get("goal_verified_at"):
        due.append(("caregiver_update_goal_verified", _as_datetime(verification["goal_verified_at"])))
    rows = []
    for kind, created_at in due:
        payload = validate_payload("family_caregiver", {
            "audience": "family_caregiver",
            "kind": kind,
            "property_label": hvac_payload.get("property_label"),
            "verified_facts": [CAREGIVER_UPDATES[kind]],
            "readiness": "informational",
            "requested_action": "No action needed: for your information",
            "access_note": hvac_payload.get("access_note"),
        })
        rows.extend(_persist_decisions(store, investigation_id, [_decision("family_caregiver", kind, True, None, payload, investigation_id)], created_at))
    return rows
