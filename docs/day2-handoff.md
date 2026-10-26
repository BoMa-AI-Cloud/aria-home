# Day 2 handoff

## What works

- D2-1 metrics (commit 24750c2): indoor trend, target gap, circuit activity, cadence-based coverage, `GET /api/metrics`. Checked by pytest; demo at 18:00 local: indoor flat ~52 F, 15.9 F below the 68 F target; furnace circuit quiet, coverage 0.50, one gap over cadence.
- D2-2 Property Power Context (commit 8c171ca, written by muse-wonder-1.0): per-circuit status, one meter lineage, mains not_available, heating binding confirmed, backup unknown, continuity activity_weighs_against_total_loss, the limited statement and four limitations, banned-phrase guard, `GET /api/power-context`. Checked by pytest.
- Meter lineage from a synthetic meter_id ("demo-cabin-meter-1"), unknown-meter limitation (commit 8002671, written by muse-spark-1.3). Checked by pytest.

## What was tested

- Backend: 80 passed at 8002671 (historical count when this handoff was first written, not the current total).
- D2-1 took three Muse runs: the operator's review found coverage overstating a 2-hour gap (0.97); the first fix broke 13 tests (a tuple-unpacking bug) because Muse could not run tests; with test permission widened, Muse repaired it.
- Browser test (`npm run test:e2e`, Playwright 1.64.1, installed Chrome, mock mode): 1 passed in 7.0 s. It checks the SYNTHETIC banner, the central question, the Investigation section above the evidence, four source cards with text status labels, "Missing readings: 1" on the thermostat card, the weather forecast label, and no page errors, console errors or failed requests.

## Current verification (2026-10-26 17:29Z)

Verification run by the operator on 2026-10-26 between 17:29:16Z and 17:30:14Z.

- Tested commit: 101fb9d6b7fa710e5278e284f8fe5439931fb343. Working tree was dirty, with uncommitted frontend-only changes (the browser test files, frontend/index.html, frontend package.json and package-lock.json, README.md). No backend file differed from that commit.
- Backend: a fresh virtual environment with only backend/requirements.txt (resolved Flask 3.1.3, httpx 0.28.1, pydantic 2.14.1, pytest 9.0.3); command `python -m pytest -q` from backend/; result 86 passed, 0 failed, 0 skipped, no warnings reported.
- Frontend, from frontend/: `npm run build` passed; `npm run typecheck` passed; `npm run test:e2e` (Playwright 1.64.1, installed Chrome, mock mode): 1 passed in 7.0 s. It checks the SYNTHETIC banner, the central question, the Investigation section above the evidence, four source cards with text status labels, "Missing readings: 1" on the thermostat card, the weather forecast label, and no page errors, console errors or failed requests.
- Historical counts (not current totals): 80 passed when docs/day2-handoff.md was first written (commit 8002671); 85 passed in a clean environment and 86 passed during the Day One closeout (commit ddbb3d6, same session).
- Live model calls: none today in this verification. The only live calls were the two historical smoke tests on 2026-10-26 at 16:52Z and 16:54Z (see docs/timeline.md).
- Day 3 functionality (the Meta investigation) is NOT implemented.

## Deterministic vs model

- All Day 2 code is deterministic; no model calls.
- No live model calls were made on Day 2.

## Known gaps

- Organizer questions still open, to be asked in Discord #office-hours Tue Oct 27 10-11 AM ET: hosted URL; labeled simulated data live; editing a submission.

## Next

- Day 3: the Meta investigation over the evidence, metrics and Power Context (model output validated against evidence ids, banned phrases and numeric claims), and the first full browser journey with the Investigation section filled.
