from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from aria_home.clock import ScenarioClock
from aria_home.contracts import Availability, CircuitBinding
from aria_home.evidence import freshness, source_status

BASE = datetime(2026, 1, 16, 20, 0, tzinfo=timezone.utc)


def test_observed_after_received_rejected(make_record):
    with pytest.raises(ValidationError, match="observed_at must not be after received_at"):
        make_record(received_at=BASE - timedelta(seconds=1))


def test_bad_unit_rejected(make_record):
    with pytest.raises(ValidationError):
        make_record(unit="W")
    with pytest.raises(ValidationError):
        make_record(quantity="circuit_power", unit="F", value=10.0)


def test_forecast_must_have_forecast_kind(make_record):
    with pytest.raises(ValidationError):
        make_record(source="weather", quantity="outdoor_temp_forecast", kind="measurement")


def test_extra_fields_forbidden(make_record):
    with pytest.raises(ValidationError):
        make_record(unexpected="nope")


def test_missing_value_stays_none_and_yields_missing(make_record):
    record = make_record(value=None)
    assert record.value is None
    assert record.value != 0
    assert freshness(record, BASE) is Availability.missing


def test_freshness_flips_to_stale_as_clock_advances(make_record):
    record = make_record(expected_cadence_s=600)
    clock = ScenarioClock(BASE, timedelta(minutes=10))
    assert freshness(record, clock.now()) is Availability.available
    clock.advance()
    clock.advance()
    assert freshness(record, clock.now()) is Availability.available
    clock.advance()
    assert freshness(record, clock.now()) is Availability.stale


def test_no_cadence_never_auto_stale(make_record):
    record = make_record(expected_cadence_s=None)
    assert freshness(record, BASE + timedelta(days=30)) is Availability.available


def test_future_record_is_invalid(make_record):
    record = make_record(
        observed_at=BASE + timedelta(minutes=5), received_at=BASE + timedelta(minutes=5)
    )
    assert freshness(record, BASE) is Availability.invalid


def test_future_within_skew_is_not_invalid(make_record):
    record = make_record(
        observed_at=BASE + timedelta(seconds=30), received_at=BASE + timedelta(seconds=30)
    )
    assert freshness(record, BASE) is Availability.available


def test_duplicate_ids_deduplicated(make_record):
    status = source_status("thermostat", [make_record(), make_record()], BASE)
    assert status.record_count == 1
    assert status.availability is Availability.available


def test_conflicting_values_detected(make_record):
    a = make_record(id="a", value=52.0)
    b = make_record(id="b", value=53.0)
    status = source_status("thermostat", [a, b], BASE)
    assert status.availability is Availability.conflicting
    assert status.record_count == 2
    assert any("conflicting" in n for n in status.notes)


def test_empty_source_is_missing(make_record):
    status = source_status("weather", [], BASE)
    assert status.availability is Availability.missing
    assert status.record_count == 0
    assert status.newest_observed_at is None
    assert status.age_s is None


def test_only_confirmed_binding_supports_equipment_statement():
    assert CircuitBinding(circuit_id="c1", equipment="furnace", status="confirmed", confirmed_by="homeowner").can_support_equipment_statement()
    assert not CircuitBinding(circuit_id="c2", equipment="furnace", status="candidate").can_support_equipment_statement()
    assert not CircuitBinding(circuit_id="c3", status="unknown").can_support_equipment_statement()
