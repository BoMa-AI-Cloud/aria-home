ARIA Home, video gap G3 (approved by Brad): finish the panel close-up recorder. The previous run
(day9-09) was interrupted; its uncommitted changes are in this working tree (App.tsx inset class,
index.css, playwright.record.config.ts, package.json "record:insets", .gitignore,
frontend/recording/insets.record.ts, one new e2e test). Read them first and continue; do not start
over. DO THE WORK NOW in this turn. No live calls, no installs, no network beyond 127.0.0.1, no git,
NO helper scripts. Shell starts in C:\aria-home: prefix frontend commands with `cd frontend && `.
Do not end your turn until `cd frontend && npm run record:insets` passes with all nine clips,
`cd frontend && npm run test:e2e` passes, and `cd frontend && npm run typecheck` passes.

The spec is unchanged from the interrupted task: nine clips i1-trip, i2-location, i3-not-responding,
i4-help, i5-restored, i6-warming, i7-verified, i8-report, i9-arrival (see docs/demo-script.md
section A3.4 for the states and replay times), 900x506 viewport at deviceScaleFactor 2, the
test-only ?inset=<panel> class has no effect without the parameter, each clip asserts its key text.
The previous run's record:insets attempts failed; read the error output by running a single test
(`npm run record:insets -- -g i1-trip`) and fix the cause.
Final answer: the cause of the earlier failure, files changed, clip names, REAL output lines.

