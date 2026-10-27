from datetime import datetime, timedelta, timezone
from pathlib import Path

from aria_home.app import create_app
from aria_home.outcomes import follow_up_for
from aria_home.scenario import load_scenario
from aria_home.verification import build_evidence_timeline

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "demo_video_v1"
TZ = timezone(timedelta(hours=-5))
REPORT_ID = "evt-video-hvac-completion-report"


def at(hour, minute=0, second=0):
    return datetime(2026, 1, 16, hour, minute, second, tzinfo=TZ)


def _timeline(now):
    scenario = load_scenario(SCENARIO_DIR)
    followup = follow_up_for(scenario, "inv-timeline", at(16, 31))
    return build_evidence_timeline(scenario, followup, now)


def _kinds(entries):
    return [e["kind"] for e in entries]


def test_evidence_timeline_order_and_verified_before_report():
    entries = _timeline(at(21, 1))
    assert _kinds(entries) == [
        "reporting_restored",
        "warming_observed",
        "target_reached",
        "goal_verified",
        "hvac_completion_report",
        "arrival_checked",
    ]
    assert [e["label"] for e in entries] == [
        "Thermostat reporting restored",
        "Warming first observed",
        "Target first reached",
        "Hold completed and goal verified",
        "HVAC completion report available",
        "Arrival checked",
    ]
    by_kind = {e["kind"]: e for e in entries}
    assert by_kind["reporting_restored"]["supporting_ids"] == ["tstat-video-temp-1820"]
    assert by_kind["reporting_restored"]["observed_at"] == at(18, 20)
    assert by_kind["warming_observed"]["observed_at"] == at(18, 50)
    assert "room-temp-1850" in by_kind["warming_observed"]["supporting_ids"]
    assert by_kind["target_reached"]["supporting_ids"] == ["room-temp-1950"]
    assert by_kind["target_reached"]["observed_at"] == at(19, 50)
    assert by_kind["goal_verified"]["observed_at"] == at(20, 20)
    assert by_kind["goal_verified"]["supporting_ids"][0] == "room-temp-1950"
    assert by_kind["goal_verified"]["supporting_ids"][-1] == "room-temp-2020"
    assert by_kind["hvac_completion_report"]["supporting_ids"] == [REPORT_ID]
    assert by_kind["hvac_completion_report"]["corroboration_only"] is True
    assert by_kind["hvac_completion_report"]["observed_at"] == at(20, 40)
    assert by_kind["hvac_completion_report"]["available_at"] == at(20, 45)
    assert by_kind["arrival_checked"]["observed_at"] == at(21, 0)
    assert "room-temp-2100" in by_kind["arrival_checked"]["supporting_ids"]
    assert by_kind["goal_verified"]["first_known_at"] < by_kind["hvac_completion_report"]["available_at"]
    assert by_kind["goal_verified"]["first_known_at"] < by_kind["hvac_completion_report"]["first_known_at"]
    for entry in entries:
        assert entry["supporting_record_ids"] == entry["supporting_ids"]
        assert entry["received_at"] is not None
        assert entry["available_at"] == entry["received_at"]
        assert entry["first_known_at"] <= at(21, 1)


def test_evidence_timeline_absent_before_each_time():
    assert _timeline(at(16, 31)) == []
    assert _kinds(_timeline(at(18, 20, 19))) == []
    assert _kinds(_timeline(at(18, 21))) == ["reporting_restored"]
    assert _kinds(_timeline(at(18, 50, 19))) == ["reporting_restored"]
    assert _kinds(_timeline(at(18, 51))) == ["reporting_restored", "warming_observed"]
    assert _kinds(_timeline(at(19, 51))) == ["reporting_restored", "warming_observed", "target_reached"]
    assert _kinds(_timeline(at(20, 21))) == [
        "reporting_restored",
        "warming_observed",
        "target_reached",
        "goal_verified",
    ]
    assert REPORT_ID not in [sid for e in _timeline(at(20, 21)) for sid in e["supporting_ids"]]
    assert _kinds(_timeline(at(20, 44))) == _kinds(_timeline(at(20, 21)))
    assert "hvac_completion_report" in _kinds(_timeline(at(20, 46)))
    assert "arrival_checked" not in _kinds(_timeline(at(20, 46)))
    assert "arrival_checked" not in _kinds(_timeline(at(21, 0, 19)))
    assert "arrival_checked" in _kinds(_timeline(at(21, 1)))


def test_evidence_timeline_no_future_entries():
    for now in [at(16, 31), at(18, 21), at(18, 51), at(19, 51), at(20, 21), at(20, 46), at(21, 1)]:
        entries = _timeline(now)
        assert entries == sorted(entries, key=lambda e: (e["first_known_at"], e["observed_at"]))
        for entry in entries:
            assert entry["first_known_at"] <= now
            assert entry["received_at"] <= now
            assert entry["available_at"] <= now


def test_follow_up_response_includes_evidence_timeline(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    client = create_app().test_client()
    resp = client.post("/api/investigations?scenario=demo_video_v1&at=2026-01-16T16:31:00-05:00")
    assert resp.status_code == 200
    inv_id = resp.get_json()["investigation_id"]
    body = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T20:21:00-05:00").get_json()
    kinds = [e["kind"] for e in body["evidence_timeline"]]
    assert kinds == ["reporting_restored", "warming_observed", "target_reached", "goal_verified"]
    assert "hvac_completion_report" not in kinds
    body = client.get(f"/api/follow-ups/{inv_id}?at=2026-01-16T21:01:00-05:00").get_json()
    kinds = [e["kind"] for e in body["evidence_timeline"]]
    assert kinds.index("goal_verified") < kinds.index("hvac_completion_report") < kinds.index("arrival_checked")
    report = body["evidence_timeline"][kinds.index("hvac_completion_report")]
    assert report["available_at"].startswith("2026-01-16T20:45")
    assert report["corroboration_only"] is True
