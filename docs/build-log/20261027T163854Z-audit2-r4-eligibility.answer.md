Model: muse-wonder-1.0
Turns: 106

**Rule adopted:** One measurement-eligibility policy in `eligibility.py`: physical measurements require allowed source per quantity (`indoor_temp`: `room_sensor`/`thermostat`; `circuit_power`: `electrical`), `kind=measurement` only (human statements corroborate only), matching quantity/zone/circuit, `received_at <= now`, no future (>60s) reading, fresh at `<= 2× expected_cadence_s` (3600s fallback, readiness-capped at `STALE_READING_AGE_S`; exactly at limit passes, +1s fails), and not superseded — only latest eligible fresh reading is current; older/stale readings are historical only. Applied in trends, circuit activity, source status, readiness (incl. arrival), recovery/outcome verification, power context, evidence-pack construction, and current-value fact validation (`current_temperature`/`target_gap`/`electrical_activity`/`equipment_function`); packs/metrics now keep `expected_cadence_s`, `provenance`, `source`, `last_id`, freshness.

**Regression first:** wrote `backend/tests/test_eligibility.py` first — initially `7 failed, 2 passed` (06:00 raw reading accepted as current at 20:21; human-only records counted). Covers stale raw, freshness boundary exact/+1s, superseded vs newer, delayed-after-receipt, human-only `cannot_tell`, mixed kinds sensors-only, missing sensor, human circuit, human-only recovery, valid sensors unchanged.

**Files changed:** `backend/aria_home/eligibility.py` (new), `metrics.py`, `evidence.py`, `readiness.py`, `verification.py`, `investigator.py`, `outcomes.py`, `power_context.py`, `app.py`, `evaluation.py`, `provider.py` (mock no longer emits stale current facts), `backend/tests/test_eligibility.py` (new), `docs/readiness-rules.md` (eligibility section + allowed source/kind table per measurement path).

**Assertion changes:** none — no existing tests or fixtures weakened/modified; only additions in the new test file.

**Final pytest:** `243 passed in 11.11s` (`cd backend && python -m pytest -q`)
