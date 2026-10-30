from datetime import datetime, timedelta, timezone
from pathlib import Path

from aria_home.app import create_app
from aria_home.notifications import ALLOWLISTS
from aria_home.outcomes import follow_up_for
from aria_home.scenario import events_as_of, load_scenario
from aria_home.verification import verify_recovery

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "care_home_v1"
TZ = timezone(timedelta(hours=-5))
FORBIDDEN = ("trip", "itinerary", "email", "phone", "location", "flight", "health", "medical", "fall")

T0231 = "2026-01-17T02:31:00-05:00"
T0445 = "2026-01-17T02:45:00-05:00"
T0421 = "2026-01-17T04:21:00-05:00"
T0451 = "2026-01-17T04:51:00-05:00"
T0621 = "2026-01-17T06:21:00-05:00"
T0701 = "2026-01-17T07:01:00-05:00"


def at(day, hour, minute=0, second=0):
    return datetime(2026, 1, day, hour, minute, second, tzinfo=TZ)


def _stage(now):
    scenario = load_scenario(SCENARIO_DIR)
    followup = follow_up_for(scenario, "inv-care", at(17, 2, 31))
    return verify_recovery(scenario, followup, now)


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


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    return create_app().test_client()


def _notifications(client, inv_id):
    resp = client.get(f"/api/notifications?investigation_id={inv_id}")
    assert resp.status_code == 200
    return resp.get_json()["notifications"]


def test_care_scenario_loads_with_warmby_plan():
    scenario = load_scenario(SCENARIO_DIR)
    assert scenario.manifest.id == "care_home_v1"
    assert scenario.trip is not None
    assert scenario.trip.planned_arrival == at(17, 7)
    assert scenario.confirmation is not None
    assert scenario.confirmation.target_temp == 68
    assert {r.source.value for r in scenario.records} >= {
        "calendar",
        "thermostat",
        "room_sensor",
        "electrical",
        "weather",
    }


def test_stage_sequence_to_warmby_time():
    assert _stage(at(17, 2, 31))["stage"] == "telemetry_missing"
    assert _stage(at(17, 4, 21))["stage"] == "reporting_restored"
    assert _stage(at(17, 4, 51))["stage"] == "warming_observed"
    assert _stage(at(17, 6, 21))["stage"] == "goal_verified"
    assert _stage(at(17, 7, 1))["stage"] == "arrival_met"


def test_late_start_replay_judges_warmby_from_available_readings():
    scenario = load_scenario(SCENARIO_DIR)
    followup = follow_up_for(scenario, "inv-care-late", at(17, 7, 1))
    result = verify_recovery(scenario, followup, at(17, 7, 1))
    assert result["stage"] == "arrival_met"
    normal = _stage(at(17, 7, 1))
    assert result["goal_verified_at"] == normal["goal_verified_at"]
    by_id = {r.id: r for r in scenario.records}
    arrival = at(17, 7)
    for rid in result["supporting_ids"]:
        assert by_id[rid].observed_at <= arrival
        assert by_id[rid].received_at <= at(17, 7, 1)
    latest = result["latest_reading_used"]
    assert latest is not None and latest["observed_at"] <= arrival


def test_caregiver_replaces_manager_with_own_allowlist_and_refusals(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = client.post(f"/api/investigations?scenario=care_home_v1&at={T0231}").get_json()["investigation_id"]
    rows = _notifications(client, inv_id)
    audiences = {r["audience"] for r in rows}
    assert "family_caregiver" in audiences
    assert "property_manager" not in audiences
    for row in rows:
        _assert_payload_clean(row["payload"])
        assert row["payload"]["audience"] == row["audience"]
    caregiver = next(r for r in rows if r["audience"] == "family_caregiver")
    assert caregiver["state"] == "simulated_delivered"
    assert caregiver["kind"] == "caregiver_alert"
    assert caregiver["payload"]["property_label"] == "demo-house"
    assert caregiver["payload"]["requested_action"]
    assert caregiver["payload"]["access_note"]


def test_caregiver_refused_before_confirmation(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = client.post("/api/investigations?scenario=care_home_v1&at=2026-01-16T18:00:00-05:00").get_json()["investigation_id"]
    rows = _notifications(client, inv_id)
    caregiver = [r for r in rows if r["audience"] == "family_caregiver"]
    assert caregiver, rows
    assert caregiver[0]["state"] == "refused"
    assert caregiver[0]["refusal_reason"] == "caregiver_not_authorized"


def test_hvac_needs_caregiver_authorisation(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = client.post(f"/api/investigations?scenario=care_home_v1&at={T0231}").get_json()["investigation_id"]
    client.get(f"/api/follow-ups/{inv_id}?at={T0231}")
    rows = _notifications(client, inv_id)
    hvac = [r for r in rows if r["audience"] == "hvac_company"]
    assert hvac and hvac[0]["state"] == "refused"
    assert hvac[0]["refusal_reason"] == "caregiver_hvac_not_authorized"

    client.get(f"/api/follow-ups/{inv_id}?at=2026-01-17T02:52:00-05:00")
    rows = _notifications(client, inv_id)
    delivered = [r for r in rows if r["audience"] == "hvac_company" and r["state"] == "simulated_delivered"]
    assert delivered, rows
    payload = delivered[0]["payload"]
    _assert_payload_clean(payload)
    assert set(payload) == {"audience", "kind", "property_label", "access_note", "manager_contact_label", "relevant_observations"}
    assert "caregiver" in payload["manager_contact_label"]


def test_ack_never_resolves(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = client.post(f"/api/investigations?scenario=care_home_v1&at={T0231}").get_json()["investigation_id"]

    def snapshot(stamp):
        body = client.get(f"/api/follow-ups/{inv_id}?at={stamp}").get_json()
        return body["outcome"]["status"], body["verification"]["stage"]

    before_0451 = snapshot(T0451)
    before_0621 = snapshot(T0621)

    rows = _notifications(client, inv_id)
    caregiver = next(r for r in rows if r["audience"] == "family_caregiver")
    resp = client.post(f"/api/notifications/{caregiver['id']}/ack", json={"actor": "family_caregiver", "at": "2026-01-17T02:40:00-05:00"})
    assert resp.status_code == 200
    assert resp.get_json()["message"] == "acknowledged, not resolved"

    assert snapshot(T0451) == before_0451
    assert snapshot(T0621) == before_0621
    assert snapshot(T0231)[1] == "telemetry_missing"
    acked = next(r for r in _notifications(client, inv_id) if r["id"] == caregiver["id"])
    assert acked["state"] == "simulated_delivered"


def test_human_report_never_verifies_and_thermostat_return_proves_nothing():
    assert _stage(at(17, 4, 21))["stage"] == "reporting_restored"
    late = _stage(at(17, 7, 1))
    assert late["stage"] == "arrival_met"
    assert "evt-care-hvac-completion-report" not in late["supporting_ids"]
    assert "evt-care-service-visit" not in late["supporting_ids"]


def test_replay_reveals_no_future(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = client.post(f"/api/investigations?scenario=care_home_v1&at={T0231}").get_json()["investigation_id"]
    import json

    body = client.get(f"/api/follow-ups/{inv_id}?at={T0231}").get_json()
    text = json.dumps(body)
    assert body["verification"]["stage"] == "telemetry_missing"
    assert '"stage": "arrival_met"' not in text
    assert '"stage": "goal_verified"' not in text
    assert '"stage": "warming_observed"' not in text
    assert "2026-01-17T06:4" not in text
    assert "caregiver_hvac_authorized" not in text
    assert "hvac_completion_report" not in text
    events = client.get(f"/api/events?scenario=care_home_v1&at={T0231}").get_json()
    kinds = {e["kind"] for e in events["events"]}
    assert "caregiver_hvac_authorized" not in kinds
    assert "hvac_request" not in kinds
    assert "hvac_completion_report" not in kinds


def test_public_demo_serves_care_default(tmp_path, monkeypatch):
    for var in ("ARIA_HOME_PROVIDER_URL", "ARIA_HOME_MODEL_ID", "MODEL_API_KEY", "ARIA_HOME_MODEL_ENABLED", "ARIA_HOME_WHATSAPP_LIVE", "ARIA_HOME_EMPORIA_LIVE", "ARIA_HOME_VISUAL_LIVE", "ARIA_HOME_E2E_HOOKS", "ARIA_HOME_DB_PATH"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / "sessions"))
    recorded = tmp_path / "recorded"
    recorded.mkdir()
    monkeypatch.setenv("ARIA_HOME_RECORDED_DIR", str(recorded))
    client = create_app().test_client()
    health = client.get("/api/health").get_json()
    assert health["scenario"] == "care_home_v1"
    scenarios = client.get("/api/scenarios").get_json()["scenarios"]
    care = next(s for s in scenarios if s["id"] == "care_home_v1")
    assert T0231 in care["checkpoints"]
    assert T0701 in care["checkpoints"]
    assert client.get(f"/api/sources?scenario=care_home_v1&at={T0231}").status_code == 200
    assert client.get("/api/sources?scenario=care_home_v1&at=2026-01-17T03:00:00-05:00").status_code == 400
