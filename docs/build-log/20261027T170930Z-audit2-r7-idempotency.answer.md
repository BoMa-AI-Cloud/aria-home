Model: muse-wonder-1.0
Turns: 46

**Rule adopted:** Deduplicate before inference on identity = scenario id + scenario fixture version (`manifest.version`) + canonical evaluation time in UTC + `input_revision` (SHA-256 of canonical-JSON visible evidence/trip/confirmation/flags/source statuses/metrics, timestamps canonicalized to UTC) + prompt version `inv-v2` + readiness policy version. Investigation id = `inv-<identity_key[:12]>`. A short `BEGIN IMMEDIATE` transaction claims the identity as `pending` (unique key, no lock held during the model call); completion stores the full result as `completed` (`ok`) or `failed` (non-`ok`). Identical completed/failed requests return the stored result with `deduplicated: true` and no provider call; identical requests while `pending` return documented **202 `{"status":"pending",…}`** with no provider call; `failed` is retried only via `?retry=true` (exactly one more call); `retry` on `completed` returns the stored result. All states persist in SQLite across restart.

**Files changed:**
- `backend/aria_home/investigator.py` — `inference_identity()` + UTC canonicalization
- `backend/aria_home/store.py` — `inference_requests` table, `claim_inference()` / `complete_inference()` / `get_inference()`
- `backend/aria_home/app.py` — `POST /api/investigations` claims before calling the provider, returns 202/stored result, handles explicit retry
- `backend/tests/test_inference_idempotency.py` — new: counting mock provider, tmp DBs; sequential (1 call), 8 concurrent (1 call, seven 202s), changed time/input (new call/id), failure/no-silent-retry + explicit retry (exactly 1 more), restarted store
- `docs/inference-idempotency.md` — rule, 202 contract, retry semantics

**Reproduction:** before the fix the new tests failed (e.g. `assert 2 == 1` provider calls on identical posts; 5 failed).

**Assertion changes:** none — no existing tests or fixtures were modified; only the new test file was added (its record-mutation helper was fixed during development to skip non-numeric values).

**Final pytest line (real):** `266 passed in 14.59s`
