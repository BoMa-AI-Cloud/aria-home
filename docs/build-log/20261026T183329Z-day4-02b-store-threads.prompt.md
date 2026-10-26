ARIA Home, Day 4 bug fix (approved by Brad). No live calls, no installs, no network, no git, NO
helper scripts. Do not end your turn until `cd backend && python -m pytest -q` passes.
Read only backend/aria_home/store.py, backend/aria_home/app.py and backend/tests/test_store.py.

BUG (seen by the operator in the browser test, where the page sends two requests at once):
POST /api/investigations?scenario=demo_v1&at=2026-01-16T18:00:00-05:00 returned 500 with
  File "...\backend\aria_home\app.py", line 232, in create_investigation
    store.save_investigation(...)
  File "...\backend\aria_home\store.py", line 138, in save_investigation
    self._conn.execute(
  sqlite3.InterfaceError: bad parameter or other API misuse
The same requests one after another succeed. Cause: one sqlite3 connection is shared across the
dev server's threads concurrently.

FIX: never share a connection between threads. Open a short-lived connection per operation (or
per request) with a busy timeout (e.g. timeout=5), use `with conn:` transactions, and keep the
idempotent insert-or-ignore behaviour. Keep the public Store API the same.
TEST: a regression test that runs 8 concurrent save/record calls for the same and different ids
from threads (concurrent.futures) against a tmp_path database and asserts no exception, one row
per id and one event per (id, evaluated_at). Existing tests must pass.
Final answer: root cause, change, REAL final pytest line.

