import math
from collections import defaultdict
from datetime import datetime, timedelta

from .clock import ensure_aware
from .contracts import Availability, DataMode, EvidenceRecord, SourceKind, SourceStatus
from .eligibility import ALLOWED_SOURCES, is_measurement_eligible, normalized_measurement_value

FUTURE_SKEW = timedelta(seconds=60)


def freshness(record: EvidenceRecord, now: datetime) -> Availability:
    ensure_aware(now, "now")
    if record.observed_at > now + FUTURE_SKEW:
        return Availability.invalid
    if record.value is None:
        return Availability.missing
    if record.expected_cadence_s is not None:
        age_s = (now - record.observed_at).total_seconds()
        if age_s > 2 * record.expected_cadence_s:
            return Availability.stale
    return Availability.available


def source_status(
    source: SourceKind,
    records: list[EvidenceRecord],
    now: datetime,
    mode: DataMode | None = None,
) -> SourceStatus:
    ensure_aware(now, "now")
    source = SourceKind(source)
    relevant = [
        r
        for r in records
        if r.source is source
        and (r.quantity not in ALLOWED_SOURCES or is_measurement_eligible(r, require_value=False))
    ]

    seen: dict = {}
    duplicates = 0
    for record in sorted(relevant, key=lambda r: (r.received_at, r.observed_at, r.id)):
        value = normalized_measurement_value(record)
        if value is not None:
            collapse_key = (record.subject, record.quantity, record.observed_at, "n", value)
        elif isinstance(record.value, str):
            collapse_key = (record.subject, record.quantity, record.observed_at, "s", record.value)
        else:
            collapse_key = (record.subject, record.quantity, record.observed_at, "m", repr(record.value))
        if collapse_key in seen:
            duplicates += 1
            continue
        seen[collapse_key] = record
    deduped = list(seen.values())

    resolved_mode = mode or (deduped[0].mode if deduped else DataMode.synthetic)
    notes: list[str] = []
    if duplicates:
        notes.append(f"removed {duplicates} duplicate record id(s)")

    if not deduped:
        notes.append("no records")
        return SourceStatus(
            source=source,
            availability=Availability.missing,
            record_count=0,
            newest_observed_at=None,
            newest_value=None,
            newest_unit=None,
            age_s=None,
            mode=resolved_mode,
            notes=notes,
            missing_count=0,
            stale_count=0,
        )

    string_groups: dict[tuple, set] = defaultdict(set)
    for record in deduped:
        if isinstance(record.value, str):
            string_groups[(record.subject, record.quantity, record.observed_at)].add(record.value)
    conflicting_keys = [key for key, values in string_groups.items() if len(values) > 1]
    groups: dict[tuple, list] = defaultdict(list)
    for record in deduped:
        value = normalized_measurement_value(record)
        if value is None:
            continue
        groups[(record.subject, record.quantity, record.observed_at)].append(value)
    numeric_conflicting = []
    for key, values in groups.items():
        ordered = sorted(values)
        if any(not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9) for a, b in zip(ordered, ordered[1:])):
            numeric_conflicting.append(key)
    conflicting_keys = list(dict.fromkeys(conflicting_keys + numeric_conflicting))
    clean_times = [
        record.observed_at
        for record in deduped
        if not any(
            record.subject == subject and record.quantity == quantity and record.observed_at == observed_at
            for subject, quantity, observed_at in conflicting_keys
        )
    ]
    if clean_times:
        latest_clean = max(clean_times)
        conflicting_keys = [
            (subject, quantity, observed_at)
            for subject, quantity, observed_at in conflicting_keys
            if observed_at >= latest_clean
        ]
    if conflicting_keys:
        for subject, quantity, observed_at in conflicting_keys:
            notes.append(
                f"conflicting values for {subject} {quantity} at {observed_at.isoformat()}"
            )

    newest_observed_at = max(r.observed_at for r in deduped)
    age_s = (now - newest_observed_at).total_seconds()

    missing_count = sum(1 for r in deduped if r.value is None)
    stale_count = sum(1 for r in deduped if freshness(r, now) is Availability.stale)
    if missing_count > 0:
        noun = "reading" if missing_count == 1 else "readings"
        notes.append(f"{missing_count} {noun} missing (no value received)")

    if conflicting_keys:
        availability = Availability.conflicting
    else:
        newest = [r for r in deduped if r.observed_at == newest_observed_at]
        newest_states = [freshness(r, now) for r in newest]
        if Availability.invalid in newest_states:
            availability = Availability.invalid
            notes.append("newest record is future-dated beyond 60s skew")
        elif all(state is Availability.missing for state in newest_states):
            availability = Availability.missing
            notes.append("newest record has no value")
        elif Availability.stale in newest_states:
            availability = Availability.stale
            notes.append("newest record is stale")
        else:
            availability = Availability.available

    newest_value: float | None = None
    newest_unit: str | None = None
    for record in deduped:
        if record.observed_at == newest_observed_at and isinstance(record.value, (int, float)) and not isinstance(record.value, bool):
            newest_value = float(record.value)
            newest_unit = record.unit
            break

    return SourceStatus(
        source=source,
        availability=availability,
        record_count=len(deduped),
        newest_observed_at=newest_observed_at,
        newest_value=newest_value,
        newest_unit=newest_unit,
        age_s=age_s,
        mode=resolved_mode,
        notes=notes,
        missing_count=missing_count,
        stale_count=stale_count,
    )
