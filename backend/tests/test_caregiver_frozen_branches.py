"""The frozen caregiver request is identical at every checkpoint after it is raised, in all three branches.

The story raises the request at 22:46 ("62 F, 6 F below the 68 F target,
furnace reported idle since 4:00 PM"). Walking
every later checkpoint — with no decision, with an approval at 22:46, or with a
decline at 22:46 — keeps the original text and the original asked time; only the
status (and the decision time) changes. The trace agrees with the follow-ups.
"""
from aria_home.app import create_app

T1920 = "2026-01-16T19:20:00-05:00"
T2100 = "2026-01-16T21:00:00-05:00"
T2141 = "2026-01-16T21:41:00-05:00"
T2246 = "2026-01-16T22:46:00-05:00"
T2247 = "2026-01-16T22:47:00-05:00"
T2331 = "2026-01-16T23:31:00-05:00"
T0021 = "2026-01-17T00:21:00-05:00"
T0031 = "2026-01-17T00:31:00-05:00"
T0141 = "2026-01-17T01:41:00-05:00"
T0151 = "2026-01-17T01:51:00-05:00"
T0701 = "2026-01-17T07:01:00-05:00"
CHECKPOINTS = (T1920, T2100, T2141, T2246, T2331, T0021, T0031, T0141, T0151, T0701)
RAISED_ONWARDS = CHECKPOINTS[3:]


def _client(tmp_path, monkeypatch, name="api.db"):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / name))
    return create_app().test_client()


def _start(client):
    resp = client.post(f"/api/investigations?scenario=care_home_v1&at={T2246}")
    assert resp.status_code == 200
    return resp.get_json()["investigation_id"]


def _follow(client, inv_id, at):
    resp = client.get(f"/api/follow-ups/{inv_id}?at={at}")
    assert resp.status_code == 200, at
    return resp.get_json()


def _trace(client, inv_id, at):
    resp = client.get(f"/api/trace?scenario=care_home_v1&at={at}&investigation_id={inv_id}")
    assert resp.status_code == 200, at
    return resp.get_json()


def _decide(client, notification_id, decision, at):
    resp = client.post(
        f"/api/notifications/{notification_id}/caregiver-decision",
        json={"decision": decision, "at": at},
    )
    assert resp.status_code == 201, at
    return resp.get_json()


def test_frozen_request_identical_without_decision(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = _start(client)
    seen = set()
    for at in RAISED_ONWARDS:
        permission = _follow(client, inv_id, at)["caregiver_permission"]
        assert permission is not None, at
        assert "62 F" in permission["text"], at
        assert "4:00 PM" in permission["text"], at
        assert permission["requested_at"].startswith("2026-01-16T22:46"), at
        seen.add((permission["text"], permission["requested_at"]))
        if at < T2247:
            assert permission["status"] == "waiting", at
            assert permission["decided_at"] is None, at
        else:
            assert permission["status"] == "approved", at
            assert permission["decided_at"] == T2247, at
            assert permission["source"] == "scenario event (the recorded story)", at
        trace = _trace(client, inv_id, at)["permission"]
        assert trace is not None, at
        assert trace["text"] == permission["text"], at
        assert trace["requested_at"] == permission["requested_at"], at
        assert trace["status"] == permission["status"], at
    assert len(seen) == 1


def test_frozen_request_identical_after_approval(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, name="approve.db")
    inv_id = _start(client)
    notification_id = _follow(client, inv_id, T2246)["caregiver_permission"]["notification_id"]
    _decide(client, notification_id, "approve", T2246)
    seen = set()
    for at in RAISED_ONWARDS:
        permission = _follow(client, inv_id, at)["caregiver_permission"]
        assert permission is not None, at
        assert "62 F" in permission["text"], at
        assert "4:00 PM" in permission["text"], at
        assert permission["requested_at"].startswith("2026-01-16T22:46"), at
        seen.add((permission["text"], permission["requested_at"]))
        if at < T2246:
            assert permission["status"] == "waiting", at
        else:
            assert permission["status"] == "approved", at
            assert permission["decided_at"] == T2246, at
            assert permission["source"] == "in-app decision", at
        trace = _trace(client, inv_id, at)["permission"]
        assert trace is not None, at
        assert trace["text"] == permission["text"], at
        assert trace["requested_at"] == permission["requested_at"], at
        assert trace["status"] == permission["status"], at
    assert len(seen) == 1


def test_frozen_request_identical_after_decline(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, name="decline.db")
    inv_id = _start(client)
    notification_id = _follow(client, inv_id, T2246)["caregiver_permission"]["notification_id"]
    _decide(client, notification_id, "decline", T2246)
    seen = set()
    for at in RAISED_ONWARDS:
        permission = _follow(client, inv_id, at)["caregiver_permission"]
        assert permission is not None, at
        assert "62 F" in permission["text"], at
        assert "4:00 PM" in permission["text"], at
        assert permission["requested_at"].startswith("2026-01-16T22:46"), at
        seen.add((permission["text"], permission["requested_at"]))
        if at < T2246:
            assert permission["status"] == "waiting", at
        else:
            assert permission["status"] == "declined", at
            assert permission["decided_at"] == T2246, at
            assert permission["source"] == "in-app decision", at
        trace = _trace(client, inv_id, at)["permission"]
        assert trace is not None, at
        assert trace["text"] == permission["text"], at
        assert trace["requested_at"] == permission["requested_at"], at
        assert trace["status"] == permission["status"], at
    assert len(seen) == 1
