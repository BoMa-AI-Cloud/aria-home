Model: muse-spark-1.3
Turns: 261

All five commands pass on the final tree. Done.

## Green board

- `cd backend && python -m pytest -q` → `656 passed in 145.08s (0:02:25)`
- `cd frontend && npm run typecheck` → `> tsc --noEmit`, no errors
- `cd frontend && npm run build` → `33 modules transformed`, `✓ built in 925ms` (dist/index.html, cards.html, main JS/CSS)
- `cd frontend && npm run test:e2e` → `50 passed (2.7m)`
- `cd frontend && npm run test:e2e:public-demo` → `42 passed (1.6m)`

## Files changed (working-tree changes kept)

Backend / docs (audit-5 repairs, from earlier in the log, verified green): `backend/aria_home/app.py` (known-investigation trace before its follow-up exists returns the scripted trace, basis "scripted story", 200; unknown ids still 404), `backend/aria_home/public_demo.py` (admission: sweep only 2-hour idle expiry, no eviction; over cap/budget → 503, allocate nothing), `backend/tests/test_audit5_trace_parity.py` (+ scripted-before-followup test, + human-report causal-independence test), `backend/tests/test_audit5_sessions_admission.py` (+ 10-minute-idle session survives full-cap admission), `backend/tests/test_public_demo.py` (retention test matches no-eviction rule), `docs/audit-5.md` (row 3), `docs/build-log/README.md` (day11-18b row).

Frontend: `frontend/src/App.tsx`, `frontend/src/index.css`, `frontend/e2e/app.spec.ts`, `frontend/e2e/public-demo.spec.ts`, `frontend/e2e/pending.spec.ts`. (`playwright.config.ts` / `playwright.public-demo.config.ts` were briefly given `stdout/stderr: "ignore"` so suite output fit in the log; reverted, no net change.)

## Locators moved vs clarified (no assertion or expected value changed anywhere)

- `app.spec.ts` care-verification blocks: Simulated-timeline assertions now run after clicking the Reasoning tab, demo-control clicks after clicking House (the timeline/article live on Reasoning by design; `.demo-controls` is hidden there).
- `public-demo.spec.ts` rewind test: same Reasoning-tab navigation before the timeline assertion.
- `pending.spec.ts:74`: `getByLabel("Scenario")` → `getByLabel("Scenario", { exact: true })`. The Scenario `<select>` did not move. The trace map now renders on the Reasoning page by design, and step `trace-step-32`'s accessible name ("…scenario has no homeowner confirmation…") substring-matches "Scenario", so the locator resolved to 2 elements (strict-mode violation). Same element, same `toHaveValue("care_home_v1")` assertion.

## What fixed the rest

- Outcome race (`public-demo.spec.ts:174`, flaky "Waiting for new readings" vs settled "Thermostat telemetry missing"): the backend value was always telemetry-missing; the frontend flashed the outcome-only label from `createFresh` before the follow-up fetch resolved. `createFresh` now sets outcome only with the follow-up response (or immediately when follow-up is null). Test captures settled state; backend causal-independence test covers the report-vs-no-report equivalence.
- Height 4562px → under 4000px, content preserved, all in collapsed `<details>` by default: verified-facts list, readiness reasons, interpretation limitations, power-context limitations, recorded second review, source-notes cells, whole evidence-timeline list, trace intro+legend ("About this map"), whole CodeChecks section ("Show all N checks", counts stay in `.checks-summary`), whole Laws section ("ARIA's Laws", auto-opens via the existing ARIA's-Laws button through new `lawsOpen` state). Still visible: ARIA's-view heading, trace map (1014px), trace time buttons, Back buttons, evidence-table status cells, visual image, readiness status lines, interpretation text.
