import json
from datetime import timedelta
from pathlib import Path

from aria_home.app import create_app
from aria_home.metrics import temperature_trend
from aria_home.scenario import events_as_of, load_scenario

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "demo_v1"
ZONE = "demo-house/main"


def _copy_scenario(tmp_path, with_room_sensor=True):
    target = tmp_path / "scenario"
    target.mkdir()
    for name in ["manifest.json", "calendar.json", "thermostat.json", "electrical.json", "weather.json"]:
        (target / name).write_text((SCENARIO_DIR / name).read_text(encoding="utf-8"), encoding="utf-8")
    if with_room_sensor:
        records = [
            {
                "id": f"room-temp-{label}",
                "source": "room_sensor",
                "kind": "measurement",
                "subject": ZONE,
                "quantity": "indoor_temp",
                "value": value,
                "unit": "F",
                "observed_at": observed,
                "received_at": received,
                "expected_cadence_s": 3600,
                "mode": "synthetic",
                "provenance": {"fixture_id": "demo_v1", "version": "1"},
            }
            for label, value, observed, received in [
                ("1500", 60.0, "2026-01-16T15:00:00-05:00", "2026-01-16T15:00:20-05:00"),
                ("1600", 62.0, "2026-01-16T16:00:00-05:00", "2026-01-16T16:00:20-05:00"),
                ("1700", 64.0, "2026-01-16T17:00:00-05:00", "2026-01-16T17:00:20-05:00"),
            ]
        ]
        (target / "room_sensor.json").write_text(json.dumps({"records": records}), encoding="utf-8")
        events = [
            {"id": "evt-early", "kind": "actor", "event_time": "2026-01-16T15:30:00-05:00", "available_at": "2026-01-16T15:30:00-05:00", "simulated": True, "payload": {"action": "arrived"}},
            {"id": "evt-late", "kind": "actor", "event_time": "2026-01-16T17:30:00-05:00", "available_at": "2026-01-16T17:30:00-05:00", "simulated": True, "payload": {"action": "left"}},
        ]
        (target / "events.json").write_text(json.dumps({"events": events}), encoding="utf-8")
    return target


def test_room_sensor_preferred_for_trend(tmp_path):
    scenario = load_scenario(_copy_scenario(tmp_path))
    start = scenario.manifest.start
    end = start + timedelta(hours=3)
    trend = temperature_trend(scenario.records, ZONE, start, end, end)
    assert trend["sample_count"] == 3
    assert trend["first_value"] == 60.0
    assert trend["last_value"] == 64.0
    assert trend["change"] == 4.0


def test_thermostat_used_when_room_sensor_absent(tmp_path):
    scenario = load_scenario(_copy_scenario(tmp_path, with_room_sensor=False))
    assert scenario.events == []
    start = scenario.manifest.start
    end = start + timedelta(hours=3)
    trend = temperature_trend(scenario.records, ZONE, start, end, end)
    assert trend["sample_count"] >= 3
    assert trend["first_value"] == 52.0
    assert 51.0 <= trend["last_value"] <= 53.0


def test_events_hidden_before_available_at(tmp_path):
    scenario = load_scenario(_copy_scenario(tmp_path))
    start = scenario.manifest.start
    assert [e.id for e in events_as_of(scenario, start + timedelta(minutes=29))] == []
    assert [e.id for e in events_as_of(scenario, start + timedelta(minutes=30))] == ["evt-early"]
    assert [e.id for e in events_as_of(scenario, start + timedelta(hours=3))] == ["evt-early", "evt-late"]
    late = events_as_of(scenario, start + timedelta(hours=3))[-1]
    assert late.simulated is True
    assert late.payload == {"action": "left"}


def test_demo_v1_sources_unchanged():
    body = create_app().test_client().get("/api/sources?scenario=demo_v1").get_json()
    assert len(body["sources"]) == 5
    assert {s["source"] for s in body["sources"]} == {"calendar", "thermostat", "electrical", "weather", "human_report"}
