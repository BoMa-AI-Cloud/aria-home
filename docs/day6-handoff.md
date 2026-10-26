# Day 6 handoff

## What Day 6 built

- D6-1 evaluation harness (commit 53a06bd): 12 cases across 7 synthetic
  scenarios (`demo_v1`, `demo_recovery_v1`, `demo_no_followup_v1`,
  `demo_revised_v1`, `demo_cancelled_v1`, `demo_video_v1`, plus `demo_video_v1`
  at five replay times), with expected readiness (and, for `demo_video_v1`
  only, expected verification stage) hand-written by the builder in
  `backend/eval/expected.json` from the fixture data. Each case runs under a
  combined (all-sources) condition and four single-source conditions
  (thermostat only, room sensor only, electrical only, calendar only) that keep
  only one source kind of evidence record; trip/confirmation context is
  retained. A live model condition (`run_model_cases`) runs `investigate()`
  per case and records status, readiness agreement, rejected-claim reasons,
  latency and tokens; it refuses without `--live`, `--max-calls N` and
  `ARIA_HOME_MODEL_ENABLED=1` together. The offline CLI
  (`python -m aria_home.evaluation --offline`) writes
  `backend/eval/results-offline.json` and `docs/evaluation.md`. The CLI was
  run by the operator and its output committed, because the Muse run could not
  execute it.
- Live results (commit 8b2f07d): 24 operator-run calls, approved by Brad (the
  12 cases on muse-spark-1.3, then on muse-wonder-1.0; committed snapshot
  53a06bd, 90 s timeout, 12000 output tokens, no retries). Source:
  `backend/eval/results-live.json`.
- D6-2 docs: the "Live model condition" section in `docs/evaluation.md`.

## Offline totals

| Condition | Fully correct (of 12) |
|---|---|
| combined | 12 |
| thermostat_only | 8 |
| room_sensor_only | 4 |
| electrical_only | 4 |
| calendar_only | 4 |

## Live results

| Model | Valid answers | Readiness agreement | Rejected answers | Median latency (s) | Min-max latency (s) | Median output tokens |
|---|---|---|---|---|---|---|
| muse-spark-1.3 | 12/12 | 12/12 | 0 | 40.9 | 20.7-53.0 | 6490 |
| muse-wonder-1.0 | 12/12 | 12/12 | 0 | 37.3 | 19.1-41.0 | 5584 |

Readiness agreement is enforced (the prompt tells the model the computed status and the validator rejects a mismatch), so 24/24 agreement shows the models followed the contract, not that they judged readiness independently. The meaningful result is that 0 of 24 answers were rejected by the claim checks. One run per case, synthetic data, small sample; input-token counts are unreliable (likely prompt caching the adapter does not record). No winner is declared on quality; wonder was faster in this sample.

## Operator checks (at commit 53a06bd)

Backend 205 passed.

## Known gap

The readiness rules have no explicit after-arrival case; the
demo_recovery_v1@20:31 label "on_track" is after its 18:00 arrival and should
be revisited.

## Next

- Filming the video against the demo-script acceptance checks.
