"""The declined night: a caregiver decline stops the HVAC visit.

After a visible decline nothing is contacted and the furnace stays out:
no HVAC request, service visit, completion report or technician voice note
in any panel, timeline, event list, notification or trace; the room holds
52.0 F then falls 0.2 F/hr; verification never reaches warming_observed,
goal_verified or arrival_met; the 07:01 warm-by expectation is missed.
Readings keep deciding every step: the decline never stops the checking.
"""
import json
from datetime import datetime
from pathlib import Path

from aria_home.declined_view import REMOVED_EVENT_KINDS, declined_view
from aria_home.investigator import PROMPT_VERSION, build_evidence_pack, inference_identity
from aria_home.provider import ALLOWED_MODEL_IDS
from aria_home.readiness import READINESS_POLICY_VERSION
from aria_home.recorded import find_recorded
from aria_home.scenario import load_scenario

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"
CARE = "care_home_v1"

CARE_TIMES = [
    "2026-01-16T19:20:00-05:00",
    "2026-01-16T21:00:00-05:00",
    "2026-01-16T23:30:00-05:00",
    "2026-01-17T02:31:00-05:00",
    "2026-01-17T02:45:00-05:00",
    "2026-01-17T04:21:00-05:00",
    "2026-01-17T04:51:00-05:00",
    "2026-01-17T06:21:00-05:00",
    "2026-01-17T06:45:00-05:00",
    "2026-01-17T07:01:00-05:00",
]

ROOM_EXPECTED = {
    0: 69.0,
    1: 68.4,
    2: 59.6,
    3: 52.0,
    4: 52.0,
    5: 51.9,
    6: 51.8,
    7: 51.5,
    8: 51.5,
    9: 51.4,
}

READINESS_EXPECTED = [
    "on_track", "on_track", "at_risk", "at_risk", "at_risk",
    "at_risk", "at_risk", "at_risk", "at_risk", "arrival_passed",
]

BANNED_PHRASES = (
    "service_visit",
    "hvac_completion_report",
    "caregiver_hvac_authorized",
    "technician",
    "Technician",
    "igniter",
    "Igniter",
    "completion report",
    "Completion report",
    "service visit",
    "Service visit",
    "was replaced",
)


def _care():
    return load_scenario(SCENARIOS_DIR / CARE)


def _client(tmp_path, monkeypatch):
    from aria_home.app import create_app
    for var in ("ARIA_HOME_MODEL_ENABLED", "ARIA_HOME_WHATSAPP_LIVE", "ARIA_HOME_EMPORIA_LIVE",
                "ARIA_HOME_VISUAL_LIVE", "ARIA_HOME_NEST_LIVE", "ARIA_HOME_E2E_HOOKS", "MODEL_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("ARIA_HOME_REVIEWS_DIR", str(tmp_path / "reviews"))
    monkeypatch.setenv("ARIA_HOME_CORRECTIONS_DIR", str(tmp_path / "corrections"))
    (tmp_path / "recorded").mkdir(exist_ok=True)
    monkeypatch.setenv("ARIA_HOME_RECORDED_DIR", str(tmp_path / "recorded"))
    return create_app().test_client()


def _post(client, at):
    return client.post("/api/investigations", query_string={"scenario": CARE, "at": at}).get_json()


def _decline(client, investigation_id, decide_at):
    body = _post(client, CARE_TIMES[2])
    investigation_id = investigation_id or body["investigation_id"]
    alert = next(r for r in body["notifications"] if r["audience"] == "family_caregiver")
    decided = client.post(
        f"/api/notifications/{alert['id']}/caregiver-decision",
        json={"decision": "decline", "at": decide_at, "scenario": CARE},
    ).get_json()
    assert decided["caregiver_permission"]["status"] == "declined"
    return investigation_id


def _follow(client, investigation_id, at):
    body = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": at}).get_json()
    assert "error" not in body, (at, body)
    return body


def _room_newest(client, at):
    sources = client.get("/api/sources", query_string={"scenario": CARE, "at": at}).get_json()
    room = next(s for s in sources["sources"] if s["source"] == "room_sensor")
    return room["newest_value"]


def _assert_no_contact(follow):
    hvac = [n for n in follow["notifications"] if n["audience"] == "hvac_company"]
    assert hvac, "the refused HVAC row is the visible proof nobody was contacted"
    assert all(n["state"] == "refused" for n in hvac)
    assert any(n.get("refusal_reason") == "caregiver_declined" for n in hvac)
    assert "human_report" not in follow
    assert not [n for n in follow["notifications"] if n["kind"].startswith("caregiver_update_")]
    kinds = {entry.get("kind") for entry in follow["evidence_timeline"]}
    assert not (kinds & {"hvac_request", "service_visit", "hvac_completion_report", "caregiver_hvac_authorized"}), kinds
    text = json.dumps(follow)
    for phrase in BANNED_PHRASES:
        assert phrase not in text, phrase


def test_declined_readiness_per_step_computed():
    scenario = declined_view(_care())
    assert scenario.declined_view is True
    for index, at_str in enumerate(CARE_TIMES):
        pack = build_evidence_pack(scenario, datetime.fromisoformat(at_str))
        assert (pack.get("readiness") or {}).get("status") == READINESS_EXPECTED[index], at_str


def test_decline_never_verifies_and_never_stops_checking(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    investigation_id = _decline(client, None, CARE_TIMES[3])
    follow = _follow(client, investigation_id, CARE_TIMES[7])
    assert follow["verification"]["stage"] == "telemetry_missing"
    assert follow["verification"]["stage"] != "goal_verified"
    assert follow["outcome"]["status"] == "awaiting_measurement"
    _assert_no_contact(follow)


def test_declined_ten_steps_decline_at_2330(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    for index in (0, 1):
        body = _post(client, CARE_TIMES[index])
        assert body["computed_readiness"] == "on_track"
        assert body["follow_up"] is None
        assert _room_newest(client, CARE_TIMES[index]) == ROOM_EXPECTED[index]
    investigation_id = _decline(client, None, CARE_TIMES[2])
    _declined_steps(client, investigation_id)


def test_declined_ten_steps_decline_at_0231(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    investigation_id = _decline(client, None, CARE_TIMES[3])
    _declined_steps(client, investigation_id)


def _declined_steps(client, investigation_id):
    assert _room_newest(client, CARE_TIMES[0]) == ROOM_EXPECTED[0]
    assert _room_newest(client, CARE_TIMES[1]) == ROOM_EXPECTED[1]
    for index in range(2, 10):
        at = CARE_TIMES[index]
        assert _room_newest(client, at) == ROOM_EXPECTED[index], at
        follow = _follow(client, investigation_id, at)
        assert follow["computed_readiness"] == READINESS_EXPECTED[index], at
        if index == 2:
            assert follow["caregiver_permission"]["status"] in ("waiting", "declined")
        else:
            assert follow["caregiver_permission"]["status"] == "declined"
        if index >= 3:
            assert follow["verification"]["stage"] == "telemetry_missing", at
            assert follow["verification"]["stage"] not in ("warming_observed", "goal_verified", "arrival_met"), at
            assert follow["outcome"]["status"] == "awaiting_measurement", at
            _assert_no_contact(follow)
            events = client.get("/api/events", query_string={"scenario": CARE, "at": at}).get_json()
            kinds = {e["kind"] for e in events["events"]}
            assert not (kinds & REMOVED_EVENT_KINDS), (at, kinds)
            trace = client.get("/api/trace", query_string={"scenario": CARE, "at": at, "investigation_id": investigation_id}).get_json()
            text = json.dumps(trace)
            for phrase in BANNED_PHRASES:
                assert phrase not in text, (at, phrase)
    last = _follow(client, investigation_id, CARE_TIMES[9])
    assert last["verification"]["stage"] == "telemetry_missing"
    assert last["outcome"]["status"] == "awaiting_measurement"
    assert _room_newest(client, CARE_TIMES[9]) == 51.4


def test_rewind_before_decision_shows_original_night(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    investigation_id = _decline(client, None, CARE_TIMES[3])
    rewind = _follow(client, investigation_id, CARE_TIMES[2])
    assert rewind["caregiver_permission"]["status"] == "waiting"
    assert rewind["history"] == []
    assert _room_newest(client, CARE_TIMES[2]) == 59.6
    events = client.get("/api/events", query_string={"scenario": CARE, "at": CARE_TIMES[2]}).get_json()
    assert {e["kind"] for e in events["events"]} == {"confirmation_request", "caregiver_alert"}
    base = _client(tmp_path, monkeypatch)
    base_id = _post(base, CARE_TIMES[2])["investigation_id"]
    assert _follow(base, base_id, CARE_TIMES[2])["verification"] == rewind["verification"]


def test_two_visitors_isolated(tmp_path, monkeypatch):
    from aria_home.app import create_app
    first = _client(tmp_path, monkeypatch)
    app_client = first.application.test_client()
    second = app_client
    declined_id = _decline(first, None, CARE_TIMES[2])
    body = _post(second, CARE_TIMES[2])
    approved_id = body["investigation_id"]
    alert = next(r for r in body["notifications"] if r["audience"] == "family_caregiver")
    decided = second.post(
        f"/api/notifications/{alert['id']}/caregiver-decision",
        json={"decision": "approve", "at": CARE_TIMES[3], "scenario": CARE},
    ).get_json()
    assert decided["caregiver_permission"]["status"] == "approved"
    declined = _follow(first, declined_id, CARE_TIMES[7])
    approved = _follow(second, approved_id, CARE_TIMES[7])
    assert declined["verification"]["stage"] == "telemetry_missing"
    assert approved["verification"]["stage"] == "goal_verified"
    assert all(n["state"] == "refused" for n in declined["notifications"] if n["audience"] == "hvac_company")
    assert any(n["state"] == "simulated_delivered" for n in approved["notifications"] if n["audience"] == "hvac_company")
    assert _room_newest(first, CARE_TIMES[7]) == 51.5
    assert _room_newest(second, CARE_TIMES[7]) == 68.0


def test_no_other_path_recordings_leak(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    investigation_id = _decline(client, None, CARE_TIMES[3])
    for at in CARE_TIMES[5:]:
        follow = _follow(client, investigation_id, at)
        rec = follow["recorded_investigation"]
        assert rec["status"] == "unavailable", at
        assert "recorded_provenance" not in rec, at
        assert "recorded_review" not in rec, at
        watcher = client.get("/api/watcher", query_string={"scenario": CARE, "at": at}).get_json()
        assert watcher["model_observations"] == [], at
        assert watcher["provenance"] is None, at
        corrections = client.get("/api/corrections", query_string={"scenario": CARE, "at": at}).get_json()
        assert corrections["corrections"] == [], at
    base = _care()
    dec = declined_view(base)
    at_early = datetime.fromisoformat(CARE_TIMES[2])
    at_late = datetime.fromisoformat(CARE_TIMES[5])
    base_early = inference_identity(base, at_early)
    dec_early = inference_identity(dec, at_early)
    assert base_early["input_revision"] == dec_early["input_revision"]
    base_late = inference_identity(base, at_late)
    dec_late = inference_identity(dec, at_late)
    assert base_late["input_revision"] != dec_late["input_revision"]
    model_id = next(iter(ALLOWED_MODEL_IDS))
    base_entry = {"answer": {
        "scenario_id": CARE,
        "evaluated_at_utc": base_late["evaluated_at_utc"],
        "input_revision": base_late["input_revision"],
        "model_id": model_id,
        "prompt_version": PROMPT_VERSION,
        "readiness_policy_version": READINESS_POLICY_VERSION,
    }}
    assert find_recorded([base_entry], CARE, dec_late["evaluated_at_utc"], dec_late["input_revision"]) is None
    assert find_recorded([base_entry], CARE, base_late["evaluated_at_utc"], base_late["input_revision"]) is base_entry


def test_approve_and_silence_identities_match_base():
    base = _care()
    dec = declined_view(base)
    for at_str in (CARE_TIMES[2], CARE_TIMES[3], CARE_TIMES[5], CARE_TIMES[7], CARE_TIMES[9]):
        at = datetime.fromisoformat(at_str)
        base_revision = inference_identity(base, at)["input_revision"]
        dec_revision = inference_identity(dec, at)["input_revision"]
        if at_str in (CARE_TIMES[2], CARE_TIMES[3]):
            assert base_revision == dec_revision, at_str
        else:
            assert base_revision != dec_revision, at_str


def test_approve_with_too_little_evidence_stays_unverified(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    body = _post(client, CARE_TIMES[2])
    investigation_id = body["investigation_id"]
    alert = next(r for r in body["notifications"] if r["audience"] == "family_caregiver")
    decided = client.post(
        f"/api/notifications/{alert['id']}/caregiver-decision",
        json={"decision": "approve", "at": CARE_TIMES[3], "scenario": CARE},
    ).get_json()
    assert decided["caregiver_permission"]["status"] == "approved"
    follow = _follow(client, investigation_id, CARE_TIMES[3])
    assert follow["verification"]["stage"] == "telemetry_missing"
    assert follow["outcome"]["status"] == "awaiting_measurement"


def test_decline_holding_metric_at_0231(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    investigation_id = _decline(client, None, CARE_TIMES[3])
    metrics = client.get("/api/metrics", query_string={"scenario": CARE, "at": CARE_TIMES[3]}).get_json()
    assert metrics["last_hour_change_f"] is not None
    assert abs(metrics["last_hour_change_f"]) <= 0.2
    assert metrics["indoor_trend"]["rate_per_hour"] < -2.0
    follow = _follow(client, investigation_id, CARE_TIMES[3])
    assert follow["metrics"]["last_hour_change_f"] == metrics["last_hour_change_f"]


def test_declined_view_derivation_unit():
    base = _care()
    dec = declined_view(base)
    assert dec.declined_view is True
    assert declined_view(dec) is dec
    assert declined_view(None) is None
    assert [e.kind for e in dec.events if e.kind in REMOVED_EVENT_KINDS] == []
    base_room = {r.id: r.value for r in base.records if r.source.value == "room_sensor" and r.quantity == "indoor_temp"}
    dec_room = {r.id: r.value for r in dec.records if r.source.value == "room_sensor" and r.quantity == "indoor_temp"}
    assert set(base_room) == set(dec_room)
    for record in dec.records:
        if record.source.value == "room_sensor" and record.quantity == "indoor_temp":
            if record.observed_at < datetime.fromisoformat("2026-01-17T03:30:00-05:00"):
                assert record.value == base_room[record.id], record.id
            else:
                assert record.value <= 52.0, (record.id, record.value)
    thermostat_obs = [r.observed_at for r in dec.records if r.source.value == "thermostat"]
    assert max(thermostat_obs) == datetime.fromisoformat("2026-01-17T01:30:00-05:00")
    pre_max = max(
        float(r.value) for r in base.records
        if r.quantity == "circuit_power"
        and (r.binding.circuit_id if r.binding else r.subject) == "circuit-blower"
        and r.observed_at < datetime.fromisoformat("2026-01-17T03:30:00-05:00")
    )
    for record in dec.records:
        if record.quantity == "circuit_power" and (record.binding.circuit_id if record.binding else record.subject) == "circuit-blower":
            assert float(record.value) <= pre_max, (record.id, record.value)
