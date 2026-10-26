Model: muse-wonder-1.0
Turns: 34

**Change**
- `backend/aria_home/outcomes.py`: `evaluate_outcome` now counts only non-null `indoor_temp` measurement readings for the follow-up zone with `received_at <= now` and `created_at < observed_at <= deadline`, deduplicated by `(source, observed_at)`. Status order unchanged in effect but now on counted readings only: `target_reached` (last two counted ≥ target) → `warming_observed` → `awaiting_measurement` (`now < deadline`) → `not_observed_by_deadline` (≥ `min_samples`) → `unable_to_verify`. After-deadline readings add `Readings after the deadline are not counted toward this follow-up.`, joined with the retained human-statement causation note; statements still never set a status.
- `docs/readiness-rules.md`: added “Follow-up outcomes” section documenting the counting window, deduplication, status order, after-deadline note, and the `demo_recovery_v1` 20:31 example.
- `frontend/src/App.tsx`: `demo_recovery_v1` label renamed from “Manager visit, heat restored” to “Manager report, late warming”.

**Test assertions changed, and why**
- `backend/tests/test_outcomes.py`
  - `test_demo_recovery_target_reached_at_2030_with_note` → `test_demo_recovery_warming_at_2031_with_after_deadline_note`: status `target_reached` → `warming_observed`, `last_value` 68.4 → 66.9, `note == causation` → note contains both causation and after-deadline notes, plus `sample_count == 8` — the 68.2/68.4 readings at 20:15/20:30 are after the 20:00 deadline and no longer count.
  - `test_demo_recovery_not_target_reached_at_2015`: its hand-rolled counted-readings filter gained `observed_at <= deadline`; last counted value 68.2 → 66.9, counted at-target readings 1 → 0, added `last_value == 66.9` and the after-deadline note — same rule; its `warming_observed` status assertion is unchanged.
  - Added (no prior assertions changed): two at-target readings before the deadline give `target_reached`; a duplicated `(source, observed_at)` at-target reading counts once (`sample_count == 1`, not `target_reached`); post-deadline at-target readings alone give `unable_to_verify` (0 counted), and with 3 flat pre-deadline readings give `not_observed_by_deadline`, each carrying exactly the after-deadline note.
- `backend/tests/test_store.py`
  - `test_outcome_history_grows_idempotent_and_survives_restart`: history `[warming_observed, target_reached]` → `[warming_observed, warming_observed]` in all three assertions (20:31 GET, repeated 20:31 GET, reopened store) — 20:31 is now warming, not target.
  - `test_post_then_get_follow_up`: `status`, `outcome.status`, and `follow_up.last_status` at 20:30:20 `target_reached` → `warming_observed` — same rule.
- `frontend/e2e/app.spec.ts`
  - Scenario selection uses the new label; at 20:31 `Target reached` visible → `Warming observed` visible, added the after-deadline note assertion, kept the causation-note assertion; history `Target reached` containment removed, `Warming observed` history, item count ≥ 2, and the no-follow-up “Unable to verify” assertions kept unchanged.

**Real output lines**
- `cd backend && python -m pytest -q` → `170 passed in 3.92s`
- `cd frontend && npm run typecheck` → `> tsc --noEmit` (no errors)
- `cd frontend && npm run test:e2e` → `ok 1 [chrome] › e2e\app.spec.ts:5:1 › synthetic evidence overview renders without errors`, `ok 2 [chrome] › e2e\app.spec.ts:80:1 › demo replay controls drive the outcome panel`, `2 passed (9.9s)`
