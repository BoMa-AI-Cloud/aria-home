import threading
from concurrent.futures import ThreadPoolExecutor

from aria_home.app import create_app
from aria_home.store import Store


def test_concurrent_first_time_initialisation_fresh_db(tmp_path):
    for round_no in range(5):
        db = tmp_path / f"fresh-{round_no}.db"
        barrier = threading.Barrier(8)

        def init(_):
            barrier.wait()
            return Store(db)

        with ThreadPoolExecutor(max_workers=8) as pool:
            stores = list(pool.map(init, range(8)))
        assert len(stores) == 8
        assert Store(db).list_investigations() == []


def test_sources_follow_scenario_and_at_and_echo_context(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    monkeypatch.setenv("ARIA_HOME_MODEL_ENABLED", "0")
    client = create_app().test_client()
    resp = client.get("/api/sources?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["scenario"] == "demo_video_v1"
    assert data["at"] == "2026-01-16T16:31:00-05:00"
    assert data["timezone"] == "America/New_York"
    assert data["sources"]

    resp2 = client.get("/api/sources?scenario=demo_v1&at=2026-01-16T18:00:00-05:00")
    data2 = resp2.get_json()
    assert data2["scenario"] == "demo_v1"
    assert data2["at"] == "2026-01-16T18:00:00-05:00"


def test_every_get_echoes_scenario_and_at(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api2.db"))
    monkeypatch.setenv("ARIA_HOME_MODEL_ENABLED", "0")
    client = create_app().test_client()
    for path in [
        "/api/health",
        "/api/sources?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00",
        "/api/metrics?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00",
        "/api/power-context?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00",
        "/api/investigation?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00",
        "/api/events?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00",
        "/api/notifications?at=2026-01-16T16:31:00-05:00",
        "/api/provider",
    ]:
        resp = client.get(path)
        assert resp.status_code == 200, path
        data = resp.get_json()
        assert "scenario" in data, path
        assert "at" in data, path
        assert "timezone" in data, path
