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
    timezone: str = "America/New_York"
    scenario_period_note: str | None = None

    @field_validator("start")
    @classmethod
    def _aware(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("manifest start must be timezone-aware")
        return value


class ScenarioEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    event_time: datetime
    available_at: datetime
    simulated: bool = True
    payload: dict = Field(default_factory=dict)

    @field_validator("event_time", "available_at")
    @classmethod
    def _aware(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event datetimes must be timezone-aware")
        return value


SimulatedEvent = ScenarioEvent
ActorEvent = ScenarioEvent


@dataclass
class Scenario:
    manifest: ScenarioManifest
    records: list[EvidenceRecord]
    trip: Trip | None = None
    confirmation: HomeownerConfirmation | None = None
    confirmations: list[HomeownerConfirmation] = field(default_factory=list)
    path: Path | None = field(default=None, repr=False)
    trips: list[Trip] = field(default_factory=list)
    events: list["ScenarioEvent"] = field(default_factory=list)
    arrival_plan: dict | None = None
    visual: dict | None = None
    visuals: list = field(default_factory=list)

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


def _confirmation_history(scenario) -> list[HomeownerConfirmation]:
    listed = list(getattr(scenario, "confirmations", None) or []) if scenario is not None else []
    single = getattr(scenario, "confirmation", None) if scenario is not None else None
    if listed and (single is None or any(item is single for item in listed)):
        history = listed
    elif single is not None:
        history = [single]
    else:
        history = listed
    unique: list[HomeownerConfirmation] = []
    for item in history:
        if item not in unique:
            unique.append(item)
    return sorted(unique, key=lambda item: item.confirmed_at)


def context_as_of(scenario, now: datetime) -> AsOfContext:
    ensure_aware(now, "now")
    history = _trip_history(scenario)
    visible = [t for t in history if t.known_at is None or t.known_at <= now]
    trip = visible[-1] if visible else None
    confirmation_history = _confirmation_history(scenario)
    visible_confirmations = [c for c in confirmation_history if c.confirmed_at <= now]
    raw_confirmation = visible_confirmations[-1] if visible_confirmations else None
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
    return replace(scenario, trip=ctx.trip, confirmation=ctx.confirmation, confirmations=[ctx.confirmation] if ctx.confirmation is not None else [], trips=list(ctx.trips))


as_of_scenario = scenario_as_of


def load_scenario(path) -> Scenario:
    base = Path(path)
    if base.is_file():
        base = base.parent
    manifest = ScenarioManifest.model_validate(_read_json(base / "manifest.json"))

    records: list[EvidenceRecord] = []
    trips: list[Trip] = []
    confirmation: HomeownerConfirmation | None = None
    confirmations: list[HomeownerConfirmation] = []
    arrival_plan: dict | None = None

    source_files = list(SOURCE_FILES)
    if (base / "room_sensor.json").is_file():
        source_files.append("room_sensor.json")
    for filename in source_files:
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
            if confirmation not in confirmations:
                confirmations.append(confirmation)
        if isinstance(extra.get("arrival_plan"), dict):
            arrival_plan = dict(extra["arrival_plan"])
        if isinstance(extra.get("confirmations"), list):
            for item in extra["confirmations"]:
                candidate = HomeownerConfirmation.model_validate(item)
                if candidate not in confirmations:
                    confirmations.append(candidate)
                confirmation = candidate
        for row in rows:
            data = dict(row)
            data["mode"] = manifest.mode.value
            records.append(EvidenceRecord.model_validate(data))

    trips = sorted(trips, key=_trip_sort_key)
    trip = trips[-1] if trips else None
    events: list[ScenarioEvent] = []
    events_path = base / "events.json"
    if events_path.is_file():
        events_payload = _read_json(events_path)
        if isinstance(events_payload, list):
            event_rows = events_payload
        else:
            event_rows = events_payload.get("events", events_payload.get("records", []))
        events = [ScenarioEvent.model_validate(row) for row in event_rows]
    visual = None
    visuals: list = []
    visual_path = base / "visual.json"
    if visual_path.is_file():
        from .visual import ReplayVisualProvider

        spec = _read_json(visual_path)
        specs = spec if isinstance(spec, list) else [spec]
        for item in specs:
            observation = ReplayVisualProvider().observe(
                item["image_id"],
                item["phrase"],
                observed_at=item["observed_at"],
                received_at=item["received_at"],
                file=item.get("file"),
            )
            record = observation.as_dict()
            if item.get("known_miss"):
                record["known_miss"] = True
            if isinstance(spec, list):
                visuals.append(record)
            else:
                visual = record
    return Scenario(manifest=manifest, records=records, trip=trip, confirmation=confirmation, confirmations=sorted(confirmations, key=lambda item: item.confirmed_at), path=base, trips=trips, events=events, arrival_plan=arrival_plan, visual=visual, visuals=visuals)


def visible_records(records: list[EvidenceRecord], now: datetime) -> list[EvidenceRecord]:
    ensure_aware(now, "now")
    return [r for r in records if r.received_at <= now]


def events_as_of(scenario, now: datetime) -> list[ScenarioEvent]:
    ensure_aware(now, "now")
    return [event for event in (getattr(scenario, "events", None) or []) if event.available_at <= now]


def _visual_received(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def visual_as_of(scenario, now: datetime) -> dict | None:
    ensure_aware(now, "now")
    candidates = list(getattr(scenario, "visuals", None) or [])
    single = getattr(scenario, "visual", None)
    if isinstance(single, dict):
        candidates.append(single)
    best = None
    best_received = None
    for item in candidates:
        if not isinstance(item, dict):
            continue
        received = _visual_received(item.get("received_at"))
        if received is not None and received > now:
            continue
        if best is None or (received is not None and (best_received is None or received > best_received)):
            best, best_received = item, received
    return best
