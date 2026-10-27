import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .outcomes import FollowUp
from .scheduling import validate_follow_up_time

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
        self._init_schema()

    @contextmanager
    def _connection(self, immediate=False):
        conn = sqlite3.connect(str(self.path), timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            if immediate:
                conn.execute("BEGIN IMMEDIATE")
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_schema(self):
        statements = [
            """CREATE TABLE IF NOT EXISTS investigations (
                    id TEXT PRIMARY KEY,
                    scenario TEXT NOT NULL,
                    evaluated_at TEXT NOT NULL,
                    status TEXT,
                    output TEXT,
                    model_id TEXT,
                    provider_mode TEXT,
                    prompt_version TEXT,
                    created_at TEXT NOT NULL
                )""",
            """CREATE TABLE IF NOT EXISTS follow_ups (
                    investigation_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    deadline TEXT NOT NULL,
                    target TEXT,
                    last_status TEXT,
                    last_evaluated_at TEXT,
                    supporting_ids TEXT NOT NULL DEFAULT '[]'
                )""",
            """CREATE TABLE IF NOT EXISTS outcome_events (
                    investigation_id TEXT NOT NULL,
                    evaluated_at TEXT NOT NULL,
                    status TEXT,
                    sample_count INTEGER,
                    note TEXT,
                    UNIQUE(investigation_id, evaluated_at)
                )""",
            """CREATE TABLE IF NOT EXISTS inference_requests (
                    identity_key TEXT PRIMARY KEY,
                    investigation_id TEXT NOT NULL UNIQUE,
                    scenario_id TEXT NOT NULL,
                    scenario_fixture_version TEXT NOT NULL,
                    evaluated_at_utc TEXT NOT NULL,
                    input_revision TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    readiness_policy_version TEXT NOT NULL,
                    state TEXT NOT NULL,
                    result_json TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )""",
            """CREATE TABLE IF NOT EXISTS notifications (
                    id TEXT PRIMARY KEY,
                    investigation_id TEXT NOT NULL,
                    audience TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    delivery TEXT NOT NULL DEFAULT 'simulated',
                    state TEXT NOT NULL,
                    refusal_reason TEXT
                )""",
            """CREATE TABLE IF NOT EXISTS notification_acks (
                    id TEXT PRIMARY KEY,
                    notification_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    acknowledged_at TEXT NOT NULL,
                    UNIQUE(notification_id, actor, acknowledged_at)
                )""",
        ]
        with self._connection(immediate=True) as conn:
            for statement in statements:
                conn.execute(statement)
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(follow_ups)").fetchall()}
            if "next_check_at" not in cols:
                conn.execute("ALTER TABLE follow_ups ADD COLUMN next_check_at TEXT")
            if "schedule_status" not in cols:
                conn.execute("ALTER TABLE follow_ups ADD COLUMN schedule_status TEXT")
            if "deadline_passed" not in cols:
                conn.execute("ALTER TABLE follow_ups ADD COLUMN deadline_passed INTEGER NOT NULL DEFAULT 0")

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def claim_inference(self, identity, *, retry=False):
        now = _iso(datetime.now(timezone.utc))
        with self._connection(immediate=True) as conn:
            if retry:
                cur = conn.execute(
                    "UPDATE inference_requests SET state = 'pending', result_json = NULL, attempts = attempts + 1, updated_at = ? WHERE identity_key = ? AND state = 'failed'",
                    (now, identity["identity_key"]),
                )
                if cur.rowcount == 1:
                    row = conn.execute("SELECT * FROM inference_requests WHERE identity_key = ?", (identity["identity_key"],)).fetchone()
                    return True, self._inference_from_row(row)
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO inference_requests
                    (identity_key, investigation_id, scenario_id, scenario_fixture_version, evaluated_at_utc, input_revision, prompt_version, readiness_policy_version, state, result_json, attempts, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL, 1, ?, ?)
                """,
                (identity["identity_key"], identity["investigation_id"], identity["scenario_id"], identity["scenario_fixture_version"], identity["evaluated_at_utc"], identity["input_revision"], identity["prompt_version"], identity["readiness_policy_version"], now, now),
            )
            claimed = cur.rowcount == 1
            row = conn.execute("SELECT * FROM inference_requests WHERE identity_key = ?", (identity["identity_key"],)).fetchone()
            return claimed, self._inference_from_row(row)

    @staticmethod
    def _inference_from_row(row):
        if row is None:
            return None
        return {
            "identity_key": row["identity_key"],
            "investigation_id": row["investigation_id"],
            "scenario_id": row["scenario_id"],
            "scenario_fixture_version": row["scenario_fixture_version"],
            "evaluated_at_utc": row["evaluated_at_utc"],
            "input_revision": row["input_revision"],
            "prompt_version": row["prompt_version"],
            "readiness_policy_version": row["readiness_policy_version"],
            "state": row["state"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "attempts": row["attempts"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get_inference(self, identity_key):
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM inference_requests WHERE identity_key = ?", (identity_key,)).fetchone()
        return self._inference_from_row(row)

    def complete_inference(self, identity_key, result, state):
        if state not in ("completed", "failed"):
            raise ValueError("inference state must be 'completed' or 'failed'")
        with self._connection(immediate=True) as conn:
            conn.execute(
                "UPDATE inference_requests SET state = ?, result_json = ?, updated_at = ? WHERE identity_key = ?",
                (state, json.dumps(_jsonable(result)), _iso(datetime.now(timezone.utc)), identity_key),
            )
            row = conn.execute("SELECT * FROM inference_requests WHERE identity_key = ?", (identity_key,)).fetchone()
        return self._inference_from_row(row)

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
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO investigations (id, scenario, evaluated_at, status, output, model_id, provider_mode, prompt_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (inv_id, scenario or "", _iso(evaluated_at) or _iso(created), status, output_json, model_id, provider_mode, prompt_version, _iso(created)),
            )
        return inv_id

    def get_investigation(self, investigation_id):
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM investigations WHERE id = ?", (investigation_id,)).fetchone()
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
            fields = dict(fields)
            for alias in ("when", "next_check", "scheduled_at"):
                if alias in fields and "next_check_at" not in fields:
                    fields["next_check_at"] = fields.pop(alias)
                else:
                    fields.pop(alias, None)
            data = {"investigation_id": investigation_id, **fields}
            follow_up = FollowUp.model_validate(data)
        elif isinstance(follow_up, dict):
            follow_up = dict(follow_up)
            for alias in ("when", "next_check", "scheduled_at"):
                if alias in follow_up and "next_check_at" not in follow_up:
                    follow_up["next_check_at"] = follow_up.pop(alias)
                else:
                    follow_up.pop(alias, None)
            follow_up = FollowUp.model_validate(follow_up)
        else:
            follow_up = FollowUp.model_validate(follow_up.model_dump(mode="python") if hasattr(follow_up, "model_dump") else follow_up)
        for name, value in (("created_at", follow_up.created_at), ("deadline", follow_up.deadline)):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
        if follow_up.deadline <= follow_up.created_at:
            raise ValueError("deadline_passed: deadline must be after created_at")
        if follow_up.next_check_at is not None:
            reasons = validate_follow_up_time(follow_up.next_check_at, follow_up.created_at, follow_up.deadline)
            if reasons:
                raise ValueError("; ".join(reasons))
        inv_id = investigation_id or follow_up.investigation_id
        target = json.dumps({
            "target_temp": follow_up.target_temp,
            "target_unit": follow_up.target_unit,
            "min_samples": follow_up.min_samples,
            "min_rise_f": follow_up.min_rise_f,
            "zone": follow_up.zone,
            "cadence_s": follow_up.cadence_s,
        })
        last_status = status
        last_at = evaluated_at
        ids = supporting_ids
        if outcome is not None:
            last_status = outcome.status.value if hasattr(outcome, "status") and hasattr(outcome.status, "value") else (outcome.get("status") if isinstance(outcome, dict) else last_status)
            last_at = outcome.evaluated_at if hasattr(outcome, "evaluated_at") else (outcome.get("evaluated_at") if isinstance(outcome, dict) else last_at)
            ids = outcome.supporting_ids if hasattr(outcome, "supporting_ids") else (outcome.get("supporting_ids") if isinstance(outcome, dict) else ids)
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO follow_ups (investigation_id, created_at, deadline, target, last_status, last_evaluated_at, supporting_ids, next_check_at, schedule_status, deadline_passed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(investigation_id) DO NOTHING
                """,
                (inv_id, _iso(follow_up.created_at), _iso(follow_up.deadline), target, last_status, _iso(_parse_dt(last_at)) if last_at else None, json.dumps(list(ids or [])), _iso(follow_up.next_check_at), follow_up.schedule_status, 1 if follow_up.deadline_passed else 0),
            )
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
            next_check_at=_parse_dt(row["next_check_at"]) if "next_check_at" in row.keys() else None,
            schedule_status=row["schedule_status"] if "schedule_status" in row.keys() and row["schedule_status"] else "scheduled",
            deadline_passed=bool(row["deadline_passed"]) if "deadline_passed" in row.keys() else False,
            cadence_s=target.get("cadence_s"),
        )

    def get_follow_up(self, investigation_id):
        row = self.get_follow_up_row(investigation_id)
        if row is None:
            return None
        return self._follow_up_from_row(row)

    get_followup = get_follow_up

    def get_follow_up_row(self, investigation_id):
        with self._connection() as conn:
            return self._follow_up_row_from_conn(conn, investigation_id)

    @staticmethod
    def _follow_up_row_from_conn(conn, investigation_id):
        row = conn.execute("SELECT * FROM follow_ups WHERE investigation_id = ?", (investigation_id,)).fetchone()
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
            "next_check_at": row["next_check_at"] if "next_check_at" in row.keys() else None,
            "schedule_status": row["schedule_status"] if "schedule_status" in row.keys() else None,
            "deadline_passed": bool(row["deadline_passed"]) if "deadline_passed" in row.keys() else False,
        }

    def record_outcome(self, investigation_id, outcome=None, *, status=None, evaluated_at=None, supporting_ids=None, sample_count=None, note=None):
        if outcome is not None:
            if isinstance(outcome, dict):
                status = outcome.get("status", status)
                evaluated_at = outcome.get("evaluated_at", evaluated_at)
                supporting_ids = outcome.get("supporting_ids", supporting_ids)
                sample_count = outcome.get("sample_count", sample_count)
                note = outcome.get("note", note)
            else:
                status = getattr(outcome, "status", status)
                evaluated_at = getattr(outcome, "evaluated_at", evaluated_at)
                supporting_ids = getattr(outcome, "supporting_ids", supporting_ids)
                sample_count = getattr(outcome, "sample_count", sample_count)
                note = getattr(outcome, "note", note)
        if hasattr(status, "value"):
            status = status.value
        at_iso = _iso(_parse_dt(evaluated_at)) if evaluated_at else None
        with self._connection(immediate=True) as conn:
            row = self._follow_up_row_from_conn(conn, investigation_id)
            if row is None:
                return None
            if at_iso is not None and row["last_evaluated_at"]:
                latest = _parse_dt(row["last_evaluated_at"])
                current = _parse_dt(at_iso)
                if current <= latest:
                    return row
            conn.execute(
                "UPDATE follow_ups SET last_status = ?, last_evaluated_at = ?, supporting_ids = ? WHERE investigation_id = ?",
                (status, at_iso, json.dumps(list(supporting_ids or [])), investigation_id),
            )
            if at_iso is not None:
                conn.execute(
                    "INSERT OR IGNORE INTO outcome_events (investigation_id, evaluated_at, status, sample_count, note) VALUES (?, ?, ?, ?, ?)",
                    (investigation_id, at_iso, status, sample_count, note),
                )
            return self._follow_up_row_from_conn(conn, investigation_id)

    update_follow_up = record_outcome
    save_outcome = record_outcome

    def list_outcomes(self, investigation_id, at=None):
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT investigation_id, evaluated_at, status, sample_count, note FROM outcome_events WHERE investigation_id = ? ORDER BY evaluated_at",
                (investigation_id,),
            ).fetchall()
        results = [
            {
                "investigation_id": r["investigation_id"],
                "evaluated_at": r["evaluated_at"],
                "status": r["status"],
                "sample_count": r["sample_count"],
                "note": r["note"],
            }
            for r in rows
        ]
        if at is not None:
            cutoff = _parse_dt(at)
            results = [r for r in results if _parse_dt(r["evaluated_at"]) <= cutoff]
        return results

    def save_notification(self, *, investigation_id, audience, kind, idempotency_key, payload, created_at, delivery="simulated", state="queued", refusal_reason=None):
        notif_id = f"notif-{hashlib.sha256(idempotency_key.encode()).hexdigest()[:12]}"
        with self._connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO notifications (id, investigation_id, audience, kind, idempotency_key, payload_json, created_at, delivery, state, refusal_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (notif_id, investigation_id, audience, kind, idempotency_key, json.dumps(_jsonable(payload)), _iso(_parse_dt(created_at)) or _iso(datetime.now(timezone.utc)), delivery, state, refusal_reason),
            )
            row = conn.execute("SELECT * FROM notifications WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        return self._notification_from_row(row) if row else None

    @staticmethod
    def _notification_from_row(row):
        return {
            "id": row["id"],
            "investigation_id": row["investigation_id"],
            "audience": row["audience"],
            "kind": row["kind"],
            "idempotency_key": row["idempotency_key"],
            "payload": json.loads(row["payload_json"]) if row["payload_json"] else {},
            "payload_json": row["payload_json"],
            "created_at": row["created_at"],
            "delivery": row["delivery"],
            "state": row["state"],
            "refusal_reason": row["refusal_reason"] if "refusal_reason" in row.keys() else None,
            "reason": row["refusal_reason"] if "refusal_reason" in row.keys() else None,
        }

    def update_notification_state(self, notification_id, state):
        with self._connection() as conn:
            conn.execute("UPDATE notifications SET state = ? WHERE id = ?", (state, notification_id))
            row = conn.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone()
        return self._notification_from_row(row) if row else None

    def get_notification(self, notification_id, at=None):
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM notifications WHERE id = ?", (notification_id,)).fetchone()
        if row is None:
            return None
        result = self._notification_from_row(row)
        if at is not None and _parse_dt(result["created_at"]) > _parse_dt(at):
            return None
        result["acks"] = self.list_acks(notification_id, at=at)
        return result

    def list_notifications(self, investigation_id=None, at=None):
        with self._connection() as conn:
            if investigation_id is None:
                rows = conn.execute("SELECT * FROM notifications ORDER BY created_at, audience, id").fetchall()
            else:
                rows = conn.execute("SELECT * FROM notifications WHERE investigation_id = ? ORDER BY created_at, audience, id", (investigation_id,)).fetchall()
        cutoff = _parse_dt(at) if at is not None else None
        results = []
        for row in rows:
            item = self._notification_from_row(row)
            if cutoff is not None and _parse_dt(item["created_at"]) > cutoff:
                continue
            item["acks"] = self.list_acks(item["id"], at=cutoff)
            results.append(item)
        return results

    def record_ack(self, notification_id, actor, acknowledged_at):
        at = _parse_dt(acknowledged_at)
        if at is None or at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("acknowledged_at must be timezone-aware")
        ack_id = f"ack-{hashlib.sha256(f'{notification_id}|{actor}|{_iso(at)}'.encode()).hexdigest()[:12]}"
        with self._connection() as conn:
            exists = conn.execute("SELECT id FROM notifications WHERE id = ?", (notification_id,)).fetchone()
            if exists is None:
                return None
            conn.execute(
                "INSERT OR IGNORE INTO notification_acks (id, notification_id, actor, acknowledged_at) VALUES (?, ?, ?, ?)",
                (ack_id, notification_id, str(actor), _iso(at)),
            )
            row = conn.execute("SELECT * FROM notification_acks WHERE notification_id = ? AND actor = ? AND acknowledged_at = ?", (notification_id, str(actor), _iso(at))).fetchone()
        return {"id": row["id"], "notification_id": row["notification_id"], "actor": row["actor"], "acknowledged_at": row["acknowledged_at"], "by": row["actor"], "at": row["acknowledged_at"]}

    def list_acks(self, notification_id, at=None):
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM notification_acks WHERE notification_id = ? ORDER BY acknowledged_at, actor", (notification_id,)).fetchall()
        results = [{"id": r["id"], "notification_id": r["notification_id"], "actor": r["actor"], "acknowledged_at": r["acknowledged_at"], "by": r["actor"], "at": r["acknowledged_at"]} for r in rows]
        if at is not None:
            cutoff = _parse_dt(at)
            results = [r for r in results if _parse_dt(r["acknowledged_at"]) <= cutoff]
        return results

    def list_investigations(self):
        with self._connection() as conn:
            rows = conn.execute("SELECT id FROM investigations ORDER BY created_at, id").fetchall()
        return [self.get_investigation(r["id"]) for r in rows]


SQLiteStore = Store
InvestigationStore = Store
HomeStore = Store
