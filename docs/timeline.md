# Timeline (UTC, 2026-10-26)

Times for commits come from `git log`. EDT = UTC-4.

- 14:58Z: A placeholder repository (README only) was created, before the kickoff.
- 15:40Z: The placeholder repository was renamed, made private and archived. It contains no code.
- 16:23Z: The Meta Global AI Developer Hackathon kickoff session ended (12:23 PM EDT). Organizers: building starts after the kickoff session. Solo entrant Brad Wentzel, Indie Developer track.
- 16:23Z: This repository was created fresh: commit f333d48 (README and .gitignore).
- 16:37Z: Commit 79d2730, Task 1: backend health endpoint and tests.
- 16:44Z: Commit 20f67ec, Task 2: evidence foundation (contracts, scenario clock, freshness, synthetic demo scenario, `/api/sources`).
- 16:47Z: Commit 3e2a6fa, Task 4: provider adapter (mock and gated live Meta provider, `/api/provider`).
- 16:48Z: Commit 0ba5213, Task 3: frontend with four synthetic source cards.
- 16:52Z: Live smoke test 001 through the app's adapter, approved by Brad: max_tokens 16. Model muse-spark-1.3 answered but returned no text (the limit was spent on hidden reasoning).
- 16:54Z: Commit 817fb25: the adapter reports reply block types, stop reason and usage; new `no_text` error.
- 16:54Z: Live smoke test 002 through the app's adapter, approved by Brad: max_tokens 256. OK, text "ready", 2.4 s, 15 input / 152 output tokens, blocks [redacted_thinking, text], stop_reason end_turn.
- 17:00Z: Commit 09b1dbd: missing-reading counts on source cards, key read only from MODEL_API_KEY, app smoke test.
- 17:09Z: Commit 24750c2, D2-1 metrics: indoor trend, target gap, circuit activity, cadence-based coverage, `/api/metrics`. Three Muse runs: the operator's review found coverage overstating a 2-hour gap (0.97); the first fix broke 13 tests (a tuple-unpacking bug) because Muse could not run tests; with test permission widened, Muse repaired it. Demo at 18:00 local: indoor flat ~52 F, 15.9 F below the 68 F target; furnace circuit quiet, coverage 0.50, one gap over cadence.
- 17:12Z: Commit 8c171ca, D2-2 Property Power Context: per-circuit status, one meter lineage, mains not_available, heating binding confirmed, backup unknown, continuity activity_weighs_against_total_loss, the limited statement and four limitations, banned-phrase guard, `/api/power-context`. Written by muse-wonder-1.0.
- 17:14Z: Commit 8002671: meter lineage from a synthetic meter_id ("demo-cabin-meter-1"), unknown-meter limitation. Written by muse-spark-1.3.
- 17:33Z: Commit 814ca9e: Playwright browser test on installed Chrome (closed the Day 2 gap), favicon 404 fix, verified test counts, setup instructions split by terminal.
- 17:36Z: Commit 353415a, D3-1 (muse-wonder-1.0): investigation engine: evidence pack built only from records visible at the evaluation time, trip title quoted as untrusted text, versioned prompt inv-v1, strict output schema, validate() (unknown evidence ids, uncited observations, numbers not in the pack, banned phrases, readiness inconsistent with the computed gap), fallback to the deterministic summary, `/api/investigation`. Mock provider labeled "[MOCK]".
- 17:38Z: Commit 8736673: public build log of every Muse prompt and answer (docs/build-log/).
- 17:42Z: Commit c2d00ca, D3-2 (muse-spark-1.3): the browser opens on the Investigation section (readiness in words with temperatures, cited observations, hypotheses labeled as such, unknowns, one question, next check, Power Context with limitations, provenance line, mock label); evidence cards below.
- 17:43-17:44Z: Live investigation run 1, 6 calls approved by Brad (3 muse-spark-1.3, 3 muse-wonder-1.0), demo scenario, 1500 output tokens, no retries: 0 of 6 produced an answer; every reply was hidden reasoning only and stopped at the output limit.
- 17:47Z: Commit dbe4ab6: configurable investigation output limit (ARIA_HOME_INVESTIGATION_MAX_TOKENS, default 8000) and an explicit no_text reason when the limit is reached.
- 17:47-17:49Z: Live investigation run 2, 4 calls approved by Brad (2 per model), 8000 output tokens, 90 s timeout, no retries: 4 of 4 passed validation, all readiness "at_risk". muse-spark-1.3: 22.7-23.5 s, 6,917-7,350 output tokens. muse-wonder-1.0: 39.0-49.3 s, 5,713-7,943 output tokens. Runtime model chosen: muse-spark-1.3 (same pass rate in this small sample, about half the latency). Four calls on one scenario is not an evaluation; the full comparison is planned for Day 6.
- 17:52Z: Commit 5df95cb: evidence-pack numbers rounded for the model (e.g. -15.9, 0.034); validation against rounded values; default limit 12000.
- 17:53Z: Commit e1b488d: validator accepts the absolute value of a signed pack number (15.9 for -15.9); found by the operator's probe.
- 17:54Z: Commit 603773e: the missing regression tests. Tests now: 109 passed (backend); browser test 1 passed.
- Open: organizer questions (build-start time, hosted URL, labeled simulated data live, editing a submission) to be asked in Discord office hours. Investigation output persistence and follow-up outcomes are not built yet.
- Next (Day 4): persistent follow-through: store each investigation and its expected follow-up, ingest later measurements, and decide warming observed / target reached / not observed by the deadline / unable to verify, surviving restarts.
- 2026-10-26: Verification repair of four audit findings (see docs/day3-handoff.md).
- 2026-10-26: Day 4: follow-up outcomes with SQLite store, outcome history and replay UI; store thread-safety fix; inv-v2 verification repair (claim binding, code-computed readiness and scheduling, as-of context with revised/cancelled variants); demo video plan (docs/demo-script.md); outcome deadline fix; room-sensor source, simulated events and demo_video_v1 with a committed deterministic stream generator; recovery verification stages; video screen with simulated timeline. Checks at 734605b: backend 188 passed, typecheck and build passed, browser 3 passed. Live smoke (operator run): 3 inv-v2 muse-spark-1.3 calls on demo_v1, all valid, readiness at_risk, 19.8/30.9/17.8 s.
- 2026-10-26: Day 5: scoped notifications with per-audience allowlists and recorded refusals (D5-1, 4723bba); notifications panel, simulated acknowledgement and homeowner arrival update (D5-2, e512a55). Checks at e512a55: backend 198 passed, typecheck and build passed, browser 4 passed. No live model calls.
- 2026-10-26: Day 6: evaluation harness with 12 builder-labeled cases across combined vs single-source conditions (D6-1, 53a06bd) and live results on 24 operator-run calls (D6-2, 8b2f07d). Checks at 53a06bd: backend 205 passed. No live model calls by Muse; the offline CLI and live runs were operator-run.
- 2026-10-26: Day 7: readiness after arrival (D7-1 first run rejected by operator review because it fired at arrival and scored too coarsely; corrected in D7-1b; commit 0ebc264); operator walk-through UI fixes (D7-2 4d3bacb; backend 216 passed, typecheck and build passed, e2e 4 passed); user-test kit and feature freeze (D7-3 88ad45b, docs/usability.md, docs/freeze.md).
- 2026-10-27: Day 8: as-built video plan (D8-1 2a70217) and rebalanced storyboard (D8-1b a7f2bdd; the Muse run returned the table without editing the file and the operator pasted it verbatim); footage recorder (D8-2 7f23970; 5 clips recorded by the operator, e2e 4 passed); judges' README (D8-3 b7da8f3).

## How the code was written

All code was written by Claude Code sessions running Meta models (muse-wonder-1.0 for design and integration, muse-spark-1.3 for routine work). The operator reviewed each change against the project's evidence rules, ran the tests and build, and ran `npm install` after Brad approved it.

## Open organizer questions

To be asked in Discord office hours: whether a hosted URL is expected for the live product; whether a clearly labeled simulated data feed is acceptable live; whether a submission can be edited before the deadline.
