from datetime import datetime, timedelta
from pathlib import Path

from aria_home.app import create_app
from aria_home.contracts import EvidenceRecord
from aria_home.power_context import BANNED_PHRASES, power_context
from aria_home.scenario import load_scenario, visible_records

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "demo_v1"
T0 = datetime.fromisoformat("2026-01-16T15:00:00-05:00")
NOW = T0 + timedelta(hours=3)
EXACT = (
    "Fresh activity is observed on other monitored circuits. "
    "This weighs against complete property power loss during this window, "
    "but does not independently confirm power to the heating equipment."
)


def _rec(id, circuit, value, observed, binding_status="unknown", equipment=None, cadence=1800, fixture="meter-1", received=None, quantity="circuit_power", kind="measurement", unit="W", meter_id="meter-1"):
    binding = {"circuit_id": circuit, "equipment": equipment, "status": binding_status, "confirmed_by": "homeowner" if binding_status == "confirmed" else None}
    return EvidenceRecord(
        id=id,
        source="electrical",
        kind=kind,
        subject=circuit,
        quantity=quantity,
        value=value,
        unit=unit,
        observed_at=observed,
        received_at=received or (observed + timedelta(seconds=15)),
        expected_cadence_s=cadence,
        mode="synthetic",
        provenance={"fixture_id": fixture, "version": "1"},
        binding=binding,
        meter_id=meter_id,
    )


def _fresh(circuit, value, **kw):
    return _rec(f"{circuit}-fresh", circuit, value, NOW - timedelta(minutes=5), **kw)


def _assert_no_banned(result):
    text = " ".join([result.statement, *result.limitations]).lower()
    for phrase in BANNED_PHRASES:
        assert phrase.lower() not in text


def test_p1_demo():
    scenario = load_scenario(SCENARIO_DIR)
    at = scenario.manifest.start + timedelta(hours=3)
    result = power_context(visible_records(scenario.records, at), at - timedelta(hours=3), at, 15.0)
    by_id = {c.circuit_id: c for c in result.per_circuit}
    assert by_id["circuit-furnace"].status.value == "fresh_quiet"
    assert by_id["circuit-furnace"].binding.value == "confirmed"
    assert all(by_id[c].status.value == "fresh_active" for c in ("circuit-kitchen", "circuit-living", "circuit-bedroom"))
    assert result.heating_binding.value == "confirmed"
    assert result.continuity.value == "activity_weighs_against_total_loss"
    assert result.statement == EXACT
    assert result.mains.value == "not_available"
    assert result.lineage.lineage_count == 1
    assert result.lineage.meter_ids == ["demo-house-meter-1"]
    assert "Cannot exclude a lost service leg." in result.limitations
    assert "Breaker or equipment supply problems are not observable from branch readings." in result.limitations
    assert "Interruptions outside this window are not covered." in result.limitations
    assert "Backup-power configuration unknown." in result.limitations
    _assert_no_banned(result)


def test_p2_all_readings_stop_visibility_lost():
    old = NOW - timedelta(hours=2)
    records = [
        _rec("a", "circuit-furnace", 0, old, binding_status="confirmed", equipment="furnace"),
        _rec("b", "circuit-kitchen", 0, old),
        _rec("c", "circuit-living", None, old),
    ]
    result = power_context(records, T0, NOW, 15.0)
    assert result.continuity.value == "visibility_lost"
    _assert_no_banned(result)


def test_p3_fresh_zero_everywhere_insufficient():
    records = [
        _fresh("circuit-furnace", 0, binding_status="confirmed", equipment="furnace"),
        _fresh("circuit-kitchen", 0),
        _fresh("circuit-living", 0),
    ]
    result = power_context(records, T0, NOW, 15.0)
    assert all(c.status.value == "fresh_quiet" for c in result.per_circuit)
    assert result.mains.value == "not_available"
    assert result.continuity.value == "insufficient_evidence"
    _assert_no_banned(result)


def test_p5_backup_unknown_and_known_present():
    records = [
        _fresh("circuit-furnace", 3, binding_status="confirmed", equipment="furnace"),
        _fresh("circuit-kitchen", 450),
    ]
    unknown = power_context(records, T0, NOW, 15.0, backup="unknown")
    assert unknown.backup.value == "unknown"
    assert "Backup-power configuration unknown." in unknown.limitations
    present = power_context(records, T0, NOW, 15.0, backup="known_present")
    assert present.backup.value == "known_present"
    assert "Backup-power configuration unknown." not in present.limitations
    assert "backup" in present.statement.lower()
    assert "may be supplying power" in present.statement.lower()
    _assert_no_banned(unknown)
    _assert_no_banned(present)


def test_p6_stale_duplicate_conflicting_future():
    records = [
        _rec("stale-1", "circuit-stale", 100, NOW - timedelta(hours=2)),
        _rec("dup-1", "circuit-dup", 100, NOW - timedelta(minutes=5)),
        _rec("dup-1", "circuit-dup", 100, NOW - timedelta(minutes=5)),
        _rec("conf-1", "circuit-conf", 100, NOW - timedelta(minutes=5)),
        _rec("conf-2", "circuit-conf", 200, NOW - timedelta(minutes=5)),
        _rec("future-1", "circuit-future", 100, NOW + timedelta(hours=1), received=NOW + timedelta(hours=1, seconds=15)),
    ]
    result = power_context(records, T0, NOW, 15.0)
    by_id = {c.circuit_id: c for c in result.per_circuit}
    assert by_id["circuit-stale"].status.value == "stale"
    assert by_id["circuit-dup"].status.value == "fresh_active"
    assert result.lineage.counts_by_status.get("fresh_active") == 1
    assert by_id["circuit-conf"].status.value == "conflicting"
    assert by_id["circuit-future"].status.value == "invalid"
    _assert_no_banned(result)


def test_p8_candidate_binding_no_heating_wording():
    records = [
        _fresh("circuit-furnace", 3, binding_status="candidate", equipment="furnace"),
        _fresh("circuit-kitchen", 450),
    ]
    result = power_context(records, T0, NOW, 15.0)
    assert result.heating_binding.value == "candidate_only"
    assert "heating" not in result.statement.lower()
    assert "furnace" not in result.statement.lower()
    _assert_no_banned(result)


def test_p9_eight_channels_one_meter_one_lineage():
    records = [_fresh(f"circuit-{i}", 100 + i) for i in range(8)]
    result = power_context(records, T0, NOW, 15.0)
    assert result.lineage.lineage_count == 1
    assert result.lineage.meter_ids == ["meter-1"]
    assert result.lineage.counts_by_status == {"fresh_active": 8}
    assert "8 confirmations" not in result.statement
    assert "confirmation" not in result.statement.lower()
    _assert_no_banned(result)


def test_unknown_meter_lineage():
    records = [
        _rec("u1", "circuit-kitchen", 450, NOW - timedelta(minutes=5), meter_id=None),
        _rec("u2", "circuit-living", 120, NOW - timedelta(minutes=5), meter_id=None),
    ]
    result = power_context(records, T0, NOW, 15.0)
    assert result.lineage.meter_ids == ["unknown-meter"]
    assert result.lineage.lineage_count == 1
    assert "Meter identity unknown for some circuits; they are treated as one source." in result.limitations
    _assert_no_banned(result)


def test_missing_and_endpoint():
    records = [_fresh("circuit-kitchen", None)]
    result = power_context(records, T0, NOW, 15.0)
    assert result.per_circuit[0].status.value == "missing"
    _assert_no_banned(result)

    client = create_app().test_client()
    response = client.get("/api/power-context?scenario=demo_v1")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data_mode"] == "synthetic"
    assert payload["computed_by"] == "deterministic code"
    assert payload["statement"] == EXACT
    assert payload["continuity"] == "activity_weighs_against_total_loss"
    assert payload["mains"] == "not_available"
