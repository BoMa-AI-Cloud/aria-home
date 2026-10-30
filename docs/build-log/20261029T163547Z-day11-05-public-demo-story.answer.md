Model: muse-spark-1.3
Turns: 94

Done. All gates pass.

## Files changed

**Frontend**
- `frontend/src/App.tsx` — public-mode detection via `/api/health` (`public_demo` flag, no failing probe in local mode); landing view (title, purpose line, Brad's Petoskey hook, disclosure, Start/Explore/Reset); 10-step story panel over the real replay using live `/api/scenarios` checkpoints (times/labels from the API), observed-vs-first-known lines from the evidence timeline, API-rendered HVAC `fields sent`, refusal lines, ack-must-not-change guidance, Back/Rewind/Next with stale-state clearing and same-time events refetch; "Explore evidence" drawer (sources, code-computed readiness/verification reasons, recorded-or-fallback interpretation with provenance, per-audience fields sent/refused, 4-row model-role matrix); public session bar with always-visible reset.
- `frontend/src/api.ts` — `HealthResponse.public_demo`, `fetchScenarios`, `resetPublicSession`.
- `frontend/src/index.css` — landing/story/drawer styles, 40rem breakpoint, visible focus already present, text (not colour-only) status lines.
- `frontend/package.json` — `test:e2e:public-demo` script.

**Backend**
- `backend/aria_home/app.py` — `/api/health` gains `"public_demo": true/false` (lets the frontend detect demo mode without a 404 probe that tripped existing `failedRequests` assertions).
- `backend/tests/test_health.py`, `backend/tests/test_sources_api.py` — exact-match expectations extended with `"public_demo": False` (additive, not weakened).

**Tests**
- `frontend/playwright.public-demo.config.ts` (new) — backend `ARIA_HOME_PUBLIC_DEMO=1` with temp sessions/recorded dirs, UTC + America/Los_Angeles projects.
- `frontend/e2e/public-demo.spec.ts` (new, 11 tests) — landing/disclosure/fresh-session cookie; full 10-step story to arrival with zero forbidden-host calls; drawer with computed reasons + no-recording fallback + model matrix; HVAC fields from payload + ack-unchanged outcome; A/B context isolation with isolated reset; rewind leak check; rapid-step settling; identical visual bytes at UTC/+05:30/−08:00; ET rendering; 1366×768 and 390×844 smoke (spec skips itself when backend isn't in demo mode, so the default suite is unaffected).

**Docs** — `docs/public-demo-plan.md` steps 3 and 7 marked done; `README.md` "What judges should click" gains the public-demo landing/story paragraph; `docs/recording-checklist.md` gains the browser-coverage mapping.

## Real command outputs

- `cd backend && python -m pytest -q` → `464 passed in 59.10s`
- `cd frontend && npm run typecheck` → `tsc --noEmit` clean
- `cd frontend && npm run build` → `✓ built in 807ms`, `assets/main-D3Q4iItG.js 275.54 kB`
- `cd frontend && npm run test:e2e` → `17 passed` (utc) and `17 passed` (los-angeles)
- `cd frontend && npm run test:e2e:public-demo` → `22 passed` (11 utc + 11 los-angeles)

Two regressions were caught and fixed along the way: the scenarios probe 404 broke existing `failedRequests` assertions (fixed via the health flag), and stale-state clearing dropped same-time replays' events (fixed with an explicit refetch in `handleReplayTime`).
