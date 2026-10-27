Model: muse-wonder-1.0
Turns: 43

Root causes (two):
1. **DB deletion race (verified):** both Playwright configs deleted a fixed shared DB path (`aria-home-e2e.db` / `aria-home-recording.db`) at module top level. Playwright re-loads the config in every worker, so a worker could unlink the DB while the backend had it in use; SQLite's per-request connections then recreated an empty 0-byte file with no tables, failing investigation creation. Fix: DB path is chosen once in the main process (unique `aria-home-e2e-<pid>.db` / `aria-home-recording-<pid>.db`), stored in an env var workers inherit (`ARIA_HOME_E2E_DB_PATH` / `ARIA_HOME_RECORDING_DB_PATH`), and deleted only when first created — never from workers.
2. **Disabled replay button (remained after fix 1; ran 17/18 twice, 18/18 with `--workers=1`):** parallel workers (utc + los-angeles projects) share one backend, one SQLite DB, and deterministic investigation IDs. Server logs showed concurrent `POST /api/investigations` returning `202` (inference claim pending from the other worker) with no 5xx. The frontend treated that 202 as a finished investigation (hollow response, no follow-up), and replay buttons are `disabled={!investigationId}`, so the selected 16:31 button stayed `disabled aria-pressed="true"` past the 5s wait. Fix: e2e config now runs `workers: 1` (tests share mutable server state; the record config already did this), and `createInvestigation` now re-POSTs on 202 until the completed result arrives (idempotent via the backend claim dedup, max 50 attempts × 200ms). No test assertion was changed or skipped.

Files changed:
- `frontend/playwright.config.ts` — per-process env-inherited DB path; `workers: 1`
- `frontend/playwright.record.config.ts` — per-process env-inherited DB path
- `frontend/src/api.ts` — poll on 202 pending in `createInvestigation`

Three consecutive e2e runs (`cd frontend && npm run test:e2e`):
```
18 passed (31.3s)
18 passed (24.8s)
18 passed (28.0s)
```
Backend (`cd backend && python -m pytest -q`): `269 passed in 13.81s`
