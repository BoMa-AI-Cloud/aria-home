ARIA Home, video gap G1 (approved by Brad): a read-only "Confirmed plan and permissions" panel. DO
THE WORK NOW in this turn; do not stop after a plan. No helper scripts, no live calls, no installs,
no network, no git. Shell starts in C:\aria-home: prefix frontend commands with `cd frontend && `.
Do not end your turn until `cd backend && python -m pytest -q`, `cd frontend && npm run typecheck`
and `cd frontend && npm run test:e2e` pass.

Read: docs/demo-script.md section A3 (segment 2 and A3.5 G1), backend/aria_home/scenario.py
(context_as_of, confirmations), app.py, frontend/src/App.tsx, api.ts, frontend/e2e/app.spec.ts.

BUILD: GET /api/context?scenario=&at= returns the as-of confirmed plan: property label, planned
arrival with its labelled allowances (from the calendar arrival_plan; say they are scenario
estimates), target temperature, homeowner notification preference, manager coordination permission,
confirmed_at, revision id, and the context flags. Before confirmed_at it returns
{"confirmed": false} with the reason. Same as-of and echo (scenario, at, timezone) rules as the other
endpoints. Frontend: a "Confirmed plan and permissions" panel near the top, read-only, ET times,
showing "Not yet confirmed" before 09:20 in the video scenario and the fields after. Tests: backend
before/after confirmed_at and a revised trip marking it outdated; e2e for 09:20 in the video
scenario. Add the panel to the close-up recorder as i0-plan. Final answer: files and REAL outputs.

