"""Caregiver Approve/Decline through the API: HVAC only after approval; readiness and verification untouched."""
from aria_home.app import create_app
from aria_home.notifications import ALLOWLISTS

T0231 = "2026-01-17T02:31:00-05:00"
T0245 = "2026-01-17T02:45:00-05:00"
T0252 = "2026-01-17T02:52:00-05:00"
T0621 = "2026-01-17T06:21:00-05:00"


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    return create_app().test_client()


def _start(client):
    inv_id = client.post(f"/api/investigations?scenario=care_home_v1&at={T0231}").get_json()["investigation_id"]
    body = client.get(f"/api/follow-ups/{inv_id}?at={T0231}").get_json()
    return inv_id, body


def _hvac(client, inv_id, state):
    rows = client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]
    return [r for r in rows if r["audience"] == "hvac_company" and r["state"] == state]


def _decide(client, notification_id, decision, at):
    return client.post(f"/api/notifications/{notification_id}/caregiver-decision", json={"decision": decision, "at": at})


def test_permission_request_waits_with_text(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, body = _start(client)
    permission = body["caregiver_permission"]
    assert permission["status"] == "waiting"
    assert permission["text"] == "ARIA Home (synthetic scenario): your mother's home is cooling (52 F, furnace quiet since 01:30). May I contact the HVAC company? Approve or decline in ARIA Home."


def test_approve_creates_hvac_with_allowed_fields_only(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, body = _start(client)
    assert _hvac(client, inv_id, "simulated_delivered") == []
    resp = _decide(client, body["caregiver_permission"]["notification_id"], "approve", T0231)
    assert resp.status_code == 201
    assert resp.get_json()["decision"]["actor"] == "family_caregiver"
    client.get(f"/api/follow-ups/{inv_id}?at={T0231}")
    delivered = _hvac(client, inv_id, "simulated_delivered")
    assert len(delivered) == 1
    assert set(delivered[0]["payload"]) <= ALLOWLISTS["hvac_company"]
    kinds = [r["kind"] for r in client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]]
    assert "caregiver_update_hvac_contacted" in kinds


def test_decline_blocks_hvac_even_after_the_scripted_approval_time(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, body = _start(client)
    assert _decide(client, body["caregiver_permission"]["notification_id"], "decline", T0231).status_code == 201
    later = client.get(f"/api/follow-ups/{inv_id}?at={T0252}").get_json()
    assert _hvac(client, inv_id, "simulated_delivered") == []
    assert any(r["refusal_reason"] == "caregiver_declined" for r in _hvac(client, inv_id, "refused"))
    assert later["caregiver_permission"]["status"] == "declined"
    assert later["status"]


def test_decision_is_once_only(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    _, body = _start(client)
    notification_id = body["caregiver_permission"]["notification_id"]
    assert _decide(client, notification_id, "approve", T0231).status_code == 201
    second = _decide(client, notification_id, "decline", T0245)
    assert second.status_code == 200
    assert second.get_json()["recorded"] is False
    assert second.get_json()["decision"]["decision"] == "approved"


def test_approval_does_not_change_readiness_or_verification(tmp_path, monkeypatch):
    plain = _client(tmp_path / "a", monkeypatch)
    inv_a, _ = _start(plain)
    before = plain.get(f"/api/follow-ups/{inv_a}?at={T0621}").get_json()

    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "b.db"))
    approved = create_app().test_client()
    inv_b, body = _start(approved)
    _decide(approved, body["caregiver_permission"]["notification_id"], "approve", T0231)
    after = approved.get(f"/api/follow-ups/{inv_b}?at={T0621}").get_json()
    assert after["status"] == before["status"]
    assert after["outcome"] == before["outcome"]
    assert after["verification"]["stage"] == before["verification"]["stage"]
    assert after["verification"]["reasons"] == before["verification"]["reasons"]


def test_rewind_hides_a_later_approval(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, body = _start(client)
    _decide(client, body["caregiver_permission"]["notification_id"], "approve", T0245)
    rewound = client.get(f"/api/follow-ups/{inv_id}?at={T0231}").get_json()
    assert rewound["caregiver_permission"]["status"] == "waiting"


def test_decision_rejects_bad_input(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, body = _start(client)
    notification_id = body["caregiver_permission"]["notification_id"]
    assert _decide(client, notification_id, "maybe", T0231).status_code == 400
    assert client.post(f"/api/notifications/{notification_id}/caregiver-decision", json={"decision": "approve"}).status_code == 400
    assert _decide(client, notification_id, "approve", "2026-01-16T19:00:00-05:00").status_code == 409
    homeowner = next(r for r in client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"] if r["audience"] == "homeowner")
    assert _decide(client, homeowner["id"], "approve", T0231).status_code == 409


def test_permission_whatsapp_send_needs_opt_in(tmp_path, monkeypatch):
    for name in ("WHATSAPP_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_TEST_RECIPIENT", "ARIA_HOME_WHATSAPP_LIVE"):
        monkeypatch.setenv(name, "")
    client = _client(tmp_path, monkeypatch)
    _, body = _start(client)
    notification_id = body["caregiver_permission"]["notification_id"]
    resp = client.post(f"/api/notifications/{notification_id}/whatsapp")
    assert resp.status_code == 409
    assert resp.get_json()["reason"] == "not_configured"
    assert client.get(f"/api/notifications/{notification_id}/whatsapp").status_code == 405


def test_recorded_story_approval_shows_on_the_card(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, _ = _start(client)
    permission = client.get(f"/api/follow-ups/{inv_id}?at={T0245}").get_json()["caregiver_permission"]
    assert permission["status"] == "approved"
    assert permission["source"] == "scenario event (the recorded story)"
    assert permission["decided_at"] == T0245
