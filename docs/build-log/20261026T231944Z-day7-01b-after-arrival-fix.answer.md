Model: muse-wonder-1.0
Turns: 84

Corrected rule: `arrival_passed` only when `now >` confirmed arrival (strictly after); at or before arrival the earlier `on_track`/`at_risk`/`cannot_tell` rules apply unchanged. Readiness results now carry `target_at_arrival` (`met`/`not_met`/`unknown`, `null` otherwise), `expected.json` carries `expected_target_at_arrival` for `arrival_passed` cases, and a case is correct only if both readiness and at-arrival outcome match — a source condition without indoor temperatures yields `unknown` → `unsupported`.

Expected cases verified: `demo_v1@18:00` `at_risk`; `demo_recovery_v1@19:00` and `@20:31` `arrival_passed`, `not_met`; `demo_video_v1@21:01` `arrival_passed`, `met`.

New offline totals (from regenerated `backend/eval/results-offline.json` / `docs/evaluation.md`, live section kept with note that the live run used the earlier labels):

| Condition | Cases | Readiness correct | Wrong | Unsupported | Target at arrival correct (scored) | Verification correct (scored) | Fully correct |
|---|---|---|---|---|---|---|---|
| combined | 12 | 12 | 0 | 0 | 4 (4) | 5 (5) | 12 |
| thermostat_only | 12 | 10 | 0 | 4 | 4 (4) | 1 (5) | 8 |
| room_sensor_only | 12 | 7 | 0 | 9 | 1 (4) | 1 (5) | 3 |
| electrical_only | 12 | 7 | 0 | 9 | 0 (4) | 1 (5) | 3 |
| calendar_only | 12 | 7 | 0 | 9 | 0 (4) | 1 (5) | 3 |

REAL output lines:

```
213 passed in 7.71s
  4 passed (12.1s)
```
