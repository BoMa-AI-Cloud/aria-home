# Day 7 and Day 8 handoff

## Day 7

- D7-1 readiness after arrival (commit 0ebc264): adds `arrival_passed`, decided at arrival from readings received by arrival. The first run was rejected by operator review because it fired at arrival (`now >=` arrival) and scored too coarsely; corrected in D7-1b to fire strictly after arrival (`now >` arrival) with `target_at_arrival` (`met`/`not_met`/`unknown`) and per-case scoring of readiness plus at-arrival outcome.
- D7-2 UI fixes from the operator walk-through (commit 4d3bacb): Investigation renders the per-scenario created result with `Evaluation time:` (4:31 PM for the video scenario at 16:31); Outcome shows `Latest reading used: observed / received` plus `Evaluation (replay) time`; History lists verification stages with the old follow-up rule kept only as a small line; readiness reasons use formatted numbers and durations; notification and event payloads use human labels with a `fields sent:` line.
- D7-3 usability kit and freeze (commit 88ad45b, docs only): `docs/usability.md` facilitator kit (consent script, mock-mode setup with fresh DB, 5 tasks, blank P1-P5 table) and `docs/freeze.md` (frozen 2026-10-26 at 4d3bacb; allowed: bug/accessibility/wording fixes, docs, video, submission; not allowed: features, sources, providers, integrations).

Operator checks at 4d3bacb: backend 216 passed, typecheck and build passed, e2e 4 passed.

## Day 8

- D8-1 as-built video plan (commit 2a70217): rewrote `docs/demo-script.md` to the as-built app (inv-v2, verification stages `telemetry_missing` to `arrival_met`, `demo_video_v1` replay times 16:31 through 21:01, simulated-timeline cards for email/location/confirmation/scene/visit/report, 180 s storyboard, acceptance criteria, filming checklist).
- D8-1b rebalanced storyboard (commit a7f2bdd): 40 s for independent recovery (1:30-2:10), voiceover total 319 words. The Muse run returned the table without editing the file and the operator pasted it verbatim.
- D8-2 footage recorder (commit 7f23970): `frontend/playwright.record.config.ts` plus `frontend/recording/demo.record.ts` with `npm run record:demo`; drives the real frontend and backend at 1280x720 in mock mode on a fresh database, one `.webm` per storyboard segment to `frontend/recordings/` (ignored by git). 5 clips recorded by the operator, e2e 4 passed.
- D8-3 judges' README (commit b7da8f3): README rewritten for judges (existing-vs-new statement, Meta model use, results, 5-minute setup, safety rules, known limits).

## Still open

User sessions (Brad), voiceover and final edit (Brad), the evaluation title card and door shots (not product UI), office-hours answers, Day 9 clean-setup check, Day 10 submission.
