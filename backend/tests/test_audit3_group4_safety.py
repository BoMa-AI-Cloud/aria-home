import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aria_home.app import create_app
from aria_home.contracts import EvidenceRecord
from aria_home.evaluation import evaluate_cases
from aria_home.notifications import ALLOWLISTS
from aria_home.outcomes import evaluate_outcome, follow_up_for
from aria_home.scenario import events_as_of, load_scenario, visible_records
from aria_home.verification import verify_recovery

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
TZ = timezone(timedelta(hours=-5))
REPLAY = ["16:31", "16:52", "18:21", "18:51", "19:51", "20:21", "20:46", "21:01"]
FORBIDDEN = ("itinerary", "owner_email", "email", "location", "calendar", "flight", "trip")


def at(hm):
    h, m = hm.split(":")
    return datetime(2026, 1, 16, int(h), int(m), tzinfo=TZ)


def iso(hm):
    return at(hm).isoformat()


def _client(tmp_path, monkeypatch, name="g4.db"):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / name))
    return create_app().test_client()


def _keys(value):
    out = []
    if isinstance(value, dict):
        for k, v in value.items():
            out.append(str(k).lower())
            out.extend(_keys(v))
    elif isinstance(value, list):
        for item in value:
            out.extend(_keys(item))
    return out


def _hvac_at_1652(client):
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=" + iso("16:31"))
    assert resp.status_code == 200, resp.get_json()
    inv = resp.get_json()["investigation_id"]
    assert client.get(f"/api/follow-ups/{inv}?at={iso('16:31')}").status_code == 200
    assert client.get(f"/api/follow-ups/{inv}?at={iso('16:52')}").status_code == 200
    rows = client.get(f"/api/notifications?investigation_id={inv}").get_json()["notifications"]
    return inv, rows


def test_hvac_payload_excludes_sensitive_fields_and_refusals_recorded(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv, rows = _hvac_at_1652(client)
    delivered = [r for r in rows if r["audience"] == "hvac_company" and r["state"] == "simulated_delivered"]
    assert delivered, rows
    payload = delivered[0]["payload"]
    assert set(payload) == set(ALLOWLISTS["hvac_company"])
    for key in _keys(payload):
        assert not any(part in key for part in FORBIDDEN), key
    blob = json.dumps(payload).lower()
    for word in ("itinerary", "@", "flight", "calendar"):
        assert word not in blob
    refused = [r for r in rows if r["state"] == "refused"]
    assert refused and all(r["refusal_reason"] for r in refused)
    early = client.get(f"/api/follow-ups/{inv}?at={iso('16:31')}").get_json()
    assert any(r["audience"] == "hvac_company" and r["state"] == "refused" and r["refusal_reason"] == "manager_hvac_not_authorized" for r in rows)


def test_electrical_alone_never_on_track_or_warming_and_single_source_limits():
    rows = evaluate_cases()
    for row in rows:
        if row["condition"] == "electrical_only":
            assert row["got_readiness"] != "on_track", row
            assert row["got_verification"] not in ("warming_observed", "goal_verified", "arrival_met"), row
            assert row["claims"]["useful_heat"] is False, row
    thermo = next(r for r in rows if r["case_id"] == "demo_video_v1@16:31" and r["condition"] == "thermostat_only")
    assert thermo["claims"]["current_temperature"] is False, thermo
    assert thermo["claims"]["warming"] is False, thermo
    for case in ("demo_video_v1@16:31", "demo_video_v1@18:21"):
        room = next(r for r in rows if r["case_id"] == case and r["condition"] == "room_sensor_only")
        assert room["got_verification"] != "warming_observed", room
        assert room["claims"]["warming"] is False, room


def test_manager_ack_at_1652_changes_nothing(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, "ack1652.db")
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=" + iso("16:31"))
    inv = resp.get_json()["investigation_id"]

    def snap(hm):
        body = client.get(f"/api/follow-ups/{inv}?at={iso(hm)}").get_json()
        inv_body = client.get(f"/api/investigation?scenario=demo_video_v1&at={iso(hm)}").get_json()
        return (inv_body["computed_readiness"], body["outcome"]["status"], body["verification"]["stage"])

    before = {hm: snap(hm) for hm in ("18:51", "20:21")}
    rows = client.get(f"/api/notifications?investigation_id={inv}").get_json()["notifications"]
    manager = next(r for r in rows if r["audience"] == "property_manager" and r["state"] == "simulated_delivered")
    ack = client.post(f"/api/notifications/{manager['id']}/ack", json={"actor": "property_manager", "at": iso("16:52")})
    assert ack.status_code == 200, ack.get_json()
    assert ack.get_json()["message"] == "acknowledged, not resolved"
    assert {hm: snap(hm) for hm in ("18:51", "20:21")} == before


def test_completion_report_only_after_verification_and_never_sets_outcome(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, "report.db")
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=" + iso("16:31"))
    inv = resp.get_json()["investigation_id"]
    scenario = load_scenario(SCENARIOS / "demo_video_v1")
    report = next(e for e in scenario.events if e.kind == "hvac_completion_report")
    assert report.available_at > at("20:21")
    for hm, present in (("20:21", False), ("20:46", True)):
        kinds = [e["kind"] for e in client.get(f"/api/events?scenario=demo_video_v1&at={iso(hm)}").get_json()["events"]]
        assert ("hvac_completion_report" in kinds) is present, (hm, kinds)
    at_2021 = client.get(f"/api/follow-ups/{inv}?at={iso('20:21')}").get_json()
    at_2046 = client.get(f"/api/follow-ups/{inv}?at={iso('20:46')}").get_json()
    assert at_2021["verification"]["stage"] == "goal_verified"
    assert at_2046["verification"]["stage"] == at_2021["verification"]["stage"]
    assert at_2046["outcome"]["status"] == at_2021["outcome"]["status"]
    entries = [e for e in at_2046["evidence_timeline"] if e["kind"] == "hvac_completion_report"]
    assert entries and all(e["corroboration_only"] for e in entries)
    assert not [e for e in at_2021["evidence_timeline"] if e["kind"] == "hvac_completion_report"]


def test_human_fixed_message_never_advances_verification():
    scenario = load_scenario(SCENARIOS / "demo_video_v1")
    follow = follow_up_for(scenario, "g4-human", at("16:31"))
    base_stage = verify_recovery(scenario, follow, at("18:21"))["stage"]
    base_outcome = evaluate_outcome(follow, scenario.records, at("18:21")).status
    statement = EvidenceRecord.model_validate({
        "id": "human-fixed-1", "source": "thermostat", "kind": "human_statement",
        "subject": "demo-cabin/main", "quantity": "indoor_temp", "value": None, "unit": "F",
        "observed_at": at("17:00").isoformat(), "received_at": at("17:00").isoformat(),
        "expected_cadence_s": None, "mode": "synthetic",
        "provenance": {"fixture_id": "g4", "version": "1"},
    })
    augmented = replace(scenario, records=list(scenario.records) + [statement])
    assert verify_recovery(augmented, follow, at("18:21"))["stage"] == base_stage
    assert evaluate_outcome(follow, augmented.records, at("18:21")).status == base_outcome
    for event_kind in ("manager_acknowledgement", "service_visit", "hvac_completion_report"):
        assert event_kind not in ("warming_observed", "goal_verified")


def test_all_four_readiness_states_produced():
    rows = [r for r in evaluate_cases() if r["condition"] == "combined"]
    assert {r["got_readiness"] for r in rows} == {"on_track", "at_risk", "cannot_tell", "arrival_passed"}
    passed = [r for r in rows if r["got_readiness"] == "arrival_passed"]
    assert {r["target_at_arrival"] for r in passed} == {"met", "not_met"}


def test_no_future_data_at_any_replay_time(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch, "future.db")
    scenario = load_scenario(SCENARIOS / "demo_video_v1")
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=" + iso("16:31"))
    inv = resp.get_json()["investigation_id"]
    for hm in REPLAY:
        moment = at(hm)
        events = client.get(f"/api/events?scenario=demo_video_v1&at={iso(hm)}").get_json()["events"]
        assert all(datetime.fromisoformat(e["available_at"]) <= moment for e in events), hm
        assert events == [e.model_dump(mode="json") for e in events_as_of(scenario, moment)]
        assert all(r.received_at <= moment for r in visible_records(scenario.records, moment))
        notifs = client.get(f"/api/notifications?investigation_id={inv}&at={iso(hm)}")
        if notifs.status_code == 200:
            for row in notifs.get_json()["notifications"]:
                assert datetime.fromisoformat(row["created_at"]) <= moment, (hm, row)
                assert all(datetime.fromisoformat(a["acknowledged_at"]) <= moment for a in row["acks"])
        follow = client.get(f"/api/follow-ups/{inv}?at={iso(hm)}")
        if follow.status_code == 200:
            for entry in follow.get_json()["evidence_timeline"]:
                assert datetime.fromisoformat(entry["available_at"]) <= moment, (hm, entry)
                assert datetime.fromisoformat(entry["first_known_at"]) <= moment, (hm, entry)
            for entry in follow.get_json()["history"]:
                assert datetime.fromisoformat(entry["evaluated_at"]) <= moment, (hm, entry)
        inv_body = client.get(f"/api/investigation?scenario=demo_video_v1&at={iso(hm)}").get_json()
        pack = inv_body.get("evidence_pack") or {}
        for rec in pack.get("evidence", []) if isinstance(pack.get("evidence"), list) else []:
            if isinstance(rec, dict) and rec.get("received_at"):
                assert datetime.fromisoformat(rec["received_at"]) <= moment, (hm, rec.get("id"))
