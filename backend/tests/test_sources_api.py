from aria_home.app import create_app


def test_sources_default_returns_four_sources():
    client = create_app().test_client()
    resp = client.get("/api/sources")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["data_mode"] == "synthetic"
    assert len(body["sources"]) == 4
    assert {s["source"] for s in body["sources"]} == {
        "calendar",
        "thermostat",
        "electrical",
        "weather",
    }
    for source in body["sources"]:
        assert source["mode"] == "synthetic"
        assert source["record_count"] >= 1


def test_sources_ages_computed_at_requested_time():
    client = create_app().test_client()
    early = client.get("/api/sources?at=2026-01-16T16:00:30-05:00").get_json()
    late = client.get("/api/sources?at=2026-01-16T18:00:00-05:00").get_json()
    early_t = next(s for s in early["sources"] if s["source"] == "thermostat")
    late_t = next(s for s in late["sources"] if s["source"] == "thermostat")
    assert early_t["newest_observed_at"] != late_t["newest_observed_at"]
    assert late_t["age_s"] == 300
    assert early_t["age_s"] == 30
    assert late_t["record_count"] > early_t["record_count"]


def test_sources_rejects_naive_time():
    client = create_app().test_client()
    resp = client.get("/api/sources?at=2026-01-16T18:00:00")
    assert resp.status_code == 400


def test_health_unchanged():
    client = create_app().test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {
        "status": "ok",
        "service": "aria-home-backend",
        "data_mode": "synthetic",
    }


def test_demo_thermostat_reports_missing_count():
    client = create_app().test_client()
    body = client.get("/api/sources").get_json()
    thermostat = next(s for s in body["sources"] if s["source"] == "thermostat")
    assert thermostat["missing_count"] == 1
    assert thermostat["stale_count"] >= 0
    assert any("1 reading missing (no value received)" in n for n in thermostat["notes"])
