ARIA Home, audit repair R1 (approved by Brad): P1 as-of replay isolation. DO THE WORK NOW in this
turn; do not stop after a plan. No helper scripts, no live calls, no installs, no network, no git.
Do not end your turn until `cd backend && python -m pytest -q` passes and
`cd frontend && npm run test:e2e` passes. Do not touch anything outside C:\aria-home.

Read first: backend/aria_home/app.py, store.py, notifications.py, outcomes.py, verification.py,
scenario.py, backend/tests/test_store.py, test_notifications.py, test_verification.py.

FIRST write a failing offline regression test reproducing the external audit (at commit 6a659ca):
create the demo_video_v1 investigation at 16:31; acknowledge the manager notification at 16:50;
GET the follow-up at 21:01; then GET it at 16:31 again. Today the 16:31 response contains the later
arrival_met history and the 16:50 acknowledgement. Show the test fails, then fix.

REQUIRED:
- Separate the complete audit history (kept as is, never deleted) from an as-of replay projection.
  Every replay response (GET /api/follow-ups/<id>, GET /api/notifications, events, verification,
  outcome history, displayed follow-up state) includes only records whose own time is <= the
  requested `at`: outcome events by evaluated_at, notifications by created_at, acknowledgements by
  acknowledged_at, reports by available_at. A notification's state is the state it had at `at`
  (e.g. not "acknowledged" before its ack time).
- Reading an earlier replay must not create notifications or overwrite later operational state
  (no writes when `at` is earlier than the latest stored evaluation for that follow-up; document
  the rule). Repeated reads at the same `at` are idempotent.
- Requests with `at` before the investigation's created_at return an explicit 409 (or documented
  equivalent) "investigation not yet created at this time", never data.
- Document the projection rule in docs/readiness-rules.md ("Replay projection").
TESTS: the audit reproduction; advance -> rewind -> advance gives identical responses at each time;
restart (new Store on the same file) keeps both full history and correct projections; repeated reads
add no rows; before-creation request. Keep all existing tests passing; change existing assertions
only where they relied on future data leaking, and list each change.
Final answer: the rule, files changed, assertion changes, REAL output lines.

