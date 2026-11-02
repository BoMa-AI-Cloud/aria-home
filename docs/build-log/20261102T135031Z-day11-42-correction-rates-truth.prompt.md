ARIA Home: one misleading number. DO THE WORK NOW in this turn. IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; every message must carry a tool call until your final report. No live calls, no paid calls, no installs, no git, no network beyond 127.0.0.1. Do not weaken any test without replacing what it proved. Never edit backend/eval/ or backend/scenarios/. Do not edit docs other than what the runner writes itself. Shell starts in C:\aria-home. Use the Bash tool for every command, one per call, no pipes: `cd backend && python -m pytest -q`. You cannot run other Python scripts in this session.

The defect. backend/aria_home/evaluation.py, `watcher_correction_rates` and the section that renders it, prints:
"Recorded runs: 3; first-pass rejections: 3 (rate 1.00); passes after correction: 3 (rate 1.00)."
It reads backend/eval/corrections-*.json only. A correction record exists only when a first pass was rejected, so the first-pass rejection rate is 1.00 by construction and "Recorded runs" is not the number of watcher runs. A reader takes this to mean every watcher run failed its first attempt. The real numbers are elsewhere, and the function's docstring still says no runs have been recorded.

The fix:
1. Keep the function reading correction records. Stop calling them runs and stop printing a first-pass rejection rate from them. Rendered text when records exist, with the counts computed: "Correction records: 3; each began with a first attempt that failed code checks; 3 verified after one revision. A record exists only when a first attempt failed, so this is not a rejection rate across all watcher runs. Comparison C in docs/model-value-eval.md measures that on unseen nights." The section heading becomes "## Watcher correction records". Say "verified" only for records whose final_result is "corrected and verified" or "confirmed", as the code already computes.
2. Rename the returned keys so they say what they count, and update every caller and test. Keep the zero-record branch truthful and remove its placeholder wording about rates if it no longer applies.
3. Correct the docstring.
4. Add or update a test that fails if the rendered section contains "rate 1.00" or "Recorded runs", and that the counts come from the records. Red-proof it: restore the old sentence temporarily, watch it fail on an assertion, restore the fix with an edit, and rerun it.

If test_committed_evaluation_docs_start_with_rendered_offline then fails only because docs/evaluation.md needs regenerating, do not edit the doc and do not touch the test. Name it and the operator will regenerate it.

Done means: `cd backend && python -m pytest -q` passes except for that one named doc test, and your final message lists the files changed, the red-proof and the exact counts.

