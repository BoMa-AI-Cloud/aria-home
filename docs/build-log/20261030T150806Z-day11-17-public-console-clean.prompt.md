ARIA Home: the hosted public demo must load and run the guided story with zero console errors (approved by Brad, 2026-10-30). DO THE WORK NOW in this turn. IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; keep editing and running commands until the done-condition holds. No live calls, no installs, no git, no network beyond 127.0.0.1. Do not weaken any test. Keep all working-tree changes. Shell starts in C:\aria-home; prefix frontend commands with `cd frontend && `. Do not end your turn until `cd backend && python -m pytest -q`, `cd frontend && npm run typecheck`, `cd frontend && npm run build`, `cd frontend && npm run test:e2e` and `cd frontend && npm run test:e2e:public-demo` pass.

Real result from the operator on https://aria-home-demo.onrender.com (commit 798ff77), a clean browser running the guided story start to finish. The story works, but the console shows 11 "Failed to load resource" errors from these requests:
- 404 /api/live-power, /api/whatsapp/status, /api/camera/status: these routes do not exist in public-demo mode, but the frontend asks anyway.
- 400 /api/visual, /api/investigation, /api/sources, /api/context at 2026-01-16T18:00:00-05:00: on first load the app fetches at a default time that is not an allowlisted public checkpoint, before the story sets its time.
- 404 /api/follow-ups/<id> at 19:03, 19:15 and 19:20: before the follow-up exists.

Fix in frontend/src/App.tsx (and api.ts if needed), without changing backend behaviour:
1. In public mode (health.public_demo === true), never request the three owner-only status routes; normal mode keeps them.
2. In public mode, never fetch scenario data until the time is one of the story checkpoints from /api/scenarios; the first fetch uses the first checkpoint.
3. Do not request a follow-up for an investigation whose response said follow_up is null, or before the investigation's follow-up exists. Use the existing noFollowUpIds logic, or the same information.
4. Add to frontend/e2e/public-demo.spec.ts a test that runs the guided story through all ten steps and asserts that no console message of type "error" occurred and no response with status >= 400 was received; then the same for the landing page alone. Keep the existing tests.
Final answer: files changed, tests added, and the REAL output lines of every command.

