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
    return isinstance(value, (int, float)) and not isinstance(value, bool)


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
    if require_value and not _is_number(_get(record, "value")):
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
    out = []
    for record in records or []:
        rid = _get(record, "id")
        if rid in seen:
            continue
        if not is_measurement_eligible(record, now=now, quantity=quantity, zone=zone, require_value=require_value):
            continue
        seen.add(rid)
        out.append(record)
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
