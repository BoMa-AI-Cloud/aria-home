import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aria_home.contracts import EvidenceKind, SourceKind
from aria_home.investigator import build_evidence_pack, validate
from aria_home.metrics import circuit_activity, temperature_trend
from aria_home.outcomes import follow_up_for
from aria_home.readiness import compute_readiness
from aria_home.scenario import load_scenario
from aria_home.verification import verify_recovery

TZ = timezone(timedelta(hours=-5))
SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
ZONE = "demo-house/main"


def at(h, m=0, s=0):
    return datetime(2026, 1, 16, h, m, s, tzinfo=TZ)


def _output(fact, readiness="cannot_tell", at_value=None):
    return json.dumps({
        "facts": [fact],
        "interpretation": "Indoor temperature is 68 F.",
        "hypotheses": [{"text": "The property may not be ready.", "supporting_ids": [fact["evidence_id"]], "conflicting_ids": []}],
        "unknowns": ["Equipment function is not established."],
        "clarification": "Who should respond?",
        "follow_up": {"observation": "Take another reading.", "when": (at_value or at(21)).isoformat()},
        "readiness": readiness,
        "limitations": ["Limited evidence."],
    })


def _raw_pack(now, observed, cadence=300, kind="measurement", source="room_sensor", value=68.0, received=None):
    received = received or observed + timedelta(seconds=20)
    item = {
        "id": "room-raw", "source": source, "kind": kind, "subject": ZONE, "quantity": "indoor_temp",
        "value": value, "unit": "F", "observed_at": observed.isoformat(), "received_at": received.isoformat(),
        "expected_cadence_s": cadence, "provenance": {"fixture_id": "test", "version": "1"},
    }
    pack = {
        "at": now.isoformat(),
        "trip": {"id": "t1", "property_id": "demo-house", "planned_arrival": (now + timedelta(hours=2)).isoformat()},
        "confirmation": {"trip_id": "t1", "property_id": "demo-house", "target_temp": 68.0, "target_unit": "F"},
        "source_statuses": [],
        "metrics": {
            "zone": ZONE,
            "indoor_trend": {"sample_count": 1, "coverage": 1.0, "last_value": value, "unit": "F", "first_observed_at": observed.isoformat(), "last_observed_at": observed.isoformat(), "rate_per_hour": 0.0, "change": 0.0, "expected_cadence_s": cadence},
            "target_gap": {"gap": 0.0, "unit": "F", "latest_value": value, "latest_observed_at": observed.isoformat(), "target_temp": 68.0, "target_unit": "F"},
        },
        "evidence": [item],
        "evidence_ids": ["room-raw"],
    }
    readiness = compute_readiness(pack, now)
    pack["readiness"] = dict(readiness)
    pack["canonical_readiness"] = dict(readiness)
    pack["computed_readiness"] = readiness["status"]
    pack["readiness_policy_version"] = readiness["policy_version"]
    return pack


def _fact(item_id="room-raw", value=68.0, observed=None):
    return {"claim_type": "current_temperature", "evidence_id": item_id, "field": "value", "value": value, "unit": "F", "at": (observed or at(6)).isoformat()}


def test_stale_raw_reading_rejected_as_current():
    now = at(20, 21)
    pack = _raw_pack(now, at(6))
    reasons = validate(_output(_fact(observed=at(6)), at_value=now + timedelta(minutes=30)), pack)
    assert reasons, "stale 06:00 reading was accepted as current at 20:21"
    assert any("stale" in r or "current" in r or "eligible" in r or "fresh" in r for r in reasons)


def test_freshness_boundary_exactly_at_limit_and_one_second_over():
    observed = at(20, 0)
    exact_now = observed + timedelta(seconds=600)
    pack = _raw_pack(exact_now, observed, cadence=300)
    assert validate(_output(_fact(observed=observed), at_value=exact_now + timedelta(minutes=30)), pack) == []
    over_now = observed + timedelta(seconds=601)
    pack_over = _raw_pack(over_now, observed, cadence=300)
    reasons = validate(_output(_fact(observed=observed), at_value=over_now + timedelta(minutes=30)), pack_over)
    assert any("stale" in r or "fresh" in r or "current" in r or "eligible" in r for r in reasons)


def test_superseded_reading_rejected_as_current_newer_accepted():
    now = at(20, 21)
    pack = _raw_pack(now, at(20, 10), cadence=3600)
    newer_observed = at(20, 15)
    pack["evidence"].append({
        "id": "room-newer", "source": "room_sensor", "kind": "measurement", "subject": ZONE, "quantity": "indoor_temp",
        "value": 60.0, "unit": "F", "observed_at": newer_observed.isoformat(), "received_at": (newer_observed + timedelta(seconds=20)).isoformat(),
        "expected_cadence_s": 3600, "provenance": {"fixture_id": "test", "version": "1"},
    })
    pack["evidence_ids"].append("room-newer")
    old_reasons = validate(_output(_fact(observed=at(20, 10)), at_value=now + timedelta(minutes=30)), pack)
    assert any("superseded" in r or "latest" in r or "current" in r or "historical" in r for r in old_reasons)
    new_fact = {"claim_type": "current_temperature", "evidence_id": "room-newer", "field": "value", "value": 60.0, "unit": "F", "at": newer_observed.isoformat()}
    out = json.loads(_output(new_fact, at_value=now + timedelta(minutes=30)))
    out["interpretation"] = "Indoor temperature is 60 F."
    assert validate(out, pack) == []


def test_delayed_reading_visible_only_after_receipt():
    scenario = load_scenario(SCENARIOS / "demo_v1")
    base = next(r for r in scenario.records if r.quantity == "indoor_temp")
    observed = at(18, 0)
    delayed = base.model_copy(update={"id": "delayed-1", "source": SourceKind.room_sensor, "kind": EvidenceKind.measurement, "subject": ZONE, "value": 70.0, "observed_at": observed, "received_at": at(19, 0), "expected_cadence_s": 300})
    before = temperature_trend([delayed], ZONE, at(17), at(19), at(18, 30))
    after = temperature_trend([delayed], ZONE, at(17), at(19), at(19, 1))
    assert before["sample_count"] == 0
    assert after["sample_count"] == 1
    assert after["last_value"] == 70.0


def _relabelled_demo_video(kind):
    scenario = load_scenario(SCENARIOS / "demo_video_v1")
    scenario.records = [
        r.model_copy(update={"kind": EvidenceKind(kind)}) if r.quantity == "indoor_temp" else r
        for r in scenario.records
    ]
    return scenario


def test_human_only_records_give_cannot_tell():
    scenario = _relabelled_demo_video("human_statement")
    pack = build_evidence_pack(scenario, at(20, 21))
    assert pack["metrics"]["indoor_trend"]["sample_count"] == 0
    assert compute_readiness(pack, at(20, 21))["status"] == "cannot_tell"
    assert pack["computed_readiness"] == "cannot_tell"


def test_mixed_kinds_use_sensors_only():
    scenario = load_scenario(SCENARIOS / "demo_v1")
    base = next(r for r in scenario.records if r.quantity == "indoor_temp")
    def rec(rid, value, observed, kind, source="room_sensor"):
        return base.model_copy(update={"id": rid, "source": SourceKind(source), "kind": EvidenceKind(kind), "subject": ZONE, "value": value, "observed_at": observed, "received_at": observed + timedelta(seconds=20), "expected_cadence_s": 1800})
    records = [
        rec("sensor-1", 60.0, at(18), "measurement"),
        rec("sensor-2", 61.0, at(19), "measurement"),
        rec("human-1", 99.0, at(19, 30), "human_statement"),
    ]
    trend = temperature_trend(records, ZONE, at(17), at(20), at(20))
    assert trend["sample_count"] == 2
    assert trend["last_value"] == 61.0


def test_missing_sensor_human_circuit_and_temp_not_counted():
    scenario = load_scenario(SCENARIOS / "demo_v1")
    base = next(r for r in scenario.records if r.quantity == "indoor_temp")
    human = base.model_copy(update={"id": "human-only", "source": SourceKind.room_sensor, "kind": EvidenceKind.human_statement, "subject": ZONE, "value": 99.0, "observed_at": at(19), "received_at": at(19), "expected_cadence_s": 300})
    trend = temperature_trend([human], ZONE, at(18), at(20), at(20))
    assert trend["sample_count"] == 0
    elec_base = next(r for r in scenario.records if r.quantity == "circuit_power")
    human_elec = elec_base.model_copy(update={"id": "human-elec", "kind": EvidenceKind.human_statement, "value": 999.0, "observed_at": at(19), "received_at": at(19)})
    circuit_id = (human_elec.binding.circuit_id if human_elec.binding else human_elec.subject)
    activity = circuit_activity([human_elec], circuit_id, at(18), at(20), at(20))
    assert activity["sample_count"] == 0
    assert activity["max_w"] is None


def test_human_only_recovery_not_verified():
    scenario = _relabelled_demo_video("human_statement")
    followup = follow_up_for(scenario, "inv-human", at(16, 31))
    result = verify_recovery(scenario, followup, at(20, 21))
    assert result["stage"] in ("telemetry_missing", "unable_to_verify")
    assert result["stage"] != "goal_verified"


def test_valid_sensors_unchanged():
    scenario = load_scenario(SCENARIOS / "demo_video_v1")
    pack = build_evidence_pack(scenario, at(20, 21))
    assert pack["computed_readiness"] == "on_track"
    assert pack["metrics"]["indoor_trend"]["last_value"] is not None
    ev = next(e for e in pack["evidence"] if e.get("quantity") == "indoor_temp")
    assert ev["expected_cadence_s"] is not None
    assert ev["provenance"]["fixture_id"]
