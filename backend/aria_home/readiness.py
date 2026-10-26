from datetime import datetime

MIN_SAMPLES = 3
MIN_COVERAGE = 0.5
STALE_READING_AGE_S = 3600.0
SMALL_GAP_F = 2.0
MIN_TREND_WINDOW_S = 3600.0
MIN_RISE_F = 1.0
MIN_RATE_PER_HOUR_F = 0.5
PROJECTION_MARGIN_F = 0.5
ARRIVAL_TIME_MARGIN_S = 1800.0

THRESHOLDS = {
    "MIN_SAMPLES": MIN_SAMPLES,
    "MIN_COVERAGE": MIN_COVERAGE,
    "STALE_READING_AGE_S": STALE_READING_AGE_S,
    "SMALL_GAP_F": SMALL_GAP_F,
    "MIN_TREND_WINDOW_S": MIN_TREND_WINDOW_S,
    "MIN_RISE_F": MIN_RISE_F,
    "MIN_RATE_PER_HOUR_F": MIN_RATE_PER_HOUR_F,
    "PROJECTION_MARGIN_F": PROJECTION_MARGIN_F,
    "ARRIVAL_TIME_MARGIN_S": ARRIVAL_TIME_MARGIN_S,
}

_FLAG_ALIASES = {
    "cancelled": "trip_cancelled",
    "trip_cancelled": "trip_cancelled",
    "unconfirmed": "trip_unconfirmed",
    "trip_unconfirmed": "trip_unconfirmed",
    "confirmation_unconfirmed": "trip_unconfirmed",
    "not_confirmed": "trip_unconfirmed",
    "mismatched": "trip_mismatched",
    "mismatch": "trip_mismatched",
    "trip_mismatched": "trip_mismatched",
    "confirmation_mismatched": "trip_mismatched",
    "outdated": "confirmation_outdated",
    "confirmation_outdated": "confirmation_outdated",
    "confirmation_stale": "confirmation_outdated",
    "stale_confirmation": "confirmation_outdated",
}


class ReadinessResult(dict):
    @property
    def status(self):
        return self["status"]

    @property
    def reasons(self):
        return self["reasons"]

    @property
    def inputs(self):
        return self["inputs"]

    @property
    def target_at_arrival(self):
        return self.get("target_at_arrival")


def _parse_time(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _to_f(value, unit):
    if value is None:
        return None
    if unit == "C":
        return value * 9.0 / 5.0
    return value


def _rate_to_f(value, unit):
    if value is None:
        return None
    if unit == "C":
        return value * 9.0 / 5.0
    return value


def _normalize_flags(pack, flags, kwargs):
    normalized = {}
    raw = {}
    if isinstance(pack, dict):
        for key in ("readiness_flags", "flags", "context_flags"):
            if isinstance(pack.get(key), dict):
                raw.update(pack[key])
            elif isinstance(pack.get(key), (list, tuple, set)):
                for item in pack[key]:
                    raw[str(item)] = True
    if isinstance(flags, dict):
        raw.update(flags)
    elif isinstance(flags, (list, tuple, set)):
        for item in flags:
            raw[str(item)] = True
    elif flags is not None:
        raw[str(flags)] = True
    raw.update(kwargs)
    for key, value in raw.items():
        canonical = _FLAG_ALIASES.get(str(key), str(key))
        normalized[canonical] = bool(value)
    return normalized


def compute_readiness(pack=None, now=None, flags=None, **kwargs):
    data = pack if isinstance(pack, dict) else {}
    if isinstance(data.get("inputs"), dict) and "metrics" not in data:
        data = {**data, **data["inputs"]}
    metrics = data.get("metrics") if isinstance(data.get("metrics"), dict) else {}
    trend = metrics.get("indoor_trend") if isinstance(metrics.get("indoor_trend"), dict) else {}
    if not trend and isinstance(data.get("indoor_trend"), dict):
        trend = data["indoor_trend"]
    if not trend and isinstance(data.get("trend"), dict):
        trend = data["trend"]
    gap_info = metrics.get("target_gap") if isinstance(metrics.get("target_gap"), dict) else None
    if gap_info is None and isinstance(data.get("target_gap"), dict):
        gap_info = data["target_gap"]
    trip = data.get("trip") if isinstance(data.get("trip"), dict) else None
    if trip is None and isinstance(kwargs.get("trip"), dict):
        trip = kwargs.pop("trip")
    confirmation = data.get("confirmation") if isinstance(data.get("confirmation"), dict) else None
    flag_map = _normalize_flags(data, flags, kwargs)

    now_dt = _parse_time(now) or _parse_time(data.get("at")) or _parse_time(data.get("now"))
    arrival = _parse_time(trip.get("planned_arrival")) if trip else None
    if arrival is None:
        arrival = _parse_time(data.get("planned_arrival")) or _parse_time(data.get("arrival"))

    unit = gap_info.get("unit") if gap_info else trend.get("unit")
    gap_raw = _num(gap_info.get("gap")) if gap_info else None
    gap_f = None
    if gap_raw is not None:
        gap_f = gap_raw * 9.0 / 5.0 if unit == "C" else gap_raw
    last_value = _num(trend.get("last_value"))
    if not trend and gap_info:
        last_value = _num(gap_info.get("latest_value"))
    target_temp = _num(gap_info.get("target_temp")) if gap_info else None
    if target_temp is None and confirmation:
        target_temp = _num(confirmation.get("target_temp"))
    rate_raw = _num(trend.get("rate_per_hour"))
    rate_f = _rate_to_f(rate_raw, trend.get("unit") or unit)
    change_raw = _num(trend.get("change"))
    change_f = _to_f(change_raw, trend.get("unit") or unit)
    sample_count = trend.get("sample_count")
    sample_count = int(sample_count) if isinstance(sample_count, (int, float)) and not isinstance(sample_count, bool) else 0
    coverage = _num(trend.get("coverage"))
    first_at = _parse_time(trend.get("first_observed_at"))
    last_at = _parse_time(trend.get("last_observed_at")) or (_parse_time(gap_info.get("latest_observed_at")) if gap_info else None)
    window_s = (last_at - first_at).total_seconds() if first_at and last_at else None
    hours_to_arrival = ((arrival - now_dt).total_seconds() / 3600.0) if arrival and now_dt else None

    statuses = data.get("source_statuses") if isinstance(data.get("source_statuses"), list) else []
    thermostat_status = None
    for item in statuses:
        if isinstance(item, dict) and item.get("source") == "thermostat":
            thermostat_status = item
            break
    availability = thermostat_status.get("availability") if thermostat_status else None

    inputs = {
        "gap": gap_raw,
        "gap_f": gap_f,
        "unit": unit,
        "last_value": last_value,
        "target_temp": target_temp,
        "rate_per_hour": rate_raw,
        "rate_per_hour_f": rate_f,
        "change": change_raw,
        "change_f": change_f,
        "sample_count": sample_count,
        "coverage": coverage,
        "first_observed_at": first_at.isoformat() if first_at else trend.get("first_observed_at"),
        "last_observed_at": last_at.isoformat() if last_at else trend.get("last_observed_at"),
        "trend_window_s": window_s,
        "planned_arrival": arrival.isoformat() if arrival else (trip.get("planned_arrival") if trip else None),
        "now": now_dt.isoformat() if now_dt else None,
        "hours_to_arrival": hours_to_arrival,
        "thermostat_availability": availability,
        "flags": flag_map,
        "thresholds": dict(THRESHOLDS),
    }

    reasons = []
    cannot = []

    if flag_map.get("trip_cancelled"):
        cannot.append("trip is cancelled")
    if trip is not None and trip.get("cancelled"):
        cannot.append("trip is cancelled")
    if flag_map.get("trip_unconfirmed"):
        cannot.append("trip or confirmation is unconfirmed")
    if flag_map.get("trip_mismatched"):
        cannot.append("trip and confirmation do not match")
    if flag_map.get("confirmation_outdated"):
        cannot.append("confirmation is outdated")
    if trip is None:
        cannot.append("no confirmed arrival: trip is missing")
    if confirmation is None and not (gap_info and target_temp is not None):
        cannot.append("no confirmed target: confirmation is missing")
    if trip is not None and confirmation is not None:
        if confirmation.get("trip_id") and trip.get("id") and confirmation.get("trip_id") != trip.get("id"):
            cannot.append("trip and confirmation do not match")
        if confirmation.get("property_id") and trip.get("property_id") and confirmation.get("property_id") != trip.get("property_id"):
            cannot.append("trip and confirmation do not match")
    if arrival is None:
        cannot.append("no confirmed arrival time")
    if target_temp is None:
        cannot.append("no confirmed target temperature")
    if gap_info is None or gap_raw is None:
        cannot.append("target gap is unavailable")

    if availability == "conflicting":
        cannot.append("indoor readings are conflicting")
    elif any(isinstance(s, dict) and s.get("availability") == "conflicting" for s in statuses):
        cannot.append("indoor readings are conflicting")
    if availability in ("missing", "stale", "invalid"):
        cannot.append(f"indoor reading is {availability}")
    if last_value is None:
        cannot.append("indoor reading is missing")
    if sample_count < MIN_SAMPLES:
        cannot.append(f"too few indoor samples: {sample_count} < {MIN_SAMPLES}")
    if coverage is not None and coverage < MIN_COVERAGE:
        cannot.append(f"indoor coverage {coverage} is below {MIN_COVERAGE}")
    if coverage is None:
        cannot.append("indoor coverage is unavailable")
    if now_dt is not None and last_at is not None:
        age_s = (now_dt - last_at).total_seconds()
        inputs["reading_age_s"] = age_s
        if age_s > STALE_READING_AGE_S:
            cannot.append(f"latest indoor reading is stale ({age_s:.0f}s old)")
    elif last_value is not None:
        cannot.append("latest indoor reading time is unavailable")

    context_invalid = (
        flag_map.get("trip_cancelled")
        or flag_map.get("trip_unconfirmed")
        or flag_map.get("trip_mismatched")
        or flag_map.get("confirmation_outdated")
        or trip is None
        or (trip is not None and trip.get("cancelled"))
        or arrival is None
        or target_temp is None
        or (
            trip is not None
            and confirmation is not None
            and (
                (confirmation.get("trip_id") and trip.get("id") and confirmation.get("trip_id") != trip.get("id"))
                or (confirmation.get("property_id") and trip.get("property_id") and confirmation.get("property_id") != trip.get("property_id"))
            )
        )
    )
    if not context_invalid and now_dt is not None and arrival is not None and now_dt > arrival:
        target_unit = (gap_info.get("target_unit") if gap_info else None) or (confirmation.get("target_unit") if confirmation else None) or unit

        def _to_target(value, value_unit):
            if value is None:
                return None
            if value_unit is None or target_unit is None or value_unit == target_unit:
                return float(value)
            if value_unit == "C" and target_unit == "F":
                return float(value) * 9.0 / 5.0 + 32.0
            if value_unit == "F" and target_unit == "C":
                return (float(value) - 32.0) * 5.0 / 9.0
            return float(value)

        candidates = []
        for item in data.get("evidence", []) if isinstance(data.get("evidence"), list) else []:
            if not isinstance(item, dict) or item.get("quantity") != "indoor_temp":
                continue
            value = _num(item.get("value"))
            observed = _parse_time(item.get("observed_at"))
            received = _parse_time(item.get("received_at"))
            if value is None or observed is None or received is None:
                continue
            if received <= arrival and observed <= arrival:
                candidates.append((item.get("source"), observed, received, value, item.get("unit")))
        arrival_value = None
        arrival_unit = None
        arrival_observed = None
        if candidates:
            for preferred in ("room_sensor", "thermostat"):
                group = [c for c in candidates if c[0] == preferred]
                if group:
                    candidates = group
                    break
            _, arrival_observed, _, arrival_value, arrival_unit = max(candidates, key=lambda c: (c[1], c[2]))
        elif last_value is not None and last_at is not None and last_at <= arrival:
            arrival_value, arrival_unit, arrival_observed = last_value, unit, last_at

        outcome = "unknown"
        if arrival_value is not None and arrival_observed is not None and 0 <= (arrival - arrival_observed).total_seconds() <= STALE_READING_AGE_S:
            converted = _to_target(arrival_value, arrival_unit)
            if converted is not None:
                outcome = "met" if converted >= float(target_temp) else "not_met"
        inputs["evaluated_at_arrival"] = True
        inputs["arrival_outcome"] = outcome
        inputs["target_at_arrival"] = outcome
        inputs["arrival_last_value"] = arrival_value
        inputs["arrival_last_observed_at"] = arrival_observed.isoformat() if arrival_observed else None
        if outcome == "met":
            reason = f"Arrival has passed: the target was met at arrival time (latest reading received by arrival was {arrival_value} {arrival_unit} at {arrival_observed.isoformat()}, at or above the {target_temp} {target_unit} target)."
        elif outcome == "not_met":
            reason = f"Arrival has passed: the target was not met at arrival time (latest reading received by arrival was {arrival_value} {arrival_unit} at {arrival_observed.isoformat()}, below the {target_temp} {target_unit} target)."
        else:
            reason = "Arrival has passed: whether the target was met at arrival time is unknown (no fresh indoor reading was received by arrival)."
        return ReadinessResult(status="arrival_passed", reasons=[reason], inputs=inputs, target_at_arrival=outcome)

    deduped = []
    for reason in cannot:
        if reason not in deduped:
            deduped.append(reason)
    if deduped:
        return ReadinessResult(status="cannot_tell", reasons=deduped, inputs=inputs, target_at_arrival=None)

    if gap_f is not None and gap_f >= 0:
        reasons.append("latest fresh indoor reading already meets the target")
        return ReadinessResult(status="on_track", reasons=reasons, inputs=inputs, target_at_arrival=None)

    projected_f = None
    closes_in_h = None
    if rate_f is not None and rate_f > 0 and hours_to_arrival is not None and hours_to_arrival >= 0 and last_value is not None:
        last_f = last_value * 9.0 / 5.0 + 32.0 if unit == "C" else last_value
        target_f = None
        if target_temp is not None:
            target_unit = (gap_info.get("target_unit") if gap_info else None) or (confirmation.get("target_unit") if confirmation else None) or unit
            target_f = target_temp * 9.0 / 5.0 + 32.0 if target_unit == "C" else target_temp
        if target_f is not None:
            projected_f = last_f + rate_f * hours_to_arrival
            inputs["projected_value_at_arrival_f"] = projected_f
            inputs["target_temp_f"] = target_f
            closes_in_h = abs(gap_f) / rate_f if gap_f is not None else None
            inputs["hours_to_close_gap"] = closes_in_h

    small_gap = gap_f is not None and abs(gap_f) <= SMALL_GAP_F
    sustained = (
        window_s is not None and window_s >= MIN_TREND_WINDOW_S
        and change_f is not None and change_f >= MIN_RISE_F
        and rate_f is not None and rate_f >= MIN_RATE_PER_HOUR_F
    )
    with_margin = False
    if projected_f is not None and inputs.get("target_temp_f") is not None and closes_in_h is not None and hours_to_arrival is not None:
        with_margin = (
            projected_f >= inputs["target_temp_f"] + PROJECTION_MARGIN_F
            and closes_in_h * 3600.0 <= hours_to_arrival * 3600.0 - ARRIVAL_TIME_MARGIN_S
        )
    if small_gap and sustained and with_margin:
        reasons.append("gap is small and sustained warming over the trend window would close it before arrival with margin")
        return ReadinessResult(status="on_track", reasons=reasons, inputs=inputs, target_at_arrival=None)

    reasons.append("At current readings the target may not be reached by arrival; this is not a guaranteed prediction.")
    if gap_f is not None:
        reasons.append(f"latest reading is {abs(gap_f):.1f} F below target")
    if rate_raw is not None:
        reasons.append(f"observed trend is {rate_raw} per hour over {window_s:.0f}s" if window_s is not None else f"observed trend is {rate_raw} per hour")
    if not small_gap:
        reasons.append(f"gap exceeds the small-gap threshold of {SMALL_GAP_F} F")
    elif not sustained:
        reasons.append("warming is not sustained over the minimum window and rise thresholds")
    elif not with_margin:
        reasons.append("projected warming does not close the gap before arrival with margin")
    return ReadinessResult(status="at_risk", reasons=reasons, inputs=inputs, target_at_arrival=None)
