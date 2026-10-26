ARIA Home, verification fix V3 (approved by Brad): follow-up scheduling decided by code. Backend
only. No live calls, no installs, no network, no git, NO helper scripts. Do not end your turn
until `cd backend && python -m pytest -q` passes. Keep the earlier audit-repair work and the
store idempotency and outcome history.

Read first: backend/aria_home/investigator.py, backend/aria_home/outcomes.py,
backend/aria_home/store.py, backend/aria_home/app.py, backend/tests/test_store.py,
backend/tests/test_outcomes.py.

AUDIT FINDINGS (reproduced offline): a follow-up one hour BEFORE the investigation passed, and a
timezone-naive follow-up timestamp passed.

BUILD
1. A deterministic schedule function: the next check time is computed by code from the
   evaluation time, the cadence and the arrival/deadline; the model may only describe what
   observation to make. Document the window as named constants (e.g. at least 15 min after
   evaluation, at most the deadline or 24 h, whichever is earlier).
2. Any model-supplied time must be timezone-aware, strictly after the evaluation time and inside
   the window, otherwise it is rejected and the computed time is used. No invalid time ever
   reaches the store.
3. When the arrival/deadline has already passed at evaluation, say so explicitly (a status/flag,
   e.g. "deadline_passed") and schedule no future check.
4. The store and the API validate too (aware, after created_at) so an invalid time cannot be
   persisted by any path.
5. Document the rules in docs/readiness-rules.md (a new "Follow-up scheduling" section).
TESTS: past, equal-to-evaluation, naive and too-distant times are rejected/replaced; deadline
passed is handled; the POST /api/investigations path persists only a valid time; existing
idempotency, restart and history tests still pass unchanged.
Final answer: the rules and the REAL final pytest line.

