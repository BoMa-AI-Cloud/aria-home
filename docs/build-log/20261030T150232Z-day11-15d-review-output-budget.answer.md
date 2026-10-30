Model: muse-spark-1.3
Turns: 24

Done. `cd backend && python -m pytest -q` passes: **620 passed**.

**Files changed**
- `backend/aria_home/review.py`
  - Added `REVIEW_MAX_OUTPUT_TOKENS = 16000` (kept `DEFAULT_MAX_TOKENS = 512`; nothing else imports it — `provider.py` has its own); `build_review_request` now sends `max_output_tokens: 16000` and no `reasoning` parameter.
  - `parse_review_response` now checks the Responses envelope first: `status: "incomplete"` → `(None, ["review incomplete: <incomplete_details.reason or 'unknown'>"])`; `status: "failed"` or any `error` object → `(None, ["review failed: <code or message, ≤200 chars>"])`. Completed replies parse as before, so `request_live_review` returns the failed validation with that reason.
  - Exported `REVIEW_MAX_OUTPUT_TOKENS` in `__all__`.
- `backend/scripts/record_care_answers.py` — no change needed: `_record_review` already prints `"; ".join(validation reasons)` in the "review not recorded" line, so the incomplete/failed reason surfaces.
- `backend/tests/test_review_transcript.py`
  - Updated `test_review_request_uses_max_output_tokens` to expect 16000 and assert no `reasoning`/`max_tokens` keys.

**Tests added** (`test_review_transcript.py`, fakes built from the two real operator shapes)
- `test_review_incomplete_response_names_budget_reason` — reasoning-only incomplete envelope → `review incomplete: max_output_tokens`, no review.
- `test_review_incomplete_response_without_details_is_unknown` — missing details → `unknown`.
- `test_review_failed_response_names_error` — failed-status and bare error-object envelopes, incl. 200-char truncation.
- `test_live_review_reports_incomplete_budget_reason` — `request_live_review` with fake 200/incomplete: request carries 16000, validation failed with the incomplete reason.
- `test_live_review_completed_shape_passes_no_issues` — fake 200/completed with the real output-text shape → verdict `no_issues`, validation passed.

Real pytest line: `cd backend && python -m pytest -q` → 620 passed.
