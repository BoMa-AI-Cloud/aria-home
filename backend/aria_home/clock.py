from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable


def ensure_aware(value: datetime, name: str = "datetime") -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware (UTC expected)")
    return value


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime:
        ...


class FixedClock:
    def __init__(self, at: datetime):
        self._at = ensure_aware(at, "at")

    def now(self) -> datetime:
        return self._at


class ScenarioClock:
    def __init__(self, start: datetime, step: timedelta):
        self._now = ensure_aware(start, "start")
        if not isinstance(step, timedelta):
            raise TypeError("step must be a timedelta")
        if step.total_seconds() < 0:
            raise ValueError("step must not be negative")
        self._step = step

    def now(self) -> datetime:
        return self._now

    def advance(self, step: timedelta | None = None) -> datetime:
        delta = self._step if step is None else step
        if not isinstance(delta, timedelta):
            raise TypeError("step must be a timedelta")
        if delta.total_seconds() < 0:
            raise ValueError("step must not be negative")
        self._now = self._now + delta
        return self._now

    def advance_by(self, delta: timedelta) -> datetime:
        return self.advance(delta)

    def set(self, at: datetime) -> datetime:
        self._now = ensure_aware(at, "at")
        return self._now
