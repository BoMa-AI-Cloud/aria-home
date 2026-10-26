# Evaluation (offline, deterministic)

Synthetic scenarios, expected labels written by the builder, small sample, not a benchmark of real homes.

The 12 cases pair each scenario with fixed replay times. Expected readiness (and, for `demo_video_v1` only, the expected verification stage) is hand-written in `backend/eval/expected.json` from the fixture data, with a one-line reason per case. Each case is run under the combined (all-sources) condition and under source-limited conditions that keep only one source kind of evidence record; trip/confirmation context (the arrival and target being asked about) is retained. `useful_heat` is supportable in no condition: circuit watts alone never prove useful heat.

## Totals

| Condition | Cases | Readiness correct | Wrong | Unsupported | Verification correct (scored) | Fully correct |
|---|---|---|---|---|---|---|
| combined | 12 | 12 | 0 | 0 | 5 (5) | 12 |
| thermostat_only | 12 | 10 | 0 | 4 | 1 (5) | 8 |
| room_sensor_only | 12 | 4 | 0 | 8 | 1 (5) | 4 |
| electrical_only | 12 | 4 | 0 | 8 | 1 (5) | 4 |
| calendar_only | 12 | 4 | 0 | 8 | 1 (5) | 4 |

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
| demo_recovery_v1@19:00 | combined | at_risk | at_risk / unable_to_verify | yes |
| demo_recovery_v1@19:00 | thermostat_only | at_risk | at_risk / unable_to_verify | yes |
| demo_recovery_v1@19:00 | room_sensor_only | at_risk | cannot_tell / telemetry_missing | no (unsupported) |
| demo_recovery_v1@19:00 | electrical_only | at_risk | cannot_tell / telemetry_missing | no (unsupported) |
| demo_recovery_v1@19:00 | calendar_only | at_risk | cannot_tell / telemetry_missing | no (unsupported) |
| demo_recovery_v1@20:31 | combined | on_track | on_track / unable_to_verify | yes |
| demo_recovery_v1@20:31 | thermostat_only | on_track | on_track / unable_to_verify | yes |
| demo_recovery_v1@20:31 | room_sensor_only | on_track | cannot_tell / telemetry_missing | no (unsupported) |
| demo_recovery_v1@20:31 | electrical_only | on_track | cannot_tell / telemetry_missing | no (unsupported) |
| demo_recovery_v1@20:31 | calendar_only | on_track | cannot_tell / telemetry_missing | no (unsupported) |
| demo_no_followup_v1@20:31 | combined | cannot_tell | cannot_tell / telemetry_missing | yes |
| demo_no_followup_v1@20:31 | thermostat_only | cannot_tell | cannot_tell / telemetry_missing | yes |
| demo_no_followup_v1@20:31 | room_sensor_only | cannot_tell | cannot_tell / telemetry_missing | yes |
| demo_no_followup_v1@20:31 | electrical_only | cannot_tell | cannot_tell / telemetry_missing | yes |
| demo_no_followup_v1@20:31 | calendar_only | cannot_tell | cannot_tell / telemetry_missing | yes |
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
| demo_video_v1@16:31 | combined | cannot_tell / telemetry_missing | cannot_tell / telemetry_missing | yes |
| demo_video_v1@16:31 | thermostat_only | cannot_tell / telemetry_missing | cannot_tell / telemetry_missing | yes |
| demo_video_v1@16:31 | room_sensor_only | cannot_tell / telemetry_missing | cannot_tell / telemetry_missing | yes |
| demo_video_v1@16:31 | electrical_only | cannot_tell / telemetry_missing | cannot_tell / telemetry_missing | yes |
| demo_video_v1@16:31 | calendar_only | cannot_tell / telemetry_missing | cannot_tell / telemetry_missing | yes |
| demo_video_v1@18:21 | combined | at_risk / reporting_restored | at_risk / reporting_restored | yes |
| demo_video_v1@18:21 | thermostat_only | at_risk / reporting_restored | cannot_tell / unable_to_verify | no (unsupported) |
| demo_video_v1@18:21 | room_sensor_only | at_risk / reporting_restored | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@18:21 | electrical_only | at_risk / reporting_restored | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@18:21 | calendar_only | at_risk / reporting_restored | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@18:51 | combined | at_risk / warming_observed | at_risk / warming_observed | yes |
| demo_video_v1@18:51 | thermostat_only | at_risk / warming_observed | cannot_tell / unable_to_verify | no (unsupported) |
| demo_video_v1@18:51 | room_sensor_only | at_risk / warming_observed | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@18:51 | electrical_only | at_risk / warming_observed | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@18:51 | calendar_only | at_risk / warming_observed | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@20:21 | combined | on_track / goal_verified | on_track / goal_verified | yes |
| demo_video_v1@20:21 | thermostat_only | on_track / goal_verified | on_track / unable_to_verify | no (unsupported) |
| demo_video_v1@20:21 | room_sensor_only | on_track / goal_verified | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@20:21 | electrical_only | on_track / goal_verified | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@20:21 | calendar_only | on_track / goal_verified | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@21:01 | combined | on_track / arrival_met | on_track / arrival_met | yes |
| demo_video_v1@21:01 | thermostat_only | on_track / arrival_met | on_track / unable_to_verify | no (unsupported) |
| demo_video_v1@21:01 | room_sensor_only | on_track / arrival_met | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@21:01 | electrical_only | on_track / arrival_met | cannot_tell / telemetry_missing | no (unsupported) |
| demo_video_v1@21:01 | calendar_only | on_track / arrival_met | cannot_tell / telemetry_missing | no (unsupported) |

## Where a single source falls short

- room_sensor_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- room_sensor_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- room_sensor_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/None.
- room_sensor_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected on_track/None.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected on_track/None.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected on_track/None.
- room_sensor_only cannot support the current_temperature claim that combined supports at demo_revised_v1@18:00.
- electrical_only cannot support the current_temperature claim that combined supports at demo_revised_v1@18:00.
- calendar_only cannot support the current_temperature claim that combined supports at demo_revised_v1@18:00.
- room_sensor_only cannot support the current_temperature claim that combined supports at demo_cancelled_v1@18:00.
- electrical_only cannot support the current_temperature claim that combined supports at demo_cancelled_v1@18:00.
- calendar_only cannot support the current_temperature claim that combined supports at demo_cancelled_v1@18:00.
- thermostat_only cannot support the current_temperature claim that combined supports at demo_video_v1@16:31.
- thermostat_only cannot support the target_gap claim that combined supports at demo_video_v1@16:31.
- electrical_only cannot support the current_temperature claim that combined supports at demo_video_v1@16:31.
- electrical_only cannot support the target_gap claim that combined supports at demo_video_v1@16:31.
- calendar_only cannot support the current_temperature claim that combined supports at demo_video_v1@16:31.
- calendar_only cannot support the target_gap claim that combined supports at demo_video_v1@16:31.
- thermostat_only gives unsupported answer (cannot_tell/unable_to_verify) where combined gives the expected at_risk/reporting_restored.
- room_sensor_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/reporting_restored.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/reporting_restored.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/reporting_restored.
- thermostat_only gives unsupported answer (cannot_tell/unable_to_verify) where combined gives the expected at_risk/warming_observed.
- room_sensor_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/warming_observed.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/warming_observed.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected at_risk/warming_observed.
- thermostat_only gives unsupported answer (on_track/unable_to_verify) where combined gives the expected on_track/goal_verified.
- room_sensor_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected on_track/goal_verified.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected on_track/goal_verified.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected on_track/goal_verified.
- thermostat_only gives unsupported answer (on_track/unable_to_verify) where combined gives the expected on_track/arrival_met.
- room_sensor_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected on_track/arrival_met.
- electrical_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected on_track/arrival_met.
- calendar_only gives unsupported answer (cannot_tell/telemetry_missing) where combined gives the expected on_track/arrival_met.
- electrical_only at demo_video_v1@16:31 can support an electrical-activity claim (blower circuit watts) but watts alone never support a useful-heat claim; the combined view uses the flat room readings to show no warming.

## Reading this

- Combined matches every expected readiness label and every scored verification stage; the single-source conditions do not, mostly by falling back to `cannot_tell` / `telemetry_missing` / `unable_to_verify` (unsupported), not by asserting the opposite readiness.
- Thermostat-only during the `demo_video_v1` outage (16:31) cannot support a warming or even a current-temperature claim: its last reading is 15:30, stale by evaluation time. The combined view still has fresh independent room readings showing no warming.
- Electrical-only can show circuit activity (for example the blower circuit during the outage) but can never support a useful-heat claim; only temperature evidence can show warming.
- A model condition exists in `aria_home.evaluation.run_model_cases` (status, readiness agreement, rejected-claim reasons, latency, tokens per case). Offline tests run it with the mock provider. A live run requires `--live`, `--max-calls N`, and `ARIA_HOME_MODEL_ENABLED=1` together; there are no retries, and timeout/max-tokens come from the existing provider/investigator config.

## Live model condition (2026-10-26)

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
