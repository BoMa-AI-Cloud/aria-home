ARIA Home, Audit 3 repair, GROUP 3b: pending UI, ports and recording tooling (frontend) (approved by Brad).
DO THE WORK NOW in this turn. No live calls, no installs, no network beyond 127.0.0.1, no git, NO helper
scripts outside tests. Temporary databases and fake providers only; never call a real model. Do not weaken
any existing assertion. Smallest sound changes; no new features. Groups 1-2 are already in the working tree;
keep them. Shell starts in C:\aria-home; prefix frontend commands with `cd frontend && `. Do not end your turn
until `cd backend && python -m pytest -q`, `cd frontend && npm run typecheck`, `cd frontend && npm run build`
and `cd frontend && npm run test:e2e` all pass.

Read first: backend/aria_home/app.py, store.py, investigator.py, docs/inference-idempotency.md,
frontend/src/api.ts, frontend/src/App.tsx, frontend/playwright.config.ts, frontend/playwright.record.config.ts,
frontend/vite.config.ts, frontend/e2e/app.spec.ts, frontend/recording/*.ts.

Group 3a (claim lease/recovery_required, read-only GET, typed acks) is already in the working tree; keep it.

Reproduced on the current code:

11. UI GIVES UP EARLY. frontend/src/api.ts createInvestigation polls 50 x 200 ms (~10 s) while the provider
   timeout defaults to 20 s, so a concurrent caller polling an existing owner abandons a request that
   completes at 13 s. Fix: explicit pending state; elapsed-time deadline consistent with the server lifecycle
   plus transport margin; bounded polling with backoff; distinct handling of recovery_required; cancel or
   ignore stale work when scenario/time changes or the component unmounts so a slow old response never
   overwrites the current context; no confusing failures from duplicate startup effects.
   Tests (browser, with a fake slow provider in the e2e backend): 12-15 s inference with a concurrent polling
   caller shows the eventual result; server failure; recovery_required; scenario change while pending; rapid
   replay changes; no stale overwrite.

12. HARD-CODED PORTS. PLAYWRIGHT_FRONTEND_PORT=15173 and PLAYWRIGHT_BACKEND_PORT=15000 start the servers, but
   e2e/app.spec.ts navigates to absolute http://127.0.0.1:5173/ (10 places). Fix: relative routes on the
   configured baseURL; the Vite proxy follows the configured backend port; keep isolated temp DBs; never kill
   an unrelated service. Add an npm script that runs an alternate-port smoke.

ALSO (recording tooling): `npm run record:demo` fails `[insets] i4-help` and `[keys] k-ack` because the chrome
project's s3-authorized-help acknowledges the same notification first in the shared recording DB. Give each
recording project its own fresh temporary DB (or make those clips create their own unacknowledged state) so
`cd frontend && npm run record:demo` passes all clips. Run it once at the end.

Final answer: per finding, root cause, files changed, tests added, and the REAL output lines of every command.

