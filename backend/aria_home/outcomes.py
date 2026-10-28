import math
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .contracts import EvidenceKind
from .eligibility import indoor_records
from .scheduling import compute_follow_up_schedule, validate_follow_up_time

__all__ = ["OutcomeStatus", "FollowUp", "OutcomeResult", "follow_up_for", "evaluate_outcome", "compute_follow_up_schedule", "validate_follow_up_time"]


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
    zone: str = "demo-house/main"
    next_check_at: datetime | None = None
    schedule_status: str = "scheduled"
    deadline_passed: bool = False
    cadence_s: float | None = None

    @property
    def when(self):
        return self.next_check_at

    @property
    def scheduled_at(self):
        return self.next_check_at

    @field_validator("target_temp", "min_rise_f", "cadence_s")
    @classmethod
    def _finite(cls, value):
        if value is not None and not math.isfinite(float(value)):
            raise ValueError("numeric follow-up fields must be finite")
        return value

    @field_validator("created_at", "deadline", "next_check_at")
    @classmethod
    def _aware(cls, value):
        return _require_aware(value)

    @model_validator(mode="after")
    def _schedule(self):
        if self.deadline <= self.created_at:
            raise ValueError("deadline_passed: deadline must be after created_at")
        if self.next_check_at is not None:
            reasons = validate_follow_up_time(self.next_check_at, self.created_at, self.deadline)
            if reasons:
                raise ValueError("; ".join(reasons))
            self.schedule_status = "scheduled"
            self.deadline_passed = False
        else:
            schedule = compute_follow_up_schedule(self.created_at, deadline=self.deadline, cadence_s=self.cadence_s)
            self.next_check_at = schedule["next_check_at"]
            self.schedule_status = schedule["status"]
            self.deadline_passed = schedule["deadline_passed"]
        return self

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


def follow_up_for(scenario, investigation_id, created_at, cadence_s=None) -> FollowUp:
    _require_aware(created_at)
    from .scenario import context_as_of

    ctx = context_as_of(scenario, created_at)
    if ctx.trip is None:
        raise ValueError("trip_unconfirmed: scenario has no trip visible at created_at")
    if ctx.flags.get("trip_cancelled"):
        raise ValueError("trip_cancelled: scenario trip is cancelled")
    if ctx.flags.get("confirmation_outdated"):
        raise ValueError("confirmation_outdated: scenario confirmation is outdated for the current trip revision")
    if ctx.flags.get("trip_mismatched"):
        raise ValueError("trip_mismatched: scenario confirmation does not match the trip visible at created_at")
    if ctx.confirmation is None:
        raise ValueError("trip_unconfirmed: scenario has no homeowner confirmation visible at created_at")
    deadline = ctx.trip.planned_arrival + timedelta(hours=2)
    if deadline <= created_at:
        raise ValueError("deadline_passed: follow-up deadline has passed")
    if cadence_s is None:
        for record in getattr(scenario, "records", []) or []:
            if record.quantity == "indoor_temp" and record.expected_cadence_s is not None:
                cadence_s = record.expected_cadence_s
                break
    return FollowUp(
        investigation_id=investigation_id,
        created_at=created_at,
        target_temp=ctx.confirmation.target_temp,
        target_unit=ctx.confirmation.target_unit,
        deadline=deadline,
        cadence_s=cadence_s,
    )


def _to_fahrenheit(value: float, unit: str | None, fallback_unit: str) -> float:
    effective = unit or fallback_unit
    if effective == "C":
        result = value * 9.0 / 5.0 + 32.0
        return result if math.isfinite(result) else math.nan
    return value if math.isfinite(value) else math.nan


def _in_target_unit(record, target_unit: str) -> float:
    value = float(record.value)
    if not math.isfinite(value):
        return math.nan
    if record.unit == target_unit or record.unit is None:
        return value
    if record.unit == "C" and target_unit == "F":
        result = value * 9.0 / 5.0 + 32.0
        return result if math.isfinite(result) else math.nan
    if record.unit == "F" and target_unit == "C":
        result = (value - 32.0) * 5.0 / 9.0
        return result if math.isfinite(result) else math.nan
    return value


AFTER_DEADLINE_NOTE = "Readings after the deadline are not counted toward this follow-up."


def evaluate_outcome(followup: FollowUp, records, now: datetime) -> OutcomeResult:
    _require_aware(now)
    candidates = [
        r
        for r in indoor_records(records, followup.zone, now=now)
        if r.observed_at > followup.created_at
    ]
    candidates.sort(key=lambda r: (r.observed_at, r.received_at, r.id))
    has_after_deadline = any(r.observed_at > followup.deadline for r in candidates)
    readings = []
    seen = set()
    for record in candidates:
        if record.observed_at > followup.deadline:
            continue
        key = (getattr(record, "source", None), record.observed_at)
        if key in seen:
            continue
        seen.add(key)
        readings.append(record)

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

    notes = []
    if status in (OutcomeStatus.warming_observed, OutcomeStatus.target_reached):
        has_statement = any(
            r.kind == EvidenceKind.human_statement
            and r.received_at <= now
            and r.observed_at > followup.created_at
            for r in records
        )
        if has_statement:
            notes.append("An observed change after a reported action does not prove what caused it.")
    if has_after_deadline:
        notes.append(AFTER_DEADLINE_NOTE)
    note = " ".join(notes) if notes else None

    return OutcomeResult(
        status=status,
        supporting_ids=[r.id for r in readings],
        sample_count=sample_count,
        first_value=first_value,
        last_value=last_value,
        note=note,
        evaluated_at=now,
    )
