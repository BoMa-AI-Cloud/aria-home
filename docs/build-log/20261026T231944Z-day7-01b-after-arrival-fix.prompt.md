ARIA Home, Day 7 task D7-1b (approved by Brad): correct the after-arrival change from the previous
task (uncommitted in this working tree). DO THE WORK NOW in this turn. No helper scripts, no live
calls, no installs, no network, no git. Do not end your turn until `cd backend && python -m pytest -q`
passes and `cd frontend && npm run test:e2e` passes.

Read: backend/aria_home/readiness.py, evaluation.py, backend/eval/expected.json, docs/evaluation.md,
docs/readiness-rules.md, and the tests the previous task changed.

OPERATOR REVIEW FOUND TWO DEFECTS:
1. arrival_passed fires when now == arrival. demo_v1, demo_recovery_v1@18:00, demo_revised_v1 and
   demo_cancelled_v1 at 18:00 (arrival 18:00) now read arrival_passed, which breaks the main demo
   (it must stay at_risk at 18:00). Rule: arrival_passed only when now is STRICTLY after the
   confirmed arrival. At or before arrival the earlier readiness rules apply unchanged. Restore
   every expected label and test assertion for cases at or before arrival to what they were
   before the previous task (see git diff HEAD for the old values).
2. Scoring is too coarse. For arrival_passed cases, scoring must also compare the at-arrival
   outcome: expected.json gets `expected_target_at_arrival` (met / not_met / unknown) with a
   reason, readiness results carry `target_at_arrival`, and a case is correct only if both match.
   A source condition without indoor temperatures must yield unknown and therefore be scored
   unsupported, not correct.
Expected after the fix: demo_v1@18:00 at_risk; demo_recovery_v1@19:00 and @20:31 arrival_passed,
not_met; demo_video_v1@21:01 arrival_passed, met. Regenerate results-offline.json and the offline
part of docs/evaluation.md through the evaluation code path the tests exercise (no hand-editing of
the totals). Keep the live section, with its note that the live run used the earlier labels.
Final answer: the corrected rule, the new offline totals, REAL output lines.

