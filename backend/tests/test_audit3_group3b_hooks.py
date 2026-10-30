import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import aria_home.app as app_module
from aria_home.app import create_app
from aria_home.provider import MockProvider
from aria_home.store import Store

AT = "2026-01-16T18:00:00-05:00"


def _app(tmp_path, monkeypatch, name="hooks.db"):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / name))
    monkeypatch.setenv("ARIA_HOME_MODEL_ENABLED", "0")
    monkeypatch.setenv("ARIA_HOME_E2E_HOOKS", "1")
    monkeypatch.setattr(app_module, "get_provider", lambda *a, **k: MockProvider())
    return create_app()


def test_hook_delay_with_concurrent_poller(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    url = f"/api/investigations?scenario=demo_v1&at={AT}&test_delay_s=2"
    poll_url = f"/api/investigations?scenario=demo_v1&at={AT}"
    started = time.time()
    with ThreadPoolExecutor(max_workers=2) as pool:
        owner = pool.submit(lambda: app.test_client().post(url))
        time.sleep(0.3)
        poller = pool.submit(lambda: app.test_client().post(poll_url))
        poller_resp = poller.result()
        assert poller_resp.status_code == 202, poller_resp.get_json()
        owner_resp = owner.result()
    assert owner_resp.status_code == 200, owner_resp.get_json()
    assert time.time() - started >= 2.0
    again = app.test_client().post(poll_url)
    assert again.status_code == 200
    assert again.get_json()["deduplicated"] is True


def test_hook_lease_expiry_reports_recovery(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, name="hooks2.db")
    at = "2026-01-16T18:01:00-05:00"
    url = f"/api/investigations?scenario=demo_v1&at={at}&test_delay_s=3&lease_s=1"
    poll_url = f"/api/investigations?scenario=demo_v1&at={at}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        owner = pool.submit(lambda: app.test_client().post(url))
        time.sleep(1.8)
        poller_resp = app.test_client().post(poll_url)
        assert poller_resp.status_code == 409, poller_resp.get_json()
        assert poller_resp.get_json()["status"] == "recovery_required"
        owner_resp = owner.result()
    assert owner_resp.status_code == 409, owner_resp.get_json()


def test_hook_fail_returns_unavailable(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, name="hooks3.db")
    at = "2026-01-16T18:02:00-05:00"
    resp = app.test_client().post(f"/api/investigations?scenario=demo_v1&at={at}&test_fail=1")
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["status"] == "unavailable"


def test_hooks_ignored_when_model_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "hooks4.db"))
    monkeypatch.setenv("ARIA_HOME_MODEL_ENABLED", "1")
    monkeypatch.setenv("ARIA_HOME_E2E_HOOKS", "1")
    monkeypatch.setattr(app_module, "get_provider", lambda *a, **k: MockProvider())
    app = create_app()
    at = "2026-01-16T18:03:00-05:00"
    started = time.time()
    resp = app.test_client().post(f"/api/investigations?scenario=demo_v1&at={at}&test_delay_s=5&test_fail=1")
    assert resp.status_code == 200, resp.get_json()
    assert time.time() - started < 5.0
    assert resp.get_json()["status"] == "ok"
    assert Store(tmp_path / "hooks4.db").get_inference(resp.get_json()["identity_key"])["state"] == "completed"


def test_hooks_ignored_without_e2e_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "hooks-off.db"))
    monkeypatch.setenv("ARIA_HOME_MODEL_ENABLED", "0")
    monkeypatch.delenv("ARIA_HOME_E2E_HOOKS", raising=False)
    monkeypatch.setattr(app_module, "get_provider", lambda *a, **k: MockProvider())
    app = create_app()
    at = "2026-01-16T18:04:00-05:00"
    started = time.time()
    resp = app.test_client().post(f"/api/investigations?scenario=demo_v1&at={at}&test_delay_s=2&test_fail=1&lease_s=1")
    elapsed = time.time() - started
    assert resp.status_code == 200, resp.get_json()
    assert elapsed < 2.0
    body = resp.get_json()
    assert body["status"] == "ok"
    row = Store(tmp_path / "hooks-off.db").get_inference(body["identity_key"])
    assert row["state"] == "completed"
    lease_raw = row.get("lease_expires_at")
    created_raw = row.get("created_at")
    assert lease_raw and created_raw
    lease_dt = datetime.fromisoformat(str(lease_raw).replace("Z", "+00:00"))
    created_dt = datetime.fromisoformat(str(created_raw).replace("Z", "+00:00"))
    assert (lease_dt - created_dt).total_seconds() == 120


def test_e2e_reset_clears_stored_state(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, name="reset.db")
    client = app.test_client()
    created = client.post(f"/api/investigations?scenario=demo_v1&at={AT}")
    assert created.status_code == 200, created.get_json()
    investigation_id = created.get_json()["investigation_id"]
    follow_up = client.get(f"/api/follow-ups/{investigation_id}?at={AT}")
    assert follow_up.status_code == 200, follow_up.get_json()
    reset = client.post("/api/e2e/reset")
    assert reset.status_code == 200, reset.get_json()
    assert reset.get_json()["reset"] is True
    assert client.get(f"/api/follow-ups/{investigation_id}?at={AT}").status_code == 404
    store = Store(tmp_path / "reset.db")
    assert store.list_notifications(investigation_id) == []


def test_e2e_reset_missing_without_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "reset-off.db"))
    monkeypatch.setenv("ARIA_HOME_MODEL_ENABLED", "0")
    monkeypatch.delenv("ARIA_HOME_E2E_HOOKS", raising=False)
    monkeypatch.setattr(app_module, "get_provider", lambda *a, **k: MockProvider())
    app = create_app()
    assert app.test_client().post("/api/e2e/reset").status_code == 404
