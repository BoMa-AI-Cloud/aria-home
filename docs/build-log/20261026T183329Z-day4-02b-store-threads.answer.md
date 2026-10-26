Model: muse-wonder-1.0
Turns: 22

**Root cause:** `Store` shared one `sqlite3` connection (`check_same_thread=False`) across Flask dev-server threads; concurrent use raised `sqlite3.InterfaceError: bad parameter or other API misuse`.

**Change:**
- `backend/aria_home/store.py`: removed the shared connection. Each operation now opens a short-lived connection via `_connection()` (`sqlite3.connect(..., timeout=5)`, `row_factory=Row`, `with conn:` transaction, closed afterwards). `record_outcome` uses `BEGIN IMMEDIATE` to serialize its read-check-write. `close()` is now a no-op; public API and insert-or-ignore/`INSERT OR IGNORE` idempotency unchanged.
- `backend/tests/test_store.py`: added `test_concurrent_saves_and_records_are_thread_safe` — 8 threads (barrier-synchronized, `ThreadPoolExecutor`) doing save/save-follow-up/record against same + different ids on a `tmp_path` DB; asserts no exception, one investigation/follow-up row per id, and one outcome event per `(id, evaluated_at)`.

**Final pytest line (real):**
```
126 passed in 2.35s
```
