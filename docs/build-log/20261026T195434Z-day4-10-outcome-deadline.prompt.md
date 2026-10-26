ARIA Home, video build step 1 (approved by Brad): fix the target_reached deadline flaw. No live
calls, no installs, no network, no git, NO helper scripts. Your shell starts in C:\aria-home.
Do not end your turn until `cd backend && python -m pytest -q`, `cd frontend && npm run typecheck`
and `cd frontend && npm run test:e2e` all pass.

Read first: backend/aria_home/outcomes.py, backend/tests/test_outcomes.py, backend/tests/test_store.py,
docs/readiness-rules.md, docs/demo-script.md (section D "Risks"), frontend/src/App.tsx,
frontend/e2e/app.spec.ts.

FLAW: evaluate_outcome checks target_reached before the deadline, ignores the deadline, ignores
the reading source/kind and does not deduplicate. In demo_recovery_v1 the 68.2/68.4 F readings
(observed 20:15 and 20:30) are after the 18:00 arrival and the 20:00 deadline, yet 20:31 replay
reports "Target reached".

FIX (outcomes.py):
1. Only count indoor_temp records for the follow-up zone with a non-null value, received_at <= now,
   created_at < observed_at <= deadline, deduplicated by (source, observed_at).
2. Status order: target_reached (last two counted readings >= target), warming_observed,
   awaiting_measurement (now < deadline), not_observed_by_deadline, unable_to_verify. A reading
   after the deadline never contributes to success; when such readings exist, add the note
   "Readings after the deadline are not counted toward this follow-up."
3. Keep the human_statement causation note and the rule that a statement never sets a status.
4. Document the change in docs/readiness-rules.md (follow-up outcome section).
TESTS: demo_recovery_v1 at 20:31 is warming_observed (not target_reached) and carries the
after-deadline note; a synthetic case with two at-target readings before the deadline is
target_reached; duplicates do not count twice; a post-deadline at-target reading alone gives
not_observed_by_deadline or unable_to_verify per the sample count. Update existing assertions
only where this rule changes them, and say which in the final answer.
FRONTEND: rename the demo_recovery_v1 selector label to "Manager report, late warming"; update the
e2e so 20:31 shows "Warming observed" and the after-deadline note instead of "Target reached";
keep the history and no-follow-up assertions.
Final answer: the change, every test assertion changed and why, and the REAL output lines.

