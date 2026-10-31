"""Audit 5 follow-up: the caregiver permission text is frozen at alert-creation time.

The request text (and the WhatsApp text) must describe the evidence visible at
the moment ARIA asked — the alert creation time — not the replay time. The
story raises the request at 19:20 ("54 F, furnace quiet since 19:15"); replaying
the same investigation at 02:31 or later keeps that frozen text instead of
re-reading the later evidence ("52 F ... 01:30"). Before the request is raised
(19:03, 19:15) there is no card.
"""
from aria_home import whatsapp
from aria_home.app import create_app

T1903 = "2026-01-16T19:03:00-05:00"
T1915 = "2026-01-16T19:15:00-05:00"
T1920 = "2026-01-16T19:20:00-05:00"
T0231 = "2026-01-17T02:31:00-05:00"
T0451 = "2026-01-17T04:51:00-05:00"
T0621 = "2026-01-17T06:21:00-05:00"

TOKEN = "test-whatsapp-token-abc123"
PHONE_ID = "19876543210"
RECIPIENT = "+15550001111"


def _client(tmp_path, monkeypatch, name="api.db"):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / name))
    return create_app().test_client()


def _start(client, at):
    resp = client.post(f"/api/investigations?scenario=care_home_v1&at={at}")
    assert resp.status_code == 200
    return resp.get_json()["investigation_id"]


def _permission_at(client, inv_id, at):
    body = client.get(f"/api/follow-ups/{inv_id}?at={at}").get_json()
    permission = body["caregiver_permission"]
    assert permission is not None
    return permission


def test_followup_permission_text_uses_evidence_visible_when_asked(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = _start(client, T0231)
    text = _permission_at(client, inv_id, T0231)["text"]
    assert "52 F" in text
    assert "01:30" in text
    assert "54 F" not in text


def test_followup_permission_text_frozen_at_creation_on_replay(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = _start(client, T1920)
    permission = _permission_at(client, inv_id, T0231)
    assert permission["requested_at"].startswith("2026-01-16T19:20")
    assert "54 F" in permission["text"]
    assert "19:15" in permission["text"]
    assert "52 F" not in permission["text"]
    assert "01:30" not in permission["text"]


def test_followup_permission_text_stays_frozen_at_later_replays(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = _start(client, T1920)
    for at, absent in ((T0451, "04:50"), (T0621, "06:20")):
        text = _permission_at(client, inv_id, at)["text"]
        assert "54 F" in text
        assert "19:15" in text
        assert absent not in text


def test_no_permission_card_before_request_raised(tmp_path, monkeypatch):
    for name, at in (("early.db", T1903), ("mid.db", T1915)):
        client = _client(tmp_path, monkeypatch, name=name)
        created = client.post(f"/api/investigations?scenario=care_home_v1&at={at}").get_json()
        assert [
            item for item in created.get("notifications") or []
            if item.get("audience") == "family_caregiver"
            and item.get("kind") == "caregiver_alert"
            and item.get("state") == "simulated_delivered"
        ] == []


def test_decision_response_carries_frozen_text(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = _start(client, T1920)
    notification_id = _permission_at(client, inv_id, T1920)["notification_id"]
    resp = client.post(
        f"/api/notifications/{notification_id}/caregiver-decision",
        json={"decision": "approve", "at": T0231},
    )
    assert resp.status_code == 201
    text = resp.get_json()["caregiver_permission"]["text"]
    assert "54 F" in text
    assert "19:15" in text
    assert "52 F" not in text
    assert "01:30" not in text


class _FakeHttp:
    def __init__(self):
        self.calls = []

    def __call__(self, url, headers, body):
        self.calls.append({"url": url, "headers": headers, "body": body})
        return 200, {"messages": [{"id": "wamid.TEST123"}]}


def test_permission_whatsapp_body_uses_frozen_text(tmp_path, monkeypatch):
    for name in whatsapp.REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("WHATSAPP_TOKEN", TOKEN)
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", PHONE_ID)
    monkeypatch.setenv("WHATSAPP_TEST_RECIPIENT", RECIPIENT)
    monkeypatch.setenv("ARIA_HOME_WHATSAPP_LIVE", "1")
    fake = _FakeHttp()
    monkeypatch.setattr(whatsapp, "_http_post", fake)
    client = _client(tmp_path, monkeypatch)
    inv_id = _start(client, T1920)
    notification_id = _permission_at(client, inv_id, T1920)["notification_id"]
    resp = client.post(f"/api/notifications/{notification_id}/whatsapp?at={T0231}")
    assert resp.status_code == 200
    card_text = _permission_at(client, inv_id, T0231)["text"]
    text = fake.calls[0]["body"]["text"]["body"]
    assert card_text in text
    assert "54 F" in text
    assert "19:15" in text
    assert "52 F" not in text
    assert "01:30" not in text
