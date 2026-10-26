from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .contracts import EvidenceKind


class OutcomeStatus(str, Enum):
    target_reached = "target_reached"
    warming_observed = "warming_observed"
    awaiting_measurement = "awaiting_measurement"
    not_observed_by_deadline = "not_observed_by_deadline"
    unable_to_verify = "unable_to_verify"


def _require_aware(value):
    if isinstance(value, datetime) and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("datetime must be timezone-aware")
    return value


class FollowUp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    investigation_id: str = Field(min_length=1)
    created_at: datetime
    target_temp: float
    target_unit: str
    deadline: datetime
    min_samples: int = Field(default=3, ge=1)
    min_rise_f: float = 2.0
    zone: str = "demo-cabin/main"

    @field_validator("created_at", "deadline")
    @classmethod
    def _aware(cls, value):
        return _require_aware(value)

    @field_validator("target_unit")
    @classmethod
    def _unit(cls, value):
        if value not in {"F", "C"}:
            raise ValueError("target_unit must be 'F' or 'C'")
        return value


class OutcomeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OutcomeStatus
    supporting_ids: list[str] = Field(default_factory=list)
    sample_count: int = Field(ge=0)
    first_value: float | None = None
    last_value: float | None = None
    note: str | None = None
    evaluated_at: datetime

    @field_validator("evaluated_at")
    @classmethod
    def _aware(cls, value):
        return _require_aware(value)


def follow_up_for(scenario, investigation_id, created_at) -> FollowUp:
    _require_aware(created_at)
    if scenario.confirmation is None:
        raise ValueError("scenario has no homeowner confirmation")
    if scenario.trip is None:
        raise ValueError("scenario has no trip")
    return FollowUp(
        investigation_id=investigation_id,
        created_at=created_at,
        target_temp=scenario.confirmation.target_temp,
        target_unit=scenario.confirmation.target_unit,
        deadline=scenario.trip.planned_arrival + timedelta(hours=2),
    )


def _to_fahrenheit(value: float, unit: str | None, fallback_unit: str) -> float:
    effective = unit or fallback_unit
    if effective == "C":
        return value * 9.0 / 5.0 + 32.0
    return value


def _in_target_unit(record, target_unit: str) -> float:
    value = float(record.value)
    if record.unit == target_unit or record.unit is None:
        return value
    if record.unit == "C" and target_unit == "F":
        return value * 9.0 / 5.0 + 32.0
    if record.unit == "F" and target_unit == "C":
        return (value - 32.0) * 5.0 / 9.0
    return value


def evaluate_outcome(followup: FollowUp, records, now: datetime) -> OutcomeResult:
    _require_aware(now)
    readings = [
        r
        for r in records
        if r.quantity == "indoor_temp"
        and r.subject == followup.zone
        and r.value is not None
        and r.received_at <= now
        and r.observed_at > followup.created_at
    ]
    readings.sort(key=lambda r: (r.observed_at, r.received_at, r.id))

    sample_count = len(readings)
    first_value = float(readings[0].value) if readings else None
    last_value = float(readings[-1].value) if readings else None

    rise_f = None
    if readings:
        rise_f = _to_fahrenheit(float(readings[-1].value), readings[-1].unit, followup.target_unit) - _to_fahrenheit(
            float(readings[0].value), readings[0].unit, followup.target_unit
        )

    if sample_count >= 2 and all(
        _in_target_unit(r, followup.target_unit) >= followup.target_temp for r in readings[-2:]
    ):
        status = OutcomeStatus.target_reached
    elif sample_count >= followup.min_samples and rise_f is not None and rise_f >= followup.min_rise_f:
        status = OutcomeStatus.warming_observed
    elif now < followup.deadline:
        status = OutcomeStatus.awaiting_measurement
    elif sample_count >= followup.min_samples:
        status = OutcomeStatus.not_observed_by_deadline
    else:
        status = OutcomeStatus.unable_to_verify

    note = None
    if status in (OutcomeStatus.warming_observed, OutcomeStatus.target_reached):
        has_statement = any(
            r.kind == EvidenceKind.human_statement
            and r.received_at <= now
            and r.observed_at > followup.created_at
            for r in records
        )
        if has_statement:
            note = "An observed change after a reported action does not prove what caused it."

    return OutcomeResult(
        status=status,
        supporting_ids=[r.id for r in readings],
        sample_count=sample_count,
        first_value=first_value,
        last_value=last_value,
        note=note,
        evaluated_at=now,
    )
