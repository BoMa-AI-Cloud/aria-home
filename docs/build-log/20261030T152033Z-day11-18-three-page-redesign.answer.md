Model: muse-spark-1.3
Turns: 271

All five commands green. Final report:

## Files changed
- `frontend/src/App.tsx` — three-page tab structure (already in place); this session added: `active` fetch gate on TraceView/LawsView/CodeChecks, Escape-to-close on the evidence drawer, `?? []` / `rule`·`detail` fallbacks in LawsView joins, `?.` guards on `summary`/`metrics` reads
- `frontend/src/api.ts` — widened `WatcherCodeDetection` with optional `rule`/`detail`
- `frontend/src/index.css` — header/scenario-select wrap + shrink so 375px viewports don't scroll sideways
- `frontend/e2e/app.spec.ts`, `frontend/e2e/pending.spec.ts` — navigation-only updates: tab clicks to House/Reasoning before section assertions; no assertion changed
- `frontend/e2e/public-demo.spec.ts` — the four new tests (tabs, verdict-at-times, 375px no-scroll, same-origin)
- `docs/build-log/README.md` — day11-17 row (pre-existing)

## Pages
**House** is the landing state: the question heading, house-right-now status, demo controls with scenario select and replay-time buttons, outcome, notifications, timeline, and the Explore-evidence drawer. Everything a visitor needs to answer "is the house OK and who responds" is here without navigating.

**Reasoning** holds the investigation, ARIA's view trace map, code checks, Laws/watcher/corrections, evidence timeline and evidence sources. Heavy trace/watcher/laws fetching now only fires when this tab is active, restoring the old request pattern so the outcome chain settles inside test timeouts.

**Integrations** lists the connected apps (WhatsApp/camera/live-power status rows) with the same header frame — tabs, status pill, replay stepper, theme toggle — as the other two pages.

## Done-condition output (real lines)
- `cd backend && python -m pytest -q` → `620 passed in 85.91s (0:01:25)`
- `cd frontend && npm run typecheck` → `> tsc --noEmit` (no errors)
- `cd frontend && npm run build` → `✓ built in 719ms`, 33 modules transformed
- `cd frontend && npm run test:e2e` → `50 passed (2.2m)`
- `cd frontend && npm run test:e2e:public-demo` → `38 passed (1.1m)`

Three real bugs fixed along the way, none touching assertions: LawsView crashed on 02:31 watcher detections missing `kind`/`claim`/`evidence_ids`; the evidence drawer ignored Escape; and any `test_fail`-style unavailable investigation crashed the whole page on `summary.metrics` (blank body, `TypeError: Cannot read properties of undefined (reading 'indoor_trend')`).
