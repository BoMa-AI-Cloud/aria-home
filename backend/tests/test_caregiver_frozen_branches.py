"""The frozen caregiver request is identical at every checkpoint after it is raised, in all three branches.

The story raises the request at 19:20 ("54 F, 14 F below the 68 F target,
furnace reported idle since 16:00"). Walking
every later checkpoint — with no decision, with an approval at 02:31, or with a
decline at 02:31 — keeps the original text and the original asked time; only the
status (and the decision time) changes. The trace agrees with the follow-ups.
"""
from aria_home.app import create_app

T1903 = "2026-01-16T19:03:00-05:00"
T1915 = "2026-01-16T19:15:00-05:00"
T1920 = "2026-01-16T19:20:00-05:00"
T0231 = "2026-01-17T02:31:00-05:00"
T0245 = "2026-01-17T02:45:00-05:00"
T0421 = "2026-01-17T04:21:00-05:00"
T0451 = "2026-01-17T04:51:00-05:00"
T0621 = "2026-01-17T06:21:00-05:00"
T0645 = "2026-01-17T06:45:00-05:00"
T0701 = "2026-01-17T07:01:00-05:00"
CHECKPOINTS = (T1903, T1915, T1920, T0231, T0245, T0421, T0451, T0621, T0645, T0701)
RAISED_ONWARDS = CHECKPOINTS[2:]


def _client(tmp_path, monkeypatch, name="api.db"):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / name))
    return create_app().test_client()


def _start(client):
    resp = client.post(f"/api/investigations?scenario=care_home_v1&at={T1920}")
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
        assert "54 F" in permission["text"], at
        assert "16:00" in permission["text"], at
        assert permission["requested_at"].startswith("2026-01-16T19:20"), at
        seen.add((permission["text"], permission["requested_at"]))
        if at < T0245:
            assert permission["status"] == "waiting", at
            assert permission["decided_at"] is None, at
        else:
            assert permission["status"] == "approved", at
            assert permission["decided_at"] == T0245, at
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
    notification_id = _follow(client, inv_id, T0231)["caregiver_permission"]["notification_id"]
    _decide(client, notification_id, "approve", T0231)
    seen = set()
    for at in RAISED_ONWARDS:
        permission = _follow(client, inv_id, at)["caregiver_permission"]
        assert permission is not None, at
        assert "54 F" in permission["text"], at
        assert "16:00" in permission["text"], at
        assert permission["requested_at"].startswith("2026-01-16T19:20"), at
        seen.add((permission["text"], permission["requested_at"]))
        if at < T0231:
            assert permission["status"] == "waiting", at
        else:
            assert permission["status"] == "approved", at
            assert permission["decided_at"] == T0231, at
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
    notification_id = _follow(client, inv_id, T0231)["caregiver_permission"]["notification_id"]
    _decide(client, notification_id, "decline", T0231)
    seen = set()
    for at in RAISED_ONWARDS:
        permission = _follow(client, inv_id, at)["caregiver_permission"]
        assert permission is not None, at
        assert "54 F" in permission["text"], at
        assert "16:00" in permission["text"], at
        assert permission["requested_at"].startswith("2026-01-16T19:20"), at
        seen.add((permission["text"], permission["requested_at"]))
        if at < T0231:
            assert permission["status"] == "waiting", at
        else:
            assert permission["status"] == "declined", at
            assert permission["decided_at"] == T0231, at
            assert permission["source"] == "in-app decision", at
        trace = _trace(client, inv_id, at)["permission"]
        assert trace is not None, at
        assert trace["text"] == permission["text"], at
        assert trace["requested_at"] == permission["requested_at"], at
        assert trace["status"] == permission["status"], at
    assert len(seen) == 1
