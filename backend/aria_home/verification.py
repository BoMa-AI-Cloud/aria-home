import math
from datetime import timedelta

from .clock import ensure_aware
from .contracts import Availability, EvidenceKind, SourceKind
from .eligibility import circuit_records, eligible_records, indoor_records, is_fresh, is_measurement_eligible, measurement_conflict_groups, normalized_measurement_value
from .evidence import freshness
from .metrics import NOISE_FLOOR_W

GOAL_HOLD_S = 1800
MAX_GAP_CADENCE_MULTIPLIER = 2
REPORT_EVENT_KIND = "hvac_completion_report"
CORROBORATION_EVENT_KINDS = (REPORT_EVENT_KIND,)
NON_CORROBORATING_EVENT_KINDS = ("manager_acknowledgement", "manager_acknowledged", "manager_hvac_authorized", "caregiver_hvac_authorized", "caregiver_alert", "service_visit")
HEATING_REPORTED_STATES = {"heating", "heat", "heating_active"}
NON_HEATING_REPORTED_STATES = {"idle", "off", "cooling", "fan_only", "fan", "fault", "error", "failed"}
MAPPED_HEATING_EQUIPMENT = {"furnace", "blower", "heating", "hvac", "heat_pump", "heater"}


def _get(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _in_target_unit(value, unit, target_unit):
    value = float(value)
    if not math.isfinite(value):
        return math.nan
    if unit is None or unit == target_unit:
        return value
    if unit == "C" and target_unit == "F":
        result = value * 9.0 / 5.0 + 32.0
        return result if math.isfinite(result) else math.nan
    if unit == "F" and target_unit == "C":
        result = (value - 32.0) * 5.0 / 9.0
        return result if math.isfinite(result) else math.nan
    return value


def _rise_f(first, first_unit, last, last_unit, fallback_unit):
    def to_f(value, unit):
        effective = unit or fallback_unit
        result = float(value) * 9.0 / 5.0 + 32.0 if effective == "C" else float(value)
        return result if math.isfinite(result) else math.nan

    result = to_f(last, last_unit) - to_f(first, first_unit)
    return result if math.isfinite(result) else None


def _dedup(records):
    seen = set()
    out = []
    for record in records:
        value = normalized_measurement_value(record)
        if value is None:
            value = record.value if isinstance(record.value, str) else repr(record.value)
        key = (record.id, record.source, record.subject, record.quantity, record.observed_at, value)
        if key in seen:
            continue
        seen.add(key)
        out.append(record)
    return out


def _result(stage, reasons, supporting_ids, now, corroboration_ids, latest_reading_used=None, goal_verified_at=None, arrival_met_at=None):
    return {
        "stage": stage,
        "reasons": list(reasons),
        "supporting_ids": list(supporting_ids),
        "corroboration_ids": list(corroboration_ids),
        "corroboration": list(corroboration_ids),
        "evaluated_at": now,
        "latest_reading_used": latest_reading_used,
        "goal_verified_at": goal_verified_at,
        "arrival_met_at": arrival_met_at,
    }


def _reading_payload(record):
    if record is None:
        return None
    return {"id": record.id, "observed_at": record.observed_at, "received_at": record.received_at}


def _room_records(records, zone):
    return sorted(
        [r for r in indoor_records(records, zone) if r.source is SourceKind.room_sensor],
        key=lambda r: (r.observed_at, r.received_at, r.id),
    )


def _room_conflict_groups(records, zone):
    return [
        item
        for item in measurement_conflict_groups(records, quantity="indoor_temp", zone=zone)
        if item["source"] == SourceKind.room_sensor.value
    ]


def _room_conflict_times(records, zone):
    return {item["observed_at"] for item in _room_conflict_groups(records, zone)}


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


def _goal_analysis(room, followup, conflict_times=None):
    target = float(_get(followup, "target_temp"))
    target_unit = _get(followup, "target_unit")
    deadline = _get(followup, "deadline")
    cadence_s = next((r.expected_cadence_s for r in room if r.expected_cadence_s is not None), None)
    if cadence_s is None:
        cadence_s = _get(followup, "cadence_s")
    conflicts = sorted(
        t for t in (conflict_times or set()) if deadline is None or t <= deadline
    )
    eligible = []
    segment = []
    verified_at = None
    verified_segment = []
    completed = False
    events = [(r.observed_at, 0, r) for r in room] + [(t, 1, None) for t in conflicts]
    events.sort(key=lambda item: (item[0], item[1]))
    for observed_at, kind, record in events:
        if deadline is not None and observed_at > deadline:
            segment = []
            completed = False
            continue
        if record is None:
            segment = []
            completed = False
            continue
        eligible.append(record)
        value = _in_target_unit(record.value, record.unit, target_unit)
        if not math.isfinite(value) or value < target:
            segment = []
            completed = False
            continue
        if segment and cadence_s is not None:
            gap_s = (record.observed_at - segment[-1].observed_at).total_seconds()
            if gap_s > MAX_GAP_CADENCE_MULTIPLIER * cadence_s:
                segment = []
                completed = False
        segment.append(record)
        if not completed and (record.observed_at - segment[0].observed_at).total_seconds() >= GOAL_HOLD_S:
            verified_at = record.observed_at
            verified_segment = list(segment)
            completed = True
    dips_after = []
    gaps_after = []
    conflicts_after = []
    if verified_at is not None:
        conflicts_after = [t for t in conflicts if t > verified_at]
        dips_after = [
            r
            for r in eligible
            if r.observed_at > verified_at and _in_target_unit(r.value, r.unit, target_unit) < target
        ]
        if cadence_s is not None:
            for earlier, later in zip(eligible, eligible[1:]):
                if earlier.observed_at >= verified_at and (later.observed_at - earlier.observed_at).total_seconds() > MAX_GAP_CADENCE_MULTIPLIER * cadence_s:
                    gaps_after.append((earlier, later))
    return {
        "eligible": eligible,
        "segment": segment,
        "verified_at": verified_at,
        "verified_segment": verified_segment,
        "dips_after": dips_after,
        "gaps_after": gaps_after,
        "conflict_times": conflicts,
        "conflicts_after": conflicts_after,
        "cadence_s": cadence_s,
    }


def _goal_segment(room, followup):
    analysis = _goal_analysis(room, followup)
    if analysis["verified_at"] is None:
        return None, None
    return analysis["verified_segment"], analysis["verified_at"]


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

    conflict_groups_all = _room_conflict_groups(records, zone)
    conflict_times_all = {item["observed_at"] for item in conflict_groups_all}
    _hist_room = _room_records(records, zone)
    _hist_after = [r for r in _hist_room if r.observed_at > created_at and (deadline is None or r.observed_at <= deadline)]
    _hist_conflicts = {t for t in conflict_times_all if t > created_at}
    historical_verified_at = _goal_analysis(_hist_after, followup, _hist_conflicts)["verified_at"]

    thermostat = sorted(
        [r for r in eligible_records(records, "indoor_temp", zone=zone) if r.source is SourceKind.thermostat],
        key=lambda r: (r.observed_at, r.received_at, r.id),
    )
    if not thermostat or freshness(thermostat[-1], now) is not Availability.available:
        reasons = ["no fresh thermostat telemetry"]
        if thermostat:
            reasons.append(f"newest thermostat telemetry is {freshness(thermostat[-1], now).value}")
        reasons.extend(corroboration_reasons)
        early_room = _room_records(records, zone)
        latest_early = _reading_payload(early_room[-1]) if early_room else None
        return _result("telemetry_missing", reasons, [r.id for r in thermostat[-1:]] if thermostat else [], now, corroboration_ids, latest_early, goal_verified_at=historical_verified_at)

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
        return _result("unable_to_verify", reasons, restored_ids, now, corroboration_ids, latest_room, goal_verified_at=historical_verified_at)
    if freshness(room_all[-1], now) is not Availability.available:
        reasons = restored_reasons + [f"room-sensor readings are {freshness(room_all[-1], now).value}"] + corroboration_reasons
        if historical_verified_at is not None:
            reasons.append(f"temperature goal was verified at {historical_verified_at.isoformat()} but current maintenance cannot be verified from stale or missing readings")
        return _result("unable_to_verify", reasons, restored_ids, now, corroboration_ids, latest_room, goal_verified_at=historical_verified_at)

    arrival = _arrival(scenario, followup, now)
    late_start = arrival is not None and now >= arrival and created_at >= arrival
    if late_start:
        room_base = [r for r in room_all if r.observed_at <= arrival and (deadline is None or r.observed_at <= deadline)]
        conflict_base = {t for t in conflict_times_all if t <= arrival and (deadline is None or t <= deadline)}
    else:
        room_base = [r for r in room_all if r.observed_at > created_at and (deadline is None or r.observed_at <= deadline)]
        conflict_base = {t for t in conflict_times_all if t > created_at and (deadline is None or t <= deadline)}
    if not room_base:
        if late_start:
            reasons = restored_reasons + ["no room-sensor readings observed by the warm-by time"] + corroboration_reasons
        else:
            reasons = restored_reasons + ["no room-sensor readings after the follow-up was created"] + corroboration_reasons
        return _result("unable_to_verify", reasons, restored_ids, now, corroboration_ids, latest_room, goal_verified_at=historical_verified_at)
    latest_used = _reading_payload(room_base[-1])

    states = sorted(
        [r for r in records if r.source is SourceKind.thermostat and r.quantity == "hvac_reported_state" and r.subject == zone],
        key=lambda r: (r.observed_at, r.received_at, r.id),
    )
    state_record = states[-1] if states and is_fresh(states[-1], now) else None
    state_value = str(state_record.value).strip().lower() if state_record is not None and state_record.value is not None else None
    state_supports = state_value in HEATING_REPORTED_STATES
    state_non_heating = state_value in NON_HEATING_REPORTED_STATES

    property_id = zone.split("/")[0] if zone else None
    mapped_by_circuit = {}
    for record in records:
        if record.quantity != "circuit_power" or not record.binding:
            continue
        if not is_measurement_eligible(record, quantity="circuit_power"):
            continue
        meter_id = getattr(record, "meter_id", None)
        if meter_id is not None and property_id and not (meter_id == property_id or meter_id.startswith(f"{property_id}-")):
            continue
        equipment = (record.binding.equipment or "").strip().lower()
        if equipment not in MAPPED_HEATING_EQUIPMENT:
            continue
        circuit_id = record.binding.circuit_id or record.subject
        mapped_by_circuit.setdefault(circuit_id, []).append(record)
    circuit_support_ids = []
    circuit_checked = False
    circuit_quiet = False
    for group in mapped_by_circuit.values():
        group.sort(key=lambda r: (r.observed_at, r.received_at, r.id))
        latest = group[-1]
        if not is_fresh(latest, now) or not _is_number(latest.value):
            continue
        circuit_checked = True
        if float(latest.value) > NOISE_FLOOR_W:
            circuit_support_ids.append(latest.id)
        else:
            circuit_quiet = True
    if circuit_support_ids:
        circuit_quiet = False

    conflict_times_after = conflict_base
    analysis = _goal_analysis(room_base, followup, conflict_times_after)
    verified_at = analysis["verified_at"]
    segment = analysis["verified_segment"]

    equipment_reasons = []
    if state_supports:
        equipment_reasons.append("reported thermostat state supports heating as a separate equipment observation")
    elif state_non_heating:
        equipment_reasons.append(f"reported thermostat state {state_value!r} is a separate equipment observation and does not determine the temperature result")
    if circuit_support_ids:
        equipment_reasons.append("mapped circuit activity is supporting only as a separate equipment observation and does not prove heating")
    elif circuit_checked and circuit_quiet:
        equipment_reasons.append("mapped heating circuit is quiet as a separate equipment observation and does not determine the temperature result")

    if verified_at is not None:
        if analysis["conflicts_after"]:
            when = analysis["conflicts_after"][0]
            reasons = restored_reasons + [f"conflicting room-sensor readings at {when.isoformat()} after the temperature goal was verified; the conflicting readings are not resolved by record order"] + corroboration_reasons
            return _result("unable_to_verify", reasons, restored_ids, now, corroboration_ids, latest_used, goal_verified_at=verified_at)
        goal_ids = [r.id for r in segment]
        goal_reasons = restored_reasons + equipment_reasons + ["independent room-sensor readings show the temperature goal held"] + [f"every room-sensor reading held at or above {target_temp} {target_unit} for {GOAL_HOLD_S} s before the deadline"]
        if analysis["dips_after"]:
            dip = analysis["dips_after"][-1]
            dip_value = _in_target_unit(dip.value, dip.unit, target_unit)
            reasons = goal_reasons + [f"room-sensor reading {dip.id} at {dip.observed_at.isoformat()} is {dip_value} {target_unit}, below the {target_temp} {target_unit} target, after the goal was verified at {verified_at.isoformat()}; the goal is no longer maintained and a new full {GOAL_HOLD_S} s hold is required"] + corroboration_reasons
            support = list(dict.fromkeys(goal_ids + [r.id for r in analysis["dips_after"]] + [r.id for r in analysis["segment"]]))
            return _result("goal_not_maintained", reasons, support, now, corroboration_ids, latest_used, goal_verified_at=verified_at)
        if arrival is None or now < arrival:
            if analysis["gaps_after"]:
                earlier, later = analysis["gaps_after"][0]
                gap_value = (later.observed_at - earlier.observed_at).total_seconds()
                reason = f"room-sensor coverage after verification is incomplete: gap of {gap_value:.0f} s from {earlier.observed_at.isoformat()} to {later.observed_at.isoformat()} exceeds {MAX_GAP_CADENCE_MULTIPLIER}x cadence; current goal maintenance cannot be verified and a new full {GOAL_HOLD_S} s hold is required"
                return _result("unable_to_verify", goal_reasons + [reason] + corroboration_reasons, goal_ids, now, corroboration_ids, latest_used, goal_verified_at=verified_at)
            return _result("goal_verified", goal_reasons + corroboration_reasons, goal_ids, now, corroboration_ids, latest_used, goal_verified_at=verified_at)
        arrival_room = [r for r in room_base if r.observed_at <= arrival]
        arrival_conflicts = {t for t in conflict_times_after if t <= arrival}
        arrival_analysis = _goal_analysis(arrival_room, followup, arrival_conflicts)
        verified_at_arrival = arrival_analysis["verified_at"]
        if verified_at_arrival is None:
            return _result("goal_verified", goal_reasons + ["the temperature goal was verified after the confirmed arrival"] + corroboration_reasons, goal_ids, now, corroboration_ids, latest_used, goal_verified_at=verified_at)
        arrival_segment = arrival_analysis["verified_segment"]
        arrival_goal_ids = [r.id for r in arrival_segment]
        if any(arrival_segment[0].observed_at <= t <= arrival for t in arrival_analysis["conflict_times"]):
            when = next(t for t in arrival_analysis["conflict_times"] if arrival_segment[0].observed_at <= t <= arrival)
            reasons = goal_reasons + [f"conflicting room-sensor readings at {when.isoformat()} inside the arrival interval; the conflicting readings are not resolved by record order"] + corroboration_reasons
            return _result("unable_to_verify", reasons, arrival_goal_ids, now, corroboration_ids, latest_used, goal_verified_at=verified_at_arrival)
        if arrival_analysis["conflicts_after"]:
            when = arrival_analysis["conflicts_after"][0]
            reasons = goal_reasons + [f"conflicting room-sensor readings at {when.isoformat()} inside the arrival interval; the conflicting readings are not resolved by record order"] + corroboration_reasons
            return _result("unable_to_verify", reasons, arrival_goal_ids, now, corroboration_ids, latest_used, goal_verified_at=verified_at_arrival)
        through_arrival = [r for r in room_all if verified_at_arrival <= r.observed_at <= arrival]
        arrival_latest = _reading_payload(through_arrival[-1]) if through_arrival else latest_used
        if not through_arrival:
            return _result("unable_to_verify", goal_reasons + ["room-sensor coverage from verification through the confirmed arrival is incomplete: no eligible room-sensor readings at or before arrival; readings observed after arrival do not cover the pre-arrival interval"] + corroboration_reasons, arrival_goal_ids, now, corroboration_ids, arrival_latest, goal_verified_at=verified_at_arrival)
        cadence_s = next((r.expected_cadence_s for r in through_arrival if r.expected_cadence_s is not None), None)
        if cadence_s is None:
            cadence_s = next((r.expected_cadence_s for r in arrival_segment if r.expected_cadence_s is not None), None)
        if cadence_s is None:
            cadence_s = _get(followup, "cadence_s")
        if cadence_s is None:
            return _result("unable_to_verify", goal_reasons + ["room-sensor coverage from verification through the confirmed arrival cannot be verified: expected cadence is unavailable"] + corroboration_reasons, arrival_goal_ids, now, corroboration_ids, arrival_latest, goal_verified_at=verified_at_arrival)
        max_gap_s = MAX_GAP_CADENCE_MULTIPLIER * cadence_s
        coverage_points = [verified_at_arrival] + [r.observed_at for r in through_arrival] + [arrival]
        for start, end in zip(coverage_points, coverage_points[1:]):
            gap_value = (end - start).total_seconds()
            if gap_value > max_gap_s:
                reason = f"room-sensor coverage from verification through the confirmed arrival is incomplete: gap of {gap_value:.0f} s from {start.isoformat()} to {end.isoformat()} exceeds {MAX_GAP_CADENCE_MULTIPLIER}x cadence ({max_gap_s:.0f} s); readings observed after arrival do not cover the pre-arrival interval"
                return _result("unable_to_verify", goal_reasons + [reason] + corroboration_reasons, arrival_goal_ids, now, corroboration_ids, arrival_latest, goal_verified_at=verified_at_arrival)
        if any(_in_target_unit(r.value, r.unit, target_unit) < target_temp for r in through_arrival):
            if verified_at > arrival:
                return _result("goal_verified", goal_reasons + ["the temperature goal was verified after the confirmed arrival"] + corroboration_reasons, goal_ids, now, corroboration_ids, arrival_latest, goal_verified_at=verified_at)
            dip = next(r for r in through_arrival if _in_target_unit(r.value, r.unit, target_unit) < target_temp)
            reasons = goal_reasons + [f"room-sensor reading {dip.id} at {dip.observed_at.isoformat()} is below the {target_temp} {target_unit} target before the confirmed arrival, after the goal was verified at {verified_at_arrival.isoformat()}; the goal is no longer maintained and a new full {GOAL_HOLD_S} s hold is required"] + corroboration_reasons
            return _result("goal_not_maintained", reasons, arrival_goal_ids, now, corroboration_ids, arrival_latest, goal_verified_at=verified_at_arrival)
        arrival_ids = list(dict.fromkeys(arrival_goal_ids + [r.id for r in through_arrival]))
        return _result("arrival_met", goal_reasons + ["every room-sensor reading from verification through the confirmed arrival is at or above the target with no coverage gap over 2x cadence"] + corroboration_reasons, arrival_ids, now, corroboration_ids, arrival_latest, goal_verified_at=verified_at_arrival, arrival_met_at=arrival)

    candidate = _goal_analysis(room_base, followup, set())
    if candidate["verified_at"] is not None and candidate["verified_segment"]:
        seg_start = candidate["verified_segment"][0].observed_at
        inside = [t for t in sorted(conflict_times_after) if seg_start <= t <= candidate["verified_at"]]
        if inside:
            reasons = restored_reasons + [f"conflicting room-sensor readings at {inside[0].isoformat()} inside the required hold interval; the conflicting readings are not resolved by record order"] + corroboration_reasons
            return _result("unable_to_verify", reasons, restored_ids, now, corroboration_ids, latest_used, goal_verified_at=historical_verified_at if historical_verified_at and historical_verified_at < seg_start else None)

    if late_start:
        reasons = restored_reasons + [f"the temperature goal was not held at or above {target_temp} {target_unit} for {GOAL_HOLD_S} s before the warm-by time"] + corroboration_reasons
        return _result("unable_to_verify", reasons, restored_ids, now, corroboration_ids, latest_used, goal_verified_at=historical_verified_at)

    rise_f = None
    if room_base:
        first, last = room_base[0], room_base[-1]
        rise_f = _rise_f(first.value, first.unit, last.value, last.unit, target_unit)
    warming_reasons = list(restored_reasons)
    if len(room_base) < min_samples:
        warming_reasons.append(f"only {len(room_base)} room-sensor readings after the follow-up was created; {min_samples} required for warming")
    if rise_f is None or rise_f < min_rise_f:
        warming_reasons.append(f"room-sensor rise {rise_f} F is below the required {min_rise_f} F" if rise_f is not None else "room-sensor rise is unavailable")
    warming_reasons.extend(equipment_reasons)
    warming_reasons.extend(corroboration_reasons)
    if analysis["segment"] and len(room_base) >= min_samples and _in_target_unit(room_base[-1].value, room_base[-1].unit, target_unit) >= target_temp and (rise_f is None or rise_f < min_rise_f):
        reasons = restored_reasons + equipment_reasons + [f"temperature is at or above the target but has not been held for {GOAL_HOLD_S} s"] + corroboration_reasons
        return _result("reporting_restored", reasons, restored_ids, now, corroboration_ids, latest_used, goal_verified_at=historical_verified_at)
    if len(room_base) < min_samples or rise_f is None or rise_f < min_rise_f:
        return _result("reporting_restored", warming_reasons, restored_ids, now, corroboration_ids, latest_used, goal_verified_at=historical_verified_at)
    warming_ids = [r.id for r in room_base]
    if state_supports and state_record is not None:
        warming_ids.append(state_record.id)
    warming_ids.extend(circuit_support_ids)
    warming_reasons.append("independent room-sensor readings show warming")
    reasons = warming_reasons + [f"temperature goal has not been held at or above {target_temp} {target_unit} for {GOAL_HOLD_S} s without a gap over {MAX_GAP_CADENCE_MULTIPLIER}x cadence before the deadline"]
    return _result("warming_observed", reasons, warming_ids, now, corroboration_ids, latest_used, goal_verified_at=historical_verified_at)


def _timeline_entry(kind, label, supporting_ids, observed_at, received_at, first_known_at, corroboration_only=False):
    return {
        "kind": kind,
        "label": label,
        "supporting_ids": list(supporting_ids),
        "supporting_record_ids": list(supporting_ids),
        "observed_at": observed_at,
        "received_at": received_at,
        "available_at": received_at,
        "first_known_at": first_known_at,
        "evaluated_at": first_known_at,
        "corroboration_only": corroboration_only,
    }


def build_evidence_timeline(scenario, followup, now):
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
    entries = []

    thermostat = sorted(
        [r for r in eligible_records(records, "indoor_temp", zone=zone) if r.source is SourceKind.thermostat],
        key=lambda r: (r.observed_at, r.received_at, r.id),
    )
    restored = None
    restored_earlier = None
    for earlier, later in zip(thermostat, thermostat[1:]):
        cadence_s = later.expected_cadence_s or earlier.expected_cadence_s
        if cadence_s is not None and (later.observed_at - earlier.observed_at).total_seconds() > MAX_GAP_CADENCE_MULTIPLIER * cadence_s and later.observed_at > created_at:
            restored = later
            restored_earlier = earlier
            break
    if restored is not None:
        first_known = max(restored.received_at, restored_earlier.received_at)
        entries.append(_timeline_entry("reporting_restored", "Thermostat reporting restored", [restored.id], restored.observed_at, restored.received_at, first_known))

    room_all = _room_records(records, zone)
    room_after = [r for r in room_all if r.observed_at > created_at and (deadline is None or r.observed_at <= deadline)]
    if room_after:
        first = room_after[0]
        for index, record in enumerate(room_after):
            if index + 1 < min_samples:
                continue
            rise_f = _rise_f(first.value, first.unit, record.value, record.unit, target_unit)
            if rise_f is not None and rise_f >= min_rise_f:
                first_known = max(r.received_at for r in room_after[: index + 1])
                entries.append(_timeline_entry("warming_observed", "Warming first observed", [first.id, record.id], record.observed_at, record.received_at, first_known))
                break
        for record in room_after:
            if _in_target_unit(record.value, record.unit, target_unit) >= target_temp:
                entries.append(_timeline_entry("target_reached", "Target first reached", [record.id], record.observed_at, record.received_at, record.received_at))
                break

    _timeline_conflicts = _room_conflict_times(records, zone)
    analysis = _goal_analysis(room_after, followup, {t for t in _timeline_conflicts if t > created_at}) if room_after else {"verified_at": None, "verified_segment": []}
    verified_at = analysis["verified_at"]
    verified_segment = analysis["verified_segment"]
    if verified_at is not None and verified_segment:
        last = verified_segment[-1]
        first_known = max(r.received_at for r in verified_segment)
        entries.append(_timeline_entry("goal_verified", "Hold completed and goal verified", [r.id for r in verified_segment], verified_at, last.received_at, first_known))

    for event in sorted(events, key=lambda e: (e.available_at, e.event_time, e.id)):
        if event.kind in CORROBORATION_EVENT_KINDS:
            entries.append(_timeline_entry("hvac_completion_report", "HVAC completion report available", [event.id], event.event_time, event.available_at, event.available_at, corroboration_only=True))

    arrival = _arrival(scenario, followup, now)
    if arrival is not None and now >= arrival:
        through = [r for r in room_all if r.observed_at <= arrival and r.observed_at > created_at]
        if through and through[-1].observed_at >= arrival:
            last = through[-1]
            segment_known = max((r.received_at for r in verified_segment), default=last.received_at)
            first_known = max(arrival, last.received_at, segment_known)
            if first_known <= now:
                support = list(dict.fromkeys([r.id for r in verified_segment] + [last.id]))
                entries.append(_timeline_entry("arrival_checked", "Arrival checked", support, arrival, last.received_at, first_known))

    entries = [e for e in entries if e["first_known_at"] <= now]
    entries.sort(key=lambda e: (e["first_known_at"], e["observed_at"], e["kind"]))
    return entries


evidence_timeline = build_evidence_timeline
