import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from aria_home.app import create_app
from aria_home.outcomes import follow_up_for
from aria_home.scenario import load_scenario
from aria_home.verification import verify_recovery

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "demo_video_v1"
TZ = timezone(timedelta(hours=-5))
REPORT_ID = "evt-video-hvac-completion-report"


def at(hour, minute=0):
    return datetime(2026, 1, 16, hour, minute, tzinfo=TZ)


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    return create_app().test_client()


def _post_and_get(client):
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00")
    assert resp.status_code == 200
    inv_id = resp.get_json()["investigation_id"]
    return inv_id


def _verification(client, inv_id, stamp):
    resp = client.get(f"/api/follow-ups/{inv_id}?at={stamp}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "verification" in body
    return body["verification"]


def _copy_scenario(tmp_path, name):
    target = tmp_path / name
    target.mkdir()
    for path in SCENARIO_DIR.glob("*.json"):
        (target / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def _edit_room(target, fn):
    path = target / "room_sensor.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["records"] = fn(data["records"])
    path.write_text(json.dumps(data), encoding="utf-8")


def _verify_variant(target, now):
    scenario = load_scenario(target)
    followup = follow_up_for(scenario, "inv-variant", at(16, 31))
    return verify_recovery(scenario, followup, now)


def test_demo_video_recovery_stages_through_api(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    inv_id = _post_and_get(client)

    v = _verification(client, inv_id, "2026-01-16T16:31:00-05:00")
    assert v["stage"] == "telemetry_missing"
    assert v["evaluated_at"].startswith("2026-01-16T16:31")
    assert v["corroboration_ids"] == []

    v = _verification(client, inv_id, "2026-01-16T18:21:00-05:00")
    assert v["stage"] == "reporting_restored"
    assert v["corroboration_ids"] == []

    v = _verification(client, inv_id, "2026-01-16T18:51:00-05:00")
    assert v["stage"] == "warming_observed"
    assert any(sid.startswith("room-temp-") for sid in v["supporting_ids"])
    assert not any(sid.startswith("elec-") and sid in v["supporting_ids"] and v["stage"] == "telemetry_missing" for sid in v["supporting_ids"])

    v = _verification(client, inv_id, "2026-01-16T19:51:00-05:00")
    assert v["stage"] == "warming_observed"
    assert v["stage"] != "goal_verified"

    v = _verification(client, inv_id, "2026-01-16T20:21:00-05:00")
    assert v["stage"] == "goal_verified"
    assert v["corroboration_ids"] == []
    assert REPORT_ID not in v["supporting_ids"]
    assert REPORT_ID not in v["corroboration_ids"]

    v = _verification(client, inv_id, "2026-01-16T20:44:00-05:00")
    assert v["stage"] == "goal_verified"
    assert v["corroboration_ids"] == []

    v = _verification(client, inv_id, "2026-01-16T20:46:00-05:00")
    assert v["stage"] == "goal_verified"
    assert v["corroboration_ids"] == [REPORT_ID]
    assert REPORT_ID not in v["supporting_ids"]
    assert any("corroboration only" in reason for reason in v["reasons"])

    v = _verification(client, inv_id, "2026-01-16T21:01:00-05:00")
    assert v["stage"] == "arrival_met"
    assert v["corroboration_ids"] == [REPORT_ID]
    assert REPORT_ID not in v["supporting_ids"]


def test_flat_room_readings_never_pass_reporting_restored(tmp_path):
    target = _copy_scenario(tmp_path, "flat")

    def flat(records):
        for row in records:
            if row["observed_at"] >= "2026-01-16T16:31:00-05:00":
                row["value"] = 52.0
        return records

    _edit_room(target, flat)
    for now in (at(18, 51), at(20, 21), at(21, 1)):
        result = _verify_variant(target, now)
        assert result["stage"] == "reporting_restored"


def test_room_readings_removed_after_1820_unable_to_verify(tmp_path):
    target = _copy_scenario(tmp_path, "removed")
    _edit_room(target, lambda records: [r for r in records if r["observed_at"] <= "2026-01-16T18:20:00-05:00"])
    result = _verify_variant(target, at(19, 0))
    assert result["stage"] == "unable_to_verify"
    result = _verify_variant(target, at(20, 21))
    assert result["stage"] == "unable_to_verify"


def test_one_dip_inside_hold_window_not_goal_verified(tmp_path):
    target = _copy_scenario(tmp_path, "dip")

    def dip(records):
        for row in records:
            if row["observed_at"] == "2026-01-16T20:05:00-05:00":
                row["value"] = 67.9
        return records

    _edit_room(target, dip)
    result = _verify_variant(target, at(20, 21))
    assert result["stage"] != "goal_verified"
    assert result["stage"] == "warming_observed"
