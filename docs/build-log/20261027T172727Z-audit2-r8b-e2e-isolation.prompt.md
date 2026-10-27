ARIA Home, audit repair R8b (approved by Brad): browser tests are not repeatable. DO THE WORK NOW in
this turn; do not stop after a plan. No helper scripts, no live calls, no installs, no network, no
git. Do not touch anything outside C:\aria-home. Do not end your turn until
`cd frontend && npm run test:e2e` passes THREE times in a row (run it three times and show all three
summary lines) and `cd backend && python -m pytest -q` passes.

Operator measurement after R8 (uncommitted, in this tree): e2e passed 18/18 once, then failed 9/18 on
the next two runs. A failure: "rapid replay selections end on the last selection" waits for the 16:31
button to be enabled but it stays `disabled aria-pressed="true"`. The leftover database file
%TEMP%\aria-home-e2e.db is 0 bytes after a run.

Likely cause found by the operator (verify it): frontend/playwright.config.ts deletes the database
at module top level, and Playwright re-loads the config in every worker process, so a worker can
delete the database while the backend server already has it open.
FIX: choose the database path once in the main process (for example a unique path with the process
id stored in an environment variable that workers inherit, deleted only when it is first created),
never delete it from workers; same for playwright.record.config.ts. Then check whether the
disabled-button failure remains; if it does, find the cause (for example a button disabled while its
own time is the current replay time, or a stale in-flight request) and fix the app or the test
honestly: a test may wait for the right state but may not skip the assertion.
Final answer: the root cause(s), files changed, and the three REAL e2e summary lines.

