"""Tests for the backend health endpoint."""
import importlib

from aria_home.app import create_app

REQUIRED_ABSENT_VARS = [
    "ARIA_HOME_PROVIDER_URL",
    "ARIA_HOME_MODEL_ID",
    "MODEL_API_KEY",
    "ARIA_HOME_MODEL_ENABLED",
]


def test_health_returns_ok():
    client = create_app().test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {
        "status": "ok",
        "service": "aria-home-backend",
        "data_mode": "synthetic",
        "scenario": "demo_v1",
        "at": "2026-01-16T18:00:00-05:00",
        "timezone": "America/New_York",
    }


def test_import_needs_no_env_vars(monkeypatch):
    for var in REQUIRED_ABSENT_VARS:
        monkeypatch.delenv(var, raising=False)
    import aria_home.app as app_module

    importlib.reload(app_module)
    client = app_module.create_app().test_client()
    assert client.get("/api/health").status_code == 200
