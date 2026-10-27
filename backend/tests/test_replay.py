import sqlite3

from aria_home.app import create_app
from aria_home.store import Store

T_CREATE = "2026-01-16T16:31:00-05:00"
T_ACK = "2026-01-16T16:50:00-05:00"
T_LATE = "2026-01-16T21:01:00-05:00"
T_HVAC = "2026-01-16T16:52:00-05:00"


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    return create_app().test_client()


def _create(client):
    resp = client.post(f"/api/investigations?scenario=demo_video_v1&at={T_CREATE}")
    assert resp.status_code == 200
    return resp.get_json()["investigation_id"]


def _manager_id(client, inv_id):
    rows = client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]
    return next(r["id"] for r in rows if r["audience"] == "property_manager")


def _ack_manager_at_1650(client, inv_id):
    mid = _manager_id(client, inv_id)
    resp = client.post(f"/api/notifications/{mid}/ack", json={"actor": "property_manager", "at": T_ACK})
    assert resp.status_code == 200
    return mid


def _get_followup(client, inv_id, at):
    return client.get(f"/api/follow-ups/{inv_id}?at={at}")


def _counts(db):
    conn = sqlite3.connect(db)
    try:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("investigations", "follow_ups", "outcome_events", "notifications", "notification_acks")}
    finally:
        conn.close()


def test_audit_replay_at_creation_excludes_later_history_and_ack(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = _create(client)
    manager_id = _ack_manager_at_1650(client, inv_id)

    late = _get_followup(client, inv_id, T_LATE)
    assert late.status_code == 200
    late_body = late.get_json()
    assert late_body["verification"]["stage"] == "arrival_met"
    assert any(e["evaluated_at"].startswith("2026-01-16T21:01") for e in late_body["history"])

    replay = _get_followup(client, inv_id, T_CREATE)
    assert replay.status_code == 200
    body = replay.get_json()
    assert body["verification"]["stage"] == "telemetry_missing"
    assert body["verification"]["corroboration_ids"] == []
    assert body["status"] != "arrival_met"
    assert all(e["evaluated_at"] <= "2026-01-16T16:31:00-05:00" for e in body["history"])
    assert not any("arrival_met" in str(e) for e in body["history"])
    assert all(e["evaluated_at"] <= "2026-01-16T16:31:00-05:00" for e in body.get("verification_history", []))
    assert body["verification_history"][-1]["stage"] == "telemetry_missing" if body.get("verification_history") else True
    assert body["follow_up"]["last_evaluated_at"] <= "2026-01-16T16:31:00-05:00"
    assert body["follow_up"]["last_status"] == body["outcome"]["status"]

    for row in body["notifications"]:
        assert row["created_at"] <= "2026-01-16T16:31:00-05:00", row
        assert row["acks"] == [], row
    assert not any(r["audience"] == "hvac_company" and r["created_at"] > "2026-01-16T16:31:00-05:00" for r in body["notifications"])
    manager = next(r for r in body["notifications"] if r["id"] == manager_id)
    assert manager["state"] != "acknowledged"
    assert manager["acks"] == []

    via_notifications = client.get(f"/api/notifications?investigation_id={inv_id}&at={T_CREATE}")
    assert via_notifications.status_code == 200
    rows = via_notifications.get_json()["notifications"]
    assert all(r["created_at"] <= "2026-01-16T16:31:00-05:00" for r in rows)
    assert all(r["acks"] == [] for r in rows)


def test_advance_rewind_advance_identical(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = _create(client)
    t_mid = "2026-01-16T18:51:00-05:00"
    first_mid = _get_followup(client, inv_id, t_mid).get_json()
    first_late = _get_followup(client, inv_id, T_LATE).get_json()
    assert _get_followup(client, inv_id, t_mid).get_json() == first_mid
    assert _get_followup(client, inv_id, T_LATE).get_json() == first_late
    assert _get_followup(client, inv_id, t_mid).get_json() == first_mid


def test_repeated_rewind_reads_add_no_rows(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = _create(client)
    _ack_manager_at_1650(client, inv_id)
    _get_followup(client, inv_id, T_LATE)
    before = _counts(tmp_path / "api.db")
    for _ in range(3):
        assert _get_followup(client, inv_id, T_CREATE).status_code == 200
        assert client.get(f"/api/notifications?investigation_id={inv_id}&at={T_CREATE}").status_code == 200
    assert _counts(tmp_path / "api.db") == before


def test_restart_keeps_full_history_and_projections(tmp_path, monkeypatch):
    db = tmp_path / "api.db"
    client = _client(tmp_path, monkeypatch)
    inv_id = _create(client)
    manager_id = _ack_manager_at_1650(client, inv_id)
    _get_followup(client, inv_id, T_LATE)

    store = Store(db)
    full_history = store.list_outcomes(inv_id)
    assert any(e["evaluated_at"].startswith("2026-01-16T21:01") for e in full_history)
    full_notifications = store.list_notifications(inv_id)
    manager_full = next(r for r in full_notifications if r["id"] == manager_id)
    assert manager_full["acks"] and manager_full["acks"][0]["acknowledged_at"].startswith("2026-01-16T16:50")
    store.close()

    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(db))
    client2 = create_app().test_client()
    replay = _get_followup(client2, inv_id, T_CREATE).get_json()
    assert all(e["evaluated_at"] <= "2026-01-16T16:31:00-05:00" for e in replay["history"])
    assert all(r["acks"] == [] for r in replay["notifications"])
    late = _get_followup(client2, inv_id, T_LATE).get_json()
    assert late["verification"]["stage"] == "arrival_met"
    assert any(e["evaluated_at"].startswith("2026-01-16T21:01") for e in late["history"])


def test_hvac_projection_at_1652_does_not_depend_on_request_order(tmp_path, monkeypatch):
    projections = []
    for name, order in (("late_first", (T_LATE, T_HVAC)), ("hvac_first", (T_HVAC, T_LATE))):
        monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / f"{name}.db"))
        client = create_app().test_client()
        inv_id = _create(client)
        for at in order:
            assert _get_followup(client, inv_id, at).status_code == 200
        resp = client.get(f"/api/notifications?investigation_id={inv_id}&at={T_HVAC}")
        assert resp.status_code == 200
        projections.append(resp.get_json()["notifications"])
    assert projections[0] == projections[1]
    delivered = [r for r in projections[0] if r["audience"] == "hvac_company" and r["state"] == "simulated_delivered"]
    assert len(delivered) == 1
    assert "2026-01-16T16:45:00-05:00" <= delivered[0]["created_at"] <= T_HVAC
    assert delivered[0]["created_at"] == "2026-01-16T16:46:00-05:00"


def test_before_creation_returns_409(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = _create(client)
    before = "2026-01-16T16:30:00-05:00"
    resp = _get_followup(client, inv_id, before)
    assert resp.status_code == 409
    assert "not yet created" in resp.get_json()["error"]
    resp = client.get(f"/api/notifications?investigation_id={inv_id}&at={before}")
    assert resp.status_code == 409
    assert "not yet created" in resp.get_json()["error"]
