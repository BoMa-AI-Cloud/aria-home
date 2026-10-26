# Day 4 handoff

## What Day 4 built

Commits below are short hashes where the timeline or the task record gives them;
otherwise the reference is the `docs/build-log` task that produced the work
(failed runs listed at the end).

- Scenario variants (build log day4-01a1): `demo_recovery_v1` and
  `demo_no_followup_v1` cloned from `demo_v1` past 18:00, with a calendar
  `manager_report` ("Reset the furnace switch" at 18:10). Checked by
  `backend/tests/test_scenario_variants.py`; 111 passed at the time.
- Outcome rules (day4-01a2): deterministic `evaluate_outcome` in
  `backend/aria_home/outcomes.py` over later `indoor_temp` readings only
  (`awaiting_measurement` / `warming_observed` / `target_reached` /
  `not_observed_by_deadline` / `unable_to_verify`); a human statement can only
  add the does-not-prove-cause note, never a status. Checked by
  `backend/tests/test_outcomes.py`; 120 passed at the time.
- Store and API (day4-01b): SQLite store in `backend/aria_home/store.py`
  (path from `ARIA_HOME_DB_PATH`, idempotent saves and same-`now`
  re-evaluation, survives restarts), `POST /api/investigations` (runs
  `investigate()`, saves investigation + follow-up) and
  `GET /api/follow-ups/<id>` (evaluates/stores the outcome from later
  measurements only). Checked by `backend/tests/test_store.py`; 124 passed.
- Outcome history (day4-01c): `outcome_events` table
  (`UNIQUE(investigation_id, evaluated_at)`), `GET /api/follow-ups/<id>`
  returns `history` in `evaluated_at` order. Covered in `test_store.py`;
  125 passed.
- Replay UI (day4-02): scenario selector
  (demo_v1 / demo_recovery_v1 / demo_no_followup_v1), replay-time buttons,
  outcome panel with history, source cards, synthetic banner, mock label.
  The run itself ended blocked on install/test approvals; the operator ran
  typecheck, build and e2e afterwards (see day4-10 and day4-13).
- Store thread-safety fix (day4-02b): the shared `sqlite3` connection
  (`check_same_thread=False`) broke under Flask dev-server threads, so each
  operation now opens a short-lived connection (`BEGIN IMMEDIATE` in
  `record_outcome`); `close()` is a no-op. Covered by the 8-thread
  `test_concurrent_saves_and_records_are_thread_safe`; 126 passed.
- Verification repair (day4-03 to day4-08, recorded in
  docs/day3-handoff.md): inv-v1 to inv-v2 claim binding (`facts[]` with a
  per-claim-type evidence field allowlist, code-rendered `verified_facts`),
  133 passed; readiness computed in code (`backend/aria_home/readiness.py`,
  documented in docs/readiness-rules.md), 141 passed; follow-up scheduling
  computed in code (`backend/aria_home/scheduling.py`), 156 passed; as-of
  visibility (`context_as_of`, documented in backend/scenarios/README.md,
  availability timestamps added to synthetic fixtures, synthetic variants
  `demo_revised_v1` and `demo_cancelled_v1`), 166 passed; frontend inv-v2
  contract (verified facts / readiness / interpretation split); day3-handoff
  and timeline updated.
- Demo video plan (day4-09 `docs/demo-script.md` plus a README link and a
  timeline line; day4-09b fixed the opening line and word counts, 380 words
  total).
- Outcome deadline fix (day4-10): `evaluate_outcome` now counts only
  non-null `indoor_temp` measurement readings for the follow-up zone with
  `received_at <= now` and `created_at < observed_at <= deadline`,
  deduplicated by `(source, observed_at)`; after-deadline readings add
  "Readings after the deadline are not counted toward this follow-up."
  (`demo_recovery_v1` at 20:31 is now `warming_observed`, not
  `target_reached`). Documented in docs/readiness-rules.md; 170 passed,
  typecheck passed, e2e 2 passed.
- Room sensor source and simulated events loader (day4-11a, commit a23ded5):
  `room_sensor` in `SourceKind`, `ScenarioEvent` with
  `events_as_of(scenario, now)` filtering on `available_at <= now`,
  `/api/sources` lists `room_sensor` only when the scenario has room-sensor
  records, `temperature_trend` prefers room-sensor readings with thermostat
  fallback. Checked by `backend/tests/test_room_sensor.py`; 174 passed.
- `demo_video_v1` partial fixture (commit a80c30a): manifest, calendar,
  weather, events.
- `demo_video_v1` sensor streams from a committed deterministic generator
  (day4-11c, commit b38c8b3):
  `backend/scenarios/demo_video_v1/generate_streams.py` generating
  `thermostat.json` (308 records, outage 15:30-18:20), `room_sensor.json`
  (187 records) and `electrical.json` (96 records). Checked by
  `backend/tests/test_demo_video_scenario.py`; 184 passed.
- Recovery verification stages (day4-12, commit f738fb8):
  `verify_recovery` in `backend/aria_home/verification.py`
  (`telemetry_missing` to `reporting_restored` to `warming_observed` to
  `goal_verified` to `arrival_met`, `unable_to_verify` when room readings go
  missing/stale; human statements and events never advance the stage, the
  `hvac_completion_report` is corroboration only), returned as
  `verification` from `GET /api/follow-ups/<id>`. For `demo_video_v1`:
  16:31 telemetry missing, 18:21 reporting restored, 18:51 warming observed,
  20:21 goal verified, 21:01 arrival met. 188 passed.
- Video scenario on screen, video build steps 4-5 (day4-13, commit 734605b):
  `GET /api/events`, the "Trip home, thermostat offline (video)" scenario in
  the selector with first POST at 16:31 and replay buttons through 21:01, a
  SIMULATED timeline panel (hidden events never fetched), the outcome
  headline in verification-stage wording with the follow-up rule secondary,
  and event/received/evaluation times next to the stage. Covered by the new
  video e2e test; operator checks below.

## Operator checks (at commit 734605b)

Backend 188 passed, typecheck and build passed, browser tests 3 passed.

## Live smoke (operator run, 2026-10-26)

3 inv-v2 calls on muse-spark-1.3 against demo_v1, all valid, readiness
at_risk, latencies 19.8 s, 30.9 s, 17.8 s; input tokens reported as 8479, 60,
60 (likely prompt caching the adapter does not record; unconfirmed).

## Known limits

- The older follow-up rule and the verification stage can disagree (the UI
  headlines the verification stage).
- Room-sensor and blower mappings are synthetic assumptions.
- No notifications yet.

## Failed runs

Four Muse runs ended without landing their task and are recorded as such in
the build log: day4-01, day4-01a, day4-11, day4-11b. Each was superseded by a
follow-up task (day4-01a1/day4-01a2, day4-11a/day4-11c).

## Next

- Scoped notifications to homeowner and property manager.
- Model comparison / evaluation (the full comparison is planned for Day 6).
- Filming the video against the demo-script acceptance checks.
