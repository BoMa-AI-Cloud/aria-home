from datetime import date
from pathlib import Path

from aria_home.scenario import load_scenario

SCENARIOS = Path(__file__).resolve().parent.parent / "scenarios"
CUTOFF = "2026-01-16T18:00:00-05:00"


def _indoor_after(scenario, cutoff=CUTOFF):
    readings = [
        r
        for r in scenario.records
        if r.quantity == "indoor_temp"
        and r.value is not None
        and r.observed_at.isoformat() > cutoff
    ]
    return sorted(readings, key=lambda r: r.observed_at)


def test_recovery_warms_to_target():
    scenario = load_scenario(SCENARIOS / "demo_recovery_v1")
    assert scenario.manifest.id == "demo_recovery_v1"
    assert scenario.manifest.created == date(2026, 10, 26)
    assert all(r.mode.value == "synthetic" for r in scenario.records)
    readings = _indoor_after(scenario)
    assert len(readings) == 10
    assert readings[-1].value == 68.4


def test_no_followup_has_nothing_after_18():
    scenario = load_scenario(SCENARIOS / "demo_no_followup_v1")
    assert scenario.manifest.id == "demo_no_followup_v1"
    assert scenario.manifest.created == date(2026, 10, 26)
    assert all(r.mode.value == "synthetic" for r in scenario.records)
    assert _indoor_after(scenario) == []
