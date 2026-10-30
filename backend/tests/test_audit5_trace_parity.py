"""Audit 5: the decision map must agree with the real follow-up and caregiver decision."""
from datetime import datetime
from pathlib import Path

from aria_home.app import create_app
from aria_home.scenario import load_scenario
from aria_home.trace import SCRIPTED_BASIS, build_trace

T0231 = "2026-01-17T02:31:00-05:00"
T0245 = "2026-01-17T02:45:00-05:00"
T0421 = "2026-01-17T04:21:00-05:00"
T0451 = "2026-01-17T04:51:00-05:00"
T0621 = "2026-01-17T06:21:00-05:00"
T0645 = "2026-01-17T06:45:00-05:00"
T0701 = "2026-01-17T07:01:00-05:00"
CHECKPOINTS = (T0231, T0245, T0421, T0451, T0621, T0645, T0701)


def _client(tmp_path, monkeypatch, name="api.db"):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / name))
    return create_app().test_client()


def _start(client):
    inv_id = client.post(f"/api/investigations?scenario=care_home_v1&at={T0231}").get_json()["investigation_id"]
    body = client.get(f"/api/follow-ups/{inv_id}?at={T0231}").get_json()
    return inv_id, body


def _trace(client, inv_id, at):
    return client.get(f"/api/trace?scenario=care_home_v1&at={at}&investigation_id={inv_id}").get_json()


def _hvac(rows):
    return [r for r in rows if r["audience"] == "hvac_company"]


def _decide(client, notification_id, decision, at):
    return client.post(f"/api/notifications/{notification_id}/caregiver-decision", json={"decision": decision, "at": at})


def test_trace_verification_matches_followup_at_every_checkpoint(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, _ = _start(client)
    for at in CHECKPOINTS:
        followup = client.get(f"/api/follow-ups/{inv_id}?at={at}").get_json()
        trace = _trace(client, inv_id, at)
        assert trace["verification"]["stage"] == followup["verification"]["stage"], at


def test_trace_permission_and_hvac_match_decline(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, body = _start(client)
    assert _decide(client, body["caregiver_permission"]["notification_id"], "decline", T0231).status_code == 201
    followup = client.get(f"/api/follow-ups/{inv_id}?at={T0621}").get_json()
    assert followup["caregiver_permission"]["status"] == "declined"
    trace = _trace(client, inv_id, T0621)
    assert trace["permission"]["status"] == "declined"
    trace_hvac = _hvac(trace["notices"])
    assert trace_hvac and all(n["allowed"] is False for n in trace_hvac)
    assert any(n["reason"] == "caregiver_declined" for n in trace_hvac)
    real_hvac = _hvac(followup["notifications"])
    assert any(r["state"] == "refused" and r["refusal_reason"] == "caregiver_declined" for r in real_hvac)
    assert not any(r["state"] == "simulated_delivered" for r in real_hvac)


def test_trace_permission_and_hvac_match_approve(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, body = _start(client)
    assert _decide(client, body["caregiver_permission"]["notification_id"], "approve", T0245).status_code == 201
    followup = client.get(f"/api/follow-ups/{inv_id}?at={T0645}").get_json()
    assert followup["caregiver_permission"]["status"] == "approved"
    trace = _trace(client, inv_id, T0645)
    assert trace["permission"]["status"] == "approved"
    assert any(n["allowed"] is True for n in _hvac(trace["notices"]))
    assert any(r["state"] == "simulated_delivered" for r in _hvac(followup["notifications"]))


def test_trace_rewind_hides_later_decision(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, body = _start(client)
    _decide(client, body["caregiver_permission"]["notification_id"], "approve", T0245)
    trace = _trace(client, inv_id, T0231)
    assert trace["permission"]["status"] == "waiting"
    assert all(n["allowed"] is False for n in _hvac(trace["notices"]))


def test_trace_unknown_investigation_is_404(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    resp = client.get(f"/api/trace?scenario=care_home_v1&at={T0621}&investigation_id=inv-doesnotexist")
    assert resp.status_code == 404


def _public_client(monkeypatch, tmp_path):
    for var in ("ARIA_HOME_MODEL_ENABLED", "ARIA_HOME_WHATSAPP_LIVE", "ARIA_HOME_EMPORIA_LIVE", "ARIA_HOME_VISUAL_LIVE", "ARIA_HOME_NEST_LIVE", "ARIA_HOME_E2E_HOOKS", "ARIA_HOME_DB_PATH"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / "sessions"))
    recorded = tmp_path / "recorded"
    recorded.mkdir(exist_ok=True)
    monkeypatch.setenv("ARIA_HOME_RECORDED_DIR", str(recorded))
    return create_app().test_client()


def test_trace_second_visitor_never_sees_first_decision(tmp_path, monkeypatch):
    first = _public_client(monkeypatch, tmp_path)
    inv_id = first.post(f"/api/investigations?scenario=care_home_v1&at={T0231}").get_json()["investigation_id"]
    body = first.get(f"/api/follow-ups/{inv_id}?at={T0231}").get_json()
    assert _decide(first, body["caregiver_permission"]["notification_id"], "decline", T0231).status_code == 201
    second = create_app().test_client()
    resp = second.get(f"/api/trace?scenario=care_home_v1&at={T0621}&investigation_id={inv_id}")
    assert resp.status_code == 404


def test_trace_reset_clears_visitor_decision(tmp_path, monkeypatch):
    client = _public_client(monkeypatch, tmp_path)
    inv_id = client.post(f"/api/investigations?scenario=care_home_v1&at={T0231}").get_json()["investigation_id"]
    body = client.get(f"/api/follow-ups/{inv_id}?at={T0231}").get_json()
    assert _decide(client, body["caregiver_permission"]["notification_id"], "decline", T0231).status_code == 201
    assert client.get(f"/api/trace?scenario=care_home_v1&at={T0621}&investigation_id={inv_id}").status_code == 200
    assert client.post("/api/session/reset").status_code == 200
    assert client.get(f"/api/trace?scenario=care_home_v1&at={T0621}&investigation_id={inv_id}").status_code == 404


def test_trace_known_investigation_before_followup_is_scripted(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id, _ = _start(client)
    early = "2026-01-16T18:00:00-05:00"
    resp = client.get(f"/api/trace?scenario=care_home_v1&at={early}&investigation_id={inv_id}")
    assert resp.status_code == 200
    assert resp.get_json()["basis"] == SCRIPTED_BASIS
    created = client.post("/api/investigations?scenario=demo_no_followup_v1&at=2026-01-16T20:31:00-05:00").get_json()
    assert created["follow_up"] is None
    resp = client.get(f"/api/trace?scenario=demo_no_followup_v1&at=2026-01-16T20:31:00-05:00&investigation_id={created['investigation_id']}")
    assert resp.status_code == 200
    assert resp.get_json()["basis"] == SCRIPTED_BASIS


def test_trace_human_report_changes_no_decision():
    scn = load_scenario(Path(__file__).resolve().parent.parent / "scenarios" / "care_home_v1")
    at = datetime.fromisoformat(T0645)
    with_report = build_trace(scn, at)
    assert with_report["basis"] == SCRIPTED_BASIS
    assert with_report["human_report"] is not None
    without_report = build_trace(scn, at, transcript_entries=[])
    assert without_report["human_report"] is None
    assert without_report["readiness"] == with_report["readiness"]
    assert without_report["verification"]["stage"] == with_report["verification"]["stage"]
    assert without_report["verification"]["reasons"] == with_report["verification"]["reasons"]
    assert without_report["verification_timeline"] == with_report["verification_timeline"]
    assert without_report["notices"] == with_report["notices"]
