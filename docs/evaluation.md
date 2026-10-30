# Evaluation (offline, deterministic)

Synthetic scenarios, expected labels written by the builder, small sample, not a benchmark of real homes.

The 22 cases pair each scenario with fixed replay times. Expected readiness (and, for `demo_video_v1` and `care_home_v1` only, the expected verification stage) is hand-written in `backend/eval/expected.json` from the fixture data, with a one-line reason per case. For `arrival_passed` cases (now strictly after the confirmed arrival), `expected_target_at_arrival` (`met` / `not_met`) is also scored: a case is correct only if both the readiness status and the at-arrival outcome (`target_at_arrival` on the readiness result) match, so a source condition without indoor temperatures yields `unknown` and is scored unsupported, not correct. Each case is run under the combined (all-sources) condition and under source-limited conditions that keep only one source kind of evidence record; trip/confirmation context (the arrival and target being asked about) is retained. `useful_heat` is supportable in no condition: circuit watts alone never prove useful heat. The `visual_*` cases add synthetic SAM 3.1 segmentation evidence (recorded responses over synthetic images, including the recorded frost-pipe false negative); visual evidence never yields `on_track`, `warming_observed`, `goal_verified` or `arrival_met`, and zero detected objects is reported as no detection, never as an all-clear.

The model investigation contract is `inv-v3`: after the confirmed arrival has passed, the model states the temperature at arrival (`temperature_at_arrival`, the last eligible reading observed and received by arrival) and must not state a `current_temperature`. The live runs on snapshots 53a06bd, 114be6a and 77cafc9 below used the `inv-v2` contract, which asked for a current temperature even after arrival; the after-arrival rerun on snapshot efdff57 used `inv-v3`.

## Totals

| Condition | Cases | Readiness correct | Wrong | Unsupported | Target at arrival correct (scored) | Verification correct (scored) | Fully correct |
|---|---|---|---|---|---|---|---|
| combined | 22 | 22 | 0 | 0 | 7 (7) | 10 (10) | 22 |
| thermostat_only | 22 | 16 | 0 | 10 | 7 (7) | 2 (10) | 12 |
| room_sensor_only | 22 | 17 | 0 | 18 | 2 (7) | 2 (10) | 4 |
| electrical_only | 22 | 9 | 0 | 20 | 0 (7) | 2 (10) | 2 |
| calendar_only | 22 | 9 | 0 | 20 | 0 (7) | 2 (10) | 2 |

## Cases

| Case | Condition | Expected | Got | Correct? |
|---|---|---|---|---|
| demo_v1@18:00 | combined | at_risk | at_risk / unable_to_verify | yes |
| demo_v1@18:00 | thermostat_only | at_risk | at_risk / unable_to_verify | yes |
| demo_v1@18:00 | room_sensor_only | at_risk | cannot_tell / telemetry_missing | no (unsupported) |
| demo_v1@18:00 | electrical_only | at_risk | cannot_tell / telemetry_missing | no (unsupported) |
| demo_v1@18:00 | calendar_only | at_risk | cannot_tell / telemetry_missing | no (unsupported) |
| demo_recovery_v1@18:00 | combined | at_risk | at_risk / unable_to_verify | yes |
| demo_recovery_v1@18:00 | thermostat_only | at_risk | at_risk / unable_to_verify | yes |
| demo_recovery_v1@18:00 | room_sensor_only | at_risk | cannot_tell / telemetry_missing | no (unsupported) |
| demo_recovery_v1@18:00 | electrical_only | at_risk | cannot_tell / telemetry_missing | no (unsupported) |
| demo_recovery_v1@18:00 | calendar_only | at_risk | cannot_tell / telemetry_missing | no (unsupported) |
| demo_recovery_v1@19:00 | combined | arrival_passed (target at arrival: not_met) | arrival_passed / unable_to_verify (target at arrival: not_met) | yes |
| demo_recovery_v1@19:00 | thermostat_only | arrival_passed (target at arrival: not_met) | arrival_passed / unable_to_verify (target at arrival: not_met) | yes |
| demo_recovery_v1@19:00 | room_sensor_only | arrival_passed (target at arrival: not_met) | arrival_passed / telemetry_missing (target at arrival: unknown) | no (unsupported) |
| demo_recovery_v1@19:00 | electrical_only | arrival_passed (target at arrival: not_met) | arrival_passed / telemetry_missing (target at arrival: unknown) | no (unsupported) |
| demo_recovery_v1@19:00 | calendar_only | arrival_passed (target at arrival: not_met) | arrival_passed / telemetry_missing (target at arrival: unknown) | no (unsupported) |
| demo_recovery_v1@20:31 | combined | arrival_passed (target at arrival: not_met) | arrival_passed / unable_to_verify (target at arrival: not_met) | yes |
| demo_recovery_v1@20:31 | thermostat_only | arrival_passed (target at arrival: not_met) | arrival_passed / unable_to_verify (target at arrival: not_met) | yes |
| demo_recovery_v1@20:31 | room_sensor_only | arrival_passed (target at arrival: not_met) | arrival_passed / telemetry_missing (target at arrival: unknown) | no (unsupported) |
| demo_recovery_v1@20:31 | electrical_only | arrival_passed (target at arrival: not_met) | arrival_passed / telemetry_missing (target at arrival: unknown) | no (unsupported) |
| demo_recovery_v1@20:31 | calendar_only | arrival_passed (target at arrival: not_met) | arrival_passed / telemetry_missing (target at arrival: unknown) | no (unsupported) |
| demo_no_followup_v1@20:31 | combined | arrival_passed (target at arrival: not_met) | arrival_passed / telemetry_missing (target at arrival: not_met) | yes |
| demo_no_followup_v1@20:31 | thermostat_only | arrival_passed (target at arrival: not_met) | arrival_passed / telemetry_missing (target at arrival: not_met) | yes |
| demo_no_followup_v1@20:31 | room_sensor_only | arrival_passed (target at arrival: not_met) | arrival_passed / telemetry_missing (target at arrival: unknown) | no (unsupported) |
| demo_no_followup_v1@20:31 | electrical_only | arrival_passed (target at arrival: not_met) | arrival_passed / telemetry_missing (target at arrival: unknown) | no (unsupported) |
| demo_no_followup_v1@20:31 | calendar_only | arrival_passed (target at arrival: not_met) | arrival_passed / telemetry_missing (target at arrival: unknown) | no (unsupported) |
| demo_revised_v1@18:00 | combined | cannot_tell | cannot_tell | yes |
| demo_revised_v1@18:00 | thermostat_only | cannot_tell | cannot_tell | yes |
| demo_revised_v1@18:00 | room_sensor_only | cannot_tell | cannot_tell | yes |
| demo_revised_v1@18:00 | electrical_only | cannot_tell | cannot_tell | yes |
| demo_revised_v1@18:00 | calendar_only | cannot_tell | cannot_tell | yes |
| demo_cancelled_v1@18:00 | combined | cannot_tell | cannot_tell | yes |
| demo_cancelled_v1@18:00 | thermostat_only | cannot_tell | cannot_tell | yes |
| demo_cancelled_v1@18:00 | room_sensor_only | cannot_tell | cannot_tell | yes |
| demo_cancelled_v1@18:00 | electrical_only | cannot_tell | cannot_tell | yes |
| demo_cancelled_v1@18:00 | calendar_only | cannot_tell | cannot_tell | yes |
| demo_video_v1@16:31 | combined | at_risk / telemetry_missing | at_risk / telemetry_missing | yes |
| demo_video_v1@16:31 | thermostat_only | at_risk / telemetry_missing | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@16:31 | room_sensor_only | at_risk / telemetry_missing | at_risk / telemetry_missing | yes |
| demo_video_v1@16:31 | electrical_only | at_risk / telemetry_missing | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@16:31 | calendar_only | at_risk / telemetry_missing | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@18:21 | combined | at_risk / reporting_restored | at_risk / reporting_restored | yes |
| demo_video_v1@18:21 | thermostat_only | at_risk / reporting_restored | cannot_tell / unable_to_verify | no (unsupported) |
| demo_video_v1@18:21 | room_sensor_only | at_risk / reporting_restored | at_risk / telemetry_missing | no (unsupported) |
| demo_video_v1@18:21 | electrical_only | at_risk / reporting_restored | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@18:21 | calendar_only | at_risk / reporting_restored | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@18:51 | combined | at_risk / warming_observed | at_risk / warming_observed | yes |
| demo_video_v1@18:51 | thermostat_only | at_risk / warming_observed | cannot_tell / unable_to_verify | no (unsupported) |
| demo_video_v1@18:51 | room_sensor_only | at_risk / warming_observed | at_risk / telemetry_missing | no (unsupported) |
| demo_video_v1@18:51 | electrical_only | at_risk / warming_observed | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@18:51 | calendar_only | at_risk / warming_observed | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@20:21 | combined | on_track / goal_verified | on_track / goal_verified | yes |
| demo_video_v1@20:21 | thermostat_only | on_track / goal_verified | on_track / unable_to_verify | no (unsupported) |
| demo_video_v1@20:21 | room_sensor_only | on_track / goal_verified | on_track / telemetry_missing | no (unsupported) |
| demo_video_v1@20:21 | electrical_only | on_track / goal_verified | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@20:21 | calendar_only | on_track / goal_verified | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@21:01 | combined | arrival_passed / arrival_met (target at arrival: met) | arrival_passed / arrival_met (target at arrival: met) | yes |
| demo_video_v1@21:01 | thermostat_only | arrival_passed / arrival_met (target at arrival: met) | arrival_passed / unable_to_verify (target at arrival: met) | no (unsupported) |
| demo_video_v1@21:01 | room_sensor_only | arrival_passed / arrival_met (target at arrival: met) | arrival_passed / telemetry_missing (target at arrival: met) | no (unsupported) |
| demo_video_v1@21:01 | electrical_only | arrival_passed / arrival_met (target at arrival: met) | arrival_passed / telemetry_missing (target at arrival: unknown) | no (unsupported) |
| demo_video_v1@21:01 | calendar_only | arrival_passed / arrival_met (target at arrival: met) | arrival_passed / telemetry_missing (target at arrival: unknown) | no (unsupported) |
| care_home_v1@02:31 | combined | at_risk / telemetry_missing | at_risk / telemetry_missing | yes |
| care_home_v1@02:31 | thermostat_only | at_risk / telemetry_missing | cannot_tell / telemetry_missing | no (unsupported) |
| care_home_v1@02:31 | room_sensor_only | at_risk / telemetry_missing | at_risk / telemetry_missing | yes |
| care_home_v1@02:31 | electrical_only | at_risk / telemetry_missing | cannot_tell / telemetry_missing | no (unsupported) |
| care_home_v1@02:31 | calendar_only | at_risk / telemetry_missing | cannot_tell / telemetry_missing | no (unsupported) |
| care_home_v1@04:21 | combined | at_risk / reporting_restored | at_risk / reporting_restored | yes |
| care_home_v1@04:21 | thermostat_only | at_risk / reporting_restored | cannot_tell / unable_to_verify | no (unsupported) |
| care_home_v1@04:21 | room_sensor_only | at_risk / reporting_restored | at_risk / telemetry_missing | no (unsupported) |
| care_home_v1@04:21 | electrical_only | at_risk / reporting_restored | cannot_tell / telemetry_missing | no (unsupported) |
| care_home_v1@04:21 | calendar_only | at_risk / reporting_restored | cannot_tell / telemetry_missing | no (unsupported) |
| care_home_v1@04:51 | combined | at_risk / warming_observed | at_risk / warming_observed | yes |
| care_home_v1@04:51 | thermostat_only | at_risk / warming_observed | cannot_tell / unable_to_verify | no (unsupported) |
| care_home_v1@04:51 | room_sensor_only | at_risk / warming_observed | at_risk / telemetry_missing | no (unsupported) |
| care_home_v1@04:51 | electrical_only | at_risk / warming_observed | cannot_tell / telemetry_missing | no (unsupported) |
| care_home_v1@04:51 | calendar_only | at_risk / warming_observed | cannot_tell / telemetry_missing | no (unsupported) |
| care_home_v1@06:21 | combined | on_track / goal_verified | on_track / goal_verified | yes |
| care_home_v1@06:21 | thermostat_only | on_track / goal_verified | on_track / unable_to_verify | no (unsupported) |
| care_home_v1@06:21 | room_sensor_only | on_track / goal_verified | on_track / telemetry_missing | no (unsupported) |
| care_home_v1@06:21 | electrical_only | on_track / goal_verified | cannot_tell / telemetry_missing | no (unsupported) |
| care_home_v1@06:21 | calendar_only | on_track / goal_verified | cannot_tell / telemetry_missing | no (unsupported) |
| care_home_v1@07:01 | combined | arrival_passed / arrival_met (target at arrival: met) | arrival_passed / arrival_met (target at arrival: met) | yes |
| care_home_v1@07:01 | thermostat_only | arrival_passed / arrival_met (target at arrival: met) | arrival_passed / unable_to_verify (target at arrival: met) | no (unsupported) |
| care_home_v1@07:01 | room_sensor_only | arrival_passed / arrival_met (target at arrival: met) | arrival_passed / telemetry_missing (target at arrival: met) | no (unsupported) |
| care_home_v1@07:01 | electrical_only | arrival_passed / arrival_met (target at arrival: met) | arrival_passed / telemetry_missing (target at arrival: unknown) | no (unsupported) |
| care_home_v1@07:01 | calendar_only | arrival_passed / arrival_met (target at arrival: met) | arrival_passed / telemetry_missing (target at arrival: unknown) | no (unsupported) |
| visual_water_low_temp_v1@18:00 | combined | at_risk | at_risk | yes |
| visual_water_low_temp_v1@18:00 | thermostat_only | at_risk | at_risk | yes |
| visual_water_low_temp_v1@18:00 | room_sensor_only | at_risk | cannot_tell | no (unsupported) |
| visual_water_low_temp_v1@18:00 | electrical_only | at_risk | cannot_tell | no (unsupported) |
| visual_water_low_temp_v1@18:00 | calendar_only | at_risk | cannot_tell | no (unsupported) |
| visual_frost_missed_v1@18:00 | combined | at_risk | at_risk | yes |
| visual_frost_missed_v1@18:00 | thermostat_only | at_risk | at_risk | yes |
| visual_frost_missed_v1@18:00 | room_sensor_only | at_risk | cannot_tell | no (unsupported) |
| visual_frost_missed_v1@18:00 | electrical_only | at_risk | cannot_tell | no (unsupported) |
| visual_frost_missed_v1@18:00 | calendar_only | at_risk | cannot_tell | no (unsupported) |
| visual_dry_floor_v1@18:00 | combined | at_risk | at_risk | yes |
| visual_dry_floor_v1@18:00 | thermostat_only | at_risk | at_risk | yes |
| visual_dry_floor_v1@18:00 | room_sensor_only | at_risk | cannot_tell | no (unsupported) |
| visual_dry_floor_v1@18:00 | electrical_only | at_risk | cannot_tell | no (unsupported) |
| visual_dry_floor_v1@18:00 | calendar_only | at_risk | cannot_tell | no (unsupported) |
| visual_water_low_temp_v1@19:00 | combined | arrival_passed (target at arrival: not_met) | arrival_passed (target at arrival: not_met) | yes |
| visual_water_low_temp_v1@19:00 | thermostat_only | arrival_passed (target at arrival: not_met) | arrival_passed (target at arrival: not_met) | yes |
| visual_water_low_temp_v1@19:00 | room_sensor_only | arrival_passed (target at arrival: not_met) | arrival_passed (target at arrival: unknown) | no (unsupported) |
| visual_water_low_temp_v1@19:00 | electrical_only | arrival_passed (target at arrival: not_met) | arrival_passed (target at arrival: unknown) | no (unsupported) |
| visual_water_low_temp_v1@19:00 | calendar_only | arrival_passed (target at arrival: not_met) | arrival_passed (target at arrival: unknown) | no (unsupported) |
| visual_frost_missed_v1@20:31 | combined | arrival_passed (target at arrival: not_met) | arrival_passed (target at arrival: not_met) | yes |
| visual_frost_missed_v1@20:31 | thermostat_only | arrival_passed (target at arrival: not_met) | arrival_passed (target at arrival: not_met) | yes |
| visual_frost_missed_v1@20:31 | room_sensor_only | arrival_passed (target at arrival: not_met) | arrival_passed (target at arrival: unknown) | no (unsupported) |
| visual_frost_missed_v1@20:31 | electrical_only | arrival_passed (target at arrival: not_met) | arrival_passed (target at arrival: unknown) | no (unsupported) |
| visual_frost_missed_v1@20:31 | calendar_only | arrival_passed (target at arrival: not_met) | arrival_passed (target at arrival: unknown) | no (unsupported) |

## Where a single source falls short

- room_sensor_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- room_sensor_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- room_sensor_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/None.
- electrical_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/None.
- calendar_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/None.
- room_sensor_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/None.
- electrical_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/None.
- calendar_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/None.
- room_sensor_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/None.
- electrical_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/None.
- calendar_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/None.
- room_sensor_only cannot support the current_temperature claim that combined supports at demo_revised_v1@18:00.
- electrical_only cannot support the current_temperature claim that combined supports at demo_revised_v1@18:00.
- calendar_only cannot support the current_temperature claim that combined supports at demo_revised_v1@18:00.
- room_sensor_only cannot support the current_temperature claim that combined supports at demo_cancelled_v1@18:00.
- electrical_only cannot support the current_temperature claim that combined supports at demo_cancelled_v1@18:00.
- calendar_only cannot support the current_temperature claim that combined supports at demo_cancelled_v1@18:00.
- thermostat_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/telemetry_missing.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/telemetry_missing.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/telemetry_missing.
- thermostat_only gives unsupported answer (cannot_tell/unable_to_verify) where combined gives the expected at_risk/reporting_restored.
- room_sensor_only gives unsupported answer (at_risk/telemetry_missing) where combined gives the expected at_risk/reporting_restored.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/reporting_restored.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/reporting_restored.
- thermostat_only gives unsupported answer (cannot_tell/unable_to_verify) where combined gives the expected at_risk/warming_observed.
- room_sensor_only gives unsupported answer (at_risk/telemetry_missing) where combined gives the expected at_risk/warming_observed.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/warming_observed.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/warming_observed.
- thermostat_only gives unsupported answer (on_track/unable_to_verify) where combined gives the expected on_track/goal_verified.
- room_sensor_only gives unsupported answer (on_track/telemetry_missing) where combined gives the expected on_track/goal_verified.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected on_track/goal_verified.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected on_track/goal_verified.
- thermostat_only gives unsupported answer (arrival_passed/unable_to_verify) where combined gives the expected arrival_passed/arrival_met.
- room_sensor_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/arrival_met.
- electrical_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/arrival_met.
- calendar_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/arrival_met.
- thermostat_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/telemetry_missing.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/telemetry_missing.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/telemetry_missing.
- thermostat_only gives unsupported answer (cannot_tell/unable_to_verify) where combined gives the expected at_risk/reporting_restored.
- room_sensor_only gives unsupported answer (at_risk/telemetry_missing) where combined gives the expected at_risk/reporting_restored.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/reporting_restored.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/reporting_restored.
- thermostat_only gives unsupported answer (cannot_tell/unable_to_verify) where combined gives the expected at_risk/warming_observed.
- room_sensor_only gives unsupported answer (at_risk/telemetry_missing) where combined gives the expected at_risk/warming_observed.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/warming_observed.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/warming_observed.
- thermostat_only gives unsupported answer (on_track/unable_to_verify) where combined gives the expected on_track/goal_verified.
- room_sensor_only gives unsupported answer (on_track/telemetry_missing) where combined gives the expected on_track/goal_verified.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected on_track/goal_verified.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected on_track/goal_verified.
- thermostat_only gives unsupported answer (arrival_passed/unable_to_verify) where combined gives the expected arrival_passed/arrival_met.
- room_sensor_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/arrival_met.
- electrical_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/arrival_met.
- calendar_only gives unsupported answer (arrival_passed/telemetry_missing) where combined gives the expected arrival_passed/arrival_met.
- room_sensor_only gives unsupported answer (cannot_tell/None) where combined gives the expected at_risk/None.
- electrical_only gives unsupported answer (cannot_tell/None) where combined gives the expected at_risk/None.
- calendar_only gives unsupported answer (cannot_tell/None) where combined gives the expected at_risk/None.
- room_sensor_only gives unsupported answer (cannot_tell/None) where combined gives the expected at_risk/None.
- electrical_only gives unsupported answer (cannot_tell/None) where combined gives the expected at_risk/None.
- calendar_only gives unsupported answer (cannot_tell/None) where combined gives the expected at_risk/None.
- room_sensor_only gives unsupported answer (cannot_tell/None) where combined gives the expected at_risk/None.
- electrical_only gives unsupported answer (cannot_tell/None) where combined gives the expected at_risk/None.
- calendar_only gives unsupported answer (cannot_tell/None) where combined gives the expected at_risk/None.
- room_sensor_only gives unsupported answer (arrival_passed/None) where combined gives the expected arrival_passed/None.
- electrical_only gives unsupported answer (arrival_passed/None) where combined gives the expected arrival_passed/None.
- calendar_only gives unsupported answer (arrival_passed/None) where combined gives the expected arrival_passed/None.
- room_sensor_only gives unsupported answer (arrival_passed/None) where combined gives the expected arrival_passed/None.
- electrical_only gives unsupported answer (arrival_passed/None) where combined gives the expected arrival_passed/None.
- calendar_only gives unsupported answer (arrival_passed/None) where combined gives the expected arrival_passed/None.
- electrical_only at demo_video_v1@16:31 can support an electrical-activity claim (blower circuit watts) but watts alone never support a useful-heat claim; the combined view uses the flat room readings to show no warming.
- electrical_only at care_home_v1@02:31 can support an electrical-activity claim (blower circuit watts) but watts alone never support a useful-heat claim; the combined view uses the flat room readings to show no warming.

## Care camera fixtures (recorded replay)

The six synthetic home-camera frames attached to `care_home_v1` (`backend/fixtures/visual/care/`, generated by muse-image-1.0; each `*.sam.txt` is the recorded raw sam-3.1 response for that image and phrase, replayed here and by tests, never a live call). Night frames attach during the cooling, the morning frames after recovery; at any replay time the visible frame is the latest one with `received_at <= now`. Zero objects is no detection, never an all-clear: the two recorded frost misses stay `at_risk` and are shown as "missed by the model" in the evidence drawer.

| Image | Phrase | sam-3.1 objects | Correct? |
|---|---|---|---|
| care-v1-window-frost | frost | 0 | missed (frost on every pane) |
| care-v2-furnace-off | indicator light | 0 | unclear (small indicator) |
| care-v3-thermostat-blank | blank display | 1 | yes |
| care-v4-pipe-frost | frost | 0 | missed |
| care-v5-dry-floor | water puddle | 0 | yes (negative control) |
| care-v6-warm-morning | frost | 0 | yes (no frost present) |

## Watcher correction rates (recorded runs only)

No watcher runs have been recorded yet, so both rates are placeholders: first-pass rejection rate n/a (0 runs), after-correction pass rate n/a (0 runs).
Once the operator records an approved batch through `aria_home.watcher`, this section reports the first-pass rejection rate and the after-correction pass rate as separate measures, computed from `backend/eval/corrections-*.json`.

## Reading this

- Combined matches every expected readiness label and every scored verification stage; the single-source conditions do not, mostly by falling back to `cannot_tell` / `telemetry_missing` / `unable_to_verify` (unsupported), not by asserting the opposite readiness.
- Thermostat-only during the `demo_video_v1` outage (16:31) or the `care_home_v1` outage (02:31) cannot support a warming or even a current-temperature claim: the last thermostat reading is hours old, stale by evaluation time. The combined view still has fresh independent room readings showing no warming.
- Electrical-only can show circuit activity (for example the blower circuit during the outage) but can never support a useful-heat claim; only temperature evidence can show warming.
- A model condition exists in `aria_home.evaluation.run_model_cases` (status, readiness agreement, rejected-claim reasons, latency, tokens per case). Offline tests run it with the mock provider. A live run requires `--live`, `--max-calls N`, and `ARIA_HOME_MODEL_ENABLED=1` together; there are no retries, and timeout/max-tokens come from the existing provider/investigator config.

## Live model condition (2026-10-26)

Note: the live runs below predate the care story and used the trip-home scenarios (`demo_v1`, `demo_video_v1` and related fixtures); they are kept verbatim as historical runs and are not re-scored against `care_home_v1`.

Note: the live run used the earlier labels (before the strictly-after-arrival correction and target-at-arrival scoring), so its computed-readiness column reflects those earlier labels.

Run by the operator: 24 calls (the 12 cases on muse-spark-1.3, then on muse-wonder-1.0), committed snapshot 53a06bd, 90 s timeout, 12000 output tokens, no retries, approved by Brad. Source: `backend/eval/results-live.json`.

| Model | Valid answers | Readiness agreement | Rejected answers | Median latency (s) | Min-max latency (s) | Median output tokens |
|---|---|---|---|---|---|---|
| muse-spark-1.3 | 12/12 | 12/12 | 0 | 40.9 | 20.7-53.0 | 6490 |
| muse-wonder-1.0 | 12/12 | 12/12 | 0 | 37.3 | 19.1-41.0 | 5584 |

| Case | Computed readiness | muse-spark-1.3 | muse-wonder-1.0 |
|---|---|---|---|
| demo_v1@18:00 | at_risk | at_risk | at_risk |
| demo_recovery_v1@18:00 | at_risk | at_risk | at_risk |
| demo_recovery_v1@19:00 | at_risk | at_risk | at_risk |
| demo_recovery_v1@20:31 | on_track | on_track | on_track |
| demo_no_followup_v1@20:31 | cannot_tell | cannot_tell | cannot_tell |
| demo_revised_v1@18:00 | cannot_tell | cannot_tell | cannot_tell |
| demo_cancelled_v1@18:00 | cannot_tell | cannot_tell | cannot_tell |
| demo_video_v1@16:31 | cannot_tell | cannot_tell | cannot_tell |
| demo_video_v1@18:21 | at_risk | at_risk | at_risk |
| demo_video_v1@18:51 | at_risk | at_risk | at_risk |
| demo_video_v1@20:21 | on_track | on_track | on_track |
| demo_video_v1@21:01 | on_track | on_track | on_track |

Readiness agreement is enforced (the prompt tells the model the computed status and the validator rejects a mismatch), so 24/24 agreement shows the models followed the contract, not that they judged readiness independently. The meaningful result is that 0 of 24 answers were rejected by the claim checks. One run per case, synthetic data, small sample; input-token counts are unreliable (likely prompt caching the adapter does not record). No winner is declared on quality; wonder was faster in this sample.

## Live comparison on the current code (2026-10-27)

Run by the operator, approved by Brad; 12 eval cases per run; committed snapshot 114be6a (after the Audit 2 repairs); 90 s timeout; no retries. Source: `backend/eval/results-live-current.json`.

| Model | Valid | Rejected | No answer | Median latency (s) | Median output tokens |
|---|---|---|---|---|---|
| muse-spark-1.3 via the Meta Model API, 12000 output tokens | 8 | 4 | 0 | 35.9 | 6695 |
| meta-models/muse-spark-open-1026 (Meta open-weight Muse Spark Open, hackathon deployment) via Baseten, 12000 tokens | 1 | 10 | 1 (all tokens spent reasoning) | 21.6 | 6086 |
| Same model, 2000 tokens | 0 | 0 | 12 (reasoning used the whole budget) | 8.1 | 2000 |

Rejection reasons: Muse Spark Open's were mostly prose numbers not present in the cited facts (185 occurrences across the 10 rejected answers), stale or superseded readings stated as current, and the word "confirmed" twice; muse-spark-1.3's four rejections were all after-arrival cases citing a stale or superseded reading as the current temperature.

Honest reading, plainly: every valid answer agreed with the computed readiness (enforced by the contract). The earlier 24/24 results used the pre-repair checks and are not comparable. In after-arrival cases every reading is old by design while the contract still asks for a current temperature, so part of those rejections is a contract gap, not only a model error. Some number-check rejections may come from clock times (for example "09"); not investigated. One run per case, synthetic data, small sample. Conclusion: muse-spark-1.3 stays the runtime model.

## Live evaluation on snapshot 77cafc9 (2026-10-28)

Run by the operator, approved by Brad: exactly 17 calls (the 17 eval cases) on muse-spark-1.3 via the Meta Model API against snapshot 77cafc9 (after Audit 3 and the visual source), 90 s timeout, 12000 output tokens, no retries. Source: `backend/eval/results-live-77cafc9.json`.

| Model | Valid | Rejected | Readiness agreement | Median latency (s) | Median output tokens |
|---|---|---|---|---|---|
| muse-spark-1.3 via the Meta Model API | 11/17 | 6 | 11/11 | 24.5 | 6321 |

| Case | Computed readiness | Result |
|---|---|---|
| demo_v1@18:00 | at_risk | valid, agreed |
| demo_recovery_v1@18:00 | at_risk | valid, agreed |
| demo_recovery_v1@19:00 | arrival_passed | rejected: stale temperature and electrical readings cited as current |
| demo_recovery_v1@20:31 | arrival_passed | rejected: stale temperature and electrical readings cited as current |
| demo_no_followup_v1@20:31 | arrival_passed | rejected: old electrical activity cited as current |
| demo_revised_v1@18:00 | cannot_tell | valid, agreed |
| demo_cancelled_v1@18:00 | cannot_tell | valid, agreed |
| demo_video_v1@16:31 | at_risk | valid, agreed |
| demo_video_v1@18:21 | at_risk | valid, agreed |
| demo_video_v1@18:51 | at_risk | valid, agreed |
| demo_video_v1@20:21 | on_track | valid, agreed |
| demo_video_v1@21:01 | arrival_passed | rejected: superseded room reading cited as current |
| visual_water_low_temp_v1@18:00 | at_risk | valid, agreed |
| visual_frost_missed_v1@18:00 | at_risk | valid, agreed |
| visual_dry_floor_v1@18:00 | at_risk | valid, agreed |
| visual_water_low_temp_v1@19:00 | arrival_passed | rejected: stale temperature and electrical readings cited as current, plus a number not in the cited facts |
| visual_frost_missed_v1@20:31 | arrival_passed | rejected: stale temperature and electrical readings cited as current, plus numbers not in the cited facts |

Honest reading, plainly: readiness agreement is enforced by the contract (the model is told the computed status and a mismatch is rejected), so 11/11 agreement shows the model followed the contract, not that it judged readiness independently. The rejections show the claim checks working: each rejected answer cited a stale or superseded reading (or old electrical activity) as current. After arrival every reading is old by design while the `inv-v2` contract used in this run still asks for a current temperature, so these rejections are at least partly a contract gap, not only a model error (same pattern as the 2026-10-27 run). That gap is fixed by the `inv-v3` contract (temperature at arrival instead of a current temperature after arrival); the six after-arrival cases were repeated under `inv-v3` in the rerun below, which is not a full re-run of all 17 cases. One run per case, synthetic data, small sample. This is not a pass or fail of the product.

## Live after-arrival rerun on snapshot efdff57 (inv-v3)

Run by the operator, approved by Brad: exactly 6 calls (only the six after-arrival cases) on muse-spark-1.3 via the Meta Model API against snapshot efdff57 (the `inv-v3` contract change: after arrival, ask for the temperature at arrival instead of a current temperature), 90 s timeout, 12000 output tokens, no retries. Source: `backend/eval/results-live-arrival-efdff57.json`.

| Model | Valid | Rejected | Readiness agreement |
|---|---|---|---|
| muse-spark-1.3 via the Meta Model API | 5/6 | 1 | 5/5 |

| Case | Computed readiness | Result |
|---|---|---|
| demo_recovery_v1@19:00 | arrival_passed | valid, agreed |
| demo_recovery_v1@20:31 | arrival_passed | valid, agreed |
| demo_no_followup_v1@20:31 | arrival_passed | rejected: answer said "below target", contradicting the resolved target_gap fact |
| demo_video_v1@21:01 | arrival_passed | valid, agreed |
| visual_water_low_temp_v1@19:00 | arrival_passed | valid, agreed |
| visual_frost_missed_v1@20:31 | arrival_passed | valid, agreed |

Honest reading, plainly: what changed is the contract, `inv-v2` to `inv-v3` — after arrival the model states the temperature at arrival instead of a current temperature, so the stale-reading-as-current rejections of the 77cafc9 run no longer apply. Five of the six after-arrival cases now validate with readiness agreement (enforced by the contract, so agreement shows contract-following, not independent readiness judgment). The one remaining rejection is a genuine claim-check catch, not a contract gap: the answer said "below target" against the resolved target_gap fact. This rerun covers only the six after-arrival cases, so it is not a full re-run, and the 77cafc9 17-case run (inv-v2) stays as recorded. One run per case, synthetic data, small sample. This is not a pass or fail of the product.

## Second review and transcription (placeholder, 2026-10-29)

No muse-wonder-1.0 review and no muse-voice-transcribe-1.0 transcription has been recorded yet: the code that
will display them is built offline (day11-06), and the approved paid calls run after it. When recorded, reviews
(`backend/eval/reviews-*.json`, review-v1) are scored only on contract validity (known verdict, known issue kinds,
evidence ids restricted to the pack, notes of at most 200 characters) and on whether they flag the planted
unsupported claim; they never change a readiness, verification, or outcome result. Transcriptions
(`backend/eval/transcripts-*.json`) are scored only on whether the resulting `human_report` record carries the
expected statement (HVAC completion, observed 2026-01-16T20:40-05:00) without entering any measurement source list,
eligibility, verification stage, or notification payload. Until then this section stays a placeholder.

## Watcher correction rates (placeholder, 2026-10-29)

No watcher runs have been recorded yet, so both rates are placeholders: first-pass rejection rate n/a (0 runs),
after-correction pass rate n/a (0 runs). Once the operator records an approved batch through
`aria_home.watcher`, this section reports the first-pass rejection rate and the after-correction pass rate as
separate measures, computed from `backend/eval/corrections-*.json`. The offline report already renders this
section the same way (see `watcher_correction_rates` in `backend/aria_home/evaluation.py`).
