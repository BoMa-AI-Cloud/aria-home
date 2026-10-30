Model: muse-spark-1.3
Turns: 65

All work that doesn't need process execution is done and statically verified. Python execution is blocked in this session — every `python` invocation via Bash returns "requires approval", so I can't produce the dry-run output or the pytest run. Final report:

## Files changed

- **`backend/aria_home/watcher.py`** — added `is_unreadable_rejection(entry)` (rejected + `failed_checks` non-empty and all either `invalid JSON…` or `NO_TEXT_REASON`), `find_all_recorded_watchers(...)` (all identity matches), `newest_recorded_watcher(matches)` (newest by `recorded_at`, ties → later position). `find_recorded_watcher` now serves the newest `confirmed` / `corrected and verified` match; an unreadable rejection never hides a readable entry; a lone real rejection is still returned. All three exported in `__all__`.
- **`backend/scripts/record_care_watcher.py`** — `_missing_plan` uses `find_all` + `newest` + `is_unreadable_rejection`: only unreadable rejections (and absent checkpoints) count as missing. Real code-check rejections are skipped.
- **`docs/evaluation.md`** — "Second review" section rewritten (everything before `## Live model condition` untouched): ten bound muse-wonder-1.0 reviews in `reviews-care-2026-10-30-1.json`, each with the reviewed answer's `answer_digest`, all `no_issues`; legacy file kept for the record, not served while a bound review exists; 71 F falsification control → `issues_found` / `contradiction` citing room-care-1630 (52.0 F); bounded-check wording kept.
- **`docs/build-log/README.md`** — indexed the two unlisted pairs (`185314Z-day11-22-record-care-watcher`, 36 turns, `665 passed`; `190709Z-day11-22b-watcher-thinking-block`, 51 turns), results = first content line of each answer.

## Tests added (existing tests untouched)

- `backend/tests/test_watcher.py`: newest-verified-wins on repeat identity; verified preferred over newer real rejection; unreadable rejection (both `invalid JSON…` and thinking-only variants, either list order) never hides readable entry; real-check rejection is not unreadable and still served; `load_recorded_watchers` aggregates two files and `find` returns the readable entry.
- `backend/tests/test_record_care_watcher.py`: seeded 8-checkpoint dry-run `--only-missing` plans `up to 4 (2 first + up to 2 revisions)`, skips 6; thinking-only rejection re-recorded; real code-check rejection kept (plans `up to 0`).

## Blocked: dry-run output and REAL pytest line

Both commands below are refused by this session's permission mode (`Tool error: This command requires approval`, tried as single and compound commands):

- Dry run (from `backend/`): `python scripts/record_care_watcher.py --only-missing` — by code analysis against `backend/eval/watchers-care-2026-10-30.json` (single file; 02:31/02:45 rejected with exactly `invalid JSON: Expecting value: line 1 column 1 (char 0)`, other 6 verified) it will print `planned calls: up to 4 (2 first + up to 2 revisions)` and `only-missing: skipped 6 recorded watcher(s); 2 checkpoint(s) still needed`, but I could not execute it to confirm.
- Tests: `cd backend && python -m pytest -q` — not run; zero-failure done-condition unverified.

Approve python execution (or run those two commands yourself) and I'll confirm the outputs immediately.
