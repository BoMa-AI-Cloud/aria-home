Model: muse-spark-1.3
Turns: 31

Done. `cd backend && python -m pytest -q` → 705 passed.

Files changed:
- `backend/aria_home/public_demo.py` — `MAX_SESSION_BYTES` 64 MiB → 512 MiB (`DEFAULT_MAX_SESSION_BYTES`); new `MAX_BYTES_ENV` + `max_session_bytes()` (env bytes, invalid/empty → default, never unlimited); `admit_session(max_bytes=None)` resolves the env default; admission logic otherwise unchanged
- `backend/aria_home/app.py` — guard passes `max_bytes=public_demo.max_session_bytes()`
- `.env.example` — documented `ARIA_HOME_PUBLIC_DEMO_MAX_BYTES`
- `README.md` — public-demo bullet: 512 MiB default, env name/fallback, 500-session cap binds first at ~0.73 MB/session
- `docs/audit-5.md` — admission row 3: 512 MiB bound, env override, Gate A 93-sessions-fill rationale
- `backend/tests/test_public_demo.py`, `backend/tests/test_audit5_sessions_admission.py` — scrub new env var

Tests added (`backend/tests/test_public_demo.py`):
- `test_disk_bound_default_is_512mib`
- `test_disk_bound_env_override`
- `test_disk_bound_invalid_falls_back_to_default`
- `test_disk_bound_env_enforced_at_admission`

Real pytest line: `cd backend && python -m pytest -q`
