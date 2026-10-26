from datetime import datetime, timedelta, timezone
from pathlib import Path

from aria_home.outcomes import OutcomeStatus, evaluate_outcome, follow_up_for
from aria_home.scenario import load_scenario

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
TZ = timezone(timedelta(hours=-5))
CREATED_AT = datetime(2026, 1, 16, 18, 0, tzinfo=TZ)
NOTE = "An observed change after a reported action does not prove what caused it."


def _at(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _follow_up(scenario_name: str):
    scenario = load_scenario(SCENARIOS / scenario_name)
    return scenario, follow_up_for(scenario, "inv-1", CREATED_AT)


def test_follow_up_uses_confirmation_and_trip_deadline():
    scenario, followup = _follow_up("demo_v1")
    assert followup.target_temp == scenario.confirmation.target_temp
    assert followup.target_unit == scenario.confirmation.target_unit
    assert followup.deadline == scenario.trip.planned_arrival + timedelta(hours=2)
    assert followup.min_samples == 3
    assert followup.min_rise_f == 2.0
    assert followup.zone == "demo-cabin/main"


def test_demo_v1_awaiting_at_1830():
    scenario, followup = _follow_up("demo_v1")
    result = evaluate_outcome(followup, scenario.records, _at("2026-01-16T18:30:00-05:00"))
    assert result.status == OutcomeStatus.awaiting_measurement


def test_demo_v1_unable_at_2030():
    scenario, followup = _follow_up("demo_v1")
    result = evaluate_outcome(followup, scenario.records, _at("2026-01-16T20:30:00-05:00"))
    assert result.status == OutcomeStatus.unable_to_verify
    assert result.sample_count == 1


def test_demo_recovery_warming_at_1900_with_note():
    scenario, followup = _follow_up("demo_recovery_v1")
    result = evaluate_outcome(followup, scenario.records, _at("2026-01-16T19:00:00-05:00"))
    assert result.status == OutcomeStatus.warming_observed
    assert result.note == NOTE
    assert result.sample_count >= followup.min_samples
    assert result.last_value - result.first_value >= followup.min_rise_f


def test_demo_recovery_target_reached_at_2030_with_note():
    scenario, followup = _follow_up("demo_recovery_v1")
    result = evaluate_outcome(followup, scenario.records, _at("2026-01-16T20:30:20-05:00"))
    assert result.status == OutcomeStatus.target_reached
    assert result.note == NOTE
    assert result.last_value == 68.4


def test_demo_recovery_not_target_reached_at_2015():
    scenario, followup = _follow_up("demo_recovery_v1")
    now = _at("2026-01-16T20:15:20-05:00")
    result = evaluate_outcome(followup, scenario.records, now)
    assert result.status != OutcomeStatus.target_reached
    readings = [
        r
        for r in scenario.records
        if r.quantity == "indoor_temp"
        and r.subject == followup.zone
        and r.value is not None
        and r.received_at <= now
        and r.observed_at > followup.created_at
    ]
    readings.sort(key=lambda r: r.observed_at)
    assert readings[-1].value == 68.2
    assert sum(1 for r in readings if r.value >= 68) == 1
    assert result.status == OutcomeStatus.warming_observed


def test_demo_no_followup_unable_at_2030():
    scenario, followup = _follow_up("demo_no_followup_v1")
    result = evaluate_outcome(followup, scenario.records, _at("2026-01-16T20:30:00-05:00"))
    assert result.status == OutcomeStatus.unable_to_verify
    assert result.sample_count == 0
    assert result.first_value is None
    assert result.last_value is None


def test_records_received_after_now_are_ignored():
    scenario, followup = _follow_up("demo_recovery_v1")
    now = _at("2026-01-16T19:00:00-05:00")
    result = evaluate_outcome(followup, scenario.records, now)
    by_id = {r.id: r for r in scenario.records}
    assert result.supporting_ids
    assert all(by_id[record_id].received_at <= now for record_id in result.supporting_ids)
    assert result.sample_count == len(result.supporting_ids)
    later = evaluate_outcome(followup, scenario.records, _at("2026-01-16T20:30:00-05:00"))
    assert later.sample_count > result.sample_count
    assert result.status != OutcomeStatus.target_reached


def test_manager_report_alone_never_changes_status():
    scenario, followup = _follow_up("demo_recovery_v1")
    statements = [r for r in scenario.records if r.quantity == "manager_report"]
    assert statements
    before = evaluate_outcome(followup, statements, _at("2026-01-16T19:00:00-05:00"))
    assert before.status == OutcomeStatus.awaiting_measurement
    assert before.sample_count == 0
    assert before.note is None
    after = evaluate_outcome(followup, statements, _at("2026-01-16T20:30:00-05:00"))
    assert after.status == OutcomeStatus.unable_to_verify
    assert after.sample_count == 0
    assert after.note is None
