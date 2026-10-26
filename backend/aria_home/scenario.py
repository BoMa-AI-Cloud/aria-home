import json
from dataclasses import dataclass, field
from datetime import date, datetime
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


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_scenario(path) -> Scenario:
    base = Path(path)
    if base.is_file():
        base = base.parent
    manifest = ScenarioManifest.model_validate(_read_json(base / "manifest.json"))

    records: list[EvidenceRecord] = []
    trip: Trip | None = None
    confirmation: HomeownerConfirmation | None = None

    for filename in SOURCE_FILES:
        payload = _read_json(base / filename)
        if isinstance(payload, list):
            rows = payload
            extra = {}
        else:
            rows = payload.get("records", [])
            extra = payload
        if extra.get("trip") is not None:
            trip = Trip.model_validate(extra["trip"])
        if extra.get("confirmation") is not None:
            confirmation = HomeownerConfirmation.model_validate(extra["confirmation"])
        for row in rows:
            data = dict(row)
            data["mode"] = manifest.mode.value
            records.append(EvidenceRecord.model_validate(data))

    return Scenario(manifest=manifest, records=records, trip=trip, confirmation=confirmation, path=base)


def visible_records(records: list[EvidenceRecord], now: datetime) -> list[EvidenceRecord]:
    ensure_aware(now, "now")
    return [r for r in records if r.received_at <= now]
