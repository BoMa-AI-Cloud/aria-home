from datetime import datetime, timedelta

MIN_FOLLOW_UP_DELAY = timedelta(minutes=15)
MIN_FOLLOW_UP_DELAY_S = 900.0
MAX_FOLLOW_UP_DELAY = timedelta(hours=24)
MAX_FOLLOW_UP_DELAY_S = 86400.0
DEFAULT_FOLLOW_UP_CADENCE = timedelta(minutes=30)
DEFAULT_FOLLOW_UP_CADENCE_S = 1800.0
DEADLINE_GRACE = timedelta(hours=2)

MIN_DELAY = MIN_FOLLOW_UP_DELAY
MAX_DELAY = MAX_FOLLOW_UP_DELAY
DEFAULT_CADENCE = DEFAULT_FOLLOW_UP_CADENCE


def is_aware(value):
    return isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None


def _require_aware(value, name):
    if not isinstance(value, datetime):
        raise ValueError(f"{name} must be a datetime")
    if not is_aware(value):
        raise ValueError(f"{name} must be timezone-aware")
    return value


def _coerce_cadence(cadence=None, cadence_s=None):
    raw = cadence_s if cadence_s is not None else cadence
    if raw is None:
        return DEFAULT_FOLLOW_UP_CADENCE
    if isinstance(raw, timedelta):
        delta = raw
    elif isinstance(raw, (int, float)) and not isinstance(raw, bool):
        delta = timedelta(seconds=float(raw))
    else:
        return DEFAULT_FOLLOW_UP_CADENCE
    if delta.total_seconds() <= 0:
        return DEFAULT_FOLLOW_UP_CADENCE
    return delta


def effective_deadline(deadline=None, arrival=None):
    if deadline is not None:
        return _require_aware(deadline, "deadline")
    if arrival is not None:
        return _require_aware(arrival, "arrival") + DEADLINE_GRACE
    return None


def follow_up_window(evaluated_at, deadline=None, arrival=None):
    evaluated = _require_aware(evaluated_at, "evaluated_at")
    end_deadline = effective_deadline(deadline, arrival)
    earliest = evaluated + MIN_FOLLOW_UP_DELAY
    latest = evaluated + MAX_FOLLOW_UP_DELAY
    if end_deadline is not None and end_deadline < latest:
        latest = end_deadline
    return earliest, latest, end_deadline


def is_valid_follow_up_time(value, evaluated_at, deadline=None, arrival=None):
    if not is_aware(value):
        return False
    try:
        earliest, latest, _ = follow_up_window(evaluated_at, deadline, arrival)
    except ValueError:
        return False
    return value > evaluated_at and earliest <= value <= latest


def validate_follow_up_time(value, evaluated_at, deadline=None, arrival=None):
    if not isinstance(value, datetime) or not is_aware(value):
        return ["follow-up time must be timezone-aware"]
    evaluated = _require_aware(evaluated_at, "evaluated_at")
    earliest, latest, _ = follow_up_window(evaluated, deadline, arrival)
    reasons = []
    if value <= evaluated:
        reasons.append("follow-up time must be strictly after the evaluation time")
    elif value < earliest:
        reasons.append("follow-up time is before the minimum follow-up window (15 minutes after evaluation)")
    if value > latest:
        reasons.append("follow-up time is outside the scheduling window (after the deadline or 24 hours after evaluation)")
    return reasons


class FollowUpSchedule(dict):
    @property
    def next_check_at(self):
        return self.get("next_check_at")

    @property
    def scheduled_at(self):
        return self.get("next_check_at")

    @property
    def when(self):
        return self.get("next_check_at")

    @property
    def status(self):
        return self.get("status")

    @property
    def schedule_status(self):
        return self.get("status")

    @property
    def deadline_passed(self):
        return self.get("deadline_passed", False)


def compute_next_check_at(evaluated_at, deadline=None, arrival=None, cadence=None, cadence_s=None):
    schedule = compute_follow_up_schedule(evaluated_at, deadline=deadline, arrival=arrival, cadence=cadence, cadence_s=cadence_s)
    return schedule["next_check_at"]


def compute_schedule(evaluated_at, deadline=None, arrival=None, cadence=None, cadence_s=None, model_when=None, proposed_when=None):
    return compute_follow_up_schedule(evaluated_at, deadline=deadline, arrival=arrival, cadence=cadence, cadence_s=cadence_s, model_when=model_when, proposed_when=proposed_when)


def compute_follow_up_schedule(evaluated_at, deadline=None, arrival=None, cadence=None, cadence_s=None, model_when=None, proposed_when=None):
    if isinstance(arrival, (timedelta, int, float)) and cadence is None and cadence_s is None:
        cadence, arrival = arrival, None
    evaluated = _require_aware(evaluated_at, "evaluated_at")
    if deadline is not None:
        _require_aware(deadline, "deadline")
    if arrival is not None:
        _require_aware(arrival, "arrival")
    cadence_delta = _coerce_cadence(cadence, cadence_s)
    earliest, latest, end_deadline = follow_up_window(evaluated, deadline, arrival)
    supplied = model_when if model_when is not None else proposed_when
    supplied_reasons = validate_follow_up_time(supplied, evaluated, deadline, arrival) if supplied is not None else []
    supplied_valid = supplied is not None and not supplied_reasons

    if end_deadline is not None and end_deadline <= evaluated:
        return FollowUpSchedule(
            status="deadline_passed",
            schedule_status="deadline_passed",
            flag="deadline_passed",
            flags=["deadline_passed"],
            deadline_passed=True,
            evaluated_at=evaluated,
            deadline=end_deadline,
            arrival=arrival,
            earliest=earliest,
            latest=latest,
            cadence_s=cadence_delta.total_seconds(),
            next_check_at=None,
            scheduled_at=None,
            when=None,
            computed_next_check_at=None,
            model_when=supplied,
            model_time_valid=False,
            model_time_rejected=supplied is not None,
            model_time_reasons=supplied_reasons or ["follow-up deadline has passed"],
        )
    if latest < earliest:
        return FollowUpSchedule(
            status="deadline_passed",
            schedule_status="deadline_passed",
            flag="deadline_passed",
            flags=["deadline_passed"],
            deadline_passed=True,
            evaluated_at=evaluated,
            deadline=end_deadline,
            arrival=arrival,
            earliest=earliest,
            latest=latest,
            cadence_s=cadence_delta.total_seconds(),
            next_check_at=None,
            scheduled_at=None,
            when=None,
            computed_next_check_at=None,
            model_when=supplied,
            model_time_valid=False,
            model_time_rejected=supplied is not None,
            model_time_reasons=supplied_reasons or ["follow-up deadline has passed"],
        )

    computed = evaluated + cadence_delta
    if computed < earliest:
        computed = earliest
    if computed > latest:
        computed = latest
    return FollowUpSchedule(
        status="scheduled",
        schedule_status="scheduled",
        flag=None,
        flags=[],
        deadline_passed=False,
        evaluated_at=evaluated,
        deadline=end_deadline,
        arrival=arrival,
        earliest=earliest,
        latest=latest,
        cadence_s=cadence_delta.total_seconds(),
        next_check_at=computed,
        scheduled_at=computed,
        when=computed,
        computed_next_check_at=computed,
        model_when=supplied,
        model_time_valid=supplied_valid,
        model_time_rejected=supplied is not None and not supplied_valid,
        model_time_reasons=supplied_reasons,
    )


schedule_follow_up = compute_follow_up_schedule
resolve_follow_up_time = compute_next_check_at
next_check_time = compute_next_check_at
compute_next_check = compute_next_check_at
schedule_next_check = compute_follow_up_schedule
deterministic_next_check = compute_next_check_at
validate_model_time = validate_follow_up_time
is_valid_model_time = is_valid_follow_up_time
