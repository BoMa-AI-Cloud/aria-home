# Day 9 handoff

## Clean-setup check (operator, 2026-10-27)

- Fresh clone of https://github.com/BoMa-AI-Cloud/aria-home at cd776d0 into a new folder.
- Fresh virtual environment, `pip install -r requirements.txt`: backend `python -m pytest -q` -> 216 passed, with MODEL_API_KEY and ARIA_HOME_MODEL_ENABLED unset.
- `npm ci` -> found 0 vulnerabilities; `npm run build` -> built; `npm run typecheck` -> exit 0; `npm run test:e2e` with the clone's venv first on PATH -> 4 passed.
- Not checked: macOS/Linux; a machine without Google Chrome installed (the tests use the installed Chrome); a hosted URL (none exists; pending office-hours answer).

## Audit 2 repair (2026-10-27)

An external audit of commit 6a659ca reported eight backend defects, a frontend context mismatch, a schema race on a fresh database and a timezone-dependent browser assertion.

- P1 replay isolation (fixed; test_replay.py; follow-up R1b made notification times deterministic so replay order cannot change results).
- P1 arrival coverage (fixed; test_verification.py).
- P2 relapse (fixed; test_verification_relapse.py).
- P2 stale facts and P2 evidence kind (fixed; eligibility.py, test_eligibility.py).
- P2 rounding (fixed; test_readiness_precision.py; tolerance constant 0.0).
- P2 homeowner opt-out (fixed; test_notifications_homeowner_optout.py).
- P2 inference idempotency (fixed with mocks; test_inference_idempotency.py; docs/inference-idempotency.md).
- P2 frontend context (fixed; e2e).
- A schema race (fixed with one BEGIN IMMEDIATE transaction and column checks; test_r8_context_concurrency.py; note: the race failed only intermittently before the fix, so the failing-first evidence is weak).
- B timezone policy (fixed; times shown in the property zone with "ET"; e2e runs under UTC and America/Los_Angeles).

Operator checks, 2026-10-27, uncommitted working tree on top of b714051: backend `python -m pytest -q` in an isolated venv with MODEL_API_KEY unset and ARIA_HOME_MODEL_ENABLED=0 -> 269 passed; `npm run typecheck` -> exit 0; `npm run build` -> built; `npx playwright test` (installed Chrome, UTC and Los Angeles projects, one worker, fresh temp database per run) three consecutive runs -> 18 passed each. Before R8b the operator measured 18/18 once and then 9 failed / 9 passed twice; R8b found the config deleted the database from each worker and the frontend did not handle the new 202 pending reply.

Migration: existing databases are upgraded in place (new columns added if missing, new tables inference_requests and any others created); nothing is dropped.

Remaining limits: e2e runs with one worker because both projects share one backend; the tolerance constant is 0.0 by policy; idempotency was tested with mocks only, no live calls.
