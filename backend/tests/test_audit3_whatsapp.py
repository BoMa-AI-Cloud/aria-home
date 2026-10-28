import json
import socket
import sqlite3
from pathlib import Path

from aria_home import whatsapp
from aria_home.app import create_app
from aria_home.notifications import ALLOWLISTS
from aria_home.scenario import load_scenario

AUDIT = Path(__file__).resolve().parent.parent.parent / "docs" / "whatsapp-audit.json"
SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"

TOKEN = "test-whatsapp-token-abc123"
PHONE_ID = "19876543210"
RECIPIENT = "+15550001111"

LIVE_ENV = {
    "WHATSAPP_TOKEN": TOKEN,
    "WHATSAPP_PHONE_NUMBER_ID": PHONE_ID,
    "WHATSAPP_TEST_RECIPIENT": RECIPIENT,
    "ARIA_HOME_WHATSAPP_LIVE": "1",
}

INV_AT = "2026-01-16T16:31:00-05:00"
FOLLOW_AT = "2026-01-16T16:52:00-05:00"
EARLY_AT = "2026-01-16T16:31:00-05:00"


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    return create_app().test_client()


def _live_env(monkeypatch, **overrides):
    for name in whatsapp.REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)
    env = dict(LIVE_ENV)
    env.update(overrides)
    for name, value in env.items():
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


def _hvac_flow(client, fake=None):
    resp = client.post(f"/api/investigations?scenario=demo_video_v1&at={INV_AT}")
    assert resp.status_code == 200
    inv_id = resp.get_json()["investigation_id"]
    resp = client.get(f"/api/follow-ups/{inv_id}?at={FOLLOW_AT}")
    assert resp.status_code == 200
    resp = client.get(f"/api/follow-ups/{inv_id}?at={FOLLOW_AT}")
    assert resp.status_code == 200
    if fake is not None:
        assert fake.calls == []
    rows = client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]
    hvac = next(r for r in rows if r["audience"] == "hvac_company" and r["state"] == "simulated_delivered")
    return inv_id, hvac


def _send(client, notification_id, at=None):
    query = f"?at={at}" if at else ""
    return client.post(f"/api/notifications/{notification_id}/whatsapp{query}")


def _attempt_rows(tmp_path):
    conn = sqlite3.connect(tmp_path / "api.db")
    try:
        return conn.execute("SELECT notification_id, state, message_id, attempted_at FROM whatsapp_attempts").fetchall()
    finally:
        conn.close()


class _FakeHttp:
    def __init__(self, status=200, payload=None, error=None):
        self.calls = []
        self.status = status
        self.payload = payload if payload is not None else {"messages": [{"id": "wamid.TEST123"}]}
        self.error = error

    def __call__(self, url, headers, body):
        self.calls.append({"url": url, "headers": headers, "body": body})
        if self.error is not None:
            raise self.error
        return self.status, self.payload


def test_get_follow_ups_never_sends_even_when_configured(tmp_path, monkeypatch):
    _live_env(monkeypatch)
    fake = _FakeHttp()
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    inv_id, hvac = _hvac_flow(client, fake)
    assert hvac["whatsapp"] is None
    assert _attempt_rows(tmp_path) == []


def test_not_opted_in_leaves_notice_exactly_as_today(tmp_path, monkeypatch):
    for name in whatsapp.REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)

    def blocked(*args, **kwargs):
        raise AssertionError("network socket use attempted")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    client = _client(tmp_path, monkeypatch)
    _, hvac = _hvac_flow(client)
    assert hvac["delivery"] == "simulated"
    assert hvac["state"] == "simulated_delivered"
    assert hvac["whatsapp"] is None
    assert _attempt_rows(tmp_path) == []


def test_each_missing_env_var_stays_simulated(tmp_path, monkeypatch):
    for name in whatsapp.REQUIRED_ENV:
        _live_env(monkeypatch, **{name: None})
        client = _client(tmp_path, monkeypatch)
        _, hvac = _hvac_flow(client)
        assert hvac["whatsapp"] is None, name
        resp = _send(client, hvac["id"])
        assert resp.status_code == 409
        assert resp.get_json()["reason"] == "not_configured"
        assert _attempt_rows(tmp_path) == []
        (tmp_path / "api.db").unlink()


def test_whatsapp_status_reports_only_configured(tmp_path, monkeypatch):
    for name in whatsapp.REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)
    client = _client(tmp_path, monkeypatch)
    body = client.get("/api/whatsapp/status").get_json()
    assert body["configured"] is False
    text = client.get("/api/whatsapp/status").get_data(as_text=True)
    assert TOKEN not in text and RECIPIENT not in text
    _live_env(monkeypatch)
    body = client.get("/api/whatsapp/status").get_json()
    assert body["configured"] is True
    text = client.get("/api/whatsapp/status").get_data(as_text=True)
    assert TOKEN not in text and RECIPIENT not in text and PHONE_ID not in text


def test_post_sends_once_and_second_post_does_not_resend(tmp_path, monkeypatch):
    _live_env(monkeypatch)
    fake = _FakeHttp()
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    inv_id, hvac = _hvac_flow(client, fake)
    resp = _send(client, hvac["id"])
    assert resp.status_code == 200
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["url"] == f"https://graph.facebook.com/v25.0/{PHONE_ID}/messages"
    assert call["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert call["body"]["type"] == "text"
    assert call["body"]["to"] == RECIPIENT
    assert call["body"]["text"]["body"].splitlines()[0] == "ARIA Home test (synthetic scenario)"
    payload = resp.get_json()
    assert payload["whatsapp"]["state"] == "delivered_to_test_number"
    assert payload["notification"]["whatsapp"]["message_id"] == "wamid.TEST123"
    resp = _send(client, hvac["id"])
    assert resp.status_code == 200
    assert len(fake.calls) == 1
    assert len(_attempt_rows(tmp_path)) == 1
    rows = client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]
    hvac = next(r for r in rows if r["audience"] == "hvac_company")
    assert hvac["whatsapp"]["state"] == "delivered_to_test_number"
    assert hvac["whatsapp"]["message_id"] == "wamid.TEST123"
    assert hvac["whatsapp"]["attempted_at"]
    stored = _attempt_rows(tmp_path)
    assert len(stored) == 1 and stored[0][1] == "delivered_to_test_number" and stored[0][2] == "wamid.TEST123"


def test_success_records_status_and_message_id(tmp_path, monkeypatch):
    _live_env(monkeypatch)
    fake = _FakeHttp()
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    inv_id, hvac = _hvac_flow(client, fake)
    resp = _send(client, hvac["id"])
    assert resp.status_code == 200
    assert len(fake.calls) == 1
    rows = client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]
    hvac = next(r for r in rows if r["audience"] == "hvac_company")
    assert hvac["whatsapp"]["state"] == "delivered_to_test_number"
    assert hvac["whatsapp"]["message_id"] == "wamid.TEST123"
    assert hvac["whatsapp"]["attempted_at"]
    stored = _attempt_rows(tmp_path)
    assert len(stored) == 1 and stored[0][1] == "delivered_to_test_number" and stored[0][2] == "wamid.TEST123"


def test_second_post_and_replay_never_resend(tmp_path, monkeypatch):
    _live_env(monkeypatch)
    fake = _FakeHttp()
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    inv_id, hvac = _hvac_flow(client, fake)
    assert _send(client, hvac["id"]).status_code == 200
    assert len(fake.calls) == 1
    url = f"/api/investigations?scenario=demo_video_v1&at={INV_AT}"
    assert client.post(url).status_code == 200
    assert client.get(f"/api/follow-ups/{inv_id}?at={FOLLOW_AT}").status_code == 200
    assert client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T18:21:00-05:00").status_code == 200
    assert len(fake.calls) == 1
    assert len(_attempt_rows(tmp_path)) == 1


def test_not_configured_post_returns_409_and_changes_nothing(tmp_path, monkeypatch):
    for name in whatsapp.REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)
    fake = _FakeHttp()
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    _, hvac = _hvac_flow(client, fake)
    resp = _send(client, hvac["id"])
    assert resp.status_code == 409
    assert resp.get_json()["reason"] == "not_configured"
    assert fake.calls == []
    assert _attempt_rows(tmp_path) == []


def test_wrong_audience_returns_409(tmp_path, monkeypatch):
    _live_env(monkeypatch)
    fake = _FakeHttp()
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    inv_id, _ = _hvac_flow(client, fake)
    rows = client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]
    other = next(r for r in rows if r["audience"] != "hvac_company")
    resp = _send(client, other["id"])
    assert resp.status_code == 409
    assert fake.calls == []
    assert _attempt_rows(tmp_path) == []


def test_unknown_notification_returns_404(tmp_path, monkeypatch):
    _live_env(monkeypatch)
    client = _client(tmp_path, monkeypatch)
    resp = _send(client, "notif-does-not-exist")
    assert resp.status_code == 404


def test_not_yet_visible_returns_409(tmp_path, monkeypatch):
    _live_env(monkeypatch)
    fake = _FakeHttp()
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    _, hvac = _hvac_flow(client, fake)
    resp = _send(client, hvac["id"], at=EARLY_AT)
    assert resp.status_code == 409
    assert fake.calls == []
    assert _attempt_rows(tmp_path) == []


def test_outside_window_clears_status_and_never_500(tmp_path, monkeypatch):
    _live_env(monkeypatch)
    fake = _FakeHttp(status=400, payload={"error": {"code": 131047, "message": "Message failed: sent outside the 24-hour window"}})
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    resp = client.post(f"/api/investigations?scenario=demo_video_v1&at={INV_AT}")
    assert resp.status_code == 200
    inv_id = resp.get_json()["investigation_id"]
    resp = client.get(f"/api/follow-ups/{inv_id}?at={FOLLOW_AT}")
    assert resp.status_code == 200
    assert fake.calls == []
    rows = client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]
    hvac = next(r for r in rows if r["audience"] == "hvac_company")
    assert _send(client, hvac["id"]).status_code == 200
    rows = client.get(f"/api/notifications?investigation_id={inv_id}").get_json()["notifications"]
    hvac = next(r for r in rows if r["audience"] == "hvac_company")
    assert hvac["whatsapp"]["state"] == "failed:outside_24h_window"
    assert hvac["whatsapp"]["message_id"] is None
    assert "delivered" not in (hvac["whatsapp"]["state"] or "")


def test_wrong_recipient_refused_without_http(tmp_path, monkeypatch):
    _live_env(monkeypatch)
    fake = _FakeHttp()
    from aria_home.store import Store

    store = Store(path=tmp_path / "refused.db")
    notice = {"id": "notif-refusal-probe", "audience": "hvac_company", "state": "simulated_delivered", "payload": {"audience": "hvac_company", "kind": "hvac_request"}}
    result = whatsapp.attempt_hvac_whatsapp_delivery(store, notice, recipient="+19998887777", http_post=fake)
    assert result["reason"] == "refused:recipient_not_test_number"
    assert result["state"] == "refused"
    assert fake.calls == []
    assert store.get_whatsapp_attempt(notice["id"])["state"] == "refused"


def test_message_content_is_exactly_the_allowlisted_payload(tmp_path, monkeypatch):
    _live_env(monkeypatch)
    fake = _FakeHttp()
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    _, hvac = _hvac_flow(client, fake)
    assert _send(client, hvac["id"]).status_code == 200
    assert set(hvac["payload"]) == ALLOWLISTS["hvac_company"]
    text = fake.calls[0]["body"]["text"]["body"]
    assert text == whatsapp.build_hvac_whatsapp_text(hvac["payload"])
    lowered = text.lower()
    for part in ("trip", "itinerary", "email", "phone", "location", "flight"):
        assert part not in lowered, part
    assert RECIPIENT not in text and TOKEN not in text


def test_token_and_recipient_never_in_db_responses_or_logs(tmp_path, monkeypatch, caplog):
    _live_env(monkeypatch)
    fake = _FakeHttp()
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    inv_id, hvac = _hvac_flow(client, fake)
    assert _send(client, hvac["id"]).status_code == 200
    with caplog.at_level("INFO"):
        resp = client.get(f"/api/notifications?investigation_id={inv_id}")
        assert resp.status_code == 200
        body_text = resp.get_data(as_text=True)
    raw_db = (tmp_path / "api.db").read_bytes()
    for secret in (TOKEN.encode(), RECIPIENT.encode()):
        assert secret not in raw_db
        assert secret.decode() not in body_text
    assert TOKEN not in caplog.text and RECIPIENT not in caplog.text
    headers = fake.calls[0]["headers"]
    assert TOKEN in headers["Authorization"]


def test_whatsapp_audit_matches_code(tmp_path, monkeypatch):
    data = json.loads(AUDIT.read_text(encoding="utf-8"))
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "audit.db"))
    client = create_app().test_client()
    inv = client.post(f"/api/investigations?scenario=demo_video_v1&at={INV_AT}").get_json()["investigation_id"]
    client.get(f"/api/follow-ups/{inv}?at={INV_AT}")
    client.get(f"/api/follow-ups/{inv}?at={FOLLOW_AT}")
    rows = client.get(f"/api/notifications?investigation_id={inv}").get_json()["notifications"]
    hvac = next(r for r in rows if r["audience"] == "hvac_company" and r["state"] == "simulated_delivered")
    scenario = load_scenario(SCENARIOS / "demo_video_v1")
    auth = next(e for e in scenario.events if e.kind == "manager_hvac_authorized")
    expected = whatsapp.build_whatsapp_audit(
        hvac["payload"],
        {"id": auth.id, "kind": auth.kind, "available_at": auth.available_at.isoformat(), "event_time": auth.event_time.isoformat()},
    )
    assert data == expected
