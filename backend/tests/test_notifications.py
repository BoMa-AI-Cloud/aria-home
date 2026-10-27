import socket
import sqlite3

import pytest

from aria_home.app import create_app
from aria_home.notifications import ALLOWLISTS, build_payload, decide_hvac_notification, decide_notifications

FORBIDDEN = ("trip", "itinerary", "email", "phone", "location", "flight")


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    return create_app().test_client()


def _all_keys(value):
    keys = []
    if isinstance(value, dict):
        for k, v in value.items():
            keys.append(str(k).lower())
            keys.extend(_all_keys(v))
    elif isinstance(value, list):
        for item in value:
            keys.extend(_all_keys(item))
    return keys


def _assert_payload_clean(payload):
    assert set(payload) <= ALLOWLISTS[payload["audience"]]
    for key in _all_keys(payload):
        assert not any(part in key for part in FORBIDDEN), key


def _notifications(client, inv_id):
    resp = client.get(f"/api/notifications?investigation_id={inv_id}")
    assert resp.status_code == 200
    return resp.get_json()["notifications"]


def test_allowlists_and_no_forbidden_keys_via_api(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00")
    assert resp.status_code == 200
    inv_id = resp.get_json()["investigation_id"]
    rows = _notifications(client, inv_id)
    audiences = {r["audience"] for r in rows}
    assert "homeowner" in audiences
    assert "property_manager" in audiences
    for row in rows:
        _assert_payload_clean(row["payload"])
        assert row["delivery"] == "simulated"
        assert row["payload"]["audience"] == row["audience"]
    homeowner = next(r for r in rows if r["audience"] == "homeowner")
    assert homeowner["state"] == "simulated_delivered"
    assert homeowner["payload"]["readiness"]
    assert homeowner["payload"]["readiness_in_words"]
    assert homeowner["payload"]["verified_facts"] is not None
    assert homeowner["payload"]["evaluated_at"].startswith("2026-01-16T16:31")
    manager = next(r for r in rows if r["audience"] == "property_manager")
    assert manager["state"] == "simulated_delivered"
    assert manager["payload"]["property_label"] == "demo-cabin"
    assert manager["payload"]["requested_action"]
    assert manager["payload"]["access_note"]


def test_manager_refused_without_authorization(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=2026-01-16T09:05:00-05:00")
    assert resp.status_code == 200
    inv_id = resp.get_json()["investigation_id"]
    rows = _notifications(client, inv_id)
    manager = [r for r in rows if r["audience"] == "property_manager"]
    assert manager, rows
    assert manager[0]["state"] == "refused"
    assert manager[0]["refusal_reason"] == "manager_not_authorized"
    assert manager[0]["reason"] == "manager_not_authorized"
    homeowner = [r for r in rows if r["audience"] == "homeowner"]
    assert homeowner and homeowner[0]["state"] == "refused"
    assert homeowner[0]["refusal_reason"] == "homeowner_preference_missing"


def test_manager_not_created_when_on_track_unit():
    from datetime import datetime, timezone, timedelta
    decisions = decide_notifications(readiness={"status": "on_track", "reasons": []}, context=None, now=datetime(2026, 1, 16, tzinfo=timezone.utc), investigation_id="inv-x")
    assert [d["audience"] for d in decisions] == ["homeowner"]


def test_hvac_refused_before_1645_and_allowed_after_via_api(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00")
    inv_id = resp.get_json()["investigation_id"]

    resp = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T16:31:00-05:00")
    assert resp.status_code == 200
    rows = _notifications(client, inv_id)
    hvac = [r for r in rows if r["audience"] == "hvac_company"]
    assert hvac and hvac[0]["state"] == "refused"
    assert hvac[0]["refusal_reason"] == "manager_hvac_not_authorized"
    _assert_payload_clean(hvac[0]["payload"])

    resp = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T16:52:00-05:00")
    assert resp.status_code == 200
    rows = _notifications(client, inv_id)
    delivered = [r for r in rows if r["audience"] == "hvac_company" and r["state"] == "simulated_delivered"]
    assert delivered, rows
    payload = delivered[0]["payload"]
    _assert_payload_clean(payload)
    assert set(payload) == {"audience", "kind", "property_label", "access_note", "manager_contact_label", "relevant_observations"}
    assert payload["property_label"] == "demo-cabin"
    assert payload["access_note"]
    assert payload["manager_contact_label"]
    assert isinstance(payload["relevant_observations"], list)


def test_hvac_pure_gate_before_and_after():
    from datetime import datetime, timezone, timedelta
    class E:
        def __init__(self, kind): self.kind = kind; self.payload = {}
    before = decide_hvac_notification(readiness={"status": "cannot_tell", "reasons": ["x"]}, events=[], investigation_id="inv-1")
    assert not before["allowed"] and before["reason"] == "manager_hvac_not_authorized"
    after = decide_hvac_notification(readiness={"status": "cannot_tell", "reasons": ["x"]}, events=[E("manager_hvac_authorized")], investigation_id="inv-1")
    assert after["allowed"]


def test_idempotency_repeat_post_and_get(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    url = "/api/investigations?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00"
    inv_id = client.post(url).get_json()["investigation_id"]
    client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T16:52:00-05:00")
    first = _notifications(client, inv_id)
    client.post(url)
    client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T16:52:00-05:00")
    client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T16:52:00-05:00")
    second = _notifications(client, inv_id)
    assert [r["id"] for r in second] == [r["id"] for r in first]
    assert len(second) == len(first)
    keys = [r["idempotency_key"] for r in second]
    assert len(keys) == len(set(keys))


def test_ack_never_changes_outcome_or_stage(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00")
    inv_id = resp.get_json()["investigation_id"]

    def snapshot(stamp):
        body = client.get(f"/api/follow-ups/{inv_id}?at={stamp}").get_json()
        return body["outcome"]["status"], body["verification"]["stage"]

    before_1851 = snapshot("2026-01-16T18:51:00-05:00")
    before_2021 = snapshot("2026-01-16T20:21:00-05:00")

    rows = _notifications(client, inv_id)
    manager = next(r for r in rows if r["audience"] == "property_manager")
    resp = client.post(f"/api/notifications/{manager['id']}/ack", json={"actor": "property_manager", "at": "2026-01-16T16:37:00-05:00"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["message"] == "acknowledged, not resolved"
    assert body["ack"]["actor"] == "property_manager"
    assert body["ack"]["acknowledged_at"].startswith("2026-01-16T16:37")
    assert body["notification"]["acks"]

    # repeat ack is idempotent
    resp = client.post(f"/api/notifications/{manager['id']}/ack", json={"actor": "property_manager", "at": "2026-01-16T16:37:00-05:00"})
    assert len(resp.get_json()["acks"]) == 1

    assert snapshot("2026-01-16T18:51:00-05:00") == before_1851
    assert snapshot("2026-01-16T20:21:00-05:00") == before_2021
    # replay at ack time and earlier also unchanged in kind
    assert snapshot("2026-01-16T16:31:00-05:00")[1] == "telemetry_missing"
    rows = _notifications(client, inv_id)
    acked = next(r for r in rows if r["id"] == manager["id"])
    assert acked["state"] == "simulated_delivered"
    assert acked["acks"][0]["actor"] == "property_manager"


def test_no_network_monkeypatched_socket(tmp_path, monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("network socket use attempted")
    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    client = _client(tmp_path, monkeypatch)
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00")
    assert resp.status_code == 200
    inv_id = resp.get_json()["investigation_id"]
    resp = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T16:52:00-05:00")
    assert resp.status_code == 200
    rows = _notifications(client, inv_id)
    assert any(r["audience"] == "hvac_company" and r["state"] == "simulated_delivered" for r in rows)


def test_store_tables_and_refused_never_delivered(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=2026-01-16T09:05:00-05:00")
    inv_id = resp.get_json()["investigation_id"]
    conn = sqlite3.connect(tmp_path / "api.db")
    cols = [r[1] for r in conn.execute("PRAGMA table_info(notifications)").fetchall()]
    assert cols == ["id", "investigation_id", "audience", "kind", "idempotency_key", "payload_json", "created_at", "delivery", "state", "refusal_reason"] or set(["id", "investigation_id", "audience", "kind", "idempotency_key", "payload_json", "created_at", "delivery", "state"]).issubset(cols)
    rows = conn.execute("SELECT audience, state, delivery FROM notifications WHERE investigation_id=?", (inv_id,)).fetchall()
    conn.close()
    assert ("property_manager", "refused", "simulated") in rows
    assert not any(a == "property_manager" and s == "simulated_delivered" for a, s, d in rows)


def test_build_payload_allowlist_enforced():
    with pytest.raises(ValueError):
        from aria_home.notifications import validate_payload
        validate_payload("hvac_company", {"audience": "hvac_company", "email": "x@example.com"})
    payload = build_payload("hvac_company", readiness={"status": "at_risk", "reasons": ["cold"]})
    _assert_payload_clean(payload)
