"""The Reasoning map and the House agree: no notices before the caregiver is asked."""
from datetime import datetime
from pathlib import Path

import pytest

from aria_home.app import create_app
from aria_home.scenario import load_scenario
from aria_home.trace import build_trace

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
BEFORE_THE_ASK = ["2026-01-16T19:20:00-05:00", "2026-01-16T21:00:00-05:00", "2026-01-16T21:41:00-05:00"]
THE_ASK = "2026-01-16T22:46:00-05:00"


@pytest.fixture(scope="module")
def care():
    return load_scenario(SCENARIOS / "care_home_v1")


@pytest.mark.parametrize("iso", BEFORE_THE_ASK)
def test_no_notices_or_notice_steps_before_the_ask(care, iso):
    trace = build_trace(care, datetime.fromisoformat(iso))
    assert trace["notices"] == []
    assert [step for step in trace["steps"] if step["kind"] == "notice"] == []
    assert trace["permission"] is None


def test_notices_appear_when_the_caregiver_is_asked(care):
    trace = build_trace(care, datetime.fromisoformat(THE_ASK))
    assert [(n["audience"], n["allowed"]) for n in trace["notices"]] == [("homeowner", True), ("family_caregiver", True), ("hvac_company", False)]
    assert [step["label"] for step in trace["steps"] if step["kind"] == "notice"] == ["resident: raised", "family caregiver: raised", "HVAC company: refused"]


def test_other_scenarios_keep_their_notices():
    scenario = load_scenario(SCENARIOS / "demo_video_v1")
    trace = build_trace(scenario, datetime.fromisoformat("2026-01-16T16:31:00-05:00"))
    assert trace["notices"]


@pytest.mark.parametrize("iso", BEFORE_THE_ASK)
def test_map_matches_the_house_through_the_api(tmp_path, monkeypatch, iso):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    client = create_app().test_client()
    started = client.post("/api/investigations", query_string={"scenario": "care_home_v1", "at": iso})
    assert started.status_code in (200, 201)
    body = started.get_json()
    investigation_id = body["investigation_id"]
    assert body.get("notifications", []) == []
    trace = client.get("/api/trace", query_string={"scenario": "care_home_v1", "at": iso, "investigation_id": investigation_id}).get_json()
    assert trace["notices"] == []
