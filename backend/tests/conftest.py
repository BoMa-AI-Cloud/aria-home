from datetime import datetime, timezone

import pytest

from aria_home.contracts import EvidenceRecord

BASE = datetime(2026, 1, 16, 20, 0, tzinfo=timezone.utc)


@pytest.fixture
def make_record():
    def _make(**overrides):
        data = {
            "id": "rec-1",
            "source": "thermostat",
            "kind": "measurement",
            "subject": "demo-house/main",
            "quantity": "indoor_temp",
            "value": 52.0,
            "unit": "F",
            "observed_at": BASE,
            "received_at": BASE,
            "expected_cadence_s": 600,
            "mode": "synthetic",
            "provenance": {"fixture_id": "demo_v1", "version": "1"},
        }
        data.update(overrides)
        return EvidenceRecord.model_validate(data)

    return _make
