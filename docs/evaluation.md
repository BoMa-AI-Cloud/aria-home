# Evaluation (offline, deterministic)

Synthetic scenarios, expected labels written by the builder, small sample, not a benchmark of real homes.

The 12 cases pair each scenario with fixed replay times. Expected readiness (and, for `demo_video_v1` only, the expected verification stage) is hand-written in `backend/eval/expected.json` from the fixture data, with a one-line reason per case. For `arrival_passed` cases (now strictly after the confirmed arrival), `expected_target_at_arrival` (`met` / `not_met`) is also scored: a case is correct only if both the readiness status and the at-arrival outcome (`target_at_arrival` on the readiness result) match, so a source condition without indoor temperatures yields `unknown` and is scored unsupported, not correct. Each case is run under the combined (all-sources) condition and under source-limited conditions that keep only one source kind of evidence record; trip/confirmation context (the arrival and target being asked about) is retained. `useful_heat` is supportable in no condition: circuit watts alone never prove useful heat.

## Totals

| Condition | Cases | Readiness correct | Wrong | Unsupported | Target at arrival correct (scored) | Verification correct (scored) | Fully correct |
|---|---|---|---|---|---|---|---|
| combined | 12 | 12 | 0 | 0 | 4 (4) | 5 (5) | 12 |
| thermostat_only | 12 | 9 | 0 | 5 | 4 (4) | 1 (5) | 7 |
| room_sensor_only | 12 | 10 | 0 | 9 | 1 (4) | 1 (5) | 3 |
| electrical_only | 12 | 6 | 0 | 10 | 0 (4) | 1 (5) | 2 |
| calendar_only | 12 | 6 | 0 | 10 | 0 (4) | 1 (5) | 2 |

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
- electrical_only at demo_video_v1@16:31 can support an electrical-activity claim (blower circuit watts) but watts alone never support a useful-heat claim; the combined view uses the flat room readings to show no warming.

## Reading this

- Combined matches every expected readiness label and every scored verification stage; the single-source conditions do not, mostly by falling back to `cannot_tell` / `telemetry_missing` / `unable_to_verify` (unsupported), not by asserting the opposite readiness.
- Thermostat-only during the `demo_video_v1` outage (16:31) cannot support a warming or even a current-temperature claim: its last reading is 15:30, stale by evaluation time. The combined view still has fresh independent room readings showing no warming.
- Electrical-only can show circuit activity (for example the blower circuit during the outage) but can never support a useful-heat claim; only temperature evidence can show warming.
- A model condition exists in `aria_home.evaluation.run_model_cases` (status, readiness agreement, rejected-claim reasons, latency, tokens per case). Offline tests run it with the mock provider. A live run requires `--live`, `--max-calls N`, and `ARIA_HOME_MODEL_ENABLED=1` together; there are no retries, and timeout/max-tokens come from the existing provider/investigator config.

## How the code counts (Audit 3, 2026-10-28)

- **Cases and scenarios are different counts.** The code (`backend/aria_home/evaluation.py`, `CASES` / `backend/eval/expected.json`) defines **12 cases** across **6 scenarios** (`demo_v1`, `demo_recovery_v1`, `demo_no_followup_v1`, `demo_revised_v1`, `demo_cancelled_v1`, `demo_video_v1`). Each case is run under 5 conditions (combined + 4 single-source), giving 60 case-condition rows. Never write this as "12 x 7".
- **Recovery verification is scored for 5 of the 12 cases** — only the `demo_video_v1` cases carry `expected_verification` (the only scenario with room-sensor records), so per condition `verification_scored` is 5. The other 7 cases score readiness (and, where applicable, target-at-arrival) only.
- **Three different totals, kept separate:** readiness correct (of 12 per condition), verification correct (of the 5 scored), and fully correct (a case-condition row counts only if readiness, any scored verification, and any scored target-at-arrival all match). See the Totals table.
- **Readiness agreement is contract-following, not independent accuracy.** The contract (`inv-v2`) tells the model the code-computed readiness and rejects a disagreeing answer, so live agreement shows the model followed the contract. It is not evidence the model judged readiness independently.

## Recorded live runs (register; no re-runs)

| Date | Model id(s) | Provider route | Calls | Code snapshot | Policy version | Recorded result |
|---|---|---|---|---|---|---|
| 2026-10-26 | `muse-spark-1.3`; `muse-wonder-1.0` | Meta Model API | 24 total = 12 cases on each of 2 models (see below) | 53a06bd | pre-Audit-2 labels; prompt `inv-v2`; readiness labels pre-date `arrival_passed` target-at-arrival and `readiness-policy-v2` stamping | Each model 12/12 valid, 0 rejected (source: `backend/eval/results-live.json`) |
| 2026-10-27 | `muse-spark-1.3` | Meta Model API | 12 | 114be6a (after Audit 2 repairs) | prompt `inv-v2`; `readiness-policy-v1` (Day-7 labels with `arrival_passed` and target-at-arrival; the `readiness-policy-v2` stamp came later in Audit 3, 2026-10-28) | 8/12 valid, 4 rejected (source: `backend/eval/results-live-current.json`) |
| 2026-10-27 | `meta-models/muse-spark-open-1026` | Baseten (evaluation only) | 12 at 12000 tokens; 12 at 2000 tokens | 114be6a | prompt `inv-v2`; `readiness-policy-v1` (Day-7 labels with `arrival_passed` and target-at-arrival; the `readiness-policy-v2` stamp came later in Audit 3, 2026-10-28) | 1/12 valid at 12000 tokens; 0/12 valid at 2000 tokens (all 12 no-answer, reasoning used the budget) (source: `backend/eval/results-live-current.json`) |

Resolving the wording: "24 calls" was 12 cases run on each of two models, not 24 cases. "12/12 valid" applies per model in that run (12 valid of that model's 12 calls; 24/24 valid across both). Cost: no dollar figure is recorded in the recorded files, so none is stated here.

## Live model condition (2026-10-26)

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
