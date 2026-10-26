ARIA Home, Day 3 follow-up (approved by Brad). No live calls, no installs, no network, no git.
Work only inside C:\aria-home. Run tests with `cd backend && python -m pytest -q`. Read only
backend/aria_home/investigator.py, backend/tests/test_investigator.py and .env.example.

FINDINGS from 4 approved live investigations (all passed validation):
- The model quoted raw floats from the evidence pack, e.g. "gap -15.899999999999999 F",
  "change 0.10000000000000142 F", "rate_per_hour 0.03428571428571477", "mean_w 2.6666666666666665".
- Output used up to 7,943 of the 8,000-token limit.

CHANGES
1. In build_evidence_pack, round every float in the pack to one decimal place for display to the
   model (values in metrics, power context, source statuses and evidence values), EXCEPT coverage
   and rate values that would round to 0.0 while non-zero: round those to two significant
   figures instead (e.g. 0.034). Do not change the deterministic metrics modules themselves or
   the /api/metrics and /api/power-context responses; only the pack the model sees.
2. Keep validation consistent: validate() must check numbers in the model's text against the
   ROUNDED pack values (and still allow those exact rounded values). A number present only in
   the unrounded data must now be rejected if it is not in the rounded pack.
3. Raise INVESTIGATION_MAX_TOKENS_DEFAULT to 12000 (keep the 256-32000 bounds) and update the
   .env.example comment.
4. Tests: the pack contains -15.9 for the target gap and no float with more than 2 decimals; the
   rate is 0.034 (two significant figures); validate accepts "-15.9" and rejects
   "-15.899999999999999"; the default limit passed to the provider is 12000; existing tests
   pass (update only expectations that asserted the old default or unrounded pack values, and
   list them).

Final answer: changes, updated expectations, and the REAL final pytest line.

