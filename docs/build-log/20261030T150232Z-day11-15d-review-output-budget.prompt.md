ARIA Home: give the muse-wonder-1.0 review enough output budget (approved by Brad, 2026-10-30). DO THE WORK NOW in this turn. IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; keep editing and running commands until the done-condition holds. No live calls, no installs, no git, no network beyond 127.0.0.1. Tests use fakes only. Do not weaken any test. Keep all working-tree changes; do not touch backend/eval/recorded/. Shell starts in C:\aria-home. Do not end your turn until `cd backend && python -m pytest -q` passes.

Real live results from the operator (commit 798ff77, the 07:01 care answer):
- with max_output_tokens 512 (review.DEFAULT_MAX_TOKENS): HTTP 200, `"status": "incomplete"`, `"incomplete_details": {"reason": "max_output_tokens"}`, usage output_tokens 512 of which reasoning_tokens 510 (the model's default reasoning effort is "max"), output = one item of type "reasoning" with no content. The app reported only "review response carried no JSON review output".
- with max_output_tokens 16000: `"status": "completed"`, 16 s, output_tokens 1770 (1747 reasoning), and a message item whose content is `{"type": "output_text", "text": "{\"verdict\": \"no_issues\", \"issues\": []}"}`, which request_live_review validated as passed.

Fix in backend/aria_home/review.py:
1. A review-specific budget REVIEW_MAX_OUTPUT_TOKENS = 16000 used by build_review_request (keep DEFAULT_MAX_TOKENS if anything else uses it; check). Do not send a reasoning parameter.
2. parse_review_response (or request_live_review): a Responses API reply with status "incomplete" yields a failed validation whose reason names it, e.g. "review incomplete: max_output_tokens" (use incomplete_details.reason; "unknown" if absent), and a reply with status "failed" or an error object yields "review failed: <error code or message, max 200 chars>". A completed reply keeps today's parsing.
3. backend/scripts/record_care_answers.py prints that reason when a review is not recorded (it already prints the validation reasons; confirm).
4. Tests with fakes built from the two real shapes above: the request carries max_output_tokens 16000; the incomplete shape gives the incomplete reason (and no review); the completed shape gives verdict no_issues and passes.
Final answer: files changed, tests added, and the REAL pytest line.

