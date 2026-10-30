Model: muse-spark-1.3
Turns: 27

Done. `cd backend && python -m pytest -q` passes: **615 passed**.

**Files changed:**
- `backend/aria_home/review.py` — `build_review_request` now sends `max_output_tokens` (was `max_tokens`, which the Responses API rejects with 400); `_candidate_texts` now also yields the `output_text` convenience field (kept the existing `text` and `output[].content[].text` handling, which already covers `output_text`-typed blocks).
- `README.md` — replaced the stale "recorded/ holds no committed files" sentence: the hosted app serves the recorded muse-spark-1.3 answers for the ten care checkpoints and the labeled fallback anywhere else.
- `backend/aria_home/visual.py`, `provider.py` — untouched: `SamLiveProvider.build_request` (sam-3.1 → `/v1/responses`) already carries no token limit; provider/watcher Messages-API bodies keep `max_tokens`.

**Tests added:**
- `backend/tests/test_review_transcript.py::test_review_request_uses_max_output_tokens` — asserts `max_output_tokens` present, `max_tokens` absent, URL is `/v1/responses`.
- `backend/tests/test_review_transcript.py::test_review_response_parses_output_text_blocks` — Responses-shaped `output[].content[]` with `type: output_text` parses into a review.
- `backend/tests/test_review_transcript.py::test_review_response_parses_output_text_field` — top-level `output_text` convenience field parses.
- `backend/tests/test_visual.py::test_sam_live_request_carries_no_max_tokens` — sweep test for the only other `/v1/responses` builder.

Real pytest line: `615 passed in 125.85s (0:02:05)`
