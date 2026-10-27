Model: muse-wonder-1.0
Turns: 28

**Policy implemented** (`backend/aria_home/verification.py:278`, documented in `docs/readiness-rules.md`):

- `arrival_met` requires complete coverage from `verified_at` to the confirmed arrival.
- Eligible readings: room-sensor, `received_at <= now` (visibility), `verified_at <= observed_at <= arrival` (coverage, by instant — timezone offset irrelevant).
- Every gap — verification point → first eligible, consecutive eligible, and last eligible → arrival instant — must be `<= MAX_GAP_CADENCE_MULTIPLIER × cadence` (2 × 300 s = 600 s in `demo_video_v1`). Exactly at the limit passes; a reading exactly at arrival is eligible.
- Readings observed after arrival never cover the pre-arrival interval and never appear in `arrival_met` supporting ids.
- Missing/incomplete coverage (no eligible readings, excessive internal/final gap, or unknown cadence) returns `unable_to_verify` with a coverage-gap reason — never `arrival_met`. A delayed reading (e.g. observed 20:59) counts only once received, never in an earlier replay.

**Tests** (`backend/tests/test_verification.py`): reproduction (readings after 20:20–21:00 removed, fresh 21:05 kept, evaluated 21:06), exact-at-arrival, final gap exactly 600 s vs 601 s, internal excessive gap, delayed delivery, mixed timezone offsets.

**Real output:**
- Before fix: `3 failed, 10 passed` — gap case and 1-second-over case returned `arrival_met`, internal gap returned `goal_verified`.
- After fix:
```
tests/test_verification.py: 13 passed in 3.57s
cd backend && python -m pytest -q: 229 passed in 8.96s
```
