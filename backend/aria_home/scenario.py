import json
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .clock import ensure_aware
from .contracts import (
    DataMode,
    EvidenceRecord,
    HomeownerConfirmation,
    Trip,
)

SOURCE_FILES = ("calendar.json", "thermostat.json", "electrical.json", "weather.json")

_MIN_AWARE = datetime.min.replace(tzinfo=timezone.utc)


class ScenarioManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    mode: DataMode
    description: str
    author: str
    created: date
    start: datetime
    scenario_period_note: str | None = None

    @field_validator("start")
    @classmethod
    def _aware(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("manifest start must be timezone-aware")
        return value


@dataclass
class Scenario:
    manifest: ScenarioManifest
    records: list[EvidenceRecord]
    trip: Trip | None = None
    confirmation: HomeownerConfirmation | None = None
    path: Path | None = field(default=None, repr=False)
    trips: list[Trip] = field(default_factory=list)

    @property
    def trip_revisions(self):
        return _trip_history(self)


@dataclass
class AsOfContext:
    at: datetime
    trip: Trip | None = None
    confirmation: HomeownerConfirmation | None = None
    flags: dict = field(default_factory=dict)
    trips: list[Trip] = field(default_factory=list)

    @property
    def cancelled(self):
        return bool(self.flags.get("trip_cancelled"))

    @property
    def unconfirmed(self):
        return bool(self.flags.get("trip_unconfirmed"))

    @property
    def mismatched(self):
        return bool(self.flags.get("trip_mismatched"))

    @property
    def outdated(self):
        return bool(self.flags.get("confirmation_outdated"))

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def as_dict(self):
        return {
            "at": self.at.isoformat() if isinstance(self.at, datetime) else self.at,
            "trip": self.trip.model_dump(mode="json") if self.trip is not None else None,
            "confirmation": self.confirmation.model_dump(mode="json") if self.confirmation is not None else None,
            "flags": dict(self.flags),
            "readiness_flags": dict(self.flags),
        }


TripContext = AsOfContext
ContextAsOf = AsOfContext


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _trip_sort_key(trip: Trip):
    return (trip.known_at or _MIN_AWARE, trip.revision, trip.revision_id or "")


def _trip_history(scenario) -> list[Trip]:
    history: list[Trip] = []
    raw = []
    if scenario is not None:
        raw.extend(getattr(scenario, "trips", None) or [])
        single = getattr(scenario, "trip", None)
        if single is not None:
            raw.append(single)
    for trip in raw:
        if trip is None:
            continue
        replaced_same = False
        for idx, existing in enumerate(history):
            if existing == trip:
                replaced_same = True
                break
            if (
                existing.id == trip.id
                and existing.revision == trip.revision
                and single is not None
                and trip is single
            ):
                history[idx] = trip
                replaced_same = True
                break
        if not replaced_same and trip not in history:
            history.append(trip)
    return sorted(history, key=_trip_sort_key)


def _same_temp(a, a_unit, b, b_unit) -> bool:
    if a is None or b is None:
        return True
    if a_unit and b_unit and a_unit != b_unit:
        def to_f(v, u):
            return v * 9.0 / 5.0 + 32.0 if u == "C" else float(v)
        return abs(to_f(float(a), a_unit) - to_f(float(b), b_unit)) < 1e-9
    return float(a) == float(b)


def _materially_changed(reference: Trip | None, current: Trip | None, confirmation=None) -> bool:
    if reference is None or current is None:
        return False
    if reference.planned_arrival != current.planned_arrival:
        return True
    if not _same_temp(reference.target_temp, reference.target_unit, current.target_temp, current.target_unit):
        return True
    if confirmation is not None and current.target_temp is not None:
        if not _same_temp(confirmation.target_temp, confirmation.target_unit, current.target_temp, current.target_unit):
            return True
    return False


def _confirmation_reference(confirmation, history, current):
    revision_id = getattr(confirmation, "revision_id", None) or getattr(confirmation, "trip_revision_id", None)
    if revision_id:
        for trip in history:
            if trip.revision_id == revision_id:
                return trip
        return None
    trip_revision = getattr(confirmation, "trip_revision", None)
    if trip_revision is not None:
        for trip in history:
            if trip.id == confirmation.trip_id and trip.revision == trip_revision:
                return trip
        return None
    prior = [t for t in history if t.id == confirmation.trip_id and (t.known_at is None or t.known_at <= confirmation.confirmed_at)]
    return prior[-1] if prior else None


def context_as_of(scenario, now: datetime) -> AsOfContext:
    ensure_aware(now, "now")
    history = _trip_history(scenario)
    visible = [t for t in history if t.known_at is None or t.known_at <= now]
    trip = visible[-1] if visible else None
    raw_confirmation = getattr(scenario, "confirmation", None) if scenario is not None else None
    flags = {
        "trip_cancelled": False,
        "trip_unconfirmed": False,
        "trip_mismatched": False,
        "confirmation_outdated": False,
    }
    confirmation = None
    if trip is None:
        flags["trip_unconfirmed"] = True
    elif trip.cancelled:
        flags["trip_cancelled"] = True
    elif raw_confirmation is None:
        flags["trip_unconfirmed"] = True
    elif raw_confirmation.confirmed_at > now:
        flags["trip_unconfirmed"] = True
    elif raw_confirmation.trip_id != trip.id or raw_confirmation.property_id != trip.property_id:
        flags["trip_mismatched"] = True
    else:
        reference = _confirmation_reference(raw_confirmation, history, trip)
        explicit_id = getattr(raw_confirmation, "revision_id", None) or getattr(raw_confirmation, "trip_revision_id", None)
        explicit_rev = getattr(raw_confirmation, "trip_revision", None)
        is_current = reference is not None and (
            reference.revision_id == trip.revision_id and reference.revision == trip.revision
        ) if reference is not None else False
        if reference is not None and not is_current and _materially_changed(reference, trip, raw_confirmation):
            flags["confirmation_outdated"] = True
        elif reference is not None and not is_current:
            confirmation = raw_confirmation
        elif reference is None and (explicit_id is not None or explicit_rev is not None):
            if explicit_id is not None and explicit_id != trip.revision_id:
                flags["confirmation_outdated"] = True
            elif explicit_rev is not None and explicit_rev != trip.revision:
                flags["confirmation_outdated"] = True
            else:
                confirmation = raw_confirmation
        elif reference is None:
            prior = [t for t in history if t.id == raw_confirmation.trip_id and (t.known_at is None or t.known_at <= raw_confirmation.confirmed_at)]
            ref_at_confirmation = prior[-1] if prior else None
            if ref_at_confirmation is not None and (ref_at_confirmation.revision != trip.revision or ref_at_confirmation.revision_id != trip.revision_id) and _materially_changed(ref_at_confirmation, trip, raw_confirmation):
                flags["confirmation_outdated"] = True
            else:
                confirmation = raw_confirmation
        else:
            confirmation = raw_confirmation
    return AsOfContext(at=now, trip=trip, confirmation=confirmation, flags=flags, trips=visible)


as_of_context = context_as_of
visible_context = context_as_of
trip_context_as_of = context_as_of
context_at = context_as_of
get_context_as_of = context_as_of


def scenario_as_of(scenario, now: datetime) -> Scenario:
    ctx = context_as_of(scenario, now)
    return replace(scenario, trip=ctx.trip, confirmation=ctx.confirmation, trips=list(ctx.trips))


as_of_scenario = scenario_as_of


def load_scenario(path) -> Scenario:
    base = Path(path)
    if base.is_file():
        base = base.parent
    manifest = ScenarioManifest.model_validate(_read_json(base / "manifest.json"))

    records: list[EvidenceRecord] = []
    trips: list[Trip] = []
    confirmation: HomeownerConfirmation | None = None

    for filename in SOURCE_FILES:
        payload = _read_json(base / filename)
        if isinstance(payload, list):
            rows = payload
            extra = {}
        else:
            rows = payload.get("records", [])
            extra = payload
        for key in ("trips", "trip_revisions", "revisions"):
            if isinstance(extra.get(key), list):
                for item in extra[key]:
                    trip_obj = Trip.model_validate(item)
                    if trip_obj not in trips:
                        trips.append(trip_obj)
        if extra.get("trip") is not None:
            trip_obj = Trip.model_validate(extra["trip"])
            if trip_obj not in trips:
                trips.append(trip_obj)
        cancellation = extra.get("trip_cancellation") or extra.get("cancellation")
        if isinstance(cancellation, dict) and trips:
            known = cancellation.get("known_at") or cancellation.get("cancelled_at")
            if known is not None:
                base_trip = sorted(trips, key=_trip_sort_key)[-1]
                cancelled_trip = Trip.model_validate({
                    "id": cancellation.get("trip_id") or cancellation.get("id") or base_trip.id,
                    "property_id": cancellation.get("property_id") or base_trip.property_id,
                    "title": cancellation.get("title") or base_trip.title,
                    "planned_arrival": cancellation.get("planned_arrival") or base_trip.planned_arrival.isoformat(),
                    "revision": cancellation.get("revision", base_trip.revision + 1),
                    "cancelled": True,
                    "known_at": known,
                    "revision_id": cancellation.get("revision_id"),
                    "target_temp": cancellation.get("target_temp", base_trip.target_temp),
                    "target_unit": cancellation.get("target_unit", base_trip.target_unit),
                })
                if cancelled_trip not in trips:
                    trips.append(cancelled_trip)
        if extra.get("confirmation") is not None:
            confirmation = HomeownerConfirmation.model_validate(extra["confirmation"])
        for row in rows:
            data = dict(row)
            data["mode"] = manifest.mode.value
            records.append(EvidenceRecord.model_validate(data))

    trips = sorted(trips, key=_trip_sort_key)
    trip = trips[-1] if trips else None
    return Scenario(manifest=manifest, records=records, trip=trip, confirmation=confirmation, path=base, trips=trips)


def visible_records(records: list[EvidenceRecord], now: datetime) -> list[EvidenceRecord]:
    ensure_aware(now, "now")
    return [r for r in records if r.received_at <= now]
