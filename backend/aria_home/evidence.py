from collections import defaultdict
from datetime import datetime, timedelta

from .clock import ensure_aware
from .contracts import Availability, DataMode, EvidenceRecord, SourceKind, SourceStatus

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
    relevant = [r for r in records if r.source is source]

    seen: set[str] = set()
    deduped: list[EvidenceRecord] = []
    duplicates = 0
    for record in relevant:
        if record.id in seen:
            duplicates += 1
            continue
        seen.add(record.id)
        deduped.append(record)

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
            age_s=None,
            mode=resolved_mode,
            notes=notes,
        )

    groups: dict[tuple, set] = defaultdict(set)
    for record in deduped:
        groups[(record.subject, record.quantity, record.observed_at)].add(record.value)
    conflicting_keys = [key for key, values in groups.items() if len(values) > 1]
    if conflicting_keys:
        for subject, quantity, observed_at in conflicting_keys:
            notes.append(
                f"conflicting values for {subject} {quantity} at {observed_at.isoformat()}"
            )

    newest_observed_at = max(r.observed_at for r in deduped)
    age_s = (now - newest_observed_at).total_seconds()

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

    return SourceStatus(
        source=source,
        availability=availability,
        record_count=len(deduped),
        newest_observed_at=newest_observed_at,
        age_s=age_s,
        mode=resolved_mode,
        notes=notes,
    )
