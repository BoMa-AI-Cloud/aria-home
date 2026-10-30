"""Public-demo mode: restricted hosting, visitor isolation, recorded answers."""
import json
import os
import socket
import urllib.request
from datetime import datetime
from pathlib import Path

import httpx
import pytest

from aria_home import public_demo
from aria_home.app import create_app
from aria_home.investigator import PROMPT_VERSION, inference_identity, investigate
from aria_home.readiness import READINESS_POLICY_VERSION
from aria_home.recorded import NO_RECORDED_LABEL, public_investigation
from aria_home.scenario import load_scenario

VIDEO = "demo_video_v1"
T1631 = "2026-01-16T16:31:00-05:00"
T1652 = "2026-01-16T16:52:00-05:00"
T1821 = "2026-01-16T18:21:00-05:00"
T2101 = "2026-01-16T21:01:00-05:00"
BAD_AT = "2026-01-16T17:00:00-05:00"
DEMO_V1_AT = "2026-01-16T18:00:00-05:00"

SCRUB_VARS = [
    "ARIA_HOME_PROVIDER_URL",
    "ARIA_HOME_MODEL_ID",
    "MODEL_API_KEY",
    "ARIA_HOME_MODEL_ENABLED",
    "ARIA_HOME_WHATSAPP_LIVE",
    "WHATSAPP_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID",
    "WHATSAPP_TEST_RECIPIENT",
    "ARIA_HOME_EMPORIA_LIVE",
    "EMPORIA_EMAIL",
    "EMPORIA_PASSWORD",
    "ARIA_HOME_VISUAL_LIVE",
    "ARIA_HOME_E2E_HOOKS",
    "ARIA_HOME_DB_PATH",
    "ARIA_HOME_BASETEN_ENABLED",
    "BASETEN_API_KEY",
    "ARIA_HOME_INVESTIGATION_MAX_TOKENS",
]


@pytest.fixture
def public_env(monkeypatch, tmp_path):
    for var in SCRUB_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    sessions = tmp_path / "sessions"
    recorded = tmp_path / "recorded"
    recorded.mkdir()
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(sessions))
    monkeypatch.setenv("ARIA_HOME_RECORDED_DIR", str(recorded))
    return {"sessions": sessions, "recorded": recorded}


def _manager_notification_id(created):
    for item in created.get("notifications") or []:
        if item.get("audience") == "property_manager" and item.get("state") == "simulated_delivered":
            return item["id"]
    raise AssertionError("no deliverable property-manager notification in response")


def _write_answers(recorded_dir, answers, name="answers.json"):
    path = Path(recorded_dir) / name
    path.write_text(json.dumps({"answers": answers}), encoding="utf-8")
    return path


def _recorded_entry(scenario_id, at_iso, monkeypatch_record=True):
    scenario_dir = Path(__file__).resolve().parent.parent / "scenarios" / scenario_id
    scn = load_scenario(scenario_dir)
    at = datetime.fromisoformat(at_iso)
    identity = inference_identity(scn, at)
    result = investigate(scn, at)
    assert result.status == "ok", result.reasons
    return identity, {
        "scenario_id": scenario_id,
        "evaluated_at_utc": identity["evaluated_at_utc"],
        "input_revision": identity["input_revision"],
        "model_id": "muse-spark-1.3",
        "provider_route": "meta live via Meta Model API",
        "prompt_version": PROMPT_VERSION,
        "readiness_policy_version": READINESS_POLICY_VERSION,
        "code_snapshot": "test-snapshot",
        "recorded_at": "2026-10-28T12:00:00+00:00",
        "output": result.output.model_dump(mode="json"),
    }


def test_fail_closed_each_live_flag(monkeypatch, tmp_path):
    for var in SCRUB_VARS:
        monkeypatch.delenv(var, raising=False)
    for flag in public_demo.LIVE_FLAGS:
        monkeypatch.delenv(flag, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(tmp_path))
    for flag in public_demo.LIVE_FLAGS:
        monkeypatch.setenv(flag, "1")
        with pytest.raises(RuntimeError, match=flag):
            create_app()
        monkeypatch.delenv(flag)
    create_app()


def test_fresh_session_no_credentials(public_env):
    client = create_app().test_client()
    assert client.get("/api/health").status_code == 200
    resp = client.get("/api/sources", query_string={"scenario": VIDEO, "at": T1631})
    assert resp.status_code == 200
    cookie = resp.headers.get("Set-Cookie", "")
    assert "aria_demo_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "demo_video" not in cookie
    created = client.post("/api/investigations", query_string={"scenario": VIDEO, "at": T1631})
    assert created.status_code == 200
    body = created.get_json()
    assert body["investigation"]["status"] == "unavailable"
    assert NO_RECORDED_LABEL in body["investigation"]["reasons"]
    assert body["outcome"] is not None


def test_session_cookie_opaque_and_tamper(public_env):
    app = create_app()
    first = app.test_client().get("/api/sources", query_string={"scenario": VIDEO, "at": T1631})
    second = app.test_client().get("/api/sources", query_string={"scenario": VIDEO, "at": T1631})
    first_value = first.headers["Set-Cookie"].split("aria_demo_session=")[1].split(";")[0]
    second_value = second.headers["Set-Cookie"].split("aria_demo_session=")[1].split(";")[0]
    assert first_value != second_value
    tampered = app.test_client()
    tampered.set_cookie("aria_demo_session", "not-a-valid-session!!")
    retry = tampered.get("/api/sources", query_string={"scenario": VIDEO, "at": T1631})
    assert retry.status_code == 200
    assert "aria_demo_session=" in retry.headers.get("Set-Cookie", "")
    fresh_value = retry.headers["Set-Cookie"].split("aria_demo_session=")[1].split(";")[0]
    assert fresh_value != "not-a-valid-session!!"


def test_dangerous_routes_not_registered(public_env):
    app = create_app()
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    for path in ("/api/provider", "/api/power-context", "/api/live-power", "/api/whatsapp/status"):
        assert path not in rules
    assert "/api/notifications/<notification_id>/whatsapp" not in rules
    client = app.test_client()
    cases = [
        ("GET", "/api/provider"),
        ("GET", "/api/power-context"),
        ("GET", "/api/live-power"),
        ("GET", "/api/whatsapp/status"),
        ("POST", "/api/notifications/notif-abc123/whatsapp"),
    ]
    for method, path in cases:
        resp = client.open(path, method=method)
        assert resp.status_code == 404, (method, path)
        assert resp.content_type.startswith("application/json")
        assert "Traceback" not in resp.get_data(as_text=True)


def test_scenario_allowlist(public_env):
    client = create_app().test_client()
    assert client.get("/api/sources", query_string={"scenario": "nope", "at": T1631}).status_code == 404
    assert client.get("/api/sources", query_string={"scenario": "demo_revised_v1", "at": T1631}).status_code == 404
    resp = client.get("/api/scenarios")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.get_json()["scenarios"]]
    assert ids == ["care_home_v1", "demo_no_followup_v1", "demo_recovery_v1", "demo_v1", "demo_video_v1", "visual_dry_floor_v1", "visual_frost_missed_v1", "visual_water_low_temp_v1"]
    video = next(item for item in resp.get_json()["scenarios"] if item["id"] == VIDEO)
    assert T1631 in video["checkpoints"]


def test_replay_time_allowlist(public_env):
    client = create_app().test_client()
    for path in ("/api/sources", "/api/context", "/api/metrics", "/api/investigation", "/api/events", "/api/visual"):
        resp = client.get(path, query_string={"scenario": VIDEO, "at": BAD_AT})
        assert resp.status_code == 400, path
    assert client.post("/api/investigations", query_string={"scenario": VIDEO, "at": BAD_AT}).status_code == 400
    assert client.get("/api/visual/image", query_string={"scenario": "visual_water_low_temp_v1", "at": BAD_AT}).status_code == 400
    for path in ("/api/sources", "/api/context", "/api/metrics", "/api/investigation", "/api/events", "/api/visual"):
        assert client.get(path, query_string={"scenario": VIDEO, "at": T1631}).status_code == 200, path
    assert client.get("/api/sources", query_string={"scenario": VIDEO}).status_code == 200
    assert client.get("/api/visual/image", query_string={"scenario": "visual_water_low_temp_v1", "at": DEMO_V1_AT}).status_code == 200


def test_body_limits(public_env):
    client = create_app().test_client()
    created = client.post("/api/investigations", query_string={"scenario": VIDEO, "at": T1631}).get_json()
    notification_id = _manager_notification_id(created)
    ack_path = f"/api/notifications/{notification_id}/ack"
    oversized = client.post(ack_path, json={"actor": "property_manager", "at": T1652, "pad": "x" * 5000})
    assert oversized.status_code == 413
    assert oversized.content_type.startswith("application/json")
    plain = client.post(ack_path, data="actor=property_manager", content_type="text/plain")
    assert plain.status_code in (400, 415)
    malformed = client.post(ack_path, data="{not json", content_type="application/json")
    assert malformed.status_code == 400
    ok = client.post(ack_path, json={"actor": "property_manager", "at": T1652})
    assert ok.status_code == 200


def test_sessions_isolated_and_reset_clears_only_caller(public_env):
    app = create_app()
    visitor_a = app.test_client()
    visitor_b = app.test_client()
    created_a = visitor_a.post("/api/investigations", query_string={"scenario": VIDEO, "at": T1631}).get_json()
    created_b = visitor_b.post("/api/investigations", query_string={"scenario": VIDEO, "at": T1631}).get_json()
    investigation_id = created_a["investigation_id"]
    assert created_b["investigation_id"] == investigation_id
    notification_id = _manager_notification_id(created_a)
    assert visitor_a.post(f"/api/notifications/{notification_id}/ack", json={"actor": "property_manager", "at": T1652}).status_code == 200
    acks_a = visitor_a.get("/api/notifications", query_string={"investigation_id": investigation_id, "at": T1652}).get_json()["notifications"]
    acks_b = visitor_b.get("/api/notifications", query_string={"investigation_id": investigation_id, "at": T1652}).get_json()["notifications"]
    assert sum(len(item["acks"]) for item in acks_a) == 1
    assert sum(len(item["acks"]) for item in acks_b) == 0
    assert visitor_b.get(f"/api/follow-ups/{investigation_id}", query_string={"at": T1821}).status_code == 200
    assert visitor_a.post("/api/session/reset").status_code == 200
    assert visitor_a.get(f"/api/follow-ups/{investigation_id}", query_string={"at": T1821}).status_code == 404
    remaining_a = visitor_a.get("/api/notifications", query_string={"investigation_id": investigation_id, "at": T1652}).get_json()["notifications"]
    assert remaining_a == []
    remaining_b = visitor_b.get("/api/notifications", query_string={"investigation_id": investigation_id, "at": T1652}).get_json()["notifications"]
    assert remaining_b != []
    assert sum(len(item["acks"]) for item in remaining_b) == 0
    assert visitor_b.get(f"/api/follow-ups/{investigation_id}", query_string={"at": T1821}).status_code == 200


def test_ack_does_not_alter_verification(public_env):
    client = create_app().test_client()
    created = client.post("/api/investigations", query_string={"scenario": VIDEO, "at": T1631}).get_json()
    before = client.get(f"/api/follow-ups/{created['investigation_id']}", query_string={"at": T1821}).get_json()
    notification_id = _manager_notification_id(created)
    assert client.post(f"/api/notifications/{notification_id}/ack", json={"actor": "property_manager", "at": T1652}).status_code == 200
    after = client.get(f"/api/follow-ups/{created['investigation_id']}", query_string={"at": T1821}).get_json()
    assert after["verification"]["stage"] == before["verification"]["stage"]
    assert after["outcome"]["status"] == before["outcome"]["status"]


def test_retention_eviction(tmp_path):
    directory = tmp_path / "sessions"
    directory.mkdir()
    now = 1_790_000_000.0
    old = directory / "sess-old.db"
    fresh = directory / "sess-fresh.db"
    old.write_bytes(b"x")
    fresh.write_bytes(b"x")
    os.utime(old, (now - 8000, now - 8000))
    os.utime(fresh, (now, now))
    result = public_demo.sweep_sessions(directory, idle_seconds=7200, now=now)
    assert result == {"removed_idle": 1, "evicted": 0, "remaining": 1}
    assert not old.exists()
    assert fresh.exists()
    for index in range(5):
        path = directory / f"sess-{index}.db"
        path.write_bytes(b"x")
        os.utime(path, (now - index, now - index))
    result = public_demo.sweep_sessions(directory, idle_seconds=10**9, max_sessions=3, now=now)
    assert result == {"removed_idle": 0, "evicted": 0, "remaining": 6}
    for index in range(5):
        assert (directory / f"sess-{index}.db").exists()
    assert (directory / "sess-fresh.db").exists()
    admitted = public_demo.admit_session(directory, None, max_sessions=3, now=now)
    assert admitted == {"session_id": None, "path": None, "new": False, "busy": True}
    assert len(list(directory.glob("sess-*.db"))) == 6


def test_zero_outbound_http_across_full_replay(public_env, monkeypatch):
    calls = []

    def _boom(*args, **kwargs):
        calls.append(True)
        raise AssertionError("outbound HTTP attempted in public-demo mode")

    monkeypatch.setattr(httpx.Client, "request", _boom)
    monkeypatch.setattr(httpx, "post", _boom)
    monkeypatch.setattr(httpx, "get", _boom)
    monkeypatch.setattr(httpx, "request", _boom)
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)
    monkeypatch.setattr(socket.socket, "connect", _boom)
    client = create_app().test_client()
    created = client.post("/api/investigations", query_string={"scenario": VIDEO, "at": T1631})
    assert created.status_code == 200
    investigation_id = created.get_json()["investigation_id"]
    replay_times = [t for t in public_demo.CHECKPOINTS[VIDEO] if t >= T1631]
    assert len(replay_times) == 8
    for at in replay_times:
        assert client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": at}).status_code == 200
        assert client.get("/api/events", query_string={"scenario": VIDEO, "at": at}).status_code == 200
        assert client.get("/api/notifications", query_string={"investigation_id": investigation_id, "at": at}).status_code == 200
        assert client.get("/api/investigation", query_string={"scenario": VIDEO, "at": at}).status_code == 200
    for at in public_demo.CHECKPOINTS[VIDEO]:
        assert client.get("/api/events", query_string={"scenario": VIDEO, "at": at}).status_code == 200
        assert client.get("/api/sources", query_string={"scenario": VIDEO, "at": at}).status_code == 200
        assert client.get("/api/context", query_string={"scenario": VIDEO, "at": at}).status_code == 200
        assert client.get("/api/metrics", query_string={"scenario": VIDEO, "at": at}).status_code == 200
    notification_id = _manager_notification_id(created.get_json())
    assert client.post(f"/api/notifications/{notification_id}/ack", json={"actor": "property_manager", "at": T1652}).status_code == 200
    assert client.get("/api/visual", query_string={"scenario": "visual_water_low_temp_v1", "at": DEMO_V1_AT}).status_code == 200
    assert client.get("/api/visual/image", query_string={"scenario": "visual_water_low_temp_v1", "at": DEMO_V1_AT}).status_code == 200
    assert client.get("/api/evaluation/offline").status_code == 200
    assert client.get("/api/scenarios").status_code == 200
    assert calls == []


def test_recorded_answer_exact_match(public_env):
    identity, entry = _recorded_entry("demo_v1", DEMO_V1_AT)
    _write_answers(public_env["recorded"], [entry])
    scenario_dir = Path(__file__).resolve().parent.parent / "scenarios" / "demo_v1"
    scn = load_scenario(scenario_dir)
    result, provenance = public_investigation(scn, datetime.fromisoformat(DEMO_V1_AT))
    assert result.status == "ok"
    assert result.model_id == "muse-spark-1.3"
    assert result.provider_mode == "recorded"
    assert result.output is not None and result.output.verified_facts
    assert provenance is not None
    assert provenance["model_id"] == "muse-spark-1.3"
    assert provenance["provider_route"] == "meta live via Meta Model API"
    assert provenance["recorded_at"] == "2026-10-28T12:00:00+00:00"
    assert provenance["input_revision"] == identity["input_revision"]
    assert provenance["code_snapshot"] == "test-snapshot"
    assert provenance["prompt_version"] == PROMPT_VERSION
    assert provenance["readiness_policy_version"] == READINESS_POLICY_VERSION
    assert provenance["validation"] == {"passed": True, "reasons": []}
    client = create_app().test_client()
    created = client.post("/api/investigations", query_string={"scenario": "demo_v1", "at": DEMO_V1_AT}).get_json()
    assert created["investigation"]["status"] == "ok"
    assert created["investigation"]["output"]["verified_facts"]
    assert NO_RECORDED_LABEL not in created["investigation"]["reasons"]
    assert created["investigation"]["recorded_provenance"]["model_id"] == "muse-spark-1.3"
    assert created["investigation"]["recorded_provenance"]["validation"]["passed"] is True
    read = client.get("/api/investigation", query_string={"scenario": "demo_v1", "at": DEMO_V1_AT}).get_json()
    assert read["recorded_provenance"]["input_revision"] == identity["input_revision"]


def test_recorded_answer_refuses_mismatch(public_env):
    identity, entry = _recorded_entry("demo_v1", DEMO_V1_AT)
    scenario_dir = Path(__file__).resolve().parent.parent / "scenarios" / "demo_v1"
    scn = load_scenario(scenario_dir)
    at = datetime.fromisoformat(DEMO_V1_AT)
    bad_revision = dict(entry, input_revision="0" * 64)
    bad_policy = dict(entry, readiness_policy_version="readiness-policy-v0")
    bad_prompt = dict(entry, prompt_version="inv-v0")
    bad_model = dict(entry, model_id="other-model")
    tampered_output = json.loads(json.dumps(entry["output"]))
    tampered_output["readiness"] = "on_track" if tampered_output["readiness"] != "on_track" else "at_risk"
    bad_validation = dict(entry, output=tampered_output)
    assert identity["input_revision"] != "0" * 64
    cases = {
        "bad-revision.json": bad_revision,
        "bad-policy.json": bad_policy,
        "bad-prompt.json": bad_prompt,
        "bad-model.json": bad_model,
        "bad-validation.json": bad_validation,
    }
    for name, candidate in cases.items():
        for leftover in public_env["recorded"].glob("*.json"):
            leftover.unlink()
        _write_answers(public_env["recorded"], [candidate], name=name)
        result, provenance = public_investigation(scn, at)
        assert result.status == "unavailable", name
        assert NO_RECORDED_LABEL in result.reasons, name
        assert provenance is None, name


def test_recorded_answer_prefers_spark(public_env):
    identity, spark = _recorded_entry("demo_v1", DEMO_V1_AT)
    wonder = dict(spark, model_id="muse-wonder-1.0")
    _write_answers(public_env["recorded"], [wonder, spark])
    scenario_dir = Path(__file__).resolve().parent.parent / "scenarios" / "demo_v1"
    scn = load_scenario(scenario_dir)
    result, provenance = public_investigation(scn, datetime.fromisoformat(DEMO_V1_AT))
    assert result.status == "ok"
    assert provenance["model_id"] == "muse-spark-1.3"


def test_public_index_serves_frontend_or_clear_404(public_env):
    client = create_app().test_client()
    resp = client.get("/")
    dist_index = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist" / "index.html"
    if dist_index.is_file():
        assert resp.status_code == 200
        assert "text/html" in resp.content_type
    else:
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "frontend not built"


def test_public_caregiver_decision_is_session_scoped_and_simulated(public_env):
    from aria_home.app import create_app as _create

    client = _create().test_client()
    inv_id = client.post("/api/investigations?scenario=care_home_v1&at=2026-01-17T02:31:00-05:00").get_json()["investigation_id"]
    body = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-17T02:31:00-05:00").get_json()
    notification_id = body["caregiver_permission"]["notification_id"]
    off_checkpoint = client.post(f"/api/notifications/{notification_id}/caregiver-decision", json={"decision": "approve", "at": "2026-01-17T02:33:00-05:00"})
    assert off_checkpoint.status_code == 400
    assert client.post(f"/api/notifications/{notification_id}/caregiver-decision", json={"decision": "approve", "at": "2026-01-17T02:31:00-05:00"}).status_code == 201
    assert client.post(f"/api/notifications/{notification_id}/whatsapp").status_code == 404
    other = _create().test_client()
    assert other.post(f"/api/notifications/{notification_id}/caregiver-decision", json={"decision": "decline", "at": "2026-01-17T02:31:00-05:00"}).status_code == 404
