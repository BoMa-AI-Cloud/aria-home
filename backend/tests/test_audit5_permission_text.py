"""Audit 5: the caregiver permission text is built from the replay moment shown.

The request text (and the WhatsApp text) must describe the evidence visible at
the moment ARIA asks, not at the alert creation time. Each investigation is
created at its replay moment, so the ask moment (02:31) reads the 02:31
evidence: "52 F, furnace quiet since 01:30". Replaying the same investigation
later (04:51) must re-read the later evidence instead of reusing the text from
when the alert was created.
"""
from aria_home.app import create_app

T0231 = "2026-01-17T02:31:00-05:00"
T0451 = "2026-01-17T04:51:00-05:00"


def _client(tmp_path, monkeypatch, name="api.db"):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / name))
    return create_app().test_client()


def _start(client):
    inv_id = client.post(f"/api/investigations?scenario=care_home_v1&at={T0231}").get_json()["investigation_id"]
    return inv_id


def test_followup_permission_text_uses_evidence_visible_when_asked(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = _start(client)
    body = client.get(f"/api/follow-ups/{inv_id}?at={T0231}").get_json()
    text = body["caregiver_permission"]["text"]
    assert "52 F" in text
    assert "01:30" in text
    assert "54 F" not in text


def test_followup_permission_text_reread_when_replayed_later(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = _start(client)
    body = client.get(f"/api/follow-ups/{inv_id}?at={T0451}").get_json()
    text = body["caregiver_permission"]["text"]
    assert "54 F" in text
    assert "52 F" not in text
    assert "01:30" not in text
