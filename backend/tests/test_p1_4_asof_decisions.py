"""P1-4: decision/ack replies are as of the request time; a later decision is not shown."""
from aria_home.app import create_app

T0231 = "2026-01-17T02:31:00-05:00"
T0245 = "2026-01-17T02:45:00-05:00"


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "p14.db"))
    return create_app().test_client()


def _start(client):
    inv_id = client.post(f"/api/investigations?scenario=care_home_v1&at={T0231}").get_json()["investigation_id"]
    body = client.get(f"/api/follow-ups/{inv_id}?at={T0231}").get_json()
    return inv_id, body["caregiver_permission"]["notification_id"]


def test_rewound_second_decision_does_not_show_future_decision(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, notif_id = _start(client)
    assert client.post(f"/api/notifications/{notif_id}/caregiver-decision", json={"decision": "approve", "at": T0245}).status_code == 201
    resp = client.post(f"/api/notifications/{notif_id}/caregiver-decision", json={"decision": "decline", "at": T0231})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["recorded"] is False
    decision = payload["decision"]
    assert decision is None or decision.get("decided_at") is None or decision["decided_at"] <= T0231
    assert payload["caregiver_permission"]["status"] == "waiting"
    later = client.get(f"/api/follow-ups/{inv_id}?at={T0245}").get_json()
    assert later["caregiver_permission"]["status"] == "approved"


def test_repeat_same_decision_is_idempotent(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, notif_id = _start(client)
    first = client.post(f"/api/notifications/{notif_id}/caregiver-decision", json={"decision": "approve", "at": T0231})
    assert first.status_code == 201
    second = client.post(f"/api/notifications/{notif_id}/caregiver-decision", json={"decision": "approve", "at": T0231})
    assert second.status_code == 200
    assert second.get_json()["recorded"] is False
    assert second.get_json()["decision"]["decision"] == "approved"


def test_decline_then_approve_keeps_decline(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, notif_id = _start(client)
    assert client.post(f"/api/notifications/{notif_id}/caregiver-decision", json={"decision": "decline", "at": T0231}).status_code == 201
    second = client.post(f"/api/notifications/{notif_id}/caregiver-decision", json={"decision": "approve", "at": T0245})
    assert second.status_code == 200
    assert second.get_json()["decision"]["decision"] == "declined"


def test_decision_after_recorded_answer_is_refused(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, notif_id = _start(client)
    resp = client.post(f"/api/notifications/{notif_id}/caregiver-decision", json={"decision": "decline", "at": "2026-01-17T06:21:00-05:00"})
    assert resp.status_code == 409
    data = resp.get_json()
    assert data["reason"] == "already_answered"
    assert "02:45" in data["error"]
    follow_0621 = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-17T06:21:00-05:00").get_json()
    assert follow_0621["caregiver_permission"]["status"] == "approved"
    assert follow_0621["verification"]["stage"] == "goal_verified"
    follow_0701 = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-17T07:01:00-05:00").get_json()
    assert follow_0701["caregiver_permission"]["status"] == "approved"
    assert follow_0701["verification"]["stage"] == "arrival_met"


def test_decision_at_the_recorded_answer_time_is_accepted(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, notif_id = _start(client)
    resp = client.post(f"/api/notifications/{notif_id}/caregiver-decision", json={"decision": "decline", "at": T0245})
    assert resp.status_code == 201
    follow = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-17T06:21:00-05:00").get_json()
    assert follow["caregiver_permission"]["status"] == "declined"
    assert follow["verification"]["stage"] != "goal_verified"


def test_repeat_after_recorded_answer_keeps_first_decision(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, notif_id = _start(client)
    first = client.post(f"/api/notifications/{notif_id}/caregiver-decision", json={"decision": "decline", "at": T0231})
    assert first.status_code == 201
    second = client.post(f"/api/notifications/{notif_id}/caregiver-decision", json={"decision": "approve", "at": "2026-01-17T06:21:00-05:00"})
    assert second.status_code == 200
    assert second.get_json()["recorded"] is False
    follow = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-17T06:21:00-05:00").get_json()
    assert follow["caregiver_permission"]["status"] == "declined"
