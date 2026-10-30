ARIA Home: finish the care story and restore browser test coverage (approved by Brad, 2026-10-29). DO THE WORK NOW in
this turn. IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own;
keep editing and running commands until the done-condition holds. No live calls, no installs, no git, NO helper
scripts outside tests. Do not weaken, delete or skip any test to make the suite pass. Keep all working-tree changes.
Shell starts in C:\aria-home; prefix frontend commands with `cd frontend && `. Do not end your turn until all of these
pass and the counts below hold: `cd backend && python -m pytest -q`, `cd frontend && npm run typecheck`,
`cd frontend && npm run build`, `cd frontend && npm run test:e2e`, `cd frontend && npm run test:e2e:public-demo`,
`cd frontend && npm run test:e2e:alt-ports`, `cd frontend && npm run record:demo`.

1. day11-07 (replace the trip-home story with the care story; prompt in docs/build-log/*day11-07-care-story.prompt.md)
   ended at "Labels confirmed. Writing the care insets spec." Read its prompt and finish every part it lists,
   including the care insets/key-line recording specs, docs and evaluation totals.
2. Browser coverage dropped: before day11-07 the normal suite ran 34 passing tests (utc + los-angeles) and the
   public-demo suite 22; now the normal suite runs 18 passed (plus 22 public-demo tests correctly skipped outside
   public mode) and the public-demo suite 2. Find every test that was removed, emptied, narrowed or made conditional
   during day11-07 (compare against the test names listed in the earlier build-log answers for day11-03, day11-05
   and day11-06b) and restore equivalent coverage on the care story: every earlier behaviour (synthetic banner, mock
   label, notifications fields sent and refusals, ack not resolving, rewind isolation, pending/stale protection,
   visual image loading at Z and +/- offsets, guided story steps, two-visitor isolation, reset, zero external calls,
   phone and laptop sizes, keyboard basics) must again be asserted. Make the default `npm run test:e2e` exclude
   public-demo.spec.ts (it runs under its own config) so skips do not inflate the totals.
3. Report the before/after test-name lists.
Final answer: what was unfinished, the restored tests by name, and the REAL output lines (with counts) of every command.

