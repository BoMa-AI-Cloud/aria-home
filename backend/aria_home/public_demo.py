"""Public-demo mode: restricted single-process hosting of the real app.

Enabled with ARIA_HOME_PUBLIC_DEMO=1. The same Flask app serves the built
frontend (frontend/dist) and a restricted API with per-visitor isolated
SQLite state. Live, delivery, sensor and paid paths are not registered at
all, and the app refuses to start when any live flag is set alongside the
demo flag (fail closed).
"""

import hashlib
import os
import re
import secrets
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

PUBLIC_DEMO_ENV = "ARIA_HOME_PUBLIC_DEMO"
SESSIONS_DIR_ENV = "ARIA_HOME_PUBLIC_DEMO_DIR"
MAX_BYTES_ENV = "ARIA_HOME_PUBLIC_DEMO_MAX_BYTES"

LIVE_FLAGS = (
    "ARIA_HOME_MODEL_ENABLED",
    "ARIA_HOME_WHATSAPP_LIVE",
    "ARIA_HOME_EMPORIA_LIVE",
    "ARIA_HOME_VISUAL_LIVE",
    "ARIA_HOME_NEST_LIVE",
    "ARIA_HOME_E2E_HOOKS",
)

MAX_BODY_BYTES = 4096
SESSION_COOKIE = "aria_demo_session"
SESSION_IDLE_S = 2 * 60 * 60
MAX_SESSIONS = 500
# Total disk budget for all session stores (data plus SQLite sidecars). At the
# measured ~0.73 MB per investigated session, 500 sessions use ~365 MB, so the
# 512 MiB default leaves the 500-session cap as the binding limit. A 64 MiB
# bound filled after 93 sessions on judging-day-like traffic, turning judges
# away with 503; the larger default plus the env override below fixes that.
# Overridable with ARIA_HOME_PUBLIC_DEMO_MAX_BYTES (bytes); invalid or empty
# values fall back to this default, never to unlimited.
DEFAULT_MAX_SESSION_BYTES = 512 * 1024 * 1024
MAX_SESSION_BYTES = DEFAULT_MAX_SESSION_BYTES

_admission_lock = threading.Lock()

_SESSION_ID_RE = re.compile(r"[A-Za-z0-9_-]{32,128}\Z")

_VIDEO_DAY = "2026-01-16"
_VIDEO_OFFSET = "-05:00"
_VIDEO_TIMES = ("09:20", "14:06", "16:31", "16:52", "18:21", "18:51", "19:51", "20:21", "20:46", "21:01")
_GENERIC_TIMES = ("18:00", "18:30", "19:00", "20:31")
_CARE_DAY = "2026-01-16"
_CARE_DAY2 = "2026-01-17"
_CARE_TIMES = (("2026-01-16", "19:03"), ("2026-01-16", "19:15"), ("2026-01-16", "19:20"), ("2026-01-17", "02:31"), ("2026-01-17", "02:45"), ("2026-01-17", "04:21"), ("2026-01-17", "04:51"), ("2026-01-17", "06:21"), ("2026-01-17", "06:45"), ("2026-01-17", "07:01"))


def _at(label):
    return f"{_VIDEO_DAY}T{label}:00{_VIDEO_OFFSET}"


def _care_at(day, label):
    return f"{day}T{label}:00{_VIDEO_OFFSET}"


SCENARIOS = {
    "demo_v1": {"label": "No recovery", "times": _GENERIC_TIMES},
    "demo_recovery_v1": {"label": "Manager report, late warming", "times": _GENERIC_TIMES},
    "demo_no_followup_v1": {"label": "No follow-up readings", "times": _GENERIC_TIMES},
    "demo_video_v1": {"label": "Trip home, thermostat offline (video)", "times": _VIDEO_TIMES},
    "care_home_v1": {"label": "Winter night, older adult at home (guided story)", "times": _CARE_TIMES},
    "visual_water_low_temp_v1": {"label": "Water detection, low indoor temp (synthetic image)", "times": _GENERIC_TIMES},
    "visual_frost_missed_v1": {"label": "Frost query missed, low indoor temp (synthetic image)", "times": _GENERIC_TIMES},
    "visual_dry_floor_v1": {"label": "Dry floor, no detection (synthetic image)", "times": _GENERIC_TIMES},
}

def _checkpoint_iso(entry):
    if isinstance(entry, tuple):
        return _care_at(*entry)
    return _at(entry)


CHECKPOINTS = {sid: tuple(_checkpoint_iso(t) for t in spec["times"]) for sid, spec in SCENARIOS.items()}

_PARSED_CHECKPOINTS = {
    sid: tuple(datetime.fromisoformat(item) for item in items) for sid, items in CHECKPOINTS.items()
}
_UNION_CHECKPOINTS = tuple(sorted({at for items in _PARSED_CHECKPOINTS.values() for at in items}))


def is_public_demo(env=None):
    source = os.environ if env is None else env
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    return get(PUBLIC_DEMO_ENV) == "1"


def check_fail_closed(env=None):
    source = os.environ if env is None else env
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    offenders = [flag for flag in LIVE_FLAGS if get(flag) == "1"]
    if offenders:
        names = ", ".join(f"{flag}=1" for flag in offenders)
        raise RuntimeError(
            f"Refusing to start public-demo mode with live flags set ({names}); "
            "unset them — public demo forces recorded/deterministic output and registers no live routes."
        )


def sessions_dir(env=None):
    source = os.environ if env is None else env
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    raw = get(SESSIONS_DIR_ENV)
    if raw:
        return Path(raw).expanduser()
    return Path(tempfile.gettempdir()) / "aria-home-public-demo"


def max_session_bytes(env=None):
    source = os.environ if env is None else env
    get = source.get if hasattr(source, "get") else lambda k, d=None: getattr(source, k, d)
    raw = get(MAX_BYTES_ENV)
    if raw is None:
        return DEFAULT_MAX_SESSION_BYTES
    text = str(raw).strip()
    if not text:
        return DEFAULT_MAX_SESSION_BYTES
    try:
        value = int(text, 10)
    except (TypeError, ValueError):
        return DEFAULT_MAX_SESSION_BYTES
    if value <= 0:
        return DEFAULT_MAX_SESSION_BYTES
    return value


def new_session_id():
    return secrets.token_urlsafe(32)


def valid_session_id(value):
    return bool(value) and bool(_SESSION_ID_RE.fullmatch(value))


def session_db_path(directory, session_id):
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    return Path(directory) / f"sess-{digest}.db"


def _sidecars(path):
    path = Path(path)
    return [path, path.with_suffix(path.suffix + "-wal"), path.with_suffix(path.suffix + "-shm"), path.with_suffix(path.suffix + "-journal")]


def destroy_session(path):
    for candidate in _sidecars(path):
        try:
            candidate.unlink()
        except OSError:
            pass


def touch_session(path):
    try:
        os.utime(path, None)
    except OSError:
        pass


def sweep_sessions(directory, idle_seconds=SESSION_IDLE_S, max_sessions=MAX_SESSIONS, now=None):
    """Remove only sessions idle past the expiry; never evict live ones.

    The session cap and disk budget are enforced at admission time (503 when
    full), not here, so a sweep can never delete a visitor who merely paused.
    `max_sessions` is kept for caller compatibility and ignored.
    """
    _ = max_sessions
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    current = time.time() if now is None else now
    files = sorted(
        (p for p in directory.glob("sess-*.db") if p.is_file()),
        key=lambda p: (p.stat().st_mtime, p.name),
    )
    removed_idle = 0
    for path in list(files):
        try:
            idle = current - path.stat().st_mtime
        except OSError:
            continue
        if idle > idle_seconds:
            destroy_session(path)
            files.remove(path)
            removed_idle += 1
    return {"removed_idle": removed_idle, "evicted": 0, "remaining": len(files)}


def _disk_bytes(directory):
    total = 0
    for path in Path(directory).glob("sess-*.db*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            continue
    return total


def admit_session(
    directory,
    session_id,
    idle_seconds=SESSION_IDLE_S,
    max_sessions=MAX_SESSIONS,
    max_bytes=None,
    now=None,
):
    """Admit one visitor, returning {"session_id", "path", "new", "busy"}.

    A cookie the server did not issue has no store file, so it is treated as
    absent: a new id is issued and nothing is ever created under the client's
    chosen id. Expiry is checked before any touch. A new id is admitted only
    after sweeping expired (2-hour idle) sessions; past the session cap or
    disk budget the visitor is turned away busy with nothing allocated — idle
    sessions are never evicted, so a visitor who paused keeps their session.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if max_bytes is None:
        max_bytes = max_session_bytes()
    current = time.time() if now is None else now
    with _admission_lock:
        if valid_session_id(session_id):
            path = session_db_path(directory, session_id)
            if path.is_file():
                try:
                    idle = current - path.stat().st_mtime
                except OSError:
                    idle = None
                if idle is not None and idle <= idle_seconds:
                    touch_session(path)
                    return {"session_id": session_id, "path": path, "new": False, "busy": False}
                destroy_session(path)
        sweep_sessions(directory, idle_seconds=idle_seconds, max_sessions=max_sessions, now=current)
        entries = []
        for candidate in directory.glob("sess-*.db"):
            try:
                if candidate.is_file():
                    entries.append((candidate.stat().st_mtime, candidate))
            except OSError:
                continue
        entries.sort(key=lambda item: (item[0], item[1].name))
        total = _disk_bytes(directory)
        if len(entries) >= max_sessions or total >= max_bytes:
            return {"session_id": None, "path": None, "new": False, "busy": True}
        fresh_id = new_session_id()
        fresh_path = session_db_path(directory, fresh_id)
        try:
            fresh_path.touch(exist_ok=False)
            os.utime(fresh_path, (current, current))
        except OSError:
            pass
        return {"session_id": fresh_id, "path": fresh_path, "new": True, "busy": False}


def parsed_checkpoints(scenario_id):
    return _PARSED_CHECKPOINTS.get(scenario_id) or ()


def checkpoint_ok(at, scenario_id=None):
    if at is None:
        return False
    if at.tzinfo is None or at.utcoffset() is None:
        return False
    if scenario_id is not None:
        allowed = _PARSED_CHECKPOINTS.get(scenario_id)
        if allowed is None:
            return False
        return any(at == item for item in allowed)
    return any(at == item for item in _UNION_CHECKPOINTS)


def scenario_list():
    return [
        {"id": sid, "label": SCENARIOS[sid]["label"], "checkpoints": list(CHECKPOINTS[sid])}
        for sid in sorted(SCENARIOS)
    ]
