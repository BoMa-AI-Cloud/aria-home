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

## How the code was written

All code was written by Claude Code sessions running Meta models (muse-wonder-1.0 for design and integration, muse-spark-1.3 for routine work). The operator reviewed each change against the project's evidence rules, ran the tests and build, and ran `npm install` after Brad approved it.

## Open organizer questions

To be asked in Discord office hours: whether a hosted URL is expected for the live product; whether a clearly labeled simulated data feed is acceptable live; whether a submission can be edited before the deadline.
