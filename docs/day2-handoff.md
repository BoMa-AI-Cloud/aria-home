# Day 2 handoff

## What works

- D2-1 metrics (commit 24750c2): indoor trend, target gap, circuit activity, cadence-based coverage, `GET /api/metrics`. Checked by pytest; demo at 18:00 local: indoor flat ~52 F, 15.9 F below the 68 F target; furnace circuit quiet, coverage 0.50, one gap over cadence.
- D2-2 Property Power Context (commit 8c171ca, written by muse-wonder-1.0): per-circuit status, one meter lineage, mains not_available, heating binding confirmed, backup unknown, continuity activity_weighs_against_total_loss, the limited statement and four limitations, banned-phrase guard, `GET /api/power-context`. Checked by pytest.
- Meter lineage from a synthetic meter_id ("demo-cabin-meter-1"), unknown-meter limitation (commit 8002671, written by muse-spark-1.3). Checked by pytest.

## What was tested

- Backend: 80 passed.
- D2-1 took three Muse runs: the operator's review found coverage overstating a 2-hour gap (0.97); the first fix broke 13 tests (a tuple-unpacking bug) because Muse could not run tests; with test permission widened, Muse repaired it.

## Deterministic vs model

- All Day 2 code is deterministic; no model calls.
- No live model calls were made on Day 2.

## Known gaps

- No automated browser test yet.
- Organizer questions still open, to be asked in Discord #office-hours Tue Oct 27 10-11 AM ET: hosted URL; labeled simulated data live; editing a submission.

## Next

- Day 3: the Meta investigation over the evidence, metrics and Power Context (model output validated against evidence ids, banned phrases and numeric claims), and the first full browser journey with the Investigation section filled.
