import json
from datetime import timedelta
from pathlib import Path

from aria_home.contracts import DataMode
from aria_home.scenario import load_scenario, visible_records

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "demo_v1"


def test_demo_scenario_loads():
    scenario = load_scenario(SCENARIO_DIR)
    assert scenario.manifest.id == "demo_v1"
    assert scenario.manifest.mode is DataMode.synthetic
    assert scenario.manifest.author == "ARIA Home (synthetic)"
    assert scenario.trip is not None
    assert scenario.trip.property_id == "demo-house"
    assert scenario.trip.planned_arrival.hour == 18
    assert scenario.confirmation is not None
    assert scenario.confirmation.target_temp == 68
    assert scenario.confirmation.target_unit == "F"
    assert scenario.records
    assert {r.source.value for r in scenario.records} == {
        "calendar",
        "thermostat",
        "electrical",
        "weather",
    }


def test_story_shape():
    scenario = load_scenario(SCENARIO_DIR)
    at = scenario.manifest.start + timedelta(hours=3)
    visible = visible_records(scenario.records, at)
    temps = [
        r.value
        for r in visible
        if r.quantity == "indoor_temp" and r.value is not None
    ]
    assert temps and all(51.0 <= v <= 53.0 for v in temps)
    assert any(r.quantity == "indoor_temp" and r.value is None for r in visible)
    assert any(
        r.quantity == "hvac_reported_state" and r.value == "heating" for r in visible
    )
    furnace = [
        r for r in visible if r.subject == "circuit-furnace" and r.value is not None
    ]
    assert furnace and max(r.value for r in furnace) <= 5
    others = [
        r
        for r in visible
        if r.source.value == "electrical"
        and r.subject != "circuit-furnace"
        and r.value is not None
    ]
    assert len({r.subject for r in others}) == 3
    assert any(
        r.quantity == "outdoor_temp_forecast" and r.value == 30 for r in visible
    )


def test_manifest_sets_mode_and_live_row_does_not_override(tmp_path):
    target = tmp_path / "demo_v1"
    target.mkdir()
    for name in ["manifest.json", "calendar.json", "thermostat.json", "electrical.json", "weather.json"]:
        payload = json.loads((SCENARIO_DIR / name).read_text(encoding="utf-8"))
        if name == "thermostat.json":
            payload["records"][0]["mode"] = "live"
        (target / name).write_text(json.dumps(payload), encoding="utf-8")
    scenario = load_scenario(target)
    assert scenario.records
    assert all(r.mode is DataMode.synthetic for r in scenario.records)


def test_visible_records_hides_future():
    scenario = load_scenario(SCENARIO_DIR)
    at = scenario.manifest.start + timedelta(hours=3)
    visible = visible_records(scenario.records, at)
    assert len(visible) < len(scenario.records)
    assert all(r.received_at <= at for r in visible)
    later = visible_records(scenario.records, at + timedelta(hours=2))
    assert len(later) > len(visible)


def test_bindings_match_file():
    scenario = load_scenario(SCENARIO_DIR)
    raw = json.loads((SCENARIO_DIR / "electrical.json").read_text(encoding="utf-8"))
    expected = {}
    for row in raw["records"]:
        if row.get("binding"):
            expected[row["id"]] = row["binding"]["status"]
    loaded = {
        r.id: r.binding.status.value for r in scenario.records if r.binding is not None
    }
    assert loaded == expected
    assert loaded["elec-furnace-1755"] == "confirmed"


def test_manifest_created_on_or_after_hackathon():
    from datetime import date

    scenario = load_scenario(SCENARIO_DIR)
    assert scenario.manifest.created >= date(2026, 10, 26)
