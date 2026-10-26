ARIA Home, Day 5 task D5-2 (approved by Brad): notifications in the browser. DO THE WORK NOW in
this turn; do not stop after a plan. No helper scripts, no live calls, no installs, no network, no
git. Shell starts in C:\aria-home: prefix frontend commands with `cd frontend && `. Do not end your
turn until `cd backend && python -m pytest -q`, `cd frontend && npm run typecheck`,
`cd frontend && npm run build` and `cd frontend && npm run test:e2e` all pass.

Read: backend/aria_home/notifications.py and app.py (notification endpoints and response shapes),
frontend/src/App.tsx, api.ts, index.css, frontend/e2e/app.spec.ts, docs/demo-script.md (shots 8,
11, 12).

BUILD (frontend only; no backend changes unless a response field is missing, then add it with a
test):
1. api.ts types and helpers for GET /api/notifications and POST /api/notifications/<id>/ack.
2. A "Notifications (simulated delivery)" panel, separate from Investigation and Outcome: one
   card per notification with its audience in words (Homeowner, Property manager, HVAC company),
   state in words (Simulated delivery, Refused: <reason in words>), created time, and the exact
   payload fields shown as a short labeled list. Each card says "Simulated, no message was sent".
3. An "Acknowledge (simulated)" button on delivered manager cards; after it, the card shows
   "Acknowledged, not resolved" with the time, and the Outcome panel must not change.
4. A one-line homeowner update card for the video ending: when the verification stage is
   arrival_met, show "Your home reached and held 68 F before you arrived" built only from the
   verification result and verified facts, with its evaluation time.
5. Keep all existing panels, labels and tests working.
E2E (keep existing tests): video scenario at 16:31 shows a Property manager card; at 16:31 the HVAC
card is absent or refused; at 16:52 an HVAC card shows only its approved fields; acknowledging the
manager card shows "Acknowledged, not resolved" and the Outcome headline is unchanged; at 21:01 the
homeowner update appears; every notification card says "Simulated".
Final answer: changes and REAL output lines.

