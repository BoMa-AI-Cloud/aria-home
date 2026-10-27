ARIA Home, Day 9 task D9-6 (approved by Brad; a bug fix allowed by docs/freeze.md, plus recorder
pacing). DO THE WORK NOW in this turn. No helper scripts, no live calls, no installs, no network,
no git. Do not end your turn until `cd backend && python -m pytest -q`, the offline evaluation
check in the tests, `cd frontend && npm run test:e2e` and `cd frontend && npm run record:demo` pass.

Read: backend/aria_home/readiness.py, metrics.py, verification.py, evaluation.py,
backend/eval/expected.json, docs/readiness-rules.md, docs/demo-script.md (A, H),
frontend/recording/demo.record.ts.

BUG (operator, seen in the recorded footage): demo_video_v1 at 16:31 shows the verified fact
"Indoor temperature 52.0 F (at 16:30)" (room sensor, fresh) but readiness says "Cannot tell ...
indoor reading is stale", because readiness judges freshness on the thermostat. When a scenario has
room-sensor records for the zone, readiness must use the room sensor for the indoor reading,
freshness, coverage and trend (as metrics.temperature_trend already does); the offline thermostat is
reported as a separate reason ("thermostat telemetry missing; room sensor used"). Scenarios without a
room sensor are unchanged. Expected: demo_video_v1@16:31 -> at_risk (fresh room reading 16 F below
target, flat). Update backend/eval/expected.json for any case this changes, with a one-line reason,
and regenerate the offline results and docs/evaluation.md through the evaluation code path. Keep the
live section with its note. Document in docs/readiness-rules.md.
PACING: in frontend/recording/demo.record.ts hold each title card for its narration time from
section A (opening 15 s, evaluation 15 s, closing 10 s), and lengthen the holds in the app segments
so each clip's length is at least its section A segment length (s1 30 s, s2 25 s, s3 20 s, s4 40 s,
s5 25 s), holding longest on the key labels.
Final answer: the rule change, label changes, new offline totals, clip lengths, REAL output lines.

