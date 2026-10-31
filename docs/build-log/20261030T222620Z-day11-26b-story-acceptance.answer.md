Model: muse-spark-1.3
Turns: 2

All six gates pass. Final report:

## Files changed
- `backend/aria_home/app.py` — trip_unconfirmed POST branch now includes `"metrics": _replay_metrics(scn, at)` like its siblings (House lead at 19:03/19:15 had no trend while `/api/metrics` said falling/sufficient)
- `frontend/src/App.tsx` — caregiver decision time renders as `<time dateTime>` in the card (byte-identical text); verified-verdict branches and per-step fresh-record logic carried over from day11-26
- `frontend/e2e/public-demo.spec.ts` — consistency branches + earlier-explanations test (below)
- Also in tree from this job's scope: `backend/aria_home/trace.py`, `backend/tests/test_audit5_permission_text.py`, `backend/tests/test_trace.py`, `frontend/e2e/app.spec.ts`, `frontend/src/api.ts`, `frontend/src/index.css`, docs/build-log + gate-a evidence. Scratch removed: `backend/probe_out.txt`, `backend/tests/test_zz_probe.py`. `backend/eval/` untouched. All three red-proof mutations reverted byte-identical (verified by re-read).

## Tests added
- `backend/tests/test_caregiver_frozen_branches.py` — frozen request text+time identical at every checkpoint after raised, in none/approve/decline branches
- `backend/tests/test_followup_replay.py` — every follow-up carries per-step `metrics` (matches `/api/metrics`) and the per-step `recorded_investigation`
- `frontend/e2e/public-demo.spec.ts:815,819,823` — ten checkpoints × three branches, House + Reasoning vs `/api/follow-ups` + `/api/trace`
- `frontend/e2e/public-demo.spec.ts:827` — earlier explanations listed under collapsed history with own times, never as current

## Red proofs (each bug reintroduced, failure watched, then restored)
1. Reversed trend (`change = first_value - last_value` in `metrics.py:151`) → `public-demo.spec.ts:673` — `Error: lead never falls after recovery at 2026-01-17T06:21:00-05:00`, received `"Living room 68 F and falling 5.5 F an hour."` (6 failed = 3 branches × utc/los-angeles, 48 passed)
2. Verified stages return cooling headline (`App.tsx:2207-2213`) → `public-demo.spec.ts:672` — `Error: verdict never cools after recovery at 2026-01-17T06:21:00-05:00` (6 consistency + 2 collateral at `403:412`, 46 passed)
3. Recorded answer lagged one step in the follow-up continuation (`App.tsx:3261`) → `public-demo.spec.ts:750` — `Error: reasoning answer time at 2026-01-17T02:31:00-05:00`, Expected `1768635060000`, Received `1768609200000` (19:20's answer, exactly 7h11m stale, at 02:31 — the audit contradiction verbatim; 6 consistency + 2 earlier-explanations, 46 passed)

## Gate outputs (each command run exactly as written, one per call)
- `cd backend && python -m pytest -q` → `716 passed in 166.01s (0:02:46)`
- `cd frontend && npm run typecheck` → clean (`tsc --noEmit`, no errors)
- `cd frontend && npm run build` → `✓ built in 984ms`
- `cd frontend && npm run test:e2e` → `50 passed (3.0m)`
- `cd frontend && npm run test:e2e:public-demo` → `54 passed (4.0m)`
- `cd frontend && npm run test:e2e:alt-ports` → `1 passed (7.7s)`
