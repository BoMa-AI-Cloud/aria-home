from collections import Counter
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .clock import ensure_aware
from .contracts import Availability, BindingStatus, EvidenceKind, EvidenceRecord
from .evidence import freshness
from .metrics import NOISE_FLOOR_W, _cadence_coverage, _largest_gap_s

BANNED_PHRASES = (
    "power is normal",
    "no outage",
    "outage confirmed",
    "breaker tripped",
    "the furnace has power",
)

EXACT_DEMO_STATEMENT = (
    "Fresh activity is observed on other monitored circuits. "
    "This weighs against complete property power loss during this window, "
    "but does not independently confirm power to the heating equipment."
)


class CircuitStatus(str, Enum):
    fresh_active = "fresh_active"
    fresh_quiet = "fresh_quiet"
    stale = "stale"
    missing = "missing"
    invalid = "invalid"
    conflicting = "conflicting"


class MainsStatus(str, Enum):
    not_available = "not_available"
    measured_fresh = "measured_fresh"
    measured_stale = "measured_stale"
    calculated_only = "calculated_only"


class HeatingBinding(str, Enum):
    confirmed = "confirmed"
    candidate_only = "candidate_only"
    unknown = "unknown"


class BackupStatus(str, Enum):
    known_none = "known_none"
    known_present = "known_present"
    unknown = "unknown"


class Continuity(str, Enum):
    activity_weighs_against_total_loss = "activity_weighs_against_total_loss"
    visibility_lost = "visibility_lost"
    insufficient_evidence = "insufficient_evidence"
    conflicting_evidence = "conflicting_evidence"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CircuitContext(_Model):
    circuit_id: str
    binding: BindingStatus = BindingStatus.unknown
    status: CircuitStatus
    age_s: float | None = None
    last_value: float | None = None
    last_observed_at: datetime | None = None


class Lineage(_Model):
    meter_ids: list[str] = Field(default_factory=list)
    lineage_count: int = 0
    counts_by_status: dict[str, int] = Field(default_factory=dict)
    coverage: float = 0.0
    largest_gap_s: float | None = None


class PowerContext(_Model):
    per_circuit: list[CircuitContext] = Field(default_factory=list)
    lineage: Lineage = Field(default_factory=Lineage)
    mains: MainsStatus = MainsStatus.not_available
    heating_binding: HeatingBinding = HeatingBinding.unknown
    backup: BackupStatus = BackupStatus.unknown
    continuity: Continuity = Continuity.insufficient_evidence
    statement: str
    limitations: list[str] = Field(default_factory=list)
    window_start: datetime
    now: datetime

    @model_validator(mode="after")
    def _no_banned_phrases(self):
        texts = [self.statement, *self.limitations]
        lowered = " ".join(texts).lower()
        for phrase in BANNED_PHRASES:
            if phrase in lowered:
                raise ValueError(f"banned phrase in generated text: {phrase}")
        if not self.limitations:
            raise ValueError("limitations must be non-empty")
        return self


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _circuit_id(record: EvidenceRecord) -> str:
    return record.binding.circuit_id if record.binding and record.binding.circuit_id else record.subject


def _binding_status(records: list[EvidenceRecord]) -> BindingStatus:
    rank = {BindingStatus.confirmed: 2, BindingStatus.candidate: 1, BindingStatus.unknown: 0}
    statuses = [(r.binding.status if r.binding else BindingStatus.unknown) for r in records]
    if not statuses:
        return BindingStatus.unknown
    counts = Counter(statuses)
    top = max(counts.values())
    return sorted([s for s, n in counts.items() if n == top], key=lambda s: rank[s])[-1]


def _normalize_backup(backup) -> BackupStatus:
    if isinstance(backup, BackupStatus):
        return backup
    value = str(backup).strip().lower().replace("-", "_").replace(" ", "_")
    if value in {"known_none", "none", "no_backup", "absent"}:
        return BackupStatus.known_none
    if value in {"known_present", "present", "has_backup", "backup_present"}:
        return BackupStatus.known_present
    return BackupStatus.unknown


def _is_mains_record(record: EvidenceRecord) -> bool:
    quantity = record.quantity.lower()
    subject = record.subject.lower()
    if any(token in quantity for token in ("mains", "main_power", "service", "leg", "utility")):
        return True
    if any(token in subject for token in ("mains", "service-leg", "service_leg")) and (
        "power" in quantity or "voltage" in quantity or "leg" in quantity
    ):
        return True
    if "leg" in subject and ("power" in quantity or "voltage" in quantity):
        return True
    return False


def _leg_key(record: EvidenceRecord) -> str | None:
    text = f"{record.subject} {record.quantity}".lower().replace("-", "_")
    if "leg_1" in text or "leg1" in text or "leg_a" in text or "_l1" in text or "phase_1" in text or "phase_a" in text:
        return "leg1"
    if "leg_2" in text or "leg2" in text or "leg_b" in text or "_l2" in text or "phase_2" in text or "phase_b" in text:
        return "leg2"
    return None


def _both_legs_measured_fresh_nonzero(records: list[EvidenceRecord], now: datetime) -> bool:
    legs: dict[str, bool] = {}
    for record in records:
        leg = _leg_key(record)
        if leg is None:
            continue
        if record.kind is not EvidenceKind.measurement:
            continue
        if not _is_number(record.value) or float(record.value) == 0:
            continue
        if freshness(record, now) is Availability.available:
            legs[leg] = True
    return legs.get("leg1", False) and legs.get("leg2", False)


def _mains_status(records: list[EvidenceRecord], now: datetime) -> MainsStatus:
    mains = [r for r in records if _is_mains_record(r)]
    if not mains:
        return MainsStatus.not_available
    measured = [r for r in mains if r.kind is EvidenceKind.measurement]
    if not measured:
        return MainsStatus.calculated_only
    if any(freshness(r, now) is Availability.available and _is_number(r.value) for r in measured):
        return MainsStatus.measured_fresh
    return MainsStatus.measured_stale


def power_context(records, window_start, now, noise_floor_w=NOISE_FLOOR_W, backup="unknown"):
    ensure_aware(window_start, "window_start")
    ensure_aware(now, "now")
    backup_status = _normalize_backup(backup)
    records = list(records)

    seen: set[str] = set()
    deduped: list[EvidenceRecord] = []
    for record in records:
        if record.id in seen:
            continue
        seen.add(record.id)
        deduped.append(record)

    circuit_records = [r for r in deduped if r.quantity == "circuit_power"]
    by_circuit: dict[str, list[EvidenceRecord]] = {}
    for record in circuit_records:
        by_circuit.setdefault(_circuit_id(record), []).append(record)

    heating_circuit_ids = {
        _circuit_id(r)
        for r in circuit_records
        if r.binding and r.binding.equipment == "furnace"
    }

    per_circuit: list[CircuitContext] = []
    for circuit_id in sorted(by_circuit):
        group = sorted(by_circuit[circuit_id], key=lambda r: r.observed_at)
        binding = _binding_status(group)

        groups: dict[datetime, set] = {}
        for record in group:
            groups.setdefault(record.observed_at, set()).add(record.value)
        has_conflict = any(len(values) > 1 for values in groups.values())

        valid = [r for r in group if freshness(r, now) is not Availability.invalid]
        newest = valid[-1] if valid else group[-1]
        age_s = (now - newest.observed_at).total_seconds()
        last_value = float(newest.value) if _is_number(newest.value) else None

        if has_conflict:
            status = CircuitStatus.conflicting
        elif not valid:
            status = CircuitStatus.invalid
        else:
            state = freshness(newest, now)
            if state is Availability.invalid:
                status = CircuitStatus.invalid
            elif state is Availability.missing or newest.value is None:
                status = CircuitStatus.missing
                last_value = None
            elif not _is_number(newest.value):
                status = CircuitStatus.invalid
            elif state is Availability.stale:
                status = CircuitStatus.stale
            elif float(newest.value) > noise_floor_w:
                status = CircuitStatus.fresh_active
            else:
                status = CircuitStatus.fresh_quiet

        per_circuit.append(
            CircuitContext(
                circuit_id=circuit_id,
                binding=binding,
                status=status,
                age_s=age_s,
                last_value=last_value,
                last_observed_at=newest.observed_at,
            )
        )

    furnace_records = [
        r for r in circuit_records if r.binding and r.binding.equipment == "furnace"
    ]
    if any(r.binding and r.binding.status is BindingStatus.confirmed for r in furnace_records):
        heating_binding = HeatingBinding.confirmed
    elif any(r.binding and r.binding.status is BindingStatus.candidate for r in furnace_records):
        heating_binding = HeatingBinding.candidate_only
    else:
        heating_binding = HeatingBinding.unknown

    meter_ids = sorted({r.provenance.fixture_id for r in circuit_records if r.provenance and r.provenance.fixture_id})
    counts_by_status = dict(Counter(c.status.value for c in per_circuit))
    window_times = sorted(
        r.observed_at
        for r in circuit_records
        if window_start <= r.observed_at <= now
        and r.received_at <= now
        and _is_number(r.value)
        and freshness(r, now) is not Availability.invalid
    )
    cadence_s = next((r.expected_cadence_s for r in circuit_records if r.expected_cadence_s is not None), None)
    coverage, _, _ = _cadence_coverage(window_times, cadence_s, window_start, now)
    lineage = Lineage(
        meter_ids=meter_ids,
        lineage_count=len(meter_ids),
        counts_by_status=counts_by_status,
        coverage=coverage,
        largest_gap_s=_largest_gap_s(window_times),
    )

    mains = _mains_status(deduped, now)

    other_active = any(
        c.status is CircuitStatus.fresh_active for c in per_circuit if c.circuit_id not in heating_circuit_ids
    )
    any_active = any(c.status is CircuitStatus.fresh_active for c in per_circuit)
    active_for_continuity = other_active if heating_circuit_ids else any_active
    any_fresh = any(c.status in (CircuitStatus.fresh_active, CircuitStatus.fresh_quiet) for c in per_circuit)
    any_conflicting = any(c.status is CircuitStatus.conflicting for c in per_circuit)

    if any_conflicting:
        continuity = Continuity.conflicting_evidence
    elif active_for_continuity:
        continuity = Continuity.activity_weighs_against_total_loss
    elif any_fresh:
        continuity = Continuity.insufficient_evidence
    elif per_circuit:
        continuity = Continuity.visibility_lost
    else:
        continuity = Continuity.insufficient_evidence

    if continuity is Continuity.activity_weighs_against_total_loss:
        if heating_binding is HeatingBinding.confirmed and backup_status is not BackupStatus.known_present:
            statement = EXACT_DEMO_STATEMENT
        elif heating_binding is HeatingBinding.confirmed:
            statement = (
                "Fresh activity is observed on other monitored circuits. "
                "Backup power may be supplying power to those circuits. "
                "This weighs against complete property power loss during this window, "
                "but does not independently confirm power to the heating equipment."
            )
        elif backup_status is BackupStatus.known_present:
            statement = (
                "Fresh activity is observed on other monitored circuits. "
                "Backup power may be supplying power to those circuits. "
                "This weighs against complete property power loss during this window."
            )
        else:
            statement = (
                "Fresh activity is observed on other monitored circuits. "
                "This weighs against complete property power loss during this window."
            )
    elif continuity is Continuity.visibility_lost:
        statement = (
            "No fresh readings are observed on monitored circuits for this window. "
            "Visibility is lost; missing readings do not by themselves indicate a loss of power."
        )
    elif continuity is Continuity.conflicting_evidence:
        statement = (
            "Conflicting readings are observed on monitored circuits. "
            "This is insufficient evidence to assess broader power continuity during this window."
        )
    elif any_fresh:
        statement = (
            "Fresh readings are observed on monitored circuits, but no activity above the "
            "configured threshold is observed. This is insufficient evidence to assess "
            "broader power continuity during this window."
        )
    else:
        statement = (
            "No usable readings are observed on monitored circuits for this window. "
            "This is insufficient evidence to assess broader power continuity during this window."
        )

    limitations: list[str] = []
    if not _both_legs_measured_fresh_nonzero(deduped, now):
        limitations.append("Cannot exclude a lost service leg.")
    limitations.append("Breaker or equipment supply problems are not observable from branch readings.")
    limitations.append("Interruptions outside this window are not covered.")
    if backup_status is BackupStatus.unknown:
        limitations.append("Backup-power configuration unknown.")

    return PowerContext(
        per_circuit=per_circuit,
        lineage=lineage,
        mains=mains,
        heating_binding=heating_binding,
        backup=backup_status,
        continuity=continuity,
        statement=statement,
        limitations=limitations,
        window_start=window_start,
        now=now,
    )
