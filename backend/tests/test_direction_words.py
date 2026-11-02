"""No surface says the room is going the wrong way: direction comes from the last 15 minutes."""
import json
from datetime import datetime
from pathlib import Path

import pytest

from aria_home.app import create_app
from aria_home.metrics import recent_change_f
from aria_home.scenario import load_scenario, visible_records
from aria_home.trace import _direction_clause, step_activity

CARE = "care_home_v1"
SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / CARE
ASK = "2026-01-16T22:46:00-05:00"
BEFORE_REPAIR = "2026-01-16T23:31:00-05:00"
RISING = "2026-01-17T00:31:00-05:00"
WARM_BY = "2026-01-17T07:01:00-05:00"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    (tmp_path / "recorded").mkdir()
    monkeypatch.setenv("ARIA_HOME_RECORDED_DIR", str(tmp_path / "recorded"))
    return create_app().test_client()


def _surfaces(client, investigation_id, at):
    follow = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": at}).get_json()
    trace = client.get("/api/trace", query_string={"scenario": CARE, "at": at, "investigation_id": investigation_id}).get_json()
    return {
        "activity": follow["activity"]["text"],
        "scripted activity": step_activity(load_scenario(SCENARIO_DIR), datetime.fromisoformat(at))["text"],
        "readiness": json.dumps(follow["readiness"]["reasons"] if isinstance(follow.get("readiness"), dict) else follow.get("computed_readiness")),
        "verification": json.dumps(follow["verification"]["reasons"]),
        "trace steps": json.dumps([[step["label"], step["detail"]] for step in trace["steps"] if step["kind"] != "permission"]),
    }


@pytest.mark.parametrize("at, wrong_word", [(RISING, "falling"), (BEFORE_REPAIR, "rising")])
def test_no_surface_says_the_wrong_direction(client, at, wrong_word):
    investigation_id = client.post("/api/investigations", query_string={"scenario": CARE, "at": ASK}).get_json()["investigation_id"]
    for name, text in _surfaces(client, investigation_id, at).items():
        assert wrong_word not in text.lower(), name


@pytest.mark.parametrize("at, change", [(BEFORE_REPAIR, -0.6), (RISING, 2.1), (WARM_BY, 0.0)])
def test_recent_change_is_the_last_15_minutes_of_room_readings(client, at, change):
    metrics = client.get("/api/metrics", query_string={"scenario": CARE, "at": at}).get_json()
    assert metrics["recent_change_f"] == change
    investigation_id = client.post("/api/investigations", query_string={"scenario": CARE, "at": ASK}).get_json()["investigation_id"]
    follow = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": at}).get_json()
    assert follow["metrics"]["recent_change_f"] == change


def test_recent_change_is_null_when_it_cannot_be_measured():
    scenario = load_scenario(SCENARIO_DIR)
    start = scenario.manifest.start
    assert recent_change_f(visible_records(scenario.records, start), "demo-house/main", start) is None


def test_direction_clause_claims_no_rate():
    room = {"value": 60.0}
    assert _direction_clause(2.1, room, 68.0) == ", rising"
    assert _direction_clause(-0.6, room, 68.0) == ", falling"
    assert _direction_clause(0.0, room, 68.0) == ", steady"
    assert _direction_clause(None, room, 68.0) == ""
    assert _direction_clause(-0.2, {"value": 68.0}, 68.0) == ", holding"
    assert _direction_clause(-0.2, {"value": 69.0}, 68.0) == ", holding"
    assert _direction_clause(0.5, {"value": 69.1}, 68.0) == ", rising"
