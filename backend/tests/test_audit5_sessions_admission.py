"""Audit 5 findings 3, 4, 7: public-session admission and validate-before-write."""
import os
import sqlite3
import threading
import time
from pathlib import Path

import pytest

from aria_home import public_demo
from aria_home.app import create_app

CARE_AT = "2026-01-17T02:31:00-05:00"
CARE_NEXT = "2026-01-17T02:45:00-05:00"
OFF_CHECKPOINT = "2026-01-17T02:32:00-05:00"
VIDEO = "demo_video_v1"
VIDEO_AT = "2026-01-16T16:31:00-05:00"


@pytest.fixture
def public_env(monkeypatch, tmp_path):
    for var in (
        "ARIA_HOME_MODEL_ENABLED",
        "ARIA_HOME_WHATSAPP_LIVE",
        "ARIA_HOME_EMPORIA_LIVE",
        "ARIA_HOME_VISUAL_LIVE",
        "ARIA_HOME_NEST_LIVE",
        "ARIA_HOME_E2E_HOOKS",
        "ARIA_HOME_DB_PATH",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO", "1")
    sessions = tmp_path / "sessions"
    recorded = tmp_path / "recorded"
    recorded.mkdir()
    monkeypatch.setenv("ARIA_HOME_PUBLIC_DEMO_DIR", str(sessions))
    monkeypatch.setenv("ARIA_HOME_RECORDED_DIR", str(recorded))
    return sessions


@pytest.fixture
def private_client(monkeypatch, tmp_path):
    monkeypatch.delenv("ARIA_HOME_PUBLIC_DEMO", raising=False)
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    return create_app().test_client()


def _forged(index):
    return f"forged-{index:06d}-{'z' * 40}"


def _session_files(sessions):
    return list(Path(sessions).glob("sess-*.db"))


def _cookie_value(response):
    raw = response.headers.get("Set-Cookie", "")
    assert f"{public_demo.SESSION_COOKIE}=" in raw
    return raw.split(f"{public_demo.SESSION_COOKIE}=")[1].split(";")[0]


def _dump_tables(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]
    dump = {}
    for table in tables:
        dump[table] = [dict(r) for r in conn.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()]
    conn.close()
    return dump


def _only_session_db(sessions):
    files = _session_files(sessions)
    assert len(files) == 1
    return files[0]


def _start_care(client):
    inv_id = client.post(f"/api/investigations?scenario=care_home_v1&at={CARE_AT}").get_json()["investigation_id"]
    body = client.get(f"/api/follow-ups/{inv_id}?at={CARE_AT}").get_json()
    return inv_id, body["caregiver_permission"]["notification_id"]


def test_forged_cookies_never_exceed_cap(public_env):
    app = create_app()
    statuses = []
    for index in range(public_demo.MAX_SESSIONS + 20):
        visitor = app.test_client()
        visitor.set_cookie(public_demo.SESSION_COOKIE, _forged(index))
        resp = visitor.get("/api/notifications", query_string={"investigation_id": "inv-none"})
        statuses.append(resp.status_code)
    assert len(_session_files(public_env)) <= public_demo.MAX_SESSIONS
    assert statuses[-1] == 503


def test_expired_cookie_is_reissued_not_reused(public_env):
    app = create_app()
    first = app.test_client().get("/api/notifications", query_string={"investigation_id": "inv-none"})
    old_value = _cookie_value(first)
    old_path = public_demo.session_db_path(public_env, old_value)
    assert old_path.is_file()
    aged = time.time() - public_demo.SESSION_IDLE_S - 100
    os.utime(old_path, (aged, aged))
    visitor = app.test_client()
    visitor.set_cookie(public_demo.SESSION_COOKIE, old_value)
    retry = visitor.get("/api/notifications", query_string={"investigation_id": "inv-none"})
    assert retry.status_code == 200
    new_value = _cookie_value(retry)
    assert new_value != old_value
    assert not old_path.exists()


def test_forged_id_creates_no_file(public_env):
    app = create_app()
    forged = _forged(999999)
    visitor = app.test_client()
    visitor.set_cookie(public_demo.SESSION_COOKIE, forged)
    resp = visitor.get("/api/notifications", query_string={"investigation_id": "inv-none"})
    assert resp.status_code == 200
    assert not public_demo.session_db_path(public_env, forged).exists()
    assert _cookie_value(resp) != forged


def test_cap_full_returns_503_without_allocating(public_env):
    now = time.time()
    for index in range(public_demo.MAX_SESSIONS):
        path = public_env / f"sess-fill-{index:04d}.db"
        public_env.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
        os.utime(path, (now, now))
    before = _session_files(public_env)
    visitor = create_app().test_client()
    visitor.set_cookie(public_demo.SESSION_COOKIE, _forged(7))
    resp = visitor.get("/api/notifications", query_string={"investigation_id": "inv-none"})
    assert resp.status_code == 503
    assert "capacity" in resp.get_json()["error"].lower()
    assert "Set-Cookie" not in resp.headers
    assert len(_session_files(public_env)) == len(before)


def test_idle_session_survives_full_cap_admission(public_env):
    now = time.time()
    idle_then = now - 10 * 60
    public_env.mkdir(parents=True, exist_ok=True)
    for index in range(public_demo.MAX_SESSIONS):
        path = public_env / f"sess-idle-{index:04d}.db"
        path.write_bytes(b"")
        os.utime(path, (idle_then, idle_then))
    before = sorted(path.name for path in _session_files(public_env))
    assert len(before) == public_demo.MAX_SESSIONS
    visitor = create_app().test_client()
    visitor.set_cookie(public_demo.SESSION_COOKIE, _forged(4242))
    resp = visitor.get("/api/notifications", query_string={"investigation_id": "inv-none"})
    assert resp.status_code == 503
    assert "capacity" in resp.get_json()["error"].lower()
    assert "Set-Cookie" not in resp.headers
    assert sorted(path.name for path in _session_files(public_env)) == before


def test_concurrent_admissions_stay_capped(public_env):
    app = create_app()
    errors = []

    def _burst(offset):
        try:
            for index in range(70):
                visitor = app.test_client()
                visitor.set_cookie(public_demo.SESSION_COOKIE, _forged(offset + index))
                visitor.get("/api/notifications", query_string={"investigation_id": "inv-none"})
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_burst, args=(slot * 1000,)) for slot in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert len(_session_files(public_env)) <= public_demo.MAX_SESSIONS


def test_public_ack_off_checkpoint_writes_nothing(public_env):
    client = create_app().test_client()
    _, notification_id = _start_care(client)
    db_path = _only_session_db(public_env)
    before = _dump_tables(db_path)
    resp = client.post(
        f"/api/notifications/{notification_id}/ack",
        json={"actor": "family_caregiver", "at": OFF_CHECKPOINT},
    )
    assert resp.status_code == 400
    assert _dump_tables(db_path) == before
    assert client.get("/api/notifications").get_json()["notifications"] != []


def test_public_ack_at_checkpoint_still_works_and_idempotent(public_env):
    client = create_app().test_client()
    _, notification_id = _start_care(client)
    first = client.post(
        f"/api/notifications/{notification_id}/ack",
        json={"actor": "family_caregiver", "at": CARE_NEXT},
    )
    assert first.status_code == 200
    second = client.post(
        f"/api/notifications/{notification_id}/ack",
        json={"actor": "family_caregiver", "at": CARE_NEXT},
    )
    assert second.status_code == 200
    assert second.get_json()["ack"]["id"] == first.get_json()["ack"]["id"]


def test_rejected_decision_leaves_tables_unchanged(public_env):
    client = create_app().test_client()
    _, notification_id = _start_care(client)
    db_path = _only_session_db(public_env)
    cases = [
        {"decision": "approve", "at": OFF_CHECKPOINT},
        {"decision": "maybe", "at": CARE_AT},
        {"decision": "approve", "at": "2026-01-16T19:00:00-05:00"},
    ]
    for payload in cases:
        before = _dump_tables(db_path)
        resp = client.post(f"/api/notifications/{notification_id}/caregiver-decision", json=payload)
        assert resp.status_code in (400, 409), payload
        assert _dump_tables(db_path) == before, payload


def test_rejected_investigation_and_whatsapp_leave_tables_unchanged(public_env):
    client = create_app().test_client()
    _, notification_id = _start_care(client)
    db_path = _only_session_db(public_env)
    before = _dump_tables(db_path)
    assert client.post("/api/investigations?scenario=care_home_v1&at=2026-01-17T02:32:00-05:00").status_code == 400
    assert client.post(f"/api/notifications/{notification_id}/whatsapp").status_code == 404
    assert _dump_tables(db_path) == before


def test_private_whatsapp_rejection_writes_nothing(private_client, tmp_path, monkeypatch):
    for name in ("WHATSAPP_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_TEST_RECIPIENT", "ARIA_HOME_WHATSAPP_LIVE"):
        monkeypatch.setenv(name, "")
    inv_id = private_client.post(f"/api/investigations?scenario=care_home_v1&at={CARE_AT}").get_json()["investigation_id"]
    body = private_client.get(f"/api/follow-ups/{inv_id}?at={CARE_AT}").get_json()
    notification_id = body["caregiver_permission"]["notification_id"]
    before = _dump_tables(tmp_path / "api.db")
    resp = private_client.post(f"/api/notifications/{notification_id}/whatsapp")
    assert resp.status_code == 409
    assert _dump_tables(tmp_path / "api.db") == before


def test_decision_unhashable_and_mistyped_bodies_are_400(private_client):
    inv_id, notification_id = _start_care(private_client)
    _ = inv_id
    for decision in ([], {}, None, 5, True):
        resp = private_client.post(
            f"/api/notifications/{notification_id}/caregiver-decision",
            json={"decision": decision, "at": CARE_AT},
        )
        assert resp.status_code == 400, repr(decision)
    exact = private_client.post(
        f"/api/notifications/{notification_id}/caregiver-decision",
        json={"decision": [], "at": CARE_AT},
    )
    assert exact.status_code == 400
    for bad_at in ([], {}, None, 5, True, "not-a-time", "2026-01-17 02:31:00"):
        resp = private_client.post(
            f"/api/notifications/{notification_id}/caregiver-decision",
            json={"decision": "approve", "at": bad_at},
        )
        assert resp.status_code == 400, repr(bad_at)
    for body in ([], "x", 5, None):
        resp = private_client.post(f"/api/notifications/{notification_id}/caregiver-decision", json=body)
        assert resp.status_code == 400, repr(body)


def test_public_decision_unhashable_is_400(public_env):
    client = create_app().test_client()
    _, notification_id = _start_care(client)
    resp = client.post(
        f"/api/notifications/{notification_id}/caregiver-decision",
        json={"decision": [], "at": CARE_AT},
    )
    assert resp.status_code == 400


def test_ack_mistyped_bodies_are_400(private_client):
    _, notification_id = _start_care(private_client)
    for actor in ([], {}, None, 5, True, "  "):
        resp = private_client.post(
            f"/api/notifications/{notification_id}/ack",
            json={"actor": actor, "at": CARE_AT},
        )
        assert resp.status_code in (400, 403), repr(actor)
    for bad_at in ([], {}, 5, True, "not-a-time"):
        resp = private_client.post(
            f"/api/notifications/{notification_id}/ack",
            json={"actor": "family_caregiver", "at": bad_at},
        )
        assert resp.status_code == 400, repr(bad_at)
    for body in ([], "x", 5, None):
        resp = private_client.post(f"/api/notifications/{notification_id}/ack", json=body)
        assert resp.status_code == 400, repr(body)
