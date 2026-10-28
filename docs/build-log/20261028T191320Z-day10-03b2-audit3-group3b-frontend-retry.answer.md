Model: muse-spark-1.3
Turns: 4

All checks pass. Final report:

## GROUP 3b — done

**11. UI gives up early** — Root cause: `createInvestigation` polled `50 × 200 ms` (~10 s) while the provider timeout is 20 s and the server claim lease is 120 s, so a poller abandoned a 13 s inference; 409 `recovery_required` was thrown as a generic failure; the outcome panel hardcoded `"Follow-up not reachable"` instead of rendering the real error.
- `frontend/src/api.ts`: elapsed-time deadline `INFERENCE_POLL_DEADLINE_MS` (120 s lease + 15 s transport margin), exponential backoff capped at 2 s, 202 continues / 409-with-`recovery_required` throws typed `RecoveryRequiredError` / other non-OK throws, abort-aware sleep (signal no longer passed to `fetch`, so effect cleanup never produces aborted-network `requestfailed` events that the overview test counts).
- `frontend/src/App.tsx`: per-effect `AbortController` with cleanup abort, `RecoveryRequiredError` → distinct `"Inference recovery required — repeat with retry"` message, abort/token guards so stale responses never overwrite current context (StrictMode double-effects safe); `OutcomeSection` renders the actual error text.
- `backend/aria_home/app.py`: test-only hooks, honored only when `ARIA_HOME_MODEL_ENABLED != "1"` (live mode ignores them): `test_delay_s` (0–30 s post-claim sleep), `test_fail=1` (forced unavailable), `lease_s` (1–600 s lease override). Fixed my own `min(max(x), 30)` clamp bug (single-arg `max` throws → delay was silently 0).

**12. Hard-coded ports** — Root cause: 11 absolute `http://127.0.0.1:5173/` navigations in `e2e/app.spec.ts` (plus 6 in `recording/`) bypassed the configured `baseURL`.
- `e2e/app.spec.ts` (11×), `recording/demo.record.ts` (4×), `insets.record.ts`, `keys.record.ts` → relative routes (`/`, `/cards.html#…`, `/?inset=…`, `/?key=…`).
- `playwright.record.config.ts` now honors `PLAYWRIGHT_FRONTEND_PORT`/`PLAYWRIGHT_BACKEND_PORT` (Vite proxy already followed the backend port).
- Added `test:e2e:alt-ports` (new `playwright.alt.config.ts`, self-contained on 15173/15000 — a re-export couldn't set env before import hoisting, and `VAR=x` prefixes don't work under Windows `cmd`).

**Recording DB isolation** — Root cause: all three recording projects shared one `ARIA_HOME_RECORDING_DB_PATH`, so chrome's `s3-authorized-help` ack left `i4-help`/`k-ack` with nothing to acknowledge. `record:demo` now runs chrome, insets, keys as three sequential invocations, each with its own fresh temp DB.

**Tests added**
- `frontend/e2e/pending.spec.ts` (5 browser tests, unique per-project/per-test `e2e_at` identities to defeat shared-DB dedup): 12 s slow inference + concurrent poller → eventual result; `test_fail` → unavailable; expired lease → distinct recovery text; scenario change while pending keeps context, no stale overwrite; rapid replays end on last selection.
- `backend/tests/test_audit3_group3b_hooks.py` (4 tests): delay + concurrent 202→200, lease expiry → 409 + owner 409, fail → unavailable, hooks ignored when model enabled.

**Real command outputs**
- `cd backend && python -m pytest -q` → `348 passed in 40.90s`
- `cd frontend && npm run typecheck` → `tsc --noEmit` clean
- `cd frontend && npm run build` → `✓ built in 749ms`
- `cd frontend && npm run test:e2e` → `32 passed (1.5m)`
- `cd frontend && npm run test:e2e:alt-ports` → `1 passed (6.6s)` on 15173/15000
- `cd frontend && npm run record:demo` → exit 0, chrome + insets + keys all pass (`13 passed` keys incl. `k-ack`; `i4-help` in insets run)

No live calls, no installs, no git; temp DBs + mock/fake providers only; no existing assertion weakened.
