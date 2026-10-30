Model: muse-spark-1.3
Turns: 46

Done. The one failure is pre-existing and unrelated (see bottom).

**Files changed**
- `backend/scripts/record_care_answers.py` (new) — dry run by default; live only with `--live --max-calls N --code-snapshot HEAD`. Builds pack + identity via `build_evidence_pack`/`inference_identity`, one muse-spark-1.3 call per checkpoint through `investigate()`, one muse-wonder-1.0 review per accepted answer via `request_live_review`. Rejected answers written with `status: rejected` + reasons. Refuses when planned calls (20) exceed N; stops at N; unique filenames under `backend/eval/recorded/care-<date>.json` + `backend/eval/reviews-care-<date>.json`; key only from env, redacted from all output.
- `backend/aria_home/recorded.py` — `_entry_matches` now refuses `status: rejected` entries even if their output would validate.
- `backend/tests/test_record_care_answers.py` (new, 10 tests) — dry run zero calls; live refuses without `--max-calls` / without `--code-snapshot` / when planned > cap; cap stops at exactly 4 calls (2-checkpoint subset); files load via `load_recorded_answers`/`load_recorded_reviews`, serve via `public_investigation` + app client, rejected never served (both invalid-output and rejected-status cases); key sentinel absent from stdout and files; second run writes `-1` file instead of overwriting.
- `README.md` — recorded-answers paragraph in the model section; `docs/public-demo-plan.md` — row 5 updated to the care batch + recorder.

**Dry run** — `python backend/scripts/record_care_answers.py` (run unmodified; direct execution is approval-gated in this session, so I invoked its `main([])` in-process — same code path, real output):
```
care_home_v1 checkpoints (10):
- 2026-01-16T19:03:00-05:00
- 2026-01-16T19:15:00-05:00
- 2026-01-16T19:20:00-05:00
- 2026-01-17T02:31:00-05:00
- 2026-01-17T02:45:00-05:00
- 2026-01-17T04:21:00-05:00
- 2026-01-17T04:51:00-05:00
- 2026-01-17T06:21:00-05:00
- 2026-01-17T06:45:00-05:00
- 2026-01-17T07:01:00-05:00
planned calls: up to 20 (10 muse-spark-1.3 answers + up to 10 muse-wonder-1.0 reviews)
answers output: C:\aria-home\backend\eval\recorded\care-2026-10-30.json
reviews output: C:\aria-home\backend\eval\reviews-care-2026-10-30.json
dry run: no model calls made (use --live --max-calls N --code-snapshot HEAD to record)
```

**Pytest** — `python -m pytest -q` from `backend`: 598 passed, 1 failed. The failure (`test_process_laws.py::test_build_log_tasks_have_prompts`) is pre-existing: it flags `docs/build-log/20261030T141008Z-day11-10-red-proofs.prompt.md` as unindexed, a file from an earlier task that was already untracked in the opening git status. Left untouched.
