"""The declined night: what care_home_v1 looks like after a caregiver decline.

A decline means nobody was contacted, so the recorded visit, the warming
curve, the resumed thermostat feed and the completion report never happened.
This module derives that night deterministically from the loaded base
scenario at request time: no fixture files are read or written.

The derivation keeps every record id, kind, provenance, binding and meter
assignment, so anything keyed on record identity (evidence packs, input
revisions, outcome histories) stays comparable with the base night. Only
values after the would-be visit begins change, plus the thermostat records
after its outage began and the four scripted HVAC/visit events:

- room sensor: unchanged until the visit would have ended, then the same
  3.644 F an hour fall to a 52.0 F floor, holding until 04:00, then down
  0.2 F per hour, rounded to 0.1 F.
- blower circuit: capped at its pre-visit maximum (no warming signature).
- thermostat: records after the outage began are removed (no 04:20 resume).
- events: caregiver_hvac_authorized, hvac_request, service_visit and
  hvac_completion_report are removed.

All boundaries (visit start, pre-visit blower maximum, thermostat cutoff)
come from the loaded data; the hold/fall shape above is the declined-night
model. Readiness, verification, outcomes and every status are still computed
by the existing code from the derived data, never hard-coded here.
"""
from dataclasses import replace
from datetime import timedelta

DECLINED_SCENARIO_ID = "care_home_v1"

VISIT_EVENT_KIND = "service_visit"

REMOVED_EVENT_KINDS = frozenset({
    "caregiver_hvac_authorized",
    "hvac_request",
    "technician_arrival",
    "service_visit",
    "hvac_completion_report",
})

VISIT_LENGTH = timedelta(minutes=45)
HOLD_AFTER_VISIT_START = timedelta(hours=4, minutes=30)
COOLING_F_PER_HOUR = 3.644
FALL_F_PER_HOUR = 0.2
HOLD_TEMP_F = 52.0
BLOWER_CIRCUIT_ID = "circuit-blower"


def _visit_start(scenario):
    starts = [e.event_time for e in (getattr(scenario, "events", None) or []) if e.kind == VISIT_EVENT_KIND]
    return min(starts) if starts else None


def _thermostat_cutoff(scenario):
    """Last thermostat reading before its first sampling gap over 2x cadence."""
    temps = sorted(
        (r for r in (getattr(scenario, "records", None) or []) if r.source.value == "thermostat"),
        key=lambda r: (r.observed_at, r.received_at, r.id),
    )
    cutoff = None
    for earlier, later in zip(temps, temps[1:]):
        cadence_s = later.expected_cadence_s or earlier.expected_cadence_s or 300
        if (later.observed_at - earlier.observed_at).total_seconds() > 2 * cadence_s:
            break
        cutoff = later.observed_at
    if cutoff is None and temps:
        cutoff = temps[-1].observed_at
    return cutoff


def _pre_visit_blower_max(scenario, visit_start):
    values = [
        float(r.value)
        for r in (getattr(scenario, "records", None) or [])
        if r.quantity == "circuit_power"
        and (r.binding.circuit_id if r.binding else r.subject) == BLOWER_CIRCUIT_ID
        and isinstance(r.value, (int, float))
        and r.observed_at < visit_start
    ]
    return max(values) if values else None


def _declined_room_value(observed_at, visit_start, value_at_visit_end):
    fall_start = visit_start + HOLD_AFTER_VISIT_START
    if observed_at < fall_start:
        hours_cooling = (observed_at - (visit_start + VISIT_LENGTH)).total_seconds() / 3600.0
        return round(max(HOLD_TEMP_F, value_at_visit_end - COOLING_F_PER_HOUR * hours_cooling), 1)
    hours = (observed_at - fall_start).total_seconds() / 3600.0
    return round(HOLD_TEMP_F - FALL_F_PER_HOUR * hours, 1)


def declined_view(scenario):
    """The care_home_v1 night as if a visible decline stopped the HVAC visit."""
    if scenario is None or scenario.manifest.id != DECLINED_SCENARIO_ID:
        return scenario
    if getattr(scenario, "declined_view", False):
        return scenario
    visit_start = _visit_start(scenario)
    cutoff = _thermostat_cutoff(scenario)
    blower_max = _pre_visit_blower_max(scenario, visit_start) if visit_start is not None else None
    visit_end = visit_start + VISIT_LENGTH if visit_start is not None else None
    value_at_visit_end = next((r.value for r in scenario.records if r.source.value == "room_sensor" and r.quantity == "indoor_temp" and r.observed_at == visit_end), None)
    records = []
    for record in scenario.records:
        if record.source.value == "thermostat" and cutoff is not None and record.observed_at > cutoff:
            continue
        if visit_start is not None and record.observed_at >= visit_start:
            if record.source.value == "room_sensor" and record.quantity == "indoor_temp" and isinstance(record.value, (int, float)):
                if value_at_visit_end is None or record.observed_at <= visit_end:
                    records.append(record)
                else:
                    records.append(record.model_copy(update={"value": _declined_room_value(record.observed_at, visit_start, value_at_visit_end)}))
                continue
            if record.quantity == "circuit_power" and (record.binding.circuit_id if record.binding else record.subject) == BLOWER_CIRCUIT_ID and isinstance(record.value, (int, float)) and blower_max is not None:
                records.append(record.model_copy(update={"value": min(float(record.value), blower_max)}))
                continue
        records.append(record)
    events = [e for e in (getattr(scenario, "events", None) or []) if e.kind not in REMOVED_EVENT_KINDS]
    visuals = [item for item in (getattr(scenario, "visuals", None) or []) if not (isinstance(item, dict) and "warm-morning" in str(item.get("image_id")))]
    return replace(scenario, records=records, events=events, visuals=visuals, declined_view=True)
