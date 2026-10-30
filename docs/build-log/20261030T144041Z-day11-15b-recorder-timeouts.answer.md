Model: muse-spark-1.3
Turns: 44

Done. `cd backend && python -m pytest -q` passes: **606 passed**.

## Files changed

- `backend/aria_home/review.py`
  - `send_review_request` failure results now carry `status` (HTTP code or `None`) and `detail` (≤300 chars of the response's error message or body, API key replaced with `[redacted]`). Timeout/exception paths return `status: None, detail: ""`.
  - `request_live_review` propagates `status`/`detail` on failure so callers can print them. Success shape unchanged; existing review tests pass.
- `backend/scripts/record_care_answers.py`
  - `--timeout-s` (default `180.0`): applied via `dataclasses.replace` on the `ProviderConfig` for the real provider path, best-effort onto an injected provider (`timeout_s` attr / `config.timeout_s`), and passed as `request_live_review(..., timeout_s=...)`.
  - Review-not-recorded line now prints `(status=..., detail=...)`, still redacted through `emit`.
  - `--only-missing`: scans `care-*.json` in the recorded dir and `reviews-*.json` in the reviews dir, matches on `(scenario_id, evaluated_at_utc, input_revision)`; accepted checkpoints skip the answer call, accepted-without-review makes only the review call. Planned count = answers needed + reviews needed, enforced by the `--max-calls` refusal and shown in dry-run/live output.
- `backend/tests/test_record_care_answers.py` — 7 tests added (see below). `backend/eval/recorded/care-2026-10-30.json` untouched.

## Tests added

- `test_recording_timeout_defaults_to_180s` / `test_recording_timeout_override_reaches_both_seams` — fakes assert the timeout value at both seams (provider attr + `http_post` `timeout_s`).
- `test_bad_review_response_reports_scrubbed_status_and_detail` — fake 400 with sentinel key in message: stdout shows `400` + `[redacted]`, never the key.
- `test_send_review_request_failure_carries_status_and_scrubbed_detail` — direct unit check: `status == 400`, scrubbed, `len(detail) <= 300`.
- `test_only_missing_plans_nine_answers_plus_ten_reviews` — 1 accepted + 9 rejected seed: `--max-calls 18` refuses with `planned 19 calls exceed --max-calls 18`, zero calls made.
- `test_only_missing_records_nine_answers_and_ten_reviews` — same seed at `--max-calls 19`: 9 provider calls + 10 review calls, `model calls made: 19`.
- `test_only_missing_dry_run_reports_exact_remaining` — dry-runs `main(["--only-missing"])` against real repo state.

## Dry-run output of `--only-missing` against the real repo state

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
planned calls: up to 19 (9 muse-spark-1.3 answers + up to 10 muse-wonder-1.0 reviews)
only-missing: skipped 0 recorded answer(s); 9 answer(s) and 10 review(s) still needed
answers output: C:\aria-home\backend\eval\recorded\care-2026-10-30.json
reviews output: C:\aria-home\backend\eval\reviews-care-2026-10-30.json
dry run: no model calls made (use --live --max-calls N --code-snapshot HEAD to record)
```

The single accepted checkpoint is picked up as review-only; the 9 rejected ones need fresh answers. No checkpoint has both answer and review yet, hence `skipped 0`.

## REAL pytest line

`606 passed in 146.59s (0:02:26)`
