"""P1-3: every route taking an investigation id refuses a scenario mismatch like /api/trace."""
from aria_home.app import create_app

CARE = "care_home_v1"
VIDEO = "demo_video_v1"
CARE_AT = "2026-01-16T22:46:00-05:00"
VIDEO_AT = "2026-01-16T16:31:00-05:00"


def _client(tmp_path, monkeypatch, name="p13.db"):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / name))
    return create_app().test_client()


def _start(client, scenario, at):
    inv_id = client.post(f"/api/investigations?scenario={scenario}&at={at}").get_json()["investigation_id"]
    return inv_id


def test_followups_mismatch_both_directions(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    care = _start(client, CARE, CARE_AT)
    video = _start(client, VIDEO, VIDEO_AT)
    assert client.get(f"/api/follow-ups/{care}?at={CARE_AT}&scenario={VIDEO}").status_code == 400
    assert client.get(f"/api/follow-ups/{video}?at={VIDEO_AT}&scenario={CARE}").status_code == 400


def test_unknown_id_is_404(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    assert client.get(f"/api/follow-ups/inv-nope?at={CARE_AT}").status_code == 404
    assert client.get(f"/api/trace?scenario={CARE}&at={CARE_AT}&investigation_id=inv-nope").status_code == 404
    assert client.post("/api/notifications/notif-nope/caregiver-decision", json={"decision": "approve", "at": CARE_AT}).status_code == 404
    assert client.post("/api/notifications/notif-nope/ack", json={"actor": "homeowner", "at": CARE_AT}).status_code == 404


def test_valid_context_passes(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    care = _start(client, CARE, CARE_AT)
    assert client.get(f"/api/follow-ups/{care}?at={CARE_AT}&scenario={CARE}").status_code == 200
    body = client.get(f"/api/follow-ups/{care}?at={CARE_AT}").get_json()
    notif_id = body["caregiver_permission"]["notification_id"]
    assert client.post(f"/api/notifications/{notif_id}/caregiver-decision?scenario={CARE}", json={"decision": "approve", "at": CARE_AT}).status_code == 201


def test_decision_and_ack_refuse_mismatch(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    care = _start(client, CARE, CARE_AT)
    body = client.get(f"/api/follow-ups/{care}?at={CARE_AT}").get_json()
    notif_id = body["caregiver_permission"]["notification_id"]
    assert client.post(f"/api/notifications/{notif_id}/caregiver-decision?scenario={VIDEO}", json={"decision": "approve", "at": CARE_AT}).status_code == 400
    homeowner = next(r for r in client.get(f"/api/notifications?investigation_id={care}").get_json()["notifications"] if r["audience"] == "homeowner")
    assert client.post(f"/api/notifications/{homeowner['id']}/ack?scenario={VIDEO}", json={"actor": "homeowner", "at": CARE_AT}).status_code == 400
    assert client.get(f"/api/notifications?investigation_id={care}&scenario={VIDEO}").status_code == 400


def test_another_visitors_id_is_404(tmp_path, monkeypatch):
    client_a = _client(tmp_path, monkeypatch, "p13a.db")
    care = _start(client_a, CARE, CARE_AT)
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "p13b.db"))
    client_b = create_app().test_client()
    assert client_b.get(f"/api/follow-ups/{care}?at={CARE_AT}").status_code == 404
    assert client_b.get(f"/api/trace?scenario={CARE}&at={CARE_AT}&investigation_id={care}").status_code == 404
