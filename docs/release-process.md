# ARIA Home release process

Adopted 2026-10-29 at Brad's request. Every change goes through these stages in order. A stage that fails sends the
change back; a stage that was skipped is recorded as skipped in the operator log, never as passed.

| # | Stage | How it is done in this repository | Evidence it leaves |
|---|---|---|---|
| 1 | Decide and record the change | Brad's request or an audit finding is written into the ledger before work starts | docs/public-demo-plan.md, docs/audit-4.md, the operator log, the ledger page |
| 2 | Read up on the affected area | the Muse task prompt names the files and docs to read first | the task prompt in docs/build-log/ |
| 3 | Build it in isolation | one Muse task at a time through the worker, from a known tree; no two tasks edit at once | the task's build-log prompt and answer |
| 4 | Fix the whole problem class and add a safeguard | the task fixes every instance of the defect class, not only the reported one, and adds a regression test | the test files named in the audit row |
| 5 | Prove the safeguard catches the failure | a Muse task temporarily undoes each fix, runs its regression test, records the real FAILING assertion, restores the fix and records the pass; a test that still passes with the fix removed is strengthened; the operator retests | docs/red-proofs.md, then the operator retest line |
| 6 | Test locally | backend pytest, frontend typecheck and build, browser e2e in both timezones, the alternate-port command | the real output lines in the task answer and the operator check |
| 7 | Submit and review | the operator reviews the diff and retests the reproductions; any failure goes back to Muse as a new task (the operator does not fix code) | operator-log "Verified task ..." lines |
| 8 | Merge into the release batch | local pathspec commits grouped by area, pushed only with Brad's approval | commit ids in the operator log |
| 9 | Automated test run | GitHub Actions CI on the pushed commit | the CI run id and result |
| 10 | Pre-release checks | fresh clone set up from the README alone; credential-value scan of changed files; no live flags in example config; public-demo boundary tests | operator-log pre-release line |
| 11 | Deploy | only after Brad approves a specific host and deploy step | the deploy record |
| 12 | Restart and confirm the new version is running | GET /api/health reports `version.commit` and `version.source`; the commit comes from ARIA_HOME_RELEASE_COMMIT set at deploy time, else backend/RELEASE_COMMIT written at build time, else "unknown" with source "not stamped" (never read from git at runtime). It must equal the released commit; "unknown" fails this stage. The app footer and public-demo landing show "Version <short commit>" | the health response at the public URL |
| 13 | Post-release setup steps | none yet (no data migrations); listed here if a release ever needs one | n/a |
| 14 | Confirm the system knows about the change | in a clean browser at the public URL, the change is visible in the app (for example the new scenario, the Laws page, the version line) | a screenshot or page-text check in the operator log |
| 15 | Mark deployed, monitor overnight, mark verified, document | the ledger row moves to deployed; an overnight check (health and one guided-story run) runs at least once before it is marked verified; the ledger and docs are updated | ledger page, operator log |

Stages 11-15 do not apply until a deployment is approved. Until then a release ends at stage 10.
