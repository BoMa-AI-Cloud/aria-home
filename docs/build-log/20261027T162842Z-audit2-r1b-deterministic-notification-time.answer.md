Model: muse-wonder-1.0
Turns: 53

**Rule:** A delivered notification's `created_at` = `min(first scheduled check ≥ gate, discovering evaluation)`, where scheduled checks iterate `scheduling.compute_follow_up_schedule` from the follow-up's creation (anchor 16:31, cadence 300s clamped to 15-min minimum → checks 16:46, 17:01, …). For HVAC, gate = `manager_hvac_authorized.available_at` (16:45) → deterministic `2026-01-16T16:46:00-05:00` (not 16:52; 16:46 is the actual first check, and ≤16:52 so a 16:52 replay shows it regardless of order). Homeowner/manager keep gate = investigation evaluation time (16:31). Refused notifications keep discovery time. R1 rules retained: projection `created_at <= at`, no writes on rewind, full history kept, 409 before creation.

**Files changed:**
- `backend/aria_home/notifications.py` — `_deterministic_created_at()` iterating `compute_follow_up_schedule` (deadline/cadence from the stored follow-up), applied to the allowed HVAC decision in `create_hvac_notification`.
- `backend/tests/test_replay.py` — new `test_hvac_projection_at_1652_does_not_depend_on_request_order` (21:01→16:52 vs 16:52→21:01 on separate DBs, identical 16:52 projections, one delivered HVAC stamped 16:46).
- `frontend/playwright.config.ts` — e2e backend gets fresh temp DB per run (`%TMP%/aria-home-e2e.db`, `-wal`/`-shm` deleted up front, `ARIA_HOME_DB_PATH` passed, mirroring `playwright.record.config.ts`).

**Assertions changed:** None existing. Only added the new test's assertions above.

**REAL output:**
```
cd backend && python -m pytest -q
230 passed in 12.13s

cd frontend && npm run test:e2e
  ok 4 [chrome] › e2e\app.spec.ts:218:1 › video scenario shows scoped simulated notifications and homeowner update (1.7s)
  6 passed (15.3s)
```
