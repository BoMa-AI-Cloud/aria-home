ARIA Home: make the browser suites pass again (approved by Brad, 2026-10-29). DO THE WORK NOW in this turn.
IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; keep
editing and running commands until the done-condition holds. No live calls, no installs, no git, NO helper scripts
outside tests. Do not delete, skip, weaken or narrow any test; fix the app or the test's stale expectation only when the
app's new care-story behaviour is correct, and say which for each. Keep all working-tree changes. Shell starts in
C:\aria-home; prefix frontend commands with `cd frontend && `. Do not end your turn until `cd backend && python -m pytest
-q`, `cd frontend && npm run typecheck`, `cd frontend && npm run build`, `cd frontend && npm run test:e2e`,
`cd frontend && npm run test:e2e:public-demo`, `cd frontend && npm run test:e2e:alt-ports` and
`cd frontend && npm run record:demo` all pass with zero failures.

State after day11-07c and day11-11 (both ended mid-task): backend 505 passed; `npm run test:e2e` 7 failed / 29 passed;
`npm run test:e2e:public-demo` 6 failed / 16 passed (failures include toBeVisible and toContainText). day11-11 was also
investigating an unable_to_verify caused by verification.py requiring readings observed after the follow-up's
created_at when a replay starts at 07:01; finish that investigation and fix it correctly (a replay that starts late must
still judge the warm-by expectation from readings available by then, without letting future data in), with a test.
Finish anything day11-11 left undone (its prompt is in docs/build-log/*day11-11-care-visual.prompt.md).
Final answer: each failing test, its cause, the fix, and the REAL output lines with counts of every command.

Failing tests from the operator's run (fix all of them):
app.spec.ts:10 "synthetic evidence overview renders without errors" (utc, los-angeles); app.spec.ts:271 "care scenario
shows scoped simulated notifications and resident update" (utc); app.spec.ts:364 "care scenario shows warm-by plan and
consent at 19:20" (los-angeles); app.spec.ts:475 "rapid replay selections end on the last selection" (utc,
los-angeles); pending.spec.ts:61 "scenario change while pending keeps the current context" (utc, los-angeles);
public-demo.spec.ts:122 "hvac fields come from the payload and ack changes no outcome", :191 "rewind reveals no later
state", :260 "story times render in ET in any browser timezone" (utc, los-angeles each). Note the timezone-dependent
ones: times must render in the home's timezone (ET) whatever the browser timezone is.

