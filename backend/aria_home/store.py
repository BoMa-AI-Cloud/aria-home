import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .outcomes import FollowUp

ENV_VAR = "ARIA_HOME_DB_PATH"
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "instance" / "aria_home.db"


def default_db_path():
    raw = os.environ.get(ENV_VAR)
    return Path(raw).expanduser() if raw else DEFAULT_PATH


def _iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _parse_dt(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _jsonable(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def investigation_id_for(scenario, evaluated_at):
    key = f"{scenario}|{_iso(evaluated_at)}"
    return f"inv-{hashlib.sha256(key.encode()).hexdigest()[:12]}"


class Store:
    def __init__(self, path=None):
        self.path = Path(path).expanduser() if path is not None else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS investigations (
                id TEXT PRIMARY KEY,
                scenario TEXT NOT NULL,
                evaluated_at TEXT NOT NULL,
                status TEXT,
                output TEXT,
                model_id TEXT,
                provider_mode TEXT,
                prompt_version TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS follow_ups (
                investigation_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                deadline TEXT NOT NULL,
                target TEXT,
                last_status TEXT,
                last_evaluated_at TEXT,
                supporting_ids TEXT NOT NULL DEFAULT '[]'
            );
            """
        )
        self._conn.commit()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def save_investigation(self, investigation=None, *, investigation_id=None, id=None, scenario=None, evaluated_at=None, created_at=None, status=None, output=None, model_id=None, provider_mode=None, prompt_version=None):
        inv_id = investigation_id or id
        out = output
        if investigation is not None:
            if isinstance(investigation, dict):
                inv_id = inv_id or investigation.get("id") or investigation.get("investigation_id")
                scenario = scenario or investigation.get("scenario")
                evaluated_at = evaluated_at or investigation.get("evaluated_at") or investigation.get("at")
                status = status or investigation.get("status")
                if out is None:
                    out = investigation.get("output", investigation)
                model_id = model_id or investigation.get("model_id")
                provider_mode = provider_mode or investigation.get("provider_mode")
                prompt_version = prompt_version or investigation.get("prompt_version")
                created_at = created_at or investigation.get("created_at")
            else:
                status = status or getattr(investigation, "status", None)
                if hasattr(status, "value"):
                    status = status.value
                if out is None:
                    out = getattr(investigation, "output", None)
                model_id = model_id or getattr(investigation, "model_id", None)
                provider_mode = provider_mode or getattr(investigation, "provider_mode", None)
                prompt_version = prompt_version or getattr(investigation, "prompt_version", None)
                pack = getattr(investigation, "evidence_pack", None) or {}
                if evaluated_at is None and isinstance(pack, dict):
                    evaluated_at = pack.get("at")
        if evaluated_at is not None:
            evaluated_at = _parse_dt(evaluated_at)
        if not inv_id:
            inv_id = investigation_id_for(scenario or "demo_v1", evaluated_at)
        created = _parse_dt(created_at) or evaluated_at or datetime.now(timezone.utc)
        output_json = json.dumps(_jsonable(out)) if out is not None else None
        self._conn.execute(
            """
            INSERT INTO investigations (id, scenario, evaluated_at, status, output, model_id, provider_mode, prompt_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (inv_id, scenario or "", _iso(evaluated_at) or _iso(created), status, output_json, model_id, provider_mode, prompt_version, _iso(created)),
        )
        self._conn.commit()
        return inv_id

    def get_investigation(self, investigation_id):
        row = self._conn.execute("SELECT * FROM investigations WHERE id = ?", (investigation_id,)).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "scenario": row["scenario"],
            "evaluated_at": row["evaluated_at"],
            "status": row["status"],
            "output": json.loads(row["output"]) if row["output"] else None,
            "model_id": row["model_id"],
            "provider_mode": row["provider_mode"],
            "prompt_version": row["prompt_version"],
            "created_at": row["created_at"],
        }

    def save_follow_up(self, follow_up=None, *, investigation_id=None, outcome=None, status=None, evaluated_at=None, supporting_ids=None, **fields):
        if follow_up is None:
            data = {"investigation_id": investigation_id, **fields}
            follow_up = FollowUp.model_validate(data)
        elif isinstance(follow_up, dict):
            follow_up = FollowUp.model_validate(follow_up)
        inv_id = investigation_id or follow_up.investigation_id
        target = json.dumps({
            "target_temp": follow_up.target_temp,
            "target_unit": follow_up.target_unit,
            "min_samples": follow_up.min_samples,
            "min_rise_f": follow_up.min_rise_f,
            "zone": follow_up.zone,
        })
        last_status = status
        last_at = evaluated_at
        ids = supporting_ids
        if outcome is not None:
            last_status = outcome.status.value if hasattr(outcome, "status") and hasattr(outcome.status, "value") else (outcome.get("status") if isinstance(outcome, dict) else last_status)
            last_at = outcome.evaluated_at if hasattr(outcome, "evaluated_at") else (outcome.get("evaluated_at") if isinstance(outcome, dict) else last_at)
            ids = outcome.supporting_ids if hasattr(outcome, "supporting_ids") else (outcome.get("supporting_ids") if isinstance(outcome, dict) else ids)
        self._conn.execute(
            """
            INSERT INTO follow_ups (investigation_id, created_at, deadline, target, last_status, last_evaluated_at, supporting_ids)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(investigation_id) DO NOTHING
            """,
            (inv_id, _iso(follow_up.created_at), _iso(follow_up.deadline), target, last_status, _iso(_parse_dt(last_at)) if last_at else None, json.dumps(list(ids or []))),
        )
        self._conn.commit()
        if outcome is not None:
            self.record_outcome(inv_id, outcome)
        return inv_id

    create_follow_up = save_follow_up
    save_followup = save_follow_up

    def _follow_up_from_row(self, row):
        raw_target = row["target"]
        target = json.loads(raw_target) if isinstance(raw_target, str) else (raw_target or {})
        if isinstance(target, (int, float)):
            target = {"target_temp": float(target), "target_unit": "F"}
        return FollowUp(
            investigation_id=row["investigation_id"],
            created_at=_parse_dt(row["created_at"]),
            target_temp=target.get("target_temp", target.get("temp")),
            target_unit=target.get("target_unit", target.get("unit", "F")),
            deadline=_parse_dt(row["deadline"]),
            min_samples=target.get("min_samples", 3),
            min_rise_f=target.get("min_rise_f", 2.0),
            zone=target.get("zone", "demo-cabin/main"),
        )

    def get_follow_up(self, investigation_id):
        row = self.get_follow_up_row(investigation_id)
        if row is None:
            return None
        return self._follow_up_from_row(row)

    get_followup = get_follow_up

    def get_follow_up_row(self, investigation_id):
        row = self._conn.execute("SELECT * FROM follow_ups WHERE investigation_id = ?", (investigation_id,)).fetchone()
        if row is None:
            return None
        return {
            "investigation_id": row["investigation_id"],
            "created_at": row["created_at"],
            "deadline": row["deadline"],
            "target": json.loads(row["target"]) if row["target"] else None,
            "last_status": row["last_status"],
            "status": row["last_status"],
            "last_evaluated_at": row["last_evaluated_at"],
            "supporting_ids": json.loads(row["supporting_ids"] or "[]"),
        }

    def record_outcome(self, investigation_id, outcome=None, *, status=None, evaluated_at=None, supporting_ids=None):
        if outcome is not None:
            if isinstance(outcome, dict):
                status = outcome.get("status", status)
                evaluated_at = outcome.get("evaluated_at", evaluated_at)
                supporting_ids = outcome.get("supporting_ids", supporting_ids)
            else:
                status = getattr(outcome, "status", status)
                evaluated_at = getattr(outcome, "evaluated_at", evaluated_at)
                supporting_ids = getattr(outcome, "supporting_ids", supporting_ids)
        if hasattr(status, "value"):
            status = status.value
        at_iso = _iso(_parse_dt(evaluated_at)) if evaluated_at else None
        row = self.get_follow_up_row(investigation_id)
        if row is None:
            return None
        if at_iso is not None and row["last_evaluated_at"] == at_iso:
            return row
        self._conn.execute(
            "UPDATE follow_ups SET last_status = ?, last_evaluated_at = ?, supporting_ids = ? WHERE investigation_id = ?",
            (status, at_iso, json.dumps(list(supporting_ids or [])), investigation_id),
        )
        self._conn.commit()
        return self.get_follow_up_row(investigation_id)

    update_follow_up = record_outcome
    save_outcome = record_outcome

    def list_investigations(self):
        rows = self._conn.execute("SELECT id FROM investigations ORDER BY created_at, id").fetchall()
        return [self.get_investigation(r["id"]) for r in rows]


SQLiteStore = Store
InvestigationStore = Store
HomeStore = Store
