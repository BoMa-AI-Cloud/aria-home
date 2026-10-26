Model: muse-wonder-1.0
Turns: 38

Stages: `telemetry_missing` → `reporting_restored` → `warming_observed` → `goal_verified` → `arrival_met`; `unable_to_verify` when room readings are missing/stale after reporting is restored. Human/event records never advance the stage; `hvac_completion_report` appears only in `corroboration_ids` after 20:45.

Constants: `GOAL_HOLD_S=1800`, `MAX_GAP_CADENCE_MULTIPLIER=2`, `REPORT_EVENT_KIND="hvac_completion_report"`, `CORROBORATION_EVENT_KINDS=(REPORT_EVENT_KIND,)`, `NON_CORROBORATING_EVENT_KINDS`, `HEATING/NON_HEATING_REPORTED_STATES`, `MAPPED_HEATING_EQUIPMENT`, plus reused `FollowUp.min_samples=3`, `FollowUp.min_rise_f=2.0`, `NOISE_FLOOR_W=15.0`.

Real final pytest line: `188 passed in 4.12s`
