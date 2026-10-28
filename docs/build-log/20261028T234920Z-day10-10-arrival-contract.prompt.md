ARIA Home: fix the after-arrival contract gap (approved by Brad, 2026-10-28). DO THE WORK NOW in this turn.
IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; keep
editing and running commands until the done-condition holds. No live calls, no installs, no network beyond
127.0.0.1, no git, NO helper scripts outside tests. Mock/fake providers only. Shell starts in C:\aria-home. Do not
end your turn until `cd backend && python -m pytest -q` and `cd frontend && npm run test:e2e` pass.

Evidence: in the 2026-10-28 live run (backend/eval/results-live-77cafc9.json) all 6 rejected answers were cases
whose computed readiness is arrival_passed. After arrival every reading is old by design, but the investigation
contract/prompt (read backend/aria_home/investigator.py, the inv-v2 prompt and its validator) still leads the model
to state a "current_temperature", and the claim checks correctly reject a stale or superseded reading presented as
current.

Fix the CONTRACT, not the checks:
- When computed readiness is arrival_passed (or the evaluation time is after arrival), the contract asks for the
  temperature AT ARRIVAL: the last eligible reading observed and received by the arrival time, cited by its
  evidence id with its observed time, as a distinct fact kind (for example `temperature_at_arrival`). It does not
  ask for, and the model must not state, a current temperature.
- The claim checks keep rejecting any reading presented as current that is stale or superseded, and must reject a
  `temperature_at_arrival` fact that cites a reading observed or received after arrival, or not the last eligible
  one by arrival, or an ineligible/conflicted one. Electrical activity is never a temperature fact.
- Bump the prompt version (inv-v2 -> inv-v3) and any policy/contract version strings you change; the inference
  identity must change accordingly. Update the deterministic fallback summary and the mock provider so mock
  answers follow the new contract.
- Tests: for each of the 6 cases (demo_recovery_v1@19:00, @20:31, demo_no_followup_v1@20:31,
  demo_video_v1@21:01, visual_water_low_temp_v1@19:00, visual_frost_missed_v1@20:31) a well-formed mock answer
  passes; an answer citing a stale reading as current is still rejected; a temperature_at_arrival citing a
  post-arrival reading is rejected; pre-arrival cases are unchanged.
- Docs: docs/evaluation.md notes the contract change and that earlier runs used inv-v2; docs/readiness-rules.md /
  docs/inference-idempotency.md as needed.
Final answer: root cause, files changed, tests added, and the REAL output lines of both commands.
Also: docs/submission.md and README still describe the OFFLINE evaluation as "12 builder-labeled synthetic cases
across 6 scenarios", but the code now has 17 cases (including the visual scenarios). Recompute the offline results
with the existing offline evaluation command and update those sentences to the exact counts the code produces.

