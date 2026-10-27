Model: muse-wonder-1.0
Turns: 113

Rule change (`backend/aria_home/readiness.py`, documented in `docs/readiness-rules.md`): when room-sensor `indoor_temp` records exist for the zone, readiness uses the room sensor for the indoor reading, freshness, coverage, and trend (matching `metrics.temperature_trend`), with `inputs.indoor_source="room_sensor"`. A missing/stale/invalid thermostat no longer forces `cannot_tell`; it is reported as the separate reason `"thermostat telemetry missing; room sensor used"`. Scenarios without a room sensor are unchanged.

Label changes: only `demo_video_v1@16:31` in `backend/eval/expected.json` — `cannot_tell` → `at_risk` (fresh room reading 52.0 F at 16:30, 16 F below target, flat), verification stays `telemetry_missing`, with a new one-line reason. `frontend/recording/demo.record.ts` evaluation-card expectation changed `8/12` → `7/12` for thermostat-only; `docs/demo-script.md` (section A totals/narration and section D) and `docs/submission.md` updated to match. Offline results/docs regenerated through the evaluation code path (`results-offline.json`, `docs/evaluation.md`; live section and its earlier-labels note kept).

New offline totals (fully correct): combined 12/12, thermostat_only 7/12, room_sensor_only 3/12, electrical_only 2/12, calendar_only 2/12.

Clip lengths (all ≥ section A targets 15/15/10/30/25/20/40/25 s): c1-opening 16.8s, c2-evaluation 16.7s, c3-closing 11.6s, s1-trip-cards 40.1s, s2-not-responding 27.4s, s3-authorized-help 26.0s, s4-recovery 47.6s, s5-report-and-arrival 30.3s — longest holds on the key labels (16:31 outcome/investigation, HVAC fields-sent card, 19:51/20:21 recovery headlines, arrival update).

REAL output lines:
- `217 passed in 6.33s` (`cd backend && python -m pytest -q`, incl. offline-evaluation committed-vs-run checks)
- `  ok 1 [chrome] › e2e\app.spec.ts:5:1 › synthetic evidence overview renders without errors (614ms)` … `  5 passed (12.6s)` (`cd frontend && npm run test:e2e`)
- `  ok 2 [chrome] › recording\demo.record.ts:50:1 › c2-evaluation (16.7s)`, `  ok 8 [chrome] › recording\demo.record.ts:177:1 › s5-report-and-arrival (30.3s)`, `  8 passed (3.7m)` (`cd frontend && npm run record:demo`)
