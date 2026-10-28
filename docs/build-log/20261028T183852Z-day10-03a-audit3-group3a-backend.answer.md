Model: muse-wonder-1.0
Turns: 59

## 8 — Abandoned claim stuck

**Root cause:** `inference_requests` pending rows had no owner or expiry, so every later request treated a dead claim as active forever.

**Fix:**
- `backend/aria_home/store.py`: added `owner_id` + `lease_expires_at` (120s lease, migrated columns). `claim_inference()` distinguishes active `pending` / expired → `recovery_required` / `failed` / `completed`; expired or failed claims are re-claimed only with `retry=true`, atomically under a new owner (concurrent recovery = one owner). `complete_inference(..., owner_id=...)` rejects stale owners (`completion_accepted: false`), including after lease expiry, so a late completion cannot overwrite a newer accepted result or investigation row.
- `backend/aria_home/app.py`: ordinary POST on an expired claim → **409 `recovery_required`** (no provider call); `retry=true` re-runs once; active claims return 202 even with `retry=true`; stale-owner completion returns the current pending/recovery/stored state instead of persisting.
- Documented states, recovery action (`POST …&retry=true`), and user-visible state in `docs/inference-idempotency.md`.

## 9 — GET ran inference

**Root cause:** `GET /api/investigation` called `investigate()` unconditionally.

**Fix:** `app.py` GET now only builds the deterministic evidence pack and returns the stored result for the identity, 202 for an active claim, 409 for `recovery_required`, or a documented 200 no-result summary (`status: unavailable`, `inference_state: not_started`, `output: null`). It never calls `provider.generate`. `frontend/src/api.ts`: `fetchInvestigation` accepts the 202/409 lifecycle states and the widened response status type. Updated the one existing GET test (`test_investigator.py`) to create via POST first, keeping all original assertions, plus stored-result assertions in the new tests.

## 10 — Ack body not validated

**Root cause:** the ack endpoint coerced any/missing body, defaulted unknown actors, and passed non-string times into parsing/store code (500s, intruders accepted).

**Fix (`app.py`, documented in `docs/inference-idempotency.md`):** JSON-object body required (400 otherwise); actor must be a non-empty string (400) on the per-audience simulation allowlist — homeowner→`homeowner`, property_manager→`property_manager`, hvac_company→`hvac_company`, explicitly documented as a simulation allowlist, not authentication (403 otherwise); `at` must be a timezone-aware ISO string not earlier than `created_at` (400). Only `simulated_delivered` notices can be acked; `refused`/`queued` → 409 with nothing recorded. Valid/repeated acks stay idempotent, and replay-time ack visibility is preserved.

**Tests added:** `backend/tests/test_audit3_group3_lifecycle.py` (7 tests) — restart with abandoned claim, active not stolen, expired recovery, concurrent recovery, late old-owner completion, no automatic re-run, GET call-count/stored retrieval, and every ack reproduction plus valid/repeated/refused/queued acks.

## Real command output

```
cd backend && python -m pytest tests/test_audit3_group3_lifecycle.py tests/test_inference_idempotency.py tests/test_audit3_group2_identity_persistence.py tests/test_investigator.py tests/test_notifications.py -q
62 passed in 10.21s

cd backend && python -m pytest -q
336 passed in 33.98s

cd frontend && npm run test:e2e
22 passed (32.3s)

cd frontend && npm run typecheck
> tsc --noEmit   (no errors)
```
