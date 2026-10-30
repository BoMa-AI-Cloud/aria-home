import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

import aria_home.app as app_module
from aria_home.app import create_app
from aria_home.contracts import EvidenceRecord, SourceKind
from aria_home.eligibility import is_measurement_eligible, normalized_measurement_value
from aria_home.evidence import source_status
from aria_home.investigator import build_evidence_pack
from aria_home.outcomes import follow_up_for
from aria_home.readiness import compute_readiness
from aria_home.scenario import load_scenario
from aria_home.verification import verify_recovery

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "demo_video_v1"
TZ = timezone(timedelta(hours=-5))
REPORT_ID = "evt-video-hvac-completion-report"


def at(hour, minute=0):
    return datetime(2026, 1, 16, hour, minute, tzinfo=TZ)


def _copy(tmp_path, name):
    target = tmp_path / name
    target.mkdir()
    for path in SCENARIO_DIR.glob("*.json"):
        (target / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def _edit(target, filename, fn):
    path = target / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    data["records"] = fn(data["records"])
    path.write_text(json.dumps(data), encoding="utf-8")


def _verify(target, now):
    scenario = load_scenario(target)
    followup = follow_up_for(scenario, "inv-audit3", at(16, 31))
    return verify_recovery(scenario, followup, now), scenario, followup


def _latest_room_copy(records, new_id, value, unit="F"):
    latest = next(r for r in records if r["observed_at"] == "2026-01-16T21:00:00-05:00")
    return {**latest, "id": new_id, "value": value, "unit": unit}


@pytest.mark.parametrize("prefix", ["zz-", "aa-"])
def test_conflicting_latest_reading_never_arrival_met_regardless_of_id(tmp_path, prefix):
    target = _copy(tmp_path, f"conflict-{prefix}")
    def add(records):
        return records + [_latest_room_copy(records, f"{prefix}conflict", 40.0)]
    _edit(target, "room_sensor.json", add)
    result, _, _ = _verify(target, at(21, 1))
    assert result["stage"] == "unable_to_verify"
    assert result["stage"] not in ("goal_verified", "arrival_met")


def test_conflicting_reading_reversed_insertion_order_same_result(tmp_path):
    target = _copy(tmp_path, "conflict-reversed")
    def add(records):
        return [_latest_room_copy(records, "zz-conflict", 40.0)] + records
    _edit(target, "room_sensor.json", add)
    result, _, _ = _verify(target, at(21, 1))
    assert result["stage"] == "unable_to_verify"


def test_conflict_inside_hold_interval_blocks_goal(tmp_path):
    target = _copy(tmp_path, "conflict-hold")
    def add(records):
        row = next(r for r in records if r["observed_at"] == "2026-01-16T20:05:00-05:00")
        return records + [{**row, "id": "zz-conflict-hold", "value": 40.0}]
    _edit(target, "room_sensor.json", add)
    result, _, _ = _verify(target, at(20, 21))
    assert result["stage"] == "unable_to_verify"
    assert result["stage"] != "goal_verified"


def test_identical_duplicate_collapses_and_still_arrival_met(tmp_path):
    target = _copy(tmp_path, "dup-identical")
    def add(records):
        latest = next(r for r in records if r["observed_at"] == "2026-01-16T21:00:00-05:00")
        return records + [{**latest, "id": "dup-identical"}]
    _edit(target, "room_sensor.json", add)
    result, _, _ = _verify(target, at(21, 1))
    assert result["stage"] == "arrival_met"
    assert ("room-temp-2100" in result["supporting_ids"]) != ("dup-identical" in result["supporting_ids"])
    assert len(result["supporting_ids"]) == len(set(result["supporting_ids"]))


def test_equivalent_unit_duplicate_is_not_a_conflict(tmp_path):
    target = _copy(tmp_path, "dup-celsius")
    def add(records):
        latest = next(r for r in records if r["observed_at"] == "2026-01-16T21:00:00-05:00")
        return records + [{**latest, "id": "dup-celsius", "value": (68.4 - 32.0) * 5.0 / 9.0, "unit": "C"}]
    _edit(target, "room_sensor.json", add)
    result, _, _ = _verify(target, at(21, 1))
    assert result["stage"] == "arrival_met"


def test_conflict_in_other_zone_does_not_block(tmp_path):
    target = _copy(tmp_path, "conflict-other-zone")
    def add(records):
        latest = next(r for r in records if r["observed_at"] == "2026-01-16T21:00:00-05:00")
        return records + [{**latest, "id": "other-zone-conflict", "subject": "demo-house/other", "value": 40.0}]
    _edit(target, "room_sensor.json", add)
    result, _, _ = _verify(target, at(21, 1))
    assert result["stage"] == "arrival_met"


def test_conflict_before_followup_does_not_block_arrival(tmp_path):
    target = _copy(tmp_path, "conflict-before")
    def add(records):
        row = next(r for r in records if r["observed_at"] == "2026-01-16T16:30:00-05:00")
        return records + [{**row, "id": "early-conflict", "value": 40.0}]
    _edit(target, "room_sensor.json", add)
    result, _, _ = _verify(target, at(21, 1))
    assert result["stage"] == "arrival_met"


def test_readiness_and_verification_agree_on_conflict(tmp_path):
    target = _copy(tmp_path, "conflict-agree")
    def add(records):
        return records + [_latest_room_copy(records, "zz-conflict", 40.0)]
    _edit(target, "room_sensor.json", add)
    result, scenario, _ = _verify(target, at(21, 1))
    pack = build_evidence_pack(scenario, at(21, 1))
    readiness = compute_readiness(pack, at(21, 1))
    assert result["stage"] == "unable_to_verify"
    assert readiness["status"] == "cannot_tell"
    assert readiness["inputs"]["indoor_conflict_count"] >= 1


def _base_record(**overrides):
    data = {
        "id": "rec-1", "source": "room_sensor", "kind": "measurement",
        "subject": "demo-house/main", "quantity": "indoor_temp",
        "value": 68.0, "unit": "F",
        "observed_at": at(20, 0), "received_at": at(20, 0),
        "expected_cadence_s": 300, "mode": "synthetic",
        "provenance": {"fixture_id": "test", "version": "1"},
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_values_rejected_at_contract(bad):
    with pytest.raises(ValidationError):
        EvidenceRecord.model_validate(_base_record(value=bad))


def test_string_hvac_state_remains_valid():
    record = EvidenceRecord.model_validate(_base_record(
        id="state-1", source="thermostat", kind="device_report",
        quantity="hvac_reported_state", value="heating", unit=None,
    ))
    assert record.value == "heating"


def test_invalid_unit_rejected_and_valid_power_accepted():
    with pytest.raises(ValidationError):
        EvidenceRecord.model_validate(_base_record(unit="K"))
    record = EvidenceRecord.model_validate(_base_record(
        id="pwr-1", source="electrical", quantity="circuit_power", value=500.0, unit="W",
        subject="circuit-blower",
    ))
    assert record.value == 500.0


def test_overflow_on_conversion_is_ineligible():
    record = EvidenceRecord.model_validate(_base_record(value=1e308, unit="C"))
    assert normalized_measurement_value(record) is None
    assert not is_measurement_eligible(record, require_value=True)


def test_overflow_room_values_never_verify(tmp_path):
    target = _copy(tmp_path, "overflow")
    def blow(records):
        for row in records:
            if row["observed_at"] > "2026-01-16T18:20:00-05:00":
                row["value"] = 1e308
                row["unit"] = "C"
        return records
    _edit(target, "room_sensor.json", blow)
    result, _, _ = _verify(target, at(21, 1))
    assert result["stage"] not in ("goal_verified", "arrival_met")
    assert result["stage"] == "unable_to_verify"


def test_nonfinite_scenario_load_rejected_not_accepted(tmp_path):
    target = _copy(tmp_path, "inf-scenario")
    def blow(records):
        for row in records:
            if row["observed_at"] > "2026-01-16T18:20:00-05:00":
                row["value"] = float("inf")
        return records
    _edit(target, "room_sensor.json", blow)
    with pytest.raises(ValidationError):
        load_scenario(target)


def test_api_invalid_scenario_returns_4xx_never_500(tmp_path, monkeypatch):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "api.db"))
    bad = _copy(tmp_path, "bad_inf")
    def blow(records):
        for row in records:
            row["value"] = float("inf") if isinstance(row["value"], (int, float)) else row["value"]
        return records
    _edit(bad, "room_sensor.json", blow)
    client = create_app().test_client()
    monkeypatch.setattr(app_module, "SCENARIO_PATH", tmp_path / "demo_v1")
    resp = client.get("/api/sources?scenario=bad_inf")
    assert 400 <= resp.status_code < 500


def test_source_status_string_conflict_detected(make_record):
    records = [
        make_record(id="s1", source="thermostat", kind="device_report", quantity="hvac_reported_state", value="heating", unit=None),
        make_record(id="s2", source="thermostat", kind="device_report", quantity="hvac_reported_state", value="idle", unit=None),
    ]
    status = source_status(SourceKind.thermostat, records, at(20, 1))
    assert status.availability.value == "conflicting"


def test_source_status_equivalent_units_not_conflicting(make_record):
    records = [
        make_record(id="t1", source="room_sensor", value=68.0, unit="F"),
        make_record(id="t2", source="room_sensor", value=20.0, unit="C"),
    ]
    status = source_status(SourceKind.room_sensor, records, at(20, 1))
    assert status.availability.value != "conflicting"


@pytest.mark.parametrize("state", ["idle", "off"])
def test_idle_or_off_at_target_still_arrival_met(tmp_path, state):
    target = _copy(tmp_path, f"state-{state}")
    def edit(records):
        states = [r for r in records if r["quantity"] == "hvac_reported_state"]
        latest = max(states, key=lambda r: r["observed_at"])
        latest["value"] = state
        return records
    _edit(target, "thermostat.json", edit)
    result, _, _ = _verify(target, at(21, 1))
    assert result["stage"] == "arrival_met"


def test_quiet_heating_circuit_at_target_still_arrival_met(tmp_path):
    target = _copy(tmp_path, "quiet-circuit")
    def edit(records):
        for row in records:
            if row["subject"] == "circuit-blower":
                row["value"] = 5
        return records
    _edit(target, "electrical.json", edit)
    result, _, _ = _verify(target, at(21, 1))
    assert result["stage"] == "arrival_met"


def test_stale_hvac_state_does_not_block(tmp_path):
    target = _copy(tmp_path, "stale-state")
    def edit(records):
        return [r for r in records if not (r["quantity"] == "hvac_reported_state" and r["observed_at"] > "2026-01-16T18:00:00-05:00")]
    _edit(target, "thermostat.json", edit)
    result, _, _ = _verify(target, at(21, 1))
    assert result["stage"] == "arrival_met"


def test_already_at_target_needs_no_rise(tmp_path):
    target = _copy(tmp_path, "already-warm")
    def edit(records):
        for row in records:
            row["value"] = 68.0
        return records
    _edit(target, "room_sensor.json", edit)
    result, _, _ = _verify(target, at(20, 21))
    assert result["stage"] == "goal_verified"
    result, _, _ = _verify(target, at(21, 1))
    assert result["stage"] == "arrival_met"


def test_active_fan_without_warming_stays_reporting_restored(tmp_path):
    target = _copy(tmp_path, "fan-only")
    def flat(records):
        for row in records:
            if row["observed_at"] >= "2026-01-16T16:31:00-05:00":
                row["value"] = 52.0
        return records
    _edit(target, "room_sensor.json", flat)
    def fan(records):
        states = [r for r in records if r["quantity"] == "hvac_reported_state"]
        max(states, key=lambda r: r["observed_at"])["value"] = "fan_only"
        return records
    _edit(target, "thermostat.json", fan)
    result, _, _ = _verify(target, at(20, 21))
    assert result["stage"] == "reporting_restored"


def test_temperature_relapse_after_verification(tmp_path):
    target = _copy(tmp_path, "relapse-audit")
    def edit(records):
        for row in records:
            if row["observed_at"] == "2026-01-16T20:40:00-05:00":
                row["value"] = 60.0
        return records
    _edit(target, "room_sensor.json", edit)
    result, _, _ = _verify(target, at(21, 1))
    assert result["stage"] == "goal_not_maintained"
    assert result["goal_verified_at"] is not None


def test_missing_readings_near_arrival_unable(tmp_path):
    target = _copy(tmp_path, "missing-arrival")
    _edit(target, "room_sensor.json", lambda records: [r for r in records if r["observed_at"] <= "2026-01-16T20:30:00-05:00"])
    result, _, _ = _verify(target, at(21, 1))
    assert result["stage"] == "unable_to_verify"


def test_completion_report_alone_does_not_verify(tmp_path):
    target = _copy(tmp_path, "report-only")
    def flat(records):
        for row in records:
            if row["observed_at"] >= "2026-01-16T16:31:00-05:00":
                row["value"] = 52.0
        return records
    _edit(target, "room_sensor.json", flat)
    result, _, _ = _verify(target, at(20, 46))
    assert result["stage"] == "reporting_restored"
    assert result["corroboration_ids"] == [REPORT_ID]
    assert REPORT_ID not in result["supporting_ids"]


def test_goal_verified_before_completion_report_exists(tmp_path):
    target = _copy(tmp_path, "pre-report")
    result, _, _ = _verify(target, at(20, 21))
    assert result["stage"] == "goal_verified"
    assert result["corroboration_ids"] == []
    assert REPORT_ID not in result["supporting_ids"]
