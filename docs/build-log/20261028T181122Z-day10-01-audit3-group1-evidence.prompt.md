ARIA Home, Audit 3 repair, GROUP 1: evidence and verification correctness (approved by Brad).
Backend only. DO THE WORK NOW in this turn. No live calls, no installs, no network beyond 127.0.0.1, no
git, NO helper scripts outside tests. Synthetic fixtures and fake providers only. Do not weaken any
existing assertion, relax evidence rules, or change expected labels to make tests pass. Smallest sound
changes; no new features. Shell starts in C:\aria-home. Do not end your turn until
`cd backend && python -m pytest -q` passes.

Read first: backend/aria_home/verification.py, evidence.py, eligibility.py, readiness.py, contracts.py,
outcomes.py, docs/readiness-rules.md, and the existing verification/readiness tests.

These defects were reproduced on the current code (scenario demo_video_v1, follow-up created at
2026-01-16T16:31:00-05:00, evaluated at 21:01:00-05:00):

1. CONFLICTING MEASUREMENTS CERTIFY SUCCESS. Append a room_sensor record copied from the latest visible
   one (same observed_at and received_at) with a different id and value 40.0 F. source_status says
   "conflicting", but verify_recovery returns "arrival_met" when the id starts "zz-" and
   "reporting_restored" when it starts "aa-". The result depends on id order (_room_records).
   Fix: one explicit shared conflict policy used by readiness AND verification. Never resolve a
   contradiction by id or insertion order. Collapse genuinely identical duplicates (same sensor/zone,
   same time, same value after unit normalization) keeping provenance. Readings from unrelated
   sensors/zones are not conflicts. An unresolved conflict inside the required hold or arrival
   interval yields the existing conservative stage (unable_to_verify or equivalent), never
   goal_verified/arrival_met.
   Tests: both id orderings, reversed insertion order, a conflict inside the hold interval (not only
   at its endpoint), identical duplicates, equivalent-unit duplicates (F vs C), a conflict outside the
   relevant zone/window, and readiness/verification agreeing on the same conflicted input.

2. NON-FINITE NUMERICS ACCEPTED. Rebuilding room_sensor records after 18:20 with value=float('inf')
   through EvidenceRecord.model_validate is accepted, and verification returns "arrival_met".
   Fix: reject NaN/+inf/-inf at the typed numeric contract boundary and add finite checks in shared
   eligibility and after unit conversion. Invalid samples never satisfy target, rise, hold or arrival
   rules. Keep string-valued evidence (HVAC state) valid. No new physical thresholds unless documented.
   Tests: NaN, +inf, -inf, overflow on conversion, invalid unit, ordinary valid temperatures and power,
   invalid samples cannot yield goal_verified/arrival_met, and the API returns a conservative result
   or a 4xx for such input, never a 500.

3. TEMPERATURE SUCCESS TIED TO EQUIPMENT STATE. At 21:01, changing only the latest
   hvac_reported_state to "idle" turns arrival_met into reporting_restored. Setting every room_sensor
   value to 68.0 (already at target throughout) also yields reporting_restored because no warming rise
   occurred. The latest HVAC state is read with no freshness check.
   Fix: treat as separate claims: thermostat telemetry restored; heating activity observed; warming
   observed; temperature goal held for the required interval; temperature expectation met at arrival;
   (never) repair caused recovery. Normal idle/off cycling at target and quiet heating circuits must not
   block a temperature success that the measurements support. An already-warm home does not need a
   rise to meet the arrival expectation. Scope equipment observations to the relevant zone/binding and
   enforce freshness. Keep the coverage, hold-duration, relapse and arrival-time requirements. Human
   acknowledgement, technician attendance and completion reports never create sensor verification.
   Tests: idle/off at target, quiet circuit at target, stale HVAC state, already-at-target property,
   active fan without useful warming, temperature relapse, missing observations near arrival, a human
   completion report without sufficient measurements, and independent temperature verification before
   the human completion report. The shipped demo_video_v1 sequence must still read: 18:21 reporting
   restored, 18:51 warming observed, 19:51 not yet verified, 20:21 temperature goal verified, 21:01
   arrival expectation met.

If a policy change alters a version string, bump it (for example the readiness/verification policy
version) and update docs/readiness-rules.md to describe the new rule exactly.
Final answer: per finding, root cause, files changed, tests added, and the REAL pytest output line.

