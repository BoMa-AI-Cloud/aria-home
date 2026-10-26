Model: muse-spark-1.3
Turns: 13

- `store.py`: new `outcome_events` table (`UNIQUE(investigation_id, evaluated_at)`); `record_outcome` updates the follow-up then `INSERT OR IGNORE`s one event (same-timestamp re-eval hits the existing early-return, so nothing added); new `list_outcomes(id)` in `evaluated_at` order.
- `app.py`: `GET /api/follow-ups/<id>` returns `"history": store.list_outcomes(id)`.
- `tests/test_store.py`: `test_outcome_history_grows_idempotent_and_survives_restart` — POST `demo_recovery_v1` at 18:00, GET 19:00 → `[warming_observed]`, GET 20:31 → `[warming_observed, target_reached]`, repeat 20:31 stays at two, fresh `Store` on same file lists both.

`125 passed in 1.57s`
