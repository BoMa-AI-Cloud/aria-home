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

- room sensor: 52.0 F from the visit start through the first half hour,
  then down 0.2 F per hour, rounded to 0.1 F.
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
    "service_visit",
    "hvac_completion_report",
})

HOLD_AFTER_VISIT_START = timedelta(minutes=30)
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


def _declined_room_value(observed_at, visit_start):
    fall_start = visit_start + HOLD_AFTER_VISIT_START
    if observed_at < fall_start:
        return HOLD_TEMP_F
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
    records = []
    for record in scenario.records:
        if record.source.value == "thermostat" and cutoff is not None and record.observed_at > cutoff:
            continue
        if visit_start is not None and record.observed_at >= visit_start:
            if record.source.value == "room_sensor" and record.quantity == "indoor_temp" and isinstance(record.value, (int, float)):
                records.append(record.model_copy(update={"value": _declined_room_value(record.observed_at, visit_start)}))
                continue
            if record.quantity == "circuit_power" and (record.binding.circuit_id if record.binding else record.subject) == BLOWER_CIRCUIT_ID and isinstance(record.value, (int, float)) and blower_max is not None:
                records.append(record.model_copy(update={"value": min(float(record.value), blower_max)}))
                continue
        records.append(record)
    events = [e for e in (getattr(scenario, "events", None) or []) if e.kind not in REMOVED_EVENT_KINDS]
    return replace(scenario, records=records, events=events, declined_view=True)
