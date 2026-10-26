from datetime import timedelta

from .clock import ensure_aware
from .contracts import Availability, EvidenceKind, SourceKind
from .evidence import freshness
from .metrics import NOISE_FLOOR_W

GOAL_HOLD_S = 1800
MAX_GAP_CADENCE_MULTIPLIER = 2
REPORT_EVENT_KIND = "hvac_completion_report"
CORROBORATION_EVENT_KINDS = (REPORT_EVENT_KIND,)
NON_CORROBORATING_EVENT_KINDS = ("manager_acknowledgement", "manager_acknowledged", "manager_hvac_authorized", "service_visit")
HEATING_REPORTED_STATES = {"heating", "heat", "heating_active"}
NON_HEATING_REPORTED_STATES = {"idle", "off", "cooling", "fan_only", "fan", "fault", "error", "failed"}
MAPPED_HEATING_EQUIPMENT = {"furnace", "blower", "heating", "hvac", "heat_pump", "heater"}


def _get(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _in_target_unit(value, unit, target_unit):
    value = float(value)
    if unit is None or unit == target_unit:
        return value
    if unit == "C" and target_unit == "F":
        return value * 9.0 / 5.0 + 32.0
    if unit == "F" and target_unit == "C":
        return (value - 32.0) * 5.0 / 9.0
    return value


def _rise_f(first, first_unit, last, last_unit, fallback_unit):
    def to_f(value, unit):
        effective = unit or fallback_unit
        return float(value) * 9.0 / 5.0 + 32.0 if effective == "C" else float(value)

    return to_f(last, last_unit) - to_f(first, first_unit)


def _dedup(records):
    seen = set()
    out = []
    for record in records:
        if record.id in seen:
            continue
        seen.add(record.id)
        out.append(record)
    return out


def _result(stage, reasons, supporting_ids, now, corroboration_ids, latest_reading_used=None):
    return {
        "stage": stage,
        "reasons": list(reasons),
        "supporting_ids": list(supporting_ids),
        "corroboration_ids": list(corroboration_ids),
        "corroboration": list(corroboration_ids),
        "evaluated_at": now,
        "latest_reading_used": latest_reading_used,
    }


def _reading_payload(record):
    if record is None:
        return None
    return {"id": record.id, "observed_at": record.observed_at, "received_at": record.received_at}


def _room_records(records, zone):
    room_all = sorted(
        [
            r
            for r in records
            if r.source is SourceKind.room_sensor
            and r.quantity == "indoor_temp"
            and r.subject == zone
            and r.kind is EvidenceKind.measurement
            and _is_number(r.value)
        ],
        key=lambda r: (r.observed_at, r.received_at, r.id),
    )
    seen_room = set()
    deduped = []
    for record in room_all:
        if record.observed_at in seen_room:
            continue
        seen_room.add(record.observed_at)
        deduped.append(record)
    return deduped


def _arrival(scenario, followup, now):
    try:
        from .scenario import context_as_of

        trip = context_as_of(scenario, now).trip
        if trip is not None:
            return trip.planned_arrival
    except Exception:
        pass
    trip = _get(scenario, "trip")
    if trip is not None:
        return _get(trip, "planned_arrival")
    deadline = _get(followup, "deadline")
    return deadline - timedelta(hours=2) if deadline is not None else None


def _goal_segment(room, followup):
    target = float(_get(followup, "target_temp"))
    target_unit = _get(followup, "target_unit")
    deadline = _get(followup, "deadline")
    cadence_s = next((r.expected_cadence_s for r in room if r.expected_cadence_s is not None), None)
    if cadence_s is None:
        cadence_s = _get(followup, "cadence_s")
    segment = []
    for record in room:
        if deadline is not None and record.observed_at > deadline:
            segment = []
            continue
        value = _in_target_unit(record.value, record.unit, target_unit)
        if value < target:
            segment = []
            continue
        if segment and cadence_s is not None:
            gap_s = (record.observed_at - segment[-1].observed_at).total_seconds()
            if gap_s > MAX_GAP_CADENCE_MULTIPLIER * cadence_s:
                segment = []
        segment.append(record)
        if segment and (record.observed_at - segment[0].observed_at).total_seconds() >= GOAL_HOLD_S:
            return segment, record.observed_at
    return None, None


def verify_recovery(scenario, followup, now):
    ensure_aware(now, "now")
    created_at = _get(followup, "created_at")
    deadline = _get(followup, "deadline")
    zone = _get(followup, "zone")
    target_temp = float(_get(followup, "target_temp"))
    target_unit = _get(followup, "target_unit")
    min_samples = int(_get(followup, "min_samples"))
    min_rise_f = float(_get(followup, "min_rise_f"))

    if isinstance(scenario, (list, tuple)):
        all_records = list(scenario)
        all_events = []
    else:
        all_records = list(_get(scenario, "records", []) or [])
        all_events = list(_get(scenario, "events", []) or [])
    records = _dedup([r for r in all_records if r.received_at <= now])
    events = [e for e in all_events if e.available_at <= now]
    corroboration_ids = [e.id for e in events if e.kind in CORROBORATION_EVENT_KINDS]
    corroboration_reasons = []
    if corroboration_ids:
        corroboration_reasons.append("hvac completion report is visible as corroboration only; it does not change the stage")

    thermostat = sorted(
        [r for r in records if r.source is SourceKind.thermostat and r.quantity == "indoor_temp"],
        key=lambda r: (r.observed_at, r.received_at, r.id),
    )
    if not thermostat or freshness(thermostat[-1], now) is not Availability.available:
        reasons = ["no fresh thermostat telemetry"]
        if thermostat:
            reasons.append(f"newest thermostat telemetry is {freshness(thermostat[-1], now).value}")
        reasons.extend(corroboration_reasons)
        early_room = _room_records(records, zone)
        latest_early = _reading_payload(early_room[-1]) if early_room else None
        return _result("telemetry_missing", reasons, [r.id for r in thermostat[-1:]] if thermostat else [], now, corroboration_ids, latest_early)

    gap_s = None
    post_gap = thermostat
    for earlier, later in zip(thermostat, thermostat[1:]):
        cadence_s = later.expected_cadence_s or earlier.expected_cadence_s
        gap = (later.observed_at - earlier.observed_at).total_seconds()
        if cadence_s is not None and gap > MAX_GAP_CADENCE_MULTIPLIER * cadence_s and (gap_s is None or gap > gap_s):
            gap_s = gap
            post_gap = [r for r in thermostat if r.observed_at >= later.observed_at]
    restored_ids = [r.id for r in post_gap]
    restored_reasons = ["fresh thermostat telemetry after a gap"] if gap_s is not None else ["fresh thermostat telemetry is available"]

    room_all = _room_records(records, zone)
    latest_room = _reading_payload(room_all[-1]) if room_all else None

    if not room_all:
        reasons = restored_reasons + ["room-sensor readings are missing"] + corroboration_reasons
        return _result("unable_to_verify", reasons, restored_ids, now, corroboration_ids, latest_room)
    if freshness(room_all[-1], now) is not Availability.available:
        reasons = restored_reasons + [f"room-sensor readings are {freshness(room_all[-1], now).value}"] + corroboration_reasons
        return _result("unable_to_verify", reasons, restored_ids, now, corroboration_ids, latest_room)

    room_after = [r for r in room_all if r.observed_at > created_at and (deadline is None or r.observed_at <= deadline)]
    if not room_after:
        reasons = restored_reasons + ["no room-sensor readings after the follow-up was created"] + corroboration_reasons
        return _result("unable_to_verify", reasons, restored_ids, now, corroboration_ids, latest_room)
    latest_used = _reading_payload(room_after[-1])

    states = sorted(
        [r for r in records if r.source is SourceKind.thermostat and r.quantity == "hvac_reported_state"],
        key=lambda r: (r.observed_at, r.received_at, r.id),
    )
    state_record = states[-1] if states else None
    state_value = str(state_record.value).strip().lower() if state_record is not None and state_record.value is not None else None
    state_contradicts = state_value in NON_HEATING_REPORTED_STATES
    state_supports = state_value in HEATING_REPORTED_STATES

    mapped_by_circuit = {}
    for record in records:
        if record.quantity != "circuit_power" or not record.binding:
            continue
        equipment = (record.binding.equipment or "").strip().lower()
        if equipment not in MAPPED_HEATING_EQUIPMENT:
            continue
        circuit_id = record.binding.circuit_id or record.subject
        mapped_by_circuit.setdefault(circuit_id, []).append(record)
    circuit_support_ids = []
    circuit_contradicts = False
    circuit_checked = False
    for group in mapped_by_circuit.values():
        group.sort(key=lambda r: (r.observed_at, r.received_at, r.id))
        latest = group[-1]
        if freshness(latest, now) is not Availability.available or not _is_number(latest.value):
            continue
        circuit_checked = True
        if float(latest.value) > NOISE_FLOOR_W:
            circuit_support_ids.append(latest.id)
        else:
            circuit_contradicts = True
    if circuit_checked and not circuit_support_ids:
        circuit_contradicts = True
    else:
        circuit_contradicts = circuit_contradicts and not circuit_support_ids

    rise_f = None
    if room_after:
        first, last = room_after[0], room_after[-1]
        rise_f = _rise_f(first.value, first.unit, last.value, last.unit, target_unit)
    warming_reasons = list(restored_reasons)
    if len(room_after) < min_samples:
        warming_reasons.append(f"only {len(room_after)} room-sensor readings after the follow-up was created; {min_samples} required for warming")
    if rise_f is None or rise_f < min_rise_f:
        warming_reasons.append(f"room-sensor rise {rise_f} F is below the required {min_rise_f} F" if rise_f is not None else "room-sensor rise is unavailable")
    if state_contradicts:
        warming_reasons.append(f"reported thermostat state {state_value!r} contradicts heating")
    if circuit_contradicts:
        warming_reasons.append("mapped circuit activity contradicts heating")
    warming_reasons.extend(corroboration_reasons)
    if len(room_after) < min_samples or rise_f is None or rise_f < min_rise_f or state_contradicts or circuit_contradicts:
        return _result("reporting_restored", warming_reasons, restored_ids, now, corroboration_ids, latest_used)

    warming_ids = [r.id for r in room_after]
    if state_supports and state_record is not None:
        warming_ids.append(state_record.id)
    warming_ids.extend(circuit_support_ids)
    warming_reasons.append("independent room-sensor readings show warming")
    if state_supports:
        warming_reasons.append("reported thermostat state does not contradict heating")
    if circuit_support_ids:
        warming_reasons.append("mapped circuit activity is supporting only and does not prove heating")

    segment, verified_at = _goal_segment(room_after, followup)
    if segment is None:
        reasons = warming_reasons + [f"temperature goal has not been held at or above {target_temp} {target_unit} for {GOAL_HOLD_S} s without a gap over {MAX_GAP_CADENCE_MULTIPLIER}x cadence before the deadline"]
        return _result("warming_observed", reasons, warming_ids, now, corroboration_ids, latest_used)

    goal_ids = [r.id for r in segment]
    goal_reasons = warming_reasons + [f"every room-sensor reading held at or above {target_temp} {target_unit} for {GOAL_HOLD_S} s before the deadline"]
    arrival = _arrival(scenario, followup, now)
    if arrival is None or now < arrival:
        return _result("goal_verified", goal_reasons + corroboration_reasons, goal_ids, now, corroboration_ids, latest_used)

    through_arrival = [r for r in room_all if verified_at <= r.observed_at <= arrival]
    arrival_latest = _reading_payload(through_arrival[-1]) if through_arrival else latest_used
    if not through_arrival:
        return _result("goal_verified", goal_reasons + ["no room-sensor readings from verification through the confirmed arrival"] + corroboration_reasons, goal_ids, now, corroboration_ids, arrival_latest)
    if any(_in_target_unit(r.value, r.unit, target_unit) < target_temp for r in through_arrival):
        return _result("goal_verified", goal_reasons + ["a room-sensor reading from verification through the confirmed arrival is below the target"] + corroboration_reasons, goal_ids, now, corroboration_ids, arrival_latest)
    cadence_s = next((r.expected_cadence_s for r in through_arrival if r.expected_cadence_s is not None), None)
    if cadence_s is not None and len(through_arrival) >= 2:
        gaps = [(b.observed_at - a.observed_at).total_seconds() for a, b in zip(through_arrival, through_arrival[1:])]
        if gaps and max(gaps) > MAX_GAP_CADENCE_MULTIPLIER * cadence_s:
            return _result("goal_verified", goal_reasons + ["a gap in room-sensor readings from verification through the confirmed arrival exceeds 2x cadence"] + corroboration_reasons, goal_ids, now, corroboration_ids, arrival_latest)
    arrival_ids = list(dict.fromkeys(goal_ids + [r.id for r in through_arrival]))
    return _result("arrival_met", goal_reasons + ["every room-sensor reading from verification through the confirmed arrival is at or above the target"] + corroboration_reasons, arrival_ids, now, corroboration_ids, arrival_latest)
