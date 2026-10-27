ARIA Home, video gap G2 (approved by Brad): one readable evidence timeline. DO THE WORK NOW in this
turn; do not stop after a plan. No helper scripts, no live calls, no installs, no network, no git.
Shell starts in C:\aria-home: prefix frontend commands with `cd frontend && `. Do not end your turn
until `cd backend && python -m pytest -q`, `cd frontend && npm run typecheck` and
`cd frontend && npm run test:e2e` pass.

Read: docs/demo-script.md A3 (segments 7-9, A3.5 G2), backend/aria_home/verification.py, app.py,
frontend/src/App.tsx, api.ts, frontend/recording/insets.record.ts, frontend/e2e/app.spec.ts.

BUILD: the follow-up response gains `evidence_timeline`, an ordered list built by code from the
as-of projection only: thermostat reporting restored, warming first observed, target first reached,
hold completed and goal verified, HVAC completion report available (corroboration only), arrival
checked. Each entry has its label, the supporting record id(s), observed time, received/available
time and the evaluation time at which ARIA could first know it; entries not yet known at `at` are
absent. Frontend: an "Evidence timeline" panel (ET times, readable, the report row marked
"Corroboration only") placed under the Outcome panel. Add close-up i10-timeline at 21:01 to the
recorder. Tests: backend ordering (verified strictly before report available), absence before each
time, no future entries; e2e at 21:01 shows all rows in order and at 20:21 no report row.
Final answer: files and REAL outputs.

