import math
from datetime import datetime

from .eligibility import freshness_limit_s, is_measurement_eligible, measurement_conflict_groups

MIN_SAMPLES = 3
MIN_COVERAGE = 0.5
STALE_READING_AGE_S = 3600.0
SMALL_GAP_F = 2.0
MIN_TREND_WINDOW_S = 3600.0
MIN_RISE_F = 1.0
MIN_RATE_PER_HOUR_F = 0.5
PROJECTION_MARGIN_F = 0.5
ARRIVAL_TIME_MARGIN_S = 1800.0
READINESS_POLICY_VERSION = "readiness-policy-v3"
TARGET_GAP_TOLERANCE_F = 0.0

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
    "TARGET_GAP_TOLERANCE_F": TARGET_GAP_TOLERANCE_F,
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

    @property
    def policy_version(self):
        return self.get("policy_version")


def _result(status, reasons, inputs, target_at_arrival=None):
    return ReadinessResult(status=status, reasons=reasons, inputs=inputs, target_at_arrival=target_at_arrival, policy_version=READINESS_POLICY_VERSION)


def _parse_time(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _fmt_num(value):
    if value is None:
        return "unknown"
    value = 0.0 if float(value) == 0 else float(value)
    text = f"{value:.2f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _fmt_signed(value):
    if value is None:
        return "unknown"
    value = 0.0 if float(value) == 0 else float(value)
    return f"{value:+.2f}"


def _fmt_duration(seconds):
    if seconds is None:
        return "unknown duration"
    total = int(round(float(seconds)))
    if total < 60:
        return f"{total} s"
    hours, remainder = divmod(total, 3600)
    minutes = int(round(remainder / 60))
    if minutes == 60:
        hours += 1
        minutes = 0
    if hours and minutes:
        return f"{hours} h {minutes} min"
    if hours:
        return f"{hours} h"
    return f"{minutes} min"


def _num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _to_f(value, unit):
    if value is None:
        return None
    result = value * 9.0 / 5.0 if unit == "C" else value
    return result if math.isfinite(result) else None


def _rate_to_f(value, unit):
    if value is None:
        return None
    result = value * 9.0 / 5.0 if unit == "C" else value
    return result if math.isfinite(result) else None


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
        converted_gap = gap_raw * 9.0 / 5.0 if unit == "C" else gap_raw
        gap_f = converted_gap if math.isfinite(converted_gap) else None
        if gap_f is None:
            gap_raw = None
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
    room_status = None
    for item in statuses:
        if isinstance(item, dict) and item.get("source") == "thermostat" and thermostat_status is None:
            thermostat_status = item
        if isinstance(item, dict) and item.get("source") == "room_sensor" and room_status is None:
            room_status = item
    zone = metrics.get("zone") or data.get("zone")
    evidence_list = data.get("evidence") if isinstance(data.get("evidence"), list) else []
    indoor_evidence = [
        item for item in evidence_list
        if isinstance(item, dict) and item.get("quantity") == "indoor_temp"
    ]
    eligible_indoor = [
        item for item in indoor_evidence
        if is_measurement_eligible(item, quantity="indoor_temp", zone=zone if zone and item.get("subject") is not None else None, require_value=False)
    ]
    indoor_conflicts = measurement_conflict_groups(
        indoor_evidence,
        quantity="indoor_temp",
        zone=zone if zone else None,
    ) if indoor_evidence else []
    has_room_sensor = any(
        item.get("source") == "room_sensor"
        for item in eligible_indoor
    ) or (not indoor_evidence and bool(room_status and _num(room_status.get("record_count"))))
    indoor_source = "room_sensor" if has_room_sensor else "thermostat"
    indoor_conflicts = [item for item in indoor_conflicts if item["source"] == indoor_source]
    indoor_status = room_status if has_room_sensor else thermostat_status
    availability = indoor_status.get("availability") if indoor_status else None
    thermostat_availability = thermostat_status.get("availability") if thermostat_status else None
    thermostat_missing = has_room_sensor and (
        thermostat_status is None or thermostat_availability in ("missing", "stale", "invalid")
    )
    thermostat_note = "thermostat telemetry missing; room sensor used" if thermostat_missing else None

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
        "thermostat_availability": thermostat_availability,
        "indoor_source": indoor_source,
        "indoor_availability": availability,
        "room_sensor_availability": room_status.get("availability") if room_status else None,
        "thermostat_telemetry_missing": thermostat_missing,
        "eligible_indoor_count": len(eligible_indoor),
        "indoor_conflict_count": len(indoor_conflicts),
        "indoor_conflicting_ids": [rid for item in indoor_conflicts for rid in item["ids"]],
        "indoor_measurement_eligible": bool(eligible_indoor) if indoor_evidence else None,
        "flags": flag_map,
        "thresholds": dict(THRESHOLDS),
        "policy_version": READINESS_POLICY_VERSION,
        "target_gap_tolerance_f": TARGET_GAP_TOLERANCE_F,
    }

    from .visual import SUPPORTED_DETECTIONS, detection_label, no_detection_line, observation_line

    visual = data.get("visual_evidence") if isinstance(data.get("visual_evidence"), dict) else None
    if visual is not None and now_dt is not None:
        received = _parse_time(visual.get("received_at"))
        if received is not None and received > now_dt:
            visual = None
    visual_count = 0
    visual_phrase = ""
    if visual is not None:
        visual_phrase = str(visual.get("phrase") or "")
        try:
            visual_count = int(visual.get("object_count") or 0)
        except (TypeError, ValueError):
            visual_count = 0
    visual_detected = visual is not None and visual_count > 0 and detection_label(visual_phrase) in SUPPORTED_DETECTIONS
    inputs["visual"] = (
        {
            "image_id": visual.get("image_id"),
            "phrase": visual_phrase,
            "object_count": visual_count,
            "largest_box_fraction": visual.get("largest_box_fraction"),
            "provider_mode": visual.get("provider_mode"),
            "detected": visual_detected,
        }
        if visual is not None
        else None
    )

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

    if indoor_evidence and not eligible_indoor:
        cannot.append("no eligible indoor measurement: only non-measurement or ineligible-source records are present (human statements may corroborate only)")
    if indoor_conflicts:
        cannot.append("indoor readings are conflicting")
    elif availability == "conflicting":
        cannot.append("indoor readings are conflicting")
    elif not has_room_sensor and any(isinstance(s, dict) and s.get("availability") == "conflicting" for s in statuses):
        cannot.append("indoor readings are conflicting")
    if availability in ("missing", "stale", "invalid"):
        cannot.append(f"indoor reading is {availability}")
    if last_value is None:
        cannot.append("indoor reading is missing")
    if sample_count < MIN_SAMPLES:
        cannot.append(f"too few indoor samples: {sample_count} < {MIN_SAMPLES}")
    if coverage is not None and coverage < MIN_COVERAGE:
        cannot.append(f"indoor coverage {_fmt_num(coverage)} is below {_fmt_num(MIN_COVERAGE)}")
    if coverage is None:
        cannot.append("indoor coverage is unavailable")
    if now_dt is not None and last_at is not None:
        age_s = (now_dt - last_at).total_seconds()
        inputs["reading_age_s"] = age_s
        cadence = trend.get("expected_cadence_s") or (gap_info.get("expected_cadence_s") if gap_info else None)
        if cadence is None and eligible_indoor:
            cadence = next((item.get("expected_cadence_s") for item in eligible_indoor if item.get("expected_cadence_s") is not None), None)
        freshness_limit = STALE_READING_AGE_S
        if isinstance(cadence, (int, float)) and not isinstance(cadence, bool):
            freshness_limit = min(STALE_READING_AGE_S, 2 * float(cadence))
        inputs["freshness_limit_s"] = freshness_limit
        if age_s > freshness_limit:
            cannot.append(f"latest indoor reading is stale ({_fmt_duration(age_s)} old)")
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
    if not context_invalid and not indoor_conflicts and now_dt is not None and arrival is not None and now_dt > arrival:
        target_unit = (gap_info.get("target_unit") if gap_info else None) or (confirmation.get("target_unit") if confirmation else None) or unit

        def _to_target(value, value_unit):
            if value is None or not math.isfinite(float(value)):
                return None
            if value_unit is None or target_unit is None or value_unit == target_unit:
                result = float(value)
            elif value_unit == "C" and target_unit == "F":
                result = float(value) * 9.0 / 5.0 + 32.0
            elif value_unit == "F" and target_unit == "C":
                result = (float(value) - 32.0) * 5.0 / 9.0
            else:
                result = float(value)
            return result if math.isfinite(result) else None

        candidates = []
        for item in data.get("evidence", []) if isinstance(data.get("evidence"), list) else []:
            if not isinstance(item, dict) or item.get("quantity") != "indoor_temp":
                continue
            if not is_measurement_eligible(item, quantity="indoor_temp", zone=zone if zone and item.get("subject") is not None else None):
                continue
            value = _num(item.get("value"))
            observed = _parse_time(item.get("observed_at"))
            received = _parse_time(item.get("received_at"))
            if value is None or observed is None or received is None:
                continue
            if received <= arrival and observed <= arrival:
                candidates.append((item.get("source"), observed, received, value, item.get("unit"), item))
        arrival_value = None
        arrival_unit = None
        arrival_observed = None
        arrival_item = None
        if candidates:
            for preferred in ("room_sensor", "thermostat"):
                group = [c for c in candidates if c[0] == preferred]
                if group:
                    candidates = group
                    break
            _, arrival_observed, _, arrival_value, arrival_unit, arrival_item = max(candidates, key=lambda c: (c[1], c[2]))
        elif last_value is not None and last_at is not None and last_at <= arrival and not indoor_evidence:
            arrival_value, arrival_unit, arrival_observed = last_value, unit, last_at

        outcome = "unknown"
        if arrival_value is not None and arrival_observed is not None:
            age_at_arrival = (arrival - arrival_observed).total_seconds()
            limit = STALE_READING_AGE_S
            if arrival_item is not None:
                limit = min(STALE_READING_AGE_S, freshness_limit_s(arrival_item))
            elif isinstance(trend.get("expected_cadence_s"), (int, float)):
                limit = min(STALE_READING_AGE_S, 2 * float(trend["expected_cadence_s"]))
            if 0 <= age_at_arrival <= limit:
                converted = _to_target(arrival_value, arrival_unit)
                if converted is not None:
                    tolerance = TARGET_GAP_TOLERANCE_F * 5.0 / 9.0 if target_unit == "C" else TARGET_GAP_TOLERANCE_F
                    outcome = "met" if converted >= float(target_temp) - tolerance else "not_met"
        inputs["evaluated_at_arrival"] = True
        inputs["arrival_outcome"] = outcome
        inputs["target_at_arrival"] = outcome
        inputs["arrival_last_value"] = arrival_value
        inputs["arrival_last_observed_at"] = arrival_observed.isoformat() if arrival_observed else None
        if outcome == "met":
            reason = f"Arrival has passed: the target was met at arrival time (latest reading received by arrival was {_fmt_num(arrival_value)} {arrival_unit} at {arrival_observed.isoformat()}, at or above the {_fmt_num(target_temp)} {target_unit} target)."
        elif outcome == "not_met":
            reason = f"Arrival has passed: the target was not met at arrival time (latest reading received by arrival was {_fmt_num(arrival_value)} {arrival_unit} at {arrival_observed.isoformat()}, below the {_fmt_num(target_temp)} {target_unit} target)."
        else:
            reason = "Arrival has passed: whether the target was met at arrival time is unknown (no fresh indoor reading was received by arrival)."
        return _result("arrival_passed", [reason], inputs, target_at_arrival=outcome)

    deduped = []
    for reason in cannot:
        if reason not in deduped:
            deduped.append(reason)
    if deduped:
        if visual_detected and not context_invalid and not indoor_conflicts and availability != "conflicting":
            return _result("at_risk", [observation_line(visual_phrase), "indoor temperature is unknown or insufficient; the visual detection supports attention, not a readiness guarantee"], inputs, target_at_arrival=None)
        if thermostat_note and thermostat_note not in deduped:
            deduped.append(thermostat_note)
        return _result("cannot_tell", deduped, inputs, target_at_arrival=None)

    if gap_f is not None and gap_f >= -TARGET_GAP_TOLERANCE_F:
        if thermostat_note:
            reasons.append(thermostat_note)
        reasons.append("latest fresh indoor reading already meets the target")
        return _result("on_track", reasons, inputs, target_at_arrival=None)

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
        if thermostat_note:
            reasons.append(thermostat_note)
        reasons.append("gap is small and sustained warming over the trend window would close it before arrival with margin")
        return _result("on_track", reasons, inputs, target_at_arrival=None)

    if thermostat_note:
        reasons.append(thermostat_note)
    if visual_detected:
        reasons.append(observation_line(visual_phrase))
    elif visual is not None and visual_count == 0:
        reasons.append(no_detection_line(visual_phrase))
    reasons.append("At current readings the target may not be reached by arrival; this is not a guaranteed prediction.")
    if gap_f is not None:
        reasons.append(f"latest reading is {abs(gap_f):.1f} F below target")
    if rate_raw is not None:
        rate_value = rate_f if rate_f is not None else rate_raw
        if window_s is not None:
            reasons.append(f"observed trend is {_fmt_signed(rate_value)} F per hour over {_fmt_duration(window_s)}")
        else:
            reasons.append(f"observed trend is {_fmt_signed(rate_value)} F per hour")
    if not small_gap:
        reasons.append(f"gap exceeds the small-gap threshold of {_fmt_num(SMALL_GAP_F)} F")
    elif not sustained:
        reasons.append("warming is not sustained over the minimum window and rise thresholds")
    elif not with_margin:
        reasons.append("projected warming does not close the gap before arrival with margin")
    return _result("at_risk", reasons, inputs, target_at_arrival=None)
