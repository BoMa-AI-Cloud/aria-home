ARIA Home, audit repair R1b (approved by Brad): replay results must not depend on the order in which
replay times are requested. DO THE WORK NOW in this turn; do not stop after a plan. No helper
scripts, no live calls, no installs, no network, no git. Do not touch anything outside C:\aria-home.
Do not end your turn until `cd backend && python -m pytest -q` passes AND `cd frontend && npm run
test:e2e` passes with the e2e backend on a fresh temporary database.

Context: the R1 repair (uncommitted, in this tree) projects notifications by created_at <= at and
never writes on an earlier replay. Operator review found the e2e test "video scenario shows scoped
simulated notifications and homeowner update" fails even on a fresh database: an earlier test in the
same run replays to 21:01 first, which creates the HVAC request with created_at 21:01, so a later
16:52 replay correctly hides it. The defect is that created_at is the time of the first request that
happened to evaluate it, so what a replay shows depends on click order.

FIX: a notification's created_at must be deterministic from the scenario, not from request order:
it is the first scheduled check time (from scheduling.py) at or after the moment its gate became
satisfied (for the HVAC request: the manager_hvac_authorized event's available_at; for manager and
homeowner notifications: the investigation's evaluation time), and never later than the evaluation
that discovers it. Evaluating at 21:01 first must therefore create the HVAC request stamped at its
deterministic time (e.g. 16:52 if that is the first check after 16:45, per the schedule), so a
later 16:52 replay shows it. Keep the R1 rules (no future leakage, no writes on earlier replays,
full audit history kept, 409 before creation). Also make frontend/playwright.config.ts give the e2e
backend a fresh temporary database per run (as playwright.record.config.ts does), so runs are
isolated from backend/instance.
TESTS: request order 21:01 then 16:52 gives the same 16:52 projection as 16:52 then 21:01; a backend
test for that; the existing e2e suite passes on a fresh database. List any assertion you change.
Final answer: the rule, files changed, REAL output lines.

