ARIA Home: record the after-arrival live rerun (docs only). DO THE WORK NOW in this turn. IMPORTANT: a message
without a tool call ends your turn, so never write a status or plan sentence on its own; keep editing until the
done-condition holds. No live calls, no installs, no git, NO helper scripts. Shell starts in C:\aria-home. Do not
end your turn until `cd backend && python -m pytest -q` passes.

Brad approved a rerun of only the six after-arrival cases after the inv-v3 contract change: exactly 6 calls on
muse-spark-1.3 via the Meta Model API against snapshot efdff57, 90 s timeout, 12000 output tokens, no retries.
Raw records: backend/eval/results-live-arrival-efdff57.json (every number must come from it). Operator summary for
cross-checking: 5 of 6 valid, all 5 agreeing with arrival_passed; 1 rejected, demo_no_followup_v1@20:31, because
the answer said "below target", contradicting the resolved target_gap fact.

In docs/evaluation.md add this run to the live-runs table and a short section: what changed (inv-v2 -> inv-v3,
temperature_at_arrival), the result, and that it covers only the six after-arrival cases, so it is not a full
re-run and the 77cafc9 17-case run (inv-v2) stays as recorded. Say plainly that the remaining rejection is a
genuine claim-check catch, not a contract gap. Update README Results and the docs/submission.md write-up to cite
both runs accurately without merging them into one number. No dollar figures.
Final answer: files changed and the REAL pytest line.

