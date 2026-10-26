from datetime import datetime, timedelta, timezone
from pathlib import Path

from aria_home.scenario import events_as_of, load_scenario

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "demo_video_v1"
TZ = timezone(timedelta(hours=-5))


def at(hour, minute=0, second=0):
    return datetime(2026, 1, 16, hour, minute, second, tzinfo=TZ)


def _by_source(source):
    scenario = load_scenario(SCENARIO_DIR)
    return [r for r in scenario.records if r.source.value == source]


def test_demo_video_scenario_loads():
    scenario = load_scenario(SCENARIO_DIR)
    assert scenario.manifest.id == "demo_video_v1"
    assert scenario.trip is not None
    assert scenario.trip.planned_arrival == at(21)
    assert scenario.confirmation is not None
    assert scenario.confirmation.target_temp == 68
    assert {r.source.value for r in scenario.records} >= {
        "calendar",
        "thermostat",
        "room_sensor",
        "electrical",
        "weather",
    }
    for r in scenario.records:
        if r.source.value in {"thermostat", "room_sensor", "electrical"} and r.observed_at >= at(6):
            assert r.received_at - r.observed_at == timedelta(seconds=20)


def test_no_thermostat_record_during_outage():
    records = _by_source("thermostat")
    assert records
    assert max(r.observed_at for r in records if r.observed_at <= at(15, 30)) == at(15, 30)
    assert min(r.observed_at for r in records if r.observed_at >= at(18, 20)) == at(18, 20)
    assert not [r for r in records if at(15, 30) < r.observed_at < at(18, 20)]


def test_room_sensor_continues_through_outage():
    records = sorted(
        (r for r in _by_source("room_sensor") if r.quantity == "indoor_temp"),
        key=lambda r: r.observed_at,
    )
    assert records[0].observed_at == at(6)
    assert records[-1].observed_at == at(21, 30)
    assert all(
        b.observed_at - a.observed_at == timedelta(minutes=5)
        for a, b in zip(records, records[1:])
    )
    outage = [r for r in records if at(15, 30) < r.observed_at < at(18, 20)]
    assert len(outage) > 30
    assert all(51.5 <= r.value <= 52.5 for r in outage)


def test_room_sensor_recovery_shape():
    records = {r.observed_at: r.value for r in _by_source("room_sensor") if r.quantity == "indoor_temp"}
    assert abs(records[at(6)] - 55.0) <= 0.5
    assert abs(records[at(15, 30)] - 52.0) <= 0.5
    assert records[at(18, 50)] - records[at(18, 35)] >= 2.0
    assert records[at(19, 50)] == 68.0


def test_every_room_reading_after_1950_at_least_68():
    records = [r for r in _by_source("room_sensor") if r.quantity == "indoor_temp" and r.observed_at > at(19, 50)]
    assert records
    assert all(r.value >= 68.0 for r in records)


def test_thermostat_matches_room_sensor_within_half_degree():
    room = {r.observed_at: r.value for r in _by_source("room_sensor") if r.quantity == "indoor_temp"}
    temps = [r for r in _by_source("thermostat") if r.quantity == "indoor_temp"]
    assert temps
    assert all(abs(r.value - room[r.observed_at]) <= 0.5 for r in temps)
    states = [r for r in _by_source("thermostat") if r.quantity == "hvac_reported_state"]
    assert {r.observed_at for r in states} == {r.observed_at for r in temps}


def test_electrical_blower_and_other_circuits():
    records = _by_source("electrical")
    blower = [r for r in records if r.subject == "circuit-blower"]
    assert blower and all(r.binding.status.value == "candidate" and r.binding.equipment == "blower" for r in blower)
    during = [r.value for r in blower if at(15, 30) <= r.observed_at < at(18, 20)]
    after = [r.value for r in blower if r.observed_at > at(18, 20)]
    assert during and all(400 <= v <= 600 for v in during)
    assert after and all(850 <= v <= 950 for v in after)
    others = {r.subject for r in records if r.subject != "circuit-blower"}
    assert len(others) == 2
    for subject in others:
        rows = [r for r in records if r.subject == subject]
        assert min(r.observed_at for r in rows) == at(6)
        assert max(r.observed_at for r in rows) == at(21, 30)
        assert all(r.value > 15 for r in rows)


def test_every_event_hidden_before_available_at():
    scenario = load_scenario(SCENARIO_DIR)
    assert scenario.events
    for event in scenario.events:
        assert event not in events_as_of(scenario, event.available_at - timedelta(seconds=1))
        assert event in events_as_of(scenario, event.available_at)


def test_report_available_after_verification_at_2021():
    scenario = load_scenario(SCENARIO_DIR)
    report = next(e for e in scenario.events if e.kind == "hvac_completion_report")
    assert report.available_at > at(20, 21)


def test_hvac_request_payload_has_no_itinerary_email_location_keys():
    scenario = load_scenario(SCENARIO_DIR)
    request = next(e for e in scenario.events if e.kind == "hvac_request")
    keys = {k.lower() for k in request.payload}
    assert not any(word in key for key in keys for word in ("itinerary", "email", "location"))
