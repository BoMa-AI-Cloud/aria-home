from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from aria_home.clock import FixedClock, ScenarioClock
from aria_home.contracts import EvidenceRecord

UTC = timezone.utc


def test_fixed_clock_returns_aware_time():
    at = datetime(2026, 1, 16, 20, 0, tzinfo=UTC)
    assert FixedClock(at).now() == at


def test_naive_datetimes_rejected():
    naive = datetime(2026, 1, 16, 20, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        FixedClock(naive)
    with pytest.raises(ValueError, match="timezone-aware"):
        ScenarioClock(naive, timedelta(minutes=5))
    with pytest.raises(ValidationError):
        EvidenceRecord.model_validate(
            {
                "id": "r1",
                "source": "thermostat",
                "kind": "measurement",
                "subject": "demo-house/main",
                "quantity": "indoor_temp",
                "value": 52.0,
                "unit": "F",
                "observed_at": naive,
                "received_at": naive,
                "expected_cadence_s": 600,
                "mode": "synthetic",
                "provenance": {"fixture_id": "demo_v1", "version": "1"},
            }
        )


def test_scenario_clock_advances_explicitly():
    clock = ScenarioClock(datetime(2026, 1, 16, 20, 0, tzinfo=UTC), timedelta(minutes=30))
    assert clock.now() == datetime(2026, 1, 16, 20, 0, tzinfo=UTC)
    assert clock.advance() == datetime(2026, 1, 16, 20, 30, tzinfo=UTC)
    assert clock.advance_by(timedelta(hours=1)) == datetime(2026, 1, 16, 21, 30, tzinfo=UTC)
