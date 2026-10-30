"""Tests for the backend health endpoint."""
import importlib
import os

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
    body = resp.get_json()
    expected_marker = os.path.basename(os.environ.get("ARIA_HOME_DB_PATH") or "") or None
    assert body.pop("db_marker") == expected_marker
    assert set(body.pop("version")) == {"commit", "source"}
    assert body == {
        "status": "ok",
        "service": "aria-home-backend",
        "data_mode": "synthetic",
        "scenario": "care_home_v1",
        "at": "2026-01-16T19:00:00-05:00",
        "timezone": "America/New_York",
        "public_demo": False,
    }


def test_import_needs_no_env_vars(monkeypatch):
    for var in REQUIRED_ABSENT_VARS:
        monkeypatch.delenv(var, raising=False)
    import aria_home.app as app_module

    importlib.reload(app_module)
    client = app_module.create_app().test_client()
    assert client.get("/api/health").status_code == 200
