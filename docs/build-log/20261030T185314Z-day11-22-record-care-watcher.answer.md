Model: muse-spark-1.3
Turns: 36

Done. `cd backend && python -m pytest -q` → **665 passed**.

**Files changed**
- `backend/scripts/record_care_watcher.py` (new): dry run by default; live only with `--live --max-calls N --code-snapshot SHA`; 8 checkpoints (19:20 control + 02:31–07:01), up to 16 calls; runs each checkpoint through `run_watcher` (own one-revision loop), saves verified corrections via `save_correction_record`, writes a unique `watchers-care-<date>.json` into the `load_recorded_watchers` directory; 180 s / 4096-token recording budget, app defaults untouched; key from `MODEL_API_KEY` only, redacted.
- `backend/tests/test_record_care_watcher.py` (new, 9 tests, fakes only): dry run zero calls; live refuses without cap/snapshot; cap below 16 refuses pre-call; fail-once fake gets exactly one revision call (corrected-and-verified + correction saved); files load via `load_recorded_watchers` and `/api/watcher` serves them in public-demo mode; failed run recorded as rejected, never lowers risk; timeout/budget reach the fake; second run never overwrites; `--only-missing` skips recorded checkpoints.
- `README.md`: watcher-recording paragraph in the model section. `docs/public-demo-plan.md`: step 11 notes the recorder.
- `docs/build-log/README.md`: added the missing row for the on-disk `20261030T180419Z-day11-18c-redesign-green` prompt/answer pair (pre-existing `test_build_log_tasks_have_prompts` failure, fixed by indexing, not by weakening).

**Dry-run output** (direct script execution needs approval in this session, so this is the exact text the passing dry-run test asserts — checkpoints, `up to 16`, output path, `dry run`, zero calls):
```
care_home_v1 watcher checkpoints (8):
- 2026-01-16T19:20:00-05:00
- 2026-01-17T02:31:00-05:00
- 2026-01-17T02:45:00-05:00
- 2026-01-17T04:21:00-05:00
- 2026-01-17T04:51:00-05:00
- 2026-01-17T06:21:00-05:00
- 2026-01-17T06:45:00-05:00
- 2026-01-17T07:01:00-05:00
planned calls: up to 16 (8 first + up to 8 revisions)
watchers output: backend/eval/watchers-care-<UTC-date>.json
dry run: no model calls made (use --live --max-calls N --code-snapshot HEAD to record)
```

**REAL pytest line:** `665 passed in 164.77s (0:02:44)`
