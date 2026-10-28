"""Deterministic metrics over evidence records. Pure functions: no I/O, no model calls."""

import math
from collections import Counter
from datetime import datetime

from .clock import ensure_aware
from .contracts import EvidenceRecord, SourceKind
from .eligibility import circuit_records, indoor_records, is_fresh

# Configured power threshold separating idle draw from real load. Set by
# configuration, not tuned on observed data.
NOISE_FLOOR_W = 15.0

CIRCUIT_MEANING = "electrical activity only; not proof of useful heat"


def _convert_temp(value: float, from_unit: str | None, to_unit: str | None) -> float:
    if from_unit == to_unit or from_unit is None or to_unit is None:
        return value
    if from_unit == "C" and to_unit == "F":
        return value * 9.0 / 5.0 + 32.0
    if from_unit == "F" and to_unit == "C":
        return (value - 32.0) * 5.0 / 9.0
    raise ValueError(f"cannot convert temperature from {from_unit!r} to {to_unit!r}")


def _cadence_coverage(
    times: list[datetime], cadence_s: int | None, start: datetime, end: datetime
) -> tuple[float, int, str]:
    if cadence_s is None:
        return 0.0, 0, "no_cadence"
    window_s = (end - start).total_seconds()
    if not times or window_s <= 0:
        return 0.0, 0, "cadence"
    ordered = sorted(times)
    covered = 0.0
    gaps_over = 0
    for earlier, later in zip(ordered, ordered[1:]):
        gap = (later - earlier).total_seconds()
        if gap > 2 * cadence_s:
            gaps_over += 1
            covered += cadence_s
        else:
            covered += gap
    covered += max(0.0, min(float(cadence_s), (end - ordered[-1]).total_seconds()))
    return max(0.0, min(1.0, covered / window_s)), gaps_over, "cadence"


def _largest_gap_s(times: list[datetime]) -> float | None:
    if len(times) < 2:
        return None
    ordered = sorted(times)
    return max((b - a).total_seconds() for a, b in zip(ordered, ordered[1:]))


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def temperature_trend(records: list[EvidenceRecord], zone: str, start: datetime, end: datetime, now: datetime) -> dict:
    ensure_aware(start, "start")
    ensure_aware(end, "end")
    ensure_aware(now, "now")
    deduped = indoor_records(records, zone, now=now, require_value=False)
    missing_count = 0
    samples: list[tuple[datetime, float, str | None, int | None]] = []
    sample_records: list[EvidenceRecord] = []
    for record in deduped:
        if record.observed_at < start or record.observed_at > end:
            continue
        if record.value is None or not _is_number(record.value):
            missing_count += 1
            continue
        samples.append((record.observed_at, float(record.value), record.unit, record.expected_cadence_s))
        sample_records.append(record)
    if not samples:
        return {
            "zone": zone,
            "sample_count": 0,
            "missing_count": missing_count,
            "coverage": 0.0,
            "coverage_basis": "no_cadence",
            "gaps_over_cadence": 0,
            "largest_gap_s": None,
            "first_value": None,
            "first_observed_at": None,
            "last_value": None,
            "last_observed_at": None,
            "change": None,
            "rate_per_hour": None,
            "unit": "F",
            "unit_converted": False,
            "sufficient": False,
            "source": deduped[-1].source.value if deduped else None,
            "expected_cadence_s": deduped[-1].expected_cadence_s if deduped else None,
            "last_id": None,
            "fresh": False,
            "is_fresh": False,
        }
    units = {unit for _, _, unit, _ in samples}
    if len(units) == 1:
        out_unit = samples[0][2] or "F"
        converted = False
    elif units <= {"C", "F"}:
        out_unit = "F"
        converted = any(unit == "C" for _, _, unit, _ in samples)
    else:
        out_unit = samples[0][2] or "F"
        converted = any(unit != out_unit for _, _, unit, _ in samples)
    points = sorted(
        (
            (observed, converted, cadence)
            for observed, value, unit, cadence in samples
            for converted in (_convert_temp(value, unit, out_unit),)
            if math.isfinite(converted)
        ),
        key=lambda p: p[0],
    )
    if not points:
        return {
            "zone": zone,
            "sample_count": 0,
            "missing_count": missing_count,
            "coverage": 0.0,
            "coverage_basis": "no_cadence",
            "gaps_over_cadence": 0,
            "largest_gap_s": None,
            "first_value": None,
            "first_observed_at": None,
            "last_value": None,
            "last_observed_at": None,
            "change": None,
            "rate_per_hour": None,
            "unit": "F",
            "unit_converted": False,
            "sufficient": False,
            "source": deduped[-1].source.value if deduped else None,
            "expected_cadence_s": deduped[-1].expected_cadence_s if deduped else None,
            "last_id": None,
            "fresh": False,
            "is_fresh": False,
        }
    times = [t for t, _, _ in points]
    first_time, first_value, _ = points[0]
    last_time, last_value, _ = points[-1]
    if len(points) < 2:
        change = 0.0
        rate = 0.0
    else:
        change = last_value - first_value
        span_h = (last_time - first_time).total_seconds() / 3600.0
        rate = change / span_h if span_h > 0 else 0.0
    cadence_s = next((c for _, _, c in points if c is not None), None)
    coverage, gaps_over, basis = _cadence_coverage(times, cadence_s, start, end)
    sufficient = len(points) >= 3 and coverage >= 0.5
    return {
        "zone": zone,
        "sample_count": len(points),
        "missing_count": missing_count,
        "coverage": coverage,
        "coverage_basis": basis,
        "gaps_over_cadence": gaps_over,
        "largest_gap_s": _largest_gap_s(times),
        "first_value": first_value,
        "first_observed_at": first_time,
        "last_value": last_value,
        "last_observed_at": last_time,
        "change": change,
        "rate_per_hour": rate,
        "unit": out_unit,
        "unit_converted": converted,
        "sufficient": sufficient,
        "source": sample_records[-1].source.value if sample_records else None,
        "expected_cadence_s": cadence_s,
        "last_id": sample_records[-1].id if sample_records else None,
        "last_received_at": sample_records[-1].received_at if sample_records else None,
        "provenance": sample_records[-1].provenance.model_dump(mode="json") if sample_records else None,
        "fresh": is_fresh(sample_records[-1], now) if sample_records else False,
        "is_fresh": is_fresh(sample_records[-1], now) if sample_records else False,
    }


def target_gap(trend: dict, target_temp: float, target_unit: str) -> dict | None:
    if not trend.get("sample_count") or trend.get("last_value") is None:
        return None
    unit = trend.get("unit") or "F"
    target_in_trend_unit = _convert_temp(float(target_temp), target_unit, unit)
    return {
        "gap": trend["last_value"] - target_in_trend_unit,
        "unit": unit,
        "latest_value": trend["last_value"],
        "latest_observed_at": trend["last_observed_at"],
        "target_temp": float(target_temp),
        "target_unit": target_unit,
        "source": trend.get("source"),
        "expected_cadence_s": trend.get("expected_cadence_s"),
        "last_id": trend.get("last_id"),
        "fresh": trend.get("fresh", trend.get("is_fresh")),
        "is_fresh": trend.get("is_fresh", trend.get("fresh")),
    }


def circuit_activity(
    records: list[EvidenceRecord],
    circuit_id: str,
    start: datetime,
    end: datetime,
    now: datetime,
    noise_floor_w: float = NOISE_FLOOR_W,
) -> dict:
    ensure_aware(start, "start")
    ensure_aware(end, "end")
    ensure_aware(now, "now")
    deduped = circuit_records(records, circuit_id, now=now, require_value=False)
    in_window = [r for r in deduped if start <= r.observed_at <= end]
    missing_count = 0
    samples: list[tuple[datetime, float, int | None]] = []
    sample_records: list[EvidenceRecord] = []
    for record in in_window:
        if record.value is None or not _is_number(record.value):
            missing_count += 1
            continue
        samples.append((record.observed_at, float(record.value), record.expected_cadence_s))
        sample_records.append(record)
    rank = {"confirmed": 2, "candidate": 1, "unknown": 0}
    statuses = [(r.binding.status.value if r.binding else "unknown") for r in in_window]
    binding = "unknown"
    if statuses:
        counts = Counter(statuses)
        top = max(counts.values())
        binding = sorted([s for s, n in counts.items() if n == top], key=lambda s: rank.get(s, 0))[-1]
    samples.sort(key=lambda p: p[0])
    times = [t for t, _, _ in samples]
    values = [v for _, v, _ in samples]
    cadence_s = next((c for _, _, c in samples if c is not None), None)
    coverage, gaps_over, basis = _cadence_coverage(times, cadence_s, start, end)
    return {
        "circuit_id": circuit_id,
        "sample_count": len(samples),
        "missing_count": missing_count,
        "coverage": coverage,
        "coverage_basis": basis,
        "gaps_over_cadence": gaps_over,
        "largest_gap_s": _largest_gap_s(times),
        "max_w": max(values) if values else None,
        "mean_w": sum(values) / len(values) if values else None,
        "active": any(v > noise_floor_w for v in values),
        "binding": binding,
        "noise_floor_w": noise_floor_w,
        "unit": "W",
        "first_observed_at": times[0] if times else None,
        "last_observed_at": times[-1] if times else None,
        "meaning": CIRCUIT_MEANING,
        "source": sample_records[-1].source.value if sample_records else None,
        "expected_cadence_s": cadence_s,
        "last_id": sample_records[-1].id if sample_records else None,
        "last_received_at": sample_records[-1].received_at if sample_records else None,
        "provenance": sample_records[-1].provenance.model_dump(mode="json") if sample_records else None,
        "fresh": is_fresh(sample_records[-1], now) if sample_records else False,
        "is_fresh": is_fresh(sample_records[-1], now) if sample_records else False,
    }
