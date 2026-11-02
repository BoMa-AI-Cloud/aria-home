from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def ensure_aware(value: datetime, name: str = "datetime") -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware (UTC expected)")
    return value


def plain_time(value, timezone_name=None) -> str:
    """A clock time for sentences, such as 7:03 PM, in the scenario's timezone when one is given."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    if timezone_name and value.tzinfo is not None:
        try:
            value = value.astimezone(ZoneInfo(timezone_name))
        except ZoneInfoNotFoundError:
            pass
    hour = value.hour % 12 or 12
    return f"{hour}:{value.minute:02d} {'AM' if value.hour < 12 else 'PM'}"


def plain_duration(seconds) -> str:
    """A length of time for sentences: minutes up to two hours, then hours and minutes."""
    total_min = int(round(float(seconds) / 60.0))
    if float(seconds) < 60:
        return "under 1 min"
    if total_min < 120:
        return f"{total_min} min"
    hours, minutes = divmod(total_min, 60)
    return f"{hours} h {minutes} min" if minutes else f"{hours} h"


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
