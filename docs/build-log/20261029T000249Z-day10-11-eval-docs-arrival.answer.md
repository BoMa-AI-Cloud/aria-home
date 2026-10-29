Model: muse-spark-1.3
Turns: 16

Done. `cd backend && python -m pytest -q` → 400 passed.

Files changed:
- `docs/evaluation.md` — live-runs table row for the efdff57 rerun (6 calls, 5 valid, 1 rejected, 5/5 agreement) plus a new inv-v3 after-arrival rerun section with per-case results; contract note updated (inv-v2 runs vs inv-v3 rerun); 77cafc9 section now points to the rerun instead of saying it was never repeated
- `README.md` — Results cites the 77cafc9 17-case run and the efdff57 6-case rerun separately, never merged
- `docs/submission.md` — write-up cites both runs; the "run has not been repeated" line replaced with rerun results
- `backend/aria_home/evaluation.py` — one rendered contract sentence updated to match the docs (required by `test_committed_evaluation_docs_start_with_rendered_offline`)

Result as recorded: 5 of 6 valid, all 5 agreeing with `arrival_passed`; the single rejection (`demo_no_followup_v1@20:31`) is a genuine claim-check catch — the answer said "below target" against the resolved target_gap fact.
