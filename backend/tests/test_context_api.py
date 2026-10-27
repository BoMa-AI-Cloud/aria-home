from aria_home.app import create_app


def _client(monkeypatch, tmp_path):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "context.db"))
    monkeypatch.setenv("ARIA_HOME_MODEL_ENABLED", "0")
    return create_app().test_client()


def test_context_before_confirmed_at_video(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    resp = client.get("/api/context?scenario=demo_video_v1&at=2026-01-16T09:19:00-05:00")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["confirmed"] is False
    assert payload["reason"] == "trip_unconfirmed"
    assert payload["reason_in_words"] == "Not yet confirmed"
    assert payload["flags"]["trip_unconfirmed"] is True
    assert payload["context_flags"] == payload["flags"]
    assert payload["confirmation"] is None
    assert payload["scenario"] == "demo_video_v1"
    assert payload["at"] == "2026-01-16T09:19:00-05:00"
    assert payload["timezone"] == "America/New_York"
    assert "target_temp" not in payload


def test_context_at_and_after_confirmed_at_video(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    for at in ("2026-01-16T09:20:00-05:00", "2026-01-16T16:31:00-05:00"):
        resp = client.get(f"/api/context?scenario=demo_video_v1&at={at}")
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["confirmed"] is True
        assert payload["property_label"] == "demo-cabin"
        assert payload["planned_arrival"] == "2026-01-16T21:00:00-05:00"
        assert payload["landing"] == "2026-01-16T19:45:00-05:00"
        assert payload["arrival_plan"]["planned_property_arrival"] == "2026-01-16T21:00:00-05:00"
        assert [a["minutes"] for a in payload["allowances"]] == [45, 30]
        assert "airport-exit/baggage" in payload["allowances"][0]["label"]
        assert "driving" in payload["allowances"][1]["label"]
        assert "scenario estimates" in payload["arrival_estimates_note"]
        assert payload["target_temp"] == 68
        assert payload["target_unit"] == "F"
        assert payload["notify_homeowner"] is True
        assert payload["homeowner_notification_preference"] is True
        assert payload["manager_authorized"] is True
        assert payload["manager_coordination_permission"] is True
        assert payload["confirmed_at"] == "2026-01-16T09:20:00-05:00"
        assert payload["revision_id"] == "trip-video-001-rev1"
        assert payload["flags"] == {
            "trip_cancelled": False,
            "trip_unconfirmed": False,
            "trip_mismatched": False,
            "confirmation_outdated": False,
        }
        assert payload["scenario"] == "demo_video_v1"
        assert payload["at"] == at
        assert payload["timezone"] == "America/New_York"


def test_context_revised_trip_marks_confirmation_outdated(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    before = client.get("/api/context?scenario=demo_revised_v1&at=2026-01-16T16:30:00-05:00").get_json()
    assert before["confirmed"] is True
    assert before["revision_id"] == "trip-demo-001-rev1"
    resp = client.get("/api/context?scenario=demo_revised_v1&at=2026-01-16T18:00:00-05:00")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["confirmed"] is False
    assert payload["reason"] == "confirmation_outdated"
    assert payload["flags"]["confirmation_outdated"] is True
    assert payload["context_flags"]["confirmation_outdated"] is True
    assert payload["confirmation"] is None
    assert payload["current_trip_revision_id"] == "trip-demo-001-rev2"
    assert payload["scenario"] == "demo_revised_v1"
    assert payload["at"] == "2026-01-16T18:00:00-05:00"
    assert payload["timezone"] == "America/New_York"


def test_context_echo_and_validation(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    assert client.get("/api/context?scenario=nope&at=2026-01-16T09:20:00-05:00").status_code == 404
    naive = client.get("/api/context?scenario=demo_video_v1&at=2026-01-16T09:20:00")
    assert naive.status_code == 400
    assert naive.get_json()["scenario"] == "demo_video_v1"
    assert naive.get_json()["timezone"] == "America/New_York"
