Model: muse-spark-1.3
Turns: 33

Done. Full suite: **801 passed, 1 failed** — the only failure is the named doc test, which fails solely because `docs/evaluation.md` needs regenerating (I did not touch it, per instructions).

**Files changed**
- `backend/aria_home/evaluation.py` — `watcher_correction_rates()` docstring corrected; returned keys renamed to `correction_records` / `first_attempts_failed` / `verified_after_revision` (+ `note`); `render_markdown()` section heading is now `## Watcher correction records`, zero-record branch no longer mentions rates, non-zero branch renders the specified sentence with computed counts. Only caller (`render_markdown`) updated; no other code or tests referenced the old keys.
- `backend/tests/test_evaluation.py` — added 3 tests: rendered section bans `Recorded runs` / `rate 1.00` and asserts counts come from the records; synthetic-records test proves `correction_records` / `first_attempts_failed` / `verified_after_revision` are computed from `corrections-*.json`; empty-directory test asserts the zero branch carries no rate wording.

**Red-proof**: temporarily restored the old `Recorded runs: 3; ... (rate 1.00)...` sentence — `test_watcher_correction_section_counts_records_not_runs` failed on `assert "Recorded runs" not in text` — then restored the fix and reran (passes).

**Exact counts** (from `backend/eval/corrections-*.json`, 3 files): Correction records: **3**; first attempts failed code checks: **3**; verified after one revision: **3** (all `final_result: "corrected and verified"`).

**Needs operator regeneration**: `test_committed_evaluation_docs_start_with_rendered_offline` — `docs/evaluation.md` still carries the old `Recorded runs: 3; first-pass rejections: 3 (rate 1.00); passes after correction: 3 (rate 1.00).` line.
