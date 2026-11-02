"""P1-5: a row removed between reads gives a controlled 4xx, never 500."""
from aria_home.app import create_app
from aria_home.store import Store

CARE_AT = "2026-01-16T22:46:00-05:00"


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "p15.db"))
    return create_app().test_client()


def _start(client):
    inv_id = client.post(f"/api/investigations?scenario=care_home_v1&at={CARE_AT}").get_json()["investigation_id"]
    body = client.get(f"/api/follow-ups/{inv_id}?at={CARE_AT}").get_json()
    return inv_id, body["caregiver_permission"]["notification_id"]


def test_followups_removed_between_reads_is_404_not_500(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, _ = _start(client)
    real = Store.get_follow_up
    calls = {"n": 0}

    def gone_after_first(self, investigation_id):
        calls["n"] += 1
        return real(self, investigation_id) if calls["n"] == 1 else None

    monkeypatch.setattr(Store, "get_follow_up", gone_after_first)
    resp = client.get(f"/api/follow-ups/{inv_id}?at={CARE_AT}")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "follow-up not found"


def test_trace_removed_between_reads_is_404_not_500(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, _ = _start(client)
    real = Store.get_follow_up
    calls = {"n": 0}

    def gone_after_first(self, investigation_id):
        calls["n"] += 1
        return real(self, investigation_id) if calls["n"] == 1 else None

    monkeypatch.setattr(Store, "get_follow_up", gone_after_first)
    resp = client.get(f"/api/trace?scenario=care_home_v1&at={CARE_AT}&investigation_id={inv_id}")
    assert resp.status_code == 404


def test_decision_removed_between_reads_is_404(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, notif_id = _start(client)
    real = Store.get_notification
    calls = {"n": 0}

    def gone_after_first(self, notification_id, at=None):
        calls["n"] += 1
        return real(self, notification_id) if calls["n"] == 1 else None

    monkeypatch.setattr(Store, "get_notification", gone_after_first)
    resp = client.post(f"/api/notifications/{notif_id}/caregiver-decision", json={"decision": "approve", "at": CARE_AT})
    assert resp.status_code == 404


def test_ack_after_reset_is_404_not_500(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, _ = _start(client)
    homeowner = next(r for r in client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"] if r["audience"] == "homeowner")
    Store(path=tmp_path / "p15.db").reset_e2e()
    resp = client.post(f"/api/notifications/{homeowner['id']}/ack", json={"actor": "homeowner", "at": CARE_AT})
    assert resp.status_code == 404


def test_notifications_after_reset_is_controlled(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, _ = _start(client)
    Store(path=tmp_path / "p15.db").reset_e2e()
    resp = client.get(f"/api/notifications?investigation_id={inv_id}")
    assert resp.status_code in (200, 404)
    resp = client.get(f"/api/follow-ups/{inv_id}?at={CARE_AT}")
    assert resp.status_code == 404
