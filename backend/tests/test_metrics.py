from datetime import datetime, timedelta
from pathlib import Path

from aria_home.app import create_app
from aria_home.contracts import EvidenceRecord
from aria_home.metrics import (
    NOISE_FLOOR_W,
    circuit_activity,
    target_gap,
    temperature_trend,
)
from aria_home.scenario import load_scenario

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "demo_v1"
ZONE = "demo-house/main"
T0 = datetime.fromisoformat("2026-01-16T15:00:00-05:00")


def _record(id, quantity, value, unit, observed, subject=ZONE, source="thermostat", kind="measurement", received=None, cadence=1800, binding=None):
    return EvidenceRecord(
        id=id,
        source=source,
        kind=kind,
        subject=subject,
        quantity=quantity,
        value=value,
        unit=unit,
        observed_at=observed,
        received_at=received or (observed + timedelta(seconds=20)),
        expected_cadence_s=cadence,
        mode="synthetic",
        provenance={"fixture_id": "test", "version": "1"},
        binding=binding,
    )


def _temp(id, value, unit, observed, **kwargs):
    return _record(id, "indoor_temp", value, unit, observed, **kwargs)


def _demo():
    scenario = load_scenario(SCENARIO_DIR)
    at = scenario.manifest.start + timedelta(hours=3)
    return scenario, at


def test_demo_flat_trend_at_default_time():
    scenario, at = _demo()
    trend = temperature_trend(scenario.records, ZONE, at - timedelta(hours=3), at, at)
    assert trend["sample_count"] == 7
    assert trend["missing_count"] == 1
    assert trend["unit"] == "F"
    assert trend["first_value"] == 52.0
    assert trend["last_value"] == 52.1
    assert abs(trend["change"]) <= 0.3
    assert abs(trend["rate_per_hour"]) <= 0.2
    assert trend["coverage"] > 0.5
    assert trend["sufficient"] is True


def test_rate_on_rising_series():
    records = [
        _temp("r1", 50.0, "F", T0),
        _temp("r2", 52.0, "F", T0 + timedelta(hours=1)),
        _temp("r3", 54.0, "F", T0 + timedelta(hours=2)),
    ]
    now = T0 + timedelta(hours=2, minutes=1)
    trend = temperature_trend(records, ZONE, T0, T0 + timedelta(hours=2), now)
    assert trend["change"] == 4.0
    assert trend["rate_per_hour"] == 2.0


def test_large_gap_reported_not_bridged():
    records = [
        _temp("g1", 60.0, "F", T0),
        _temp("g2", 60.0, "F", T0 + timedelta(seconds=1800)),
        _temp("g3", 60.0, "F", T0 + timedelta(seconds=1800 + 9000)),
    ]
    now = T0 + timedelta(seconds=1800 + 9000 + 60)
    trend = temperature_trend(records, ZONE, T0, now, now)
    assert trend["sample_count"] == 3
    assert trend["largest_gap_s"] == 9000
    assert trend["gaps_over_cadence"] == 1
    assert trend["coverage"] < 0.5
    assert trend["sufficient"] is False


def test_missing_values_skipped_and_counted():
    records = [
        _temp("m1", 50.0, "F", T0),
        _temp("m2", None, "F", T0 + timedelta(minutes=30)),
        _temp("m3", 52.0, "F", T0 + timedelta(hours=1)),
    ]
    now = T0 + timedelta(hours=1, minutes=1)
    trend = temperature_trend(records, ZONE, T0, T0 + timedelta(hours=1), now)
    assert trend["sample_count"] == 2
    assert trend["missing_count"] == 1
    assert trend["change"] == 2.0


def test_celsius_converted_to_fahrenheit():
    records = [
        _temp("c1", 0.0, "C", T0),
        _temp("c2", 32.0, "F", T0 + timedelta(hours=1)),
    ]
    now = T0 + timedelta(hours=1, minutes=1)
    trend = temperature_trend(records, ZONE, T0, T0 + timedelta(hours=1), now)
    assert trend["unit"] == "F"
    assert trend["unit_converted"] is True
    assert trend["last_value"] == 32.0
    assert trend["change"] == 0.0


def test_duplicate_ids_counted_once():
    records = [
        _temp("d1", 50.0, "F", T0),
        _temp("d1", 50.0, "F", T0),
        _temp("d2", 51.0, "F", T0 + timedelta(minutes=30)),
    ]
    now = T0 + timedelta(hours=1)
    trend = temperature_trend(records, ZONE, T0, T0 + timedelta(hours=1), now)
    assert trend["sample_count"] == 2


def test_setpoint_change_is_not_warming():
    records = [
        _temp("s1", 52.0, "F", T0),
        _record("sp1", "setpoint", 68.0, "F", T0, kind="device_report"),
        _temp("s2", 52.0, "F", T0 + timedelta(hours=1)),
        _record("sp2", "setpoint", 75.0, "F", T0 + timedelta(hours=1), kind="device_report"),
    ]
    now = T0 + timedelta(hours=1, minutes=1)
    trend = temperature_trend(records, ZONE, T0, T0 + timedelta(hours=1), now)
    assert trend["sample_count"] == 2
    assert trend["change"] == 0.0
    assert trend["rate_per_hour"] == 0.0


def test_target_gap_none_without_samples():
    records = [_temp("e1", 52.0, "F", T0 + timedelta(days=1))]
    trend = temperature_trend(records, ZONE, T0, T0 + timedelta(hours=3), T0 + timedelta(hours=3))
    assert trend["sample_count"] == 0
    assert target_gap(trend, 68.0, "F") is None


def test_furnace_inactive_others_active():
    scenario, at = _demo()
    start = at - timedelta(hours=3)
    furnace = circuit_activity(scenario.records, "circuit-furnace", start, at, at)
    kitchen = circuit_activity(scenario.records, "circuit-kitchen", start, at, at)
    living = circuit_activity(scenario.records, "circuit-living", start, at, at)
    bedroom = circuit_activity(scenario.records, "circuit-bedroom", start, at, at)
    assert furnace["active"] is False
    assert furnace["max_w"] <= NOISE_FLOOR_W
    assert furnace["binding"] == "confirmed"
    assert kitchen["active"] is True
    assert living["active"] is True
    assert bedroom["active"] is True
    assert bedroom["binding"] == "candidate"
    assert kitchen["binding"] == "unknown"


def test_circuit_meaning_text():
    scenario, at = _demo()
    activity = circuit_activity(scenario.records, "circuit-furnace", at - timedelta(hours=3), at, at)
    assert activity["meaning"] == "electrical activity only; not proof of useful heat"


def test_records_received_after_now_excluded():
    records = [
        _temp("n1", 52.0, "F", T0),
        _temp("n2", 99.0, "F", T0 + timedelta(hours=1), received=T0 + timedelta(hours=5)),
    ]
    trend = temperature_trend(records, ZONE, T0, T0 + timedelta(hours=2), T0 + timedelta(hours=2))
    assert trend["sample_count"] == 1
    assert trend["last_value"] == 52.0


def test_demo_future_records_excluded():
    scenario, at = _demo()
    trend = temperature_trend(scenario.records, ZONE, at - timedelta(hours=3), at, at)
    assert trend["last_observed_at"] == datetime.fromisoformat("2026-01-16T17:55:00-05:00")


def test_demo_furnace_coverage_discounts_large_gap():
    scenario, at = _demo()
    furnace = circuit_activity(scenario.records, "circuit-furnace", at - timedelta(hours=3), at, at)
    assert furnace["coverage"] < 0.6
    assert furnace["gaps_over_cadence"] == 1
    assert furnace["coverage_basis"] == "cadence"


def test_regular_series_coverage_near_one():
    records = [_temp(f"k{i}", 60.0, "F", T0 + timedelta(seconds=1800 * i)) for i in range(7)]
    end = T0 + timedelta(seconds=1800 * 6 + 60)
    trend = temperature_trend(records, ZONE, T0, end, end)
    assert abs(trend["coverage"] - 1.0) < 0.01
    assert trend["gaps_over_cadence"] == 0
    assert trend["coverage_basis"] == "cadence"


def test_single_sample_covers_one_cadence():
    end = T0 + timedelta(hours=3)
    trend = temperature_trend([_temp("s1", 60.0, "F", T0)], ZONE, T0, end, end)
    assert abs(trend["coverage"] - 1800 / 10800) < 1e-9
    assert trend["gaps_over_cadence"] == 0
    assert trend["sufficient"] is False


def test_no_cadence_records_report_no_cadence_basis():
    records = [
        _temp("n1", 60.0, "F", T0, cadence=None),
        _temp("n2", 61.0, "F", T0 + timedelta(hours=1), cadence=None),
    ]
    end = T0 + timedelta(hours=2)
    trend = temperature_trend(records, ZONE, T0, end, end)
    assert trend["coverage"] == 0.0
    assert trend["coverage_basis"] == "no_cadence"


def test_metrics_endpoint():
    app = create_app()
    client = app.test_client()
    response = client.get("/api/metrics?scenario=demo_v1&at=2026-01-16T18:00:00-05:00")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data_mode"] == "synthetic"
    assert payload["computed_by"] == "deterministic code"
    assert payload["indoor_trend"]["sample_count"] == 7
    assert payload["target_gap"]["gap"] == payload["indoor_trend"]["last_value"] - 68.0
    assert set(payload["circuits"]) == {"circuit-bedroom", "circuit-furnace", "circuit-kitchen", "circuit-living"}
    assert payload["circuits"]["circuit-furnace"]["active"] is False
    assert payload["circuits"]["circuit-kitchen"]["active"] is True
