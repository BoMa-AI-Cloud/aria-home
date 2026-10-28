import math
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DataMode(str, Enum):
    synthetic = "synthetic"
    replay = "replay"
    live = "live"


class SourceKind(str, Enum):
    calendar = "calendar"
    thermostat = "thermostat"
    electrical = "electrical"
    weather = "weather"
    room_sensor = "room_sensor"


class EvidenceKind(str, Enum):
    measurement = "measurement"
    device_report = "device_report"
    forecast = "forecast"
    human_statement = "human_statement"
    derived = "derived"


class Availability(str, Enum):
    available = "available"
    missing = "missing"
    stale = "stale"
    invalid = "invalid"
    conflicting = "conflicting"


class BindingStatus(str, Enum):
    confirmed = "confirmed"
    candidate = "candidate"
    unknown = "unknown"


class NotificationState(str, Enum):
    """Notification lifecycle.

    Acknowledgement means a human or system acknowledged receipt; it is not
    resolution of the underlying home issue.
    """

    created = "created"
    attempted = "attempted"
    provider_accepted = "provider_accepted"
    delivered = "delivered"
    acknowledged = "acknowledged"
    failed = "failed"


def _require_aware(value):
    if isinstance(value, datetime) and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("datetime must be timezone-aware")
    return value


QUANTITY_UNITS: dict[str, set[str | None]] = {
    "indoor_temp": {"F", "C"},
    "outdoor_temp": {"F", "C"},
    "outdoor_temp_forecast": {"F", "C"},
    "setpoint": {"F", "C"},
    "target_temp": {"F", "C"},
    "circuit_power": {"W"},
    "hvac_reported_state": {None},
}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Provenance(_Strict):
    fixture_id: str = Field(min_length=1)
    version: str = Field(min_length=1)


class CircuitBinding(_Strict):
    circuit_id: str = Field(min_length=1)
    equipment: str | None = None
    status: BindingStatus = BindingStatus.unknown
    confirmed_by: str | None = None

    def can_support_equipment_statement(self) -> bool:
        return self.status is BindingStatus.confirmed

    supports_equipment_statement = property(can_support_equipment_statement)


class EvidenceRecord(_Strict):
    id: str = Field(min_length=1)
    source: SourceKind
    kind: EvidenceKind
    subject: str = Field(min_length=1)
    quantity: str = Field(min_length=1)
    value: float | str | None = None
    unit: str | None = None
    observed_at: datetime
    received_at: datetime
    expected_cadence_s: int | None = Field(default=None, gt=0)
    mode: DataMode
    provenance: Provenance
    binding: CircuitBinding | None = None
    meter_id: str | None = None

    @field_validator("observed_at", "received_at")
    @classmethod
    def _aware(cls, value):
        return _require_aware(value)

    @model_validator(mode="after")
    def _validate_record(self):
        if isinstance(self.value, (int, float)) and not isinstance(self.value, bool) and not math.isfinite(float(self.value)):
            raise ValueError("value must be finite")
        if self.observed_at > self.received_at:
            raise ValueError("observed_at must not be after received_at")
        allowed = QUANTITY_UNITS.get(self.quantity)
        if allowed is not None and self.unit not in allowed:
            raise ValueError(
                f"unit {self.unit!r} is not allowed for quantity {self.quantity!r}; "
                f"allowed: {sorted(str(u) for u in allowed)}"
            )
        if "forecast" in self.quantity and self.kind is not EvidenceKind.forecast:
            raise ValueError("forecast quantities must have kind=forecast")
        return self


class Trip(_Strict):
    id: str = Field(min_length=1)
    property_id: str = Field(min_length=1)
    title: str
    planned_arrival: datetime
    revision: int = Field(default=1, ge=0)
    cancelled: bool = False
    known_at: datetime | None = None
    revision_id: str | None = None
    target_temp: float | None = None
    target_unit: str | None = None

    @field_validator("planned_arrival", "known_at")
    @classmethod
    def _aware(cls, value):
        return _require_aware(value)

    @field_validator("target_temp")
    @classmethod
    def _finite_target(cls, value):
        if value is not None and not math.isfinite(float(value)):
            raise ValueError("target_temp must be finite")
        return value

    @field_validator("target_unit")
    @classmethod
    def _unit(cls, value):
        if value is not None and value not in {"F", "C"}:
            raise ValueError("target_unit must be 'F' or 'C'")
        return value


class HomeownerConfirmation(_Strict):
    trip_id: str = Field(min_length=1)
    property_id: str = Field(min_length=1)
    target_temp: float
    target_unit: str
    notify_homeowner: bool
    manager_authorized: bool
    confirmed_at: datetime
    revision_id: str | None = None
    trip_revision: int | None = Field(default=None, ge=0)
    trip_revision_id: str | None = None

    @property
    def confirmed_revision_id(self):
        return self.revision_id or self.trip_revision_id

    @field_validator("target_temp")
    @classmethod
    def _finite_target(cls, value):
        if not math.isfinite(float(value)):
            raise ValueError("target_temp must be finite")
        return value

    @field_validator("target_unit")
    @classmethod
    def _unit(cls, value):
        if value not in {"F", "C"}:
            raise ValueError("target_unit must be 'F' or 'C'")
        return value

    @field_validator("confirmed_at")
    @classmethod
    def _aware(cls, value):
        return _require_aware(value)


class SourceStatus(_Strict):
    source: SourceKind
    availability: Availability
    record_count: int = Field(ge=0)
    newest_observed_at: datetime | None = None
    age_s: float | None = None
    mode: DataMode
    notes: list[str] = Field(default_factory=list)
    missing_count: int = Field(default=0, ge=0)
    stale_count: int = Field(default=0, ge=0)

    @field_validator("newest_observed_at")
    @classmethod
    def _aware(cls, value):
        return _require_aware(value)
