import copy
import json
from datetime import timedelta
from pathlib import Path

from aria_home.app import create_app
from aria_home.investigator import build_evidence_pack, investigate, validate
from aria_home.provider import ProviderResult
from aria_home.readiness import compute_readiness
from aria_home.scenario import load_scenario

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "demo_v1"


def _scenario():
    return load_scenario(SCENARIO_DIR)


def _at(scenario):
    return scenario.manifest.start + timedelta(hours=3)


def _pack():
    scenario = _scenario()
    at = _at(scenario)
    return scenario, at, build_evidence_pack(scenario, at)


def _valid_json(at, readiness="at_risk"):
    return json.dumps({
        "facts": [
            {"claim_type": "current_temperature", "evidence_id": "metric:indoor_trend", "field": "last_value", "value": 52.1, "unit": "F", "at": "2026-01-16T17:55:00-05:00"},
            {"claim_type": "target_temperature", "evidence_id": "metric:target_gap", "field": "target_temp", "value": 68.0, "unit": "F", "at": "2026-01-16T17:55:00-05:00"},
            {"claim_type": "target_gap", "evidence_id": "metric:target_gap", "field": "gap", "value": -15.9, "unit": "F", "at": "2026-01-16T17:55:00-05:00"},
            {"claim_type": "electrical_activity", "evidence_id": "metric:circuit_activity:circuit-furnace", "field": "max_w", "value": 5.0, "unit": "W", "at": "2026-01-16T17:55:00-05:00"},
            {"claim_type": "equipment_function", "evidence_id": "metric:circuit_activity:circuit-furnace", "field": "active", "value": "not_observed", "unit": None, "at": "2026-01-16T17:55:00-05:00"},
        ],
        "interpretation": "Indoor temperature is 52.1 F and 15.9 F below target.",
        "hypotheses": [{"text": "The property may not be ready on arrival.", "supporting_ids": ["metric:indoor_trend"], "conflicting_ids": []}],
        "unknowns": ["Whether heating equipment is receiving power is not established."],
        "clarification": "Who should respond first if the temperature has not improved?",
        "follow_up": {"observation": "Take another indoor temperature reading.", "when": (at + timedelta(minutes=30)).isoformat()},
        "readiness": readiness,
        "limitations": ["Branch readings do not establish equipment supply."],
    })


class FakeProvider:
    mode = "mock"
    model_id = "fake-model"

    def __init__(self, text):
        self._text = text
        self.calls = []

    def generate(self, prompt=None, *, messages=None, max_tokens=None):
        self.calls.append((prompt, messages, max_tokens))
        return ProviderResult(ok=True, mode="mock", requested_model=self.model_id, answered_model=self.model_id, text=self._text, latency_ms=1.0, input_tokens=10, output_tokens=20)


def test_demo_v1_at_1800_is_at_risk():
    _, at, pack = _pack()
    assert at.isoformat() == "2026-01-16T18:00:00-05:00"
    result = compute_readiness(pack, at)
    assert result["status"] == "at_risk"
    assert result.status == "at_risk"
    assert any("not a guaranteed prediction" in r for r in result["reasons"])
    assert result["inputs"]["gap"] == -15.9
    assert pack["readiness"]["status"] == "at_risk"
    assert pack["computed_readiness"] == "at_risk"


def test_demo_v1_model_on_track_rejected():
    scenario, at, pack = _pack()
    data = _valid_json(at, readiness="on_track")
    reasons = validate(data, pack)
    assert any("on_track" in r and "at_risk" in r for r in reasons)
    result = investigate(scenario, at, FakeProvider(data))
    assert result.status == "rejected"
    assert result.output is None
    assert result.summary["computed_readiness"] == "at_risk"
    assert result.summary["readiness"]["status"] == "at_risk"


def test_slightly_positive_slope_alone_never_on_track():
    _, at, pack = _pack()
    assert compute_readiness(pack, at)["status"] == "at_risk"
    small = copy.deepcopy(pack)
    small["metrics"]["target_gap"].update({"gap": -1.0, "latest_value": 67.0})
    small["metrics"]["indoor_trend"].update({"last_value": 67.0, "rate_per_hour": 0.2, "change": 0.1})
    assert compute_readiness(small, at)["status"] == "at_risk"
    short = copy.deepcopy(small)
    short["metrics"]["indoor_trend"].update({"rate_per_hour": 2.0, "change": 0.5, "first_observed_at": "2026-01-16T17:30:00-05:00"})
    assert compute_readiness(short, at)["status"] == "at_risk"


def test_missing_stale_conflicting_too_few_and_low_coverage_cannot_tell():
    _, at, pack = _pack()

    missing = copy.deepcopy(pack)
    missing["metrics"]["indoor_trend"]["last_value"] = None
    assert compute_readiness(missing, at)["status"] == "cannot_tell"

    for availability in ("stale", "conflicting", "missing"):
        tweaked = copy.deepcopy(pack)
        for status in tweaked["source_statuses"]:
            if status["source"] == "thermostat":
                status["availability"] = availability
        assert compute_readiness(tweaked, at)["status"] == "cannot_tell", availability

    stale_age = copy.deepcopy(pack)
    stale_age["metrics"]["indoor_trend"]["last_observed_at"] = "2026-01-16T16:00:00-05:00"
    stale_age["metrics"]["target_gap"]["latest_observed_at"] = "2026-01-16T16:00:00-05:00"
    assert compute_readiness(stale_age, at)["status"] == "cannot_tell"

    few = copy.deepcopy(pack)
    few["metrics"]["indoor_trend"]["sample_count"] = 2
    assert compute_readiness(few, at)["status"] == "cannot_tell"

    low_coverage = copy.deepcopy(pack)
    low_coverage["metrics"]["indoor_trend"]["coverage"] = 0.2
    assert compute_readiness(low_coverage, at)["status"] == "cannot_tell"


def test_reading_at_target_on_track():
    _, at, pack = _pack()
    at_target = copy.deepcopy(pack)
    at_target["metrics"]["target_gap"].update({"gap": 0.0, "latest_value": 68.0})
    at_target["metrics"]["indoor_trend"]["last_value"] = 68.0
    assert compute_readiness(at_target, at)["status"] == "on_track"


def test_sustained_warming_small_gap_projected_on_track():
    _, at, pack = _pack()
    warming = copy.deepcopy(pack)
    warming["trip"]["planned_arrival"] = (at + timedelta(hours=2)).isoformat()
    warming["metrics"]["target_gap"].update({"gap": -1.0, "latest_value": 67.0})
    warming["metrics"]["indoor_trend"].update({"last_value": 67.0, "first_value": 65.5, "change": 1.5, "rate_per_hour": 0.75})
    assert compute_readiness(warming, at)["status"] == "on_track"


def test_cancelled_unconfirmed_outdated_mismatched_flags_cannot_tell():
    _, at, pack = _pack()
    for flags in ({"trip_cancelled": True}, {"cancelled": True}, {"trip_unconfirmed": True}, {"unconfirmed": True}, {"confirmation_outdated": True}, {"outdated": True}, {"trip_mismatched": True}, {"mismatched": True}):
        assert compute_readiness(pack, at, flags=flags)["status"] == "cannot_tell", flags
    cancelled = copy.deepcopy(pack)
    cancelled["trip"]["cancelled"] = True
    assert compute_readiness(cancelled, at)["status"] == "cannot_tell"
    no_confirmation = copy.deepcopy(pack)
    no_confirmation["confirmation"] = None
    del no_confirmation["metrics"]["target_gap"]
    assert compute_readiness(no_confirmation, at)["status"] == "cannot_tell"


def test_post_investigations_returns_computed_status(monkeypatch, tmp_path):
    monkeypatch.setenv("ARIA_HOME_DB_PATH", str(tmp_path / "readiness.db"))
    monkeypatch.delenv("ARIA_HOME_MODEL_ENABLED", raising=False)
    client = create_app().test_client()
    resp = client.post("/api/investigations?scenario=demo_v1&at=2026-01-16T18:00:00-05:00")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["computed_readiness"] == "at_risk"
    assert payload["readiness"]["status"] == "at_risk"
    assert payload["investigation"]["computed_readiness"] == "at_risk"
    assert payload["investigation"]["output"]["readiness"] == "at_risk"
    assert payload["investigation"]["summary"]["computed_readiness"] == "at_risk"
