Model: muse-wonder-1.0
Turns: 67

Rules implemented:
- Code computes next check as evaluation + cadence (sensor cadence, default 30 min), clamped to ≥15 min after evaluation (`MIN_FOLLOW_UP_DELAY`) and ≤ earlier of deadline (arrival + 2 h) or evaluation + 24 h (`MAX_FOLLOW_UP_DELAY`) — `backend/aria_home/scheduling.py:compute_follow_up_schedule`.
- Model may only supply `follow_up.observation`; any supplied time that is past, equal to evaluation, timezone-naive, too soon, or too distant is rejected by `validate()` and replaced with the computed time in `investigate()` — no invalid time reaches the store.
- Deadline at/before evaluation: `schedule_status`/`flag` = `deadline_passed`, `deadline_passed=true`, `next_check_at=null`, no future check persisted; POST returns this explicitly.
- Store/API also validate: aware `created_at`/`deadline`/`next_check_at`, deadline strictly after `created_at`, `next_check_at` inside the window, otherwise rejected and not persisted.
- Documented in `docs/readiness-rules.md` “Follow-up scheduling”; tests in `backend/tests/test_scheduling.py`.

Real final pytest line: `156 passed in 2.85s`
