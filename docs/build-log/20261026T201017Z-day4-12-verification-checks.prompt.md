ARIA Home, video build step 3 (approved by Brad): recovery verification in code. DO THE WORK NOW
in this turn; do not stop after a plan. No helper scripts, no live calls, no installs, no
network, no git. Do not end your turn until `cd backend && python -m pytest -q` passes.

Read: backend/aria_home/outcomes.py, readiness.py, metrics.py, evidence.py, power_context.py,
scenario.py, app.py; docs/demo-script.md sections C and E; docs/readiness-rules.md;
backend/scenarios/demo_video_v1/*; backend/tests/test_demo_video_scenario.py.

BUILD backend/aria_home/verification.py, a pure function verify_recovery(scenario, followup, now)
-> {stage, reasons[], supporting_ids[], evaluated_at}, using ONLY records with received_at <= now
and events with available_at <= now. Stages, in order (each requires the previous):
1. telemetry_missing: no fresh thermostat telemetry (stale per evidence.py freshness).
2. reporting_restored: fresh thermostat telemetry after a gap. Never closes anything alone.
3. warming_observed: room_sensor (not thermostat) readings after the follow-up's created_at with
   at least FollowUp.min_samples and a rise >= min_rise_f, AND the reported thermostat state and
   the mapped circuit activity do not contradict heating. Electrical activity is supporting only.
4. goal_verified: every room_sensor reading for at least GOAL_HOLD_S = 1800 s is >= target, with
   no gap in readings longer than 2x cadence, all before the deadline.
5. arrival_met: goal_verified AND every room reading from verification through the confirmed
   arrival is >= target, evaluated at or after arrival.
If room-sensor readings are missing or stale at a stage that needs them, return unable_to_verify
(never a success stage). Human statements and events (manager acknowledgement, service_visit,
hvac_completion_report) never change the stage; if the report is visible it is listed as
corroboration only. Named module constants; document everything in docs/readiness-rules.md
("Recovery verification").
API: GET /api/follow-ups/<id> also returns "verification" for scenarios with room-sensor records.
TESTS on demo_video_v1 through the real API path (POST at 16:31, then GET): 16:31
telemetry_missing; 18:21 reporting_restored; 18:51 warming_observed; 19:51 not yet goal_verified;
20:21 goal_verified; report not visible before 20:45 and corroboration-only after; 21:01
arrival_met. Variants built in tmp_path: reconnection with flat room readings never passes
reporting_restored; room readings removed after 18:20 -> unable_to_verify; one dip below target
inside the hold window -> not goal_verified. Existing tests unchanged.
Final answer: the stages, constants and the REAL final pytest line.

