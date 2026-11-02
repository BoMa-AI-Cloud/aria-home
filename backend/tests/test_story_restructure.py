"""Acceptance tests for the 2026-11-01 care-story restructure.

Evening checkpoints are snapshots (no follow-up, no notifications, no
caregiver request) until the room is 6 F below target; the story
investigation is created at that checkpoint, 22:46, with a frozen caregiver
request. 21:41 is at_risk but only a notice.
"""
from datetime import datetime
from pathlib import Path

from aria_home.investigator import build_evidence_pack, inference_identity
from aria_home.outcomes import follow_up_for
from aria_home.scenario import load_scenario
from aria_home.trace import step_activity

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"
CARE = "care_home_v1"

CARE_TIMES = [
    "2026-01-16T19:20:00-05:00",
    "2026-01-16T21:00:00-05:00",
    "2026-01-16T21:41:00-05:00",
    "2026-01-16T22:46:00-05:00",
    "2026-01-16T23:31:00-05:00",
    "2026-01-17T00:21:00-05:00",
    "2026-01-17T00:31:00-05:00",
    "2026-01-17T01:41:00-05:00",
    "2026-01-17T01:51:00-05:00",
    "2026-01-17T07:01:00-05:00",
]

FROZEN_REQUEST_PART = "your mother's home is cooling (62 F, 6 F below the 68 F target, furnace reported idle since 4:00 PM)"


def _care():
    return load_scenario(SCENARIOS_DIR / CARE)


def _readiness(scenario, at_str):
    pack = build_evidence_pack(scenario, datetime.fromisoformat(at_str))
    readiness = pack.get("readiness") or {}
    return readiness.get("status"), pack


def test_checkpoints_are_the_final_ten():
    from aria_home.public_demo import CHECKPOINTS
    assert list(CHECKPOINTS[CARE]) == CARE_TIMES


def test_readiness_per_step():
    scenario = _care()
    assert _readiness(scenario, CARE_TIMES[0])[0] == "on_track"
    assert _readiness(scenario, CARE_TIMES[1])[0] == "on_track"
    assert _readiness(scenario, CARE_TIMES[2])[0] == "at_risk"
    assert _readiness(scenario, CARE_TIMES[3])[0] == "at_risk"
    assert _readiness(scenario, CARE_TIMES[4])[0] == "at_risk"
    assert _readiness(scenario, CARE_TIMES[5])[0] == "at_risk"
    assert _readiness(scenario, CARE_TIMES[6])[0] == "at_risk"
    assert _readiness(scenario, CARE_TIMES[7])[0] == "on_track"
    assert _readiness(scenario, CARE_TIMES[8])[0] == "on_track"
    assert _readiness(scenario, CARE_TIMES[9])[0] == "arrival_passed"


def test_room_curve_measurements():
    scenario = _care()
    visible = {}
    for record in scenario.records:
        if record.source.value != "room_sensor" or record.quantity != "indoor_temp":
            continue
        visible[record.observed_at.isoformat()] = record.value
    assert visible["2026-01-16T16:00:00-05:00"] == 70.0
    assert visible["2026-01-16T21:00:00-05:00"] == 68.4
    assert visible["2026-01-16T19:15:00-05:00"] == 69.0
    assert visible["2026-01-17T00:15:00-05:00"] == 56.6
    assert visible["2026-01-17T01:10:00-05:00"] == 68.0


def _client(tmp_path, monkeypatch):
    from aria_home.app import create_app
    for var in ("ARIA_HOME_MODEL_ENABLED", "ARIA_HOME_WHATSAPP_LIVE", "ARIA_HOME_EMPORIA_LIVE",
                "ARIA_HOME_VISUAL_LIVE", "ARIA_HOME_NEST_LIVE", "ARIA_HOME_E2E_HOOKS", "MODEL_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("ARIA_HOME_REVIEWS_DIR", str(tmp_path / "reviews"))
    monkeypatch.setenv("ARIA_HOME_CORRECTIONS_DIR", str(tmp_path / "corrections"))
    return create_app().test_client()


def _post(client, at):
    return client.post("/api/investigations", query_string={"scenario": CARE, "at": at}).get_json()


def test_snapshot_steps_create_no_follow_up_or_notifications(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    for at, readiness in zip(CARE_TIMES[:3], ("on_track", "on_track", "at_risk")):
        body = _post(client, at)
        assert body["computed_readiness"] == readiness
        assert body["follow_up"] is None
        assert body["outcome"] is None
        assert body["notifications"] == []
        assert body["schedule_status"] == "not_scheduled"
        assert body["activity"]["text"] and body["activity"]["source"]
        missing = client.get(f"/api/follow-ups/{body['investigation_id']}", query_string={"at": at}).get_json()
        assert missing.get("error") == "follow-up not found"


def test_first_alert_step_creates_frozen_request(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    body = _post(client, CARE_TIMES[3])
    assert body["computed_readiness"] == "at_risk"
    assert body["follow_up"] is not None
    alert = next(r for r in body["notifications"] if r["audience"] == "family_caregiver")
    assert alert["kind"] == "caregiver_alert"
    assert alert["state"] == "simulated_delivered"
    follow = client.get(f"/api/follow-ups/{body['investigation_id']}", query_string={"at": CARE_TIMES[3]}).get_json()
    permission = follow["caregiver_permission"]
    assert FROZEN_REQUEST_PART in permission["text"]
    assert permission["requested_at"] == "2026-01-16T22:46:00-05:00"
    assert permission["status"] == "waiting"


def _branch_permission(tmp_path, monkeypatch, decision):
    client = _client(tmp_path, monkeypatch)
    body = _post(client, CARE_TIMES[3])
    investigation_id = body["investigation_id"]
    if decision is not None:
        alert = next(r for r in body["notifications"] if r["audience"] == "family_caregiver")
        decided = client.post(
            f"/api/notifications/{alert['id']}/caregiver-decision",
            json={"decision": decision, "at": CARE_TIMES[3], "scenario": CARE},
        ).get_json()
        assert decided["caregiver_permission"]["status"] == ("approved" if decision == "approve" else "declined")
    texts = []
    for at in (CARE_TIMES[3], CARE_TIMES[4], CARE_TIMES[5], CARE_TIMES[7]):
        follow = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": at}).get_json()
        permission = follow["caregiver_permission"]
        assert permission is not None
        texts.append((permission["text"], permission["requested_at"], permission["status"]))
    return texts


def test_request_frozen_after_in_all_branches(tmp_path, monkeypatch):
    waiting = _branch_permission(tmp_path, monkeypatch, None)
    approved = _branch_permission(tmp_path, monkeypatch, "approve")
    declined = _branch_permission(tmp_path, monkeypatch, "decline")
    for texts in (waiting, approved, declined):
        assert len({(text, asked) for text, asked, _ in texts}) == 1
        assert FROZEN_REQUEST_PART in texts[0][0]
        assert texts[0][1] == "2026-01-16T22:46:00-05:00"
    assert [status for _, _, status in waiting] == ["waiting", "approved", "approved", "approved"]
    assert [status for _, _, status in approved] == ["approved", "approved", "approved", "approved"]
    assert [status for _, _, status in declined] == ["declined", "declined", "declined", "declined"]


def test_history_lists_only_current_and_earlier(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    body = _post(client, CARE_TIMES[3])
    investigation_id = body["investigation_id"]
    first = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": CARE_TIMES[3]}).get_json()
    assert first["history"] == []
    second = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": CARE_TIMES[4]}).get_json()
    assert [entry["evaluated_at"] for entry in second["history"]] == [CARE_TIMES[4]]
    assert second["verification_history"]
    assert all(isinstance(entry["stage"], str) for entry in second["verification_history"])
    rewind = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": CARE_TIMES[3]}).get_json()
    assert rewind["history"] == []
    again = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": CARE_TIMES[4]}).get_json()
    assert [entry["evaluated_at"] for entry in again["history"]] == [CARE_TIMES[4]]


def test_activity_sourced_every_step():
    scenario = _care()
    anchor = datetime.fromisoformat(CARE_TIMES[3])
    follow_up = follow_up_for(scenario, "story-test", anchor)
    seen_sources = set()
    for index, at_str in enumerate(CARE_TIMES):
        at = datetime.fromisoformat(at_str)
        activity = step_activity(scenario, at, follow_up if index >= 3 else None)
        assert activity["text"], at_str
        assert activity["source"], at_str
        seen_sources.add(activity["source"])
    assert CARE_TIMES[1] and step_activity(scenario, datetime.fromisoformat(CARE_TIMES[1]))["source"] == "computed:readiness"
    assert any(source.startswith("event:") for source in seen_sources)
    assert any(source.startswith("computed:") for source in seen_sources)
