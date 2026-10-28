import math
from datetime import datetime, timedelta

from .clock import ensure_aware
from .contracts import EvidenceKind, SourceKind

FUTURE_SKEW = timedelta(seconds=60)
FALLBACK_FRESHNESS_S = 3600.0
CADENCE_MULTIPLIER = 2

ALLOWED_SOURCES = {
    "indoor_temp": frozenset({SourceKind.room_sensor, SourceKind.thermostat}),
    "circuit_power": frozenset({SourceKind.electrical}),
}
ALLOWED_KIND = EvidenceKind.measurement


def _get(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _parse_time(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _enum_str(value):
    return value.value if hasattr(value, "value") else str(value) if value is not None else None


def _source(obj):
    raw = _enum_str(_get(obj, "source"))
    try:
        return SourceKind(raw) if raw is not None else None
    except ValueError:
        return None


def _kind(obj):
    raw = _enum_str(_get(obj, "kind"))
    try:
        return EvidenceKind(raw) if raw is not None else None
    except ValueError:
        return None


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def is_finite_number(value):
    return _is_number(value)


def normalized_measurement_value(record):
    value = _get(record, "value")
    if not _is_number(value):
        return None
    result = float(value)
    if _get(record, "unit") == "C":
        result = result * 9.0 / 5.0 + 32.0
    return result if math.isfinite(result) else None


def _values_distinct(values):
    ordered = sorted(values)
    return any(not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9) for a, b in zip(ordered, ordered[1:]))


def _conflict_key(record):
    return (
        _enum_str(_get(record, "source")),
        _get(record, "subject"),
        _get(record, "quantity"),
        _parse_time(_get(record, "observed_at")),
    )


def measurement_conflict_groups(records, quantity=None, zone=None):
    groups = {}
    for record in records or []:
        if not is_measurement_eligible(record, quantity=quantity, zone=zone, require_value=True):
            continue
        value = normalized_measurement_value(record)
        if value is None:
            continue
        key = _conflict_key(record)
        if key[3] is None:
            continue
        groups.setdefault(key, []).append((record, value))
    conflicts = []
    for key, items in groups.items():
        values = [value for _, value in items]
        if _values_distinct(values):
            conflicts.append(
                {
                    "key": key,
                    "source": key[0],
                    "subject": key[1],
                    "quantity": key[2],
                    "observed_at": key[3],
                    "values": values,
                    "ids": [str(_get(r, "id")) for r, _ in items],
                }
            )
    return sorted(conflicts, key=lambda item: item["observed_at"])


def conflicting_observed_times(records, quantity=None, zone=None):
    return {item["observed_at"] for item in measurement_conflict_groups(records, quantity=quantity, zone=zone)}


def freshness_limit_s(record):
    cadence = _get(record, "expected_cadence_s")
    if _is_number(cadence) and float(cadence) > 0:
        return CADENCE_MULTIPLIER * float(cadence)
    return FALLBACK_FRESHNESS_S


def is_fresh(record, now):
    ensure_aware(now, "now")
    observed = _parse_time(_get(record, "observed_at"))
    if observed is None or _get(record, "value") is None:
        return False
    if observed > now + FUTURE_SKEW:
        return False
    return (now - observed).total_seconds() <= freshness_limit_s(record)


def is_measurement_eligible(record, now=None, quantity=None, zone=None, require_value=True):
    q = quantity or _get(record, "quantity")
    if q not in ALLOWED_SOURCES:
        return False
    if quantity is not None and _get(record, "quantity") != quantity:
        return False
    if _kind(record) is not ALLOWED_KIND:
        return False
    if _source(record) not in ALLOWED_SOURCES[q]:
        return False
    if zone is not None and _get(record, "subject") != zone:
        return False
    value = _get(record, "value")
    if value is not None and isinstance(value, (int, float)) and not isinstance(value, bool) and normalized_measurement_value(record) is None:
        return False
    if require_value and normalized_measurement_value(record) is None:
        return False
    observed = _parse_time(_get(record, "observed_at"))
    received = _parse_time(_get(record, "received_at"))
    if observed is None or received is None or observed > received:
        return False
    if now is not None:
        ensure_aware(now, "now")
        if received > now:
            return False
        if observed > now + FUTURE_SKEW:
            return False
    return True


def _sort_key(record):
    return (_parse_time(_get(record, "observed_at")), _parse_time(_get(record, "received_at")), str(_get(record, "id")))


def eligible_records(records, quantity, now=None, zone=None, require_value=True):
    seen = set()
    filtered = []
    for record in records or []:
        rid = _get(record, "id")
        if rid in seen:
            continue
        if not is_measurement_eligible(record, now=now, quantity=quantity, zone=zone, require_value=require_value):
            continue
        seen.add(rid)
        filtered.append(record)
    filtered.sort(key=_sort_key)
    groups = {}
    order = []
    for record in filtered:
        if normalized_measurement_value(record) is None:
            order.append((None, record))
            continue
        key = _conflict_key(record)
        if key not in groups:
            groups[key] = []
            order.append((key, record))
        groups[key].append(record)
    out = []
    for key, record in order:
        if key is None:
            out.append(record)
            continue
        group = groups[key]
        values = [normalized_measurement_value(r) for r in group]
        if _values_distinct(values):
            continue
        out.append(group[0])
    return sorted(out, key=_sort_key)


def indoor_records(records, zone, now=None, require_value=True):
    eligible = eligible_records(records, "indoor_temp", now=now, zone=zone, require_value=require_value)
    room = [r for r in eligible if _source(r) is SourceKind.room_sensor]
    return room if room else [r for r in eligible if _source(r) is SourceKind.thermostat]


def circuit_records(records, circuit_id, now=None, require_value=True):
    eligible = eligible_records(records, "circuit_power", now=now, require_value=require_value)
    out = []
    for record in eligible:
        binding = _get(record, "binding")
        bound = _get(binding, "circuit_id") if binding is not None else None
        if bound == circuit_id or _get(record, "subject") == circuit_id:
            out.append(record)
    return out


def current_pool(records, quantity, now, zone=None):
    if quantity == "indoor_temp" and zone is not None:
        return indoor_records(records, zone, now=now)
    if quantity == "circuit_power":
        return eligible_records(records, quantity, now=now, zone=zone)
    return eligible_records(records, quantity, now=now, zone=zone)


def latest_eligible(records, quantity, now=None, zone=None):
    pool = current_pool(records, quantity, now, zone=zone) if now is not None else eligible_records(records, quantity, now=None, zone=zone)
    return pool[-1] if pool else None


def latest_current(records, quantity, now, zone=None):
    latest = latest_eligible(records, quantity, now=now, zone=zone)
    if latest is None or not is_fresh(latest, now):
        return None
    return latest


def is_current_record(record, records, quantity, now, zone=None):
    if not is_measurement_eligible(record, now=now, quantity=quantity, zone=zone):
        return False, "not an eligible measurement for a current claim"
    if not is_fresh(record, now):
        return False, "stale reading is not eligible as a current claim (historical only)"
    pool = current_pool(records, quantity, now, zone=zone)
    if quantity == "circuit_power" and pool:
        binding = _get(record, "binding")
        circuit_id = (_get(binding, "circuit_id") if binding is not None else None) or _get(record, "subject")
        pool = circuit_records(records, circuit_id, now=now)
    if not pool:
        return False, "not an eligible measurement for a current claim"
    latest = pool[-1]
    if str(_get(latest, "id")) != str(_get(record, "id")) or _parse_time(_get(latest, "observed_at")) != _parse_time(_get(record, "observed_at")):
        return False, "superseded reading is not eligible as a current claim; only the latest eligible fresh reading is current (older readings are historical only)"
    return True, None
