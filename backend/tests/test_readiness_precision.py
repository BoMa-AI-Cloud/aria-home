import json
import math
from datetime import datetime, timedelta
from pathlib import Path

from aria_home.investigator import build_evidence_pack, validate
from aria_home.metrics import target_gap, temperature_trend
import aria_home.readiness as readiness_mod
from aria_home.readiness import compute_readiness
from aria_home.scenario import load_scenario

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "demo_v1"
ZONE = "demo-house/main"
NOW = datetime.fromisoformat("2026-01-16T18:00:00-05:00")


def _pack_for_values(values, unit="F", target=68.0, target_unit="F"):
    times = [NOW - timedelta(hours=2) + timedelta(hours=i) for i in range(len(values))]
    trend = {
        "sample_count": len(values),
        "coverage": 1.0,
        "first_value": values[0],
        "last_value": values[-1],
        "first_observed_at": times[0].isoformat(),
        "last_observed_at": times[-1].isoformat(),
        "change": values[-1] - values[0],
        "rate_per_hour": 0.0,
        "unit": unit,
        "expected_cadence_s": 3600,
    }
    target_in_unit = target if target_unit == unit else (target - 32.0) * 5.0 / 9.0 if unit == "C" else target * 9.0 / 5.0 + 32.0
    gap = {"gap": values[-1] - target_in_unit, "unit": unit, "latest_value": values[-1], "target_temp": target_in_unit if unit != target_unit else target, "target_unit": target_unit, "latest_observed_at": times[-1].isoformat(), "expected_cadence_s": 3600}
    if unit == "C" and target_unit == "F":
        gap["target_temp"] = (target - 32.0) * 5.0 / 9.0
    return {
        "at": NOW.isoformat(),
        "trip": {"id": "t1", "property_id": "demo-house", "planned_arrival": (NOW + timedelta(hours=2)).isoformat()},
        "confirmation": {"trip_id": "t1", "property_id": "demo-house", "target_temp": target, "target_unit": target_unit},
        "source_statuses": [],
        "metrics": {"zone": ZONE, "indoor_trend": trend, "target_gap": gap},
        "evidence": [],
    }


def _flat(value, unit="F", target=68.0, target_unit="F"):
    return compute_readiness(_pack_for_values([value, value, value], unit, target, target_unit), NOW)


def test_just_below_target_is_at_risk():
    result = _flat(67.96)
    assert result["status"] == "at_risk"
    assert result["inputs"]["gap"] == 67.96 - 68.0
    assert result["policy_version"] == readiness_mod.READINESS_POLICY_VERSION


def test_exactly_at_target_is_on_track():
    assert _flat(68.0)["status"] == "on_track"


def test_just_above_target_is_on_track():
    assert _flat(68.04)["status"] == "on_track"


def test_default_tolerance_is_zero_and_not_a_rounding_side_effect():
    assert readiness_mod.TARGET_GAP_TOLERANCE_F == 0.0
    assert _flat(67.99)["status"] == "at_risk"


def test_explicit_tolerance_only_when_policy_constant_set(monkeypatch):
    import aria_home.readiness as readiness

    monkeypatch.setattr(readiness, "TARGET_GAP_TOLERANCE_F", 0.05)
    assert _flat(67.96)["status"] == "on_track"
    monkeypatch.setattr(readiness, "TARGET_GAP_TOLERANCE_F", 0.0)
    assert _flat(67.96)["status"] == "at_risk"


def test_celsius_record_converted_before_decision():
    value_c = (67.96 - 32.0) * 5.0 / 9.0
    result = _flat(value_c, unit="C", target=68.0, target_unit="F")
    assert result["status"] == "at_risk"
    assert math.isclose(result["inputs"]["gap_f"], -0.04, abs_tol=1e-9)


def test_celsius_trend_and_target_gap_conversion_exists():
    from aria_home.contracts import EvidenceRecord

    def rec(i, v, at):
        return EvidenceRecord(id=f"c{i}", source="thermostat", kind="measurement", subject=ZONE, quantity="indoor_temp", value=v, unit="C", observed_at=at, received_at=at + timedelta(seconds=20), expected_cadence_s=3600, mode="synthetic", provenance={"fixture_id": "test", "version": "1"})

    times = [NOW - timedelta(hours=2), NOW - timedelta(hours=1), NOW]
    value_c = (67.96 - 32.0) * 5.0 / 9.0
    records = [rec(i, value_c, t) for i, t in enumerate(times)]
    trend = temperature_trend(records, ZONE, times[0], NOW, NOW)
    gap = target_gap(trend, 68.0, "F")
    assert trend["unit"] == "C"
    assert gap is not None and gap["gap"] < 0
    pack = _pack_for_values([value_c] * 3, unit="C", target=68.0, target_unit="F")
    pack["metrics"]["target_gap"] = {**gap, "target_unit": "F"}
    assert compute_readiness(pack, NOW)["status"] == "at_risk"


def _demo_pack_at_6796():
    scenario = load_scenario(SCENARIO_DIR)
    at = scenario.manifest.start + timedelta(hours=3)
    for record in scenario.records:
        if record.quantity == "indoor_temp" and record.value is not None:
            record.value = 67.96
    return scenario, at, build_evidence_pack(scenario, at)


def _model_json(pack, at, readiness):
    trend = pack["metrics"]["indoor_trend"]
    gap = pack["metrics"]["target_gap"]
    return json.dumps({
        "facts": [
            {"claim_type": "current_temperature", "evidence_id": "metric:indoor_trend", "field": "last_value", "value": trend["last_value"], "unit": trend["unit"], "at": None},
            {"claim_type": "target_temperature", "evidence_id": "metric:target_gap", "field": "target_temp", "value": gap["target_temp"], "unit": "F", "at": None},
            {"claim_type": "target_gap", "evidence_id": "metric:target_gap", "field": "gap", "value": gap["gap"], "unit": gap["unit"], "at": None},
            {"claim_type": "electrical_activity", "evidence_id": "metric:circuit_activity:circuit-furnace", "field": "max_w", "value": 5.0, "unit": "W", "at": None},
            {"claim_type": "equipment_function", "evidence_id": "metric:circuit_activity:circuit-furnace", "field": "active", "value": "not_observed", "unit": None, "at": None},
        ],
        "interpretation": "Indoor temperature is 68.0 F.",
        "hypotheses": [{"text": "The property may not be ready on arrival.", "supporting_ids": ["metric:indoor_trend"], "conflicting_ids": []}],
        "unknowns": ["Whether heating equipment is receiving power is not established."],
        "clarification": "Who should respond first if the temperature has not improved?",
        "follow_up": {"observation": "Take another indoor temperature reading.", "when": (at + timedelta(minutes=30)).isoformat()},
        "readiness": readiness,
        "limitations": ["Branch readings do not establish equipment supply."],
    })


def test_evidence_pack_6796_display_rounds_but_validation_uses_canonical_status():
    _, at, pack = _demo_pack_at_6796()
    assert pack["computed_readiness"] == "at_risk"
    assert pack["readiness"]["status"] == "at_risk"
    assert pack["readiness"]["policy_version"] == readiness_mod.READINESS_POLICY_VERSION
    assert pack["canonical_readiness"]["status"] == "at_risk"
    assert pack["canonical_readiness"]["inputs"]["gap"] == 67.96 - 68.0
    assert pack["metrics"]["target_gap"]["gap"] == 0.0
    assert math.copysign(1.0, pack["metrics"]["target_gap"]["gap"]) == 1.0
    assert validate(_model_json(pack, at, "at_risk"), pack) == []
    assert any("at_risk" in r for r in validate(_model_json(pack, at, "on_track"), pack))


def test_negative_zero_gap_displays_positive_zero_and_keeps_status():
    _, at, pack = _demo_pack_at_6796()
    gap = pack["metrics"]["target_gap"]["gap"]
    assert gap == 0.0 and math.copysign(1.0, gap) == 1.0
    assert pack["computed_readiness"] == "at_risk"


def test_validation_never_trusts_model_status_or_recomputes_from_rounded_pack():
    _, at, pack = _demo_pack_at_6796()
    pack["metrics"]["target_gap"]["gap"] = 0.0
    pack["metrics"]["indoor_trend"]["last_value"] = 68.0
    assert validate(_model_json(pack, at, "at_risk"), pack) == []
