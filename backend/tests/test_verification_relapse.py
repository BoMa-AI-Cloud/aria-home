import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from aria_home.notifications import build_payload
from aria_home.outcomes import follow_up_for
from aria_home.scenario import load_scenario
from aria_home.verification import verify_recovery

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "demo_video_v1"
TZ = timezone(timedelta(hours=-5))


def at(hour, minute=0):
    return datetime(2026, 1, 16, hour, minute, tzinfo=TZ)


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


def test_relapse_after_success_is_goal_not_maintained(tmp_path):
    target = _copy_scenario(tmp_path, "relapse")

    def relapse(records):
        for row in records:
            if row["observed_at"] >= "2026-01-16T20:25:00-05:00":
                row["value"] = 64.0
        return records

    _edit_room(target, relapse)
    result = _verify_variant(target, at(20, 30))
    assert result["stage"] == "goal_not_maintained"
    assert result["goal_verified_at"] == at(20, 20)
    payload = build_payload("homeowner", verification=result, now=at(20, 30))
    assert payload["stage"] == "goal_not_maintained"
    assert "no longer" in payload["stage_in_words"]


def test_recovery_requires_new_full_hold(tmp_path):
    target = _copy_scenario(tmp_path, "recovery")

    def dip(records):
        for row in records:
            if row["observed_at"] == "2026-01-16T20:25:00-05:00":
                row["value"] = 64.0
        return records

    _edit_room(target, dip)
    relapsed = _verify_variant(target, at(20, 55))
    assert relapsed["stage"] == "goal_not_maintained"
    assert relapsed["goal_verified_at"] == at(20, 20)
    recovered = _verify_variant(target, at(21, 1))
    assert recovered["stage"] == "arrival_met"
    assert recovered["goal_verified_at"] == at(21, 0)


def test_stale_after_success_is_unable_to_verify(tmp_path):
    target = _copy_scenario(tmp_path, "stale-after")
    _edit_room(target, lambda records: [r for r in records if r["observed_at"] <= "2026-01-16T20:20:00-05:00"])
    result = _verify_variant(target, at(21, 1))
    assert result["stage"] == "unable_to_verify"
    assert result["goal_verified_at"] == at(20, 20)


def test_relapse_spanning_arrival_is_not_arrival_met(tmp_path):
    target = _copy_scenario(tmp_path, "relapse-arrival")

    def relapse(records):
        for row in records:
            if "2026-01-16T20:40:00-05:00" <= row["observed_at"] <= "2026-01-16T21:00:00-05:00":
                row["value"] = 64.0
        return records

    _edit_room(target, relapse)
    result = _verify_variant(target, at(21, 6))
    assert result["stage"] == "goal_not_maintained"
    assert result["stage"] != "arrival_met"
    assert result["goal_verified_at"] == at(20, 20)
