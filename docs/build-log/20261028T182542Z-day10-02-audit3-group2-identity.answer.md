Model: muse-wonder-1.0
Turns: 59

**4. Rounding hides decision-relevant changes**
- Root cause: `input_revision` was derived from the display-rounded evidence pack (67.96 and 68.04 both round to 68.0).
- Fix: `_build_unrounded_evidence_pack` keeps full precision; `input_revision` (`input-revision-v2`) hashes canonical full-precision visible records (values, units, UTC-normalized observed/received times, provenance, binding, cadence), as-of trip (excluding title) + confirmation, flags, source statuses, unrounded metrics, readiness status/inputs, and policy versions in stable sorted order. Display rounding is presentation-only.
- Files: `backend/aria_home/investigator.py`

**5. Provider not in identity**
- Root cause: identity contained only scenario/time/input/prompt/policy.
- Fix: `normalized_provider_identity` (`inference-identity-v2`) adds non-secret mode, provider class, model id, endpoint host/path only (scheme/query/fragment/userinfo dropped), and material generation settings (provider + investigation max-tokens). Keys/auth/secret fields are never read, so key rotation / query-only changes keep identity; mode/model/endpoint changes create a new one. Provider identity is persisted on `inference_requests`.
- Files: `backend/aria_home/provider.py`, `backend/aria_home/investigator.py`, `backend/aria_home/store.py`, `backend/aria_home/app.py`

**6. Successful retry not persisted**
- Root cause: `save_investigation` used `ON CONFLICT DO NOTHING`, so the first `unavailable` row blocked the accepted retry result.
- Fix: append-only `inference_attempts` history plus one canonical accepted result (`accepted_result_json`); `complete_inference` writes inference state, attempt outcome, accepted result and the `investigations` row in one transaction (failure rolls back to `pending`, no lock held during the provider call); `save_investigation` upserts non-`ok` rows and never downgrades `ok`. Notifications are defined as not re-issued after retry (per-investigation/audience/kind idempotency keys, no duplicates), while later first-time consumers (follow-ups, HVAC construction) read the accepted stored output. Documented in `docs/inference-idempotency.md`.
- Files: `backend/aria_home/store.py`, `backend/aria_home/app.py`, `docs/inference-idempotency.md`

**7. Endpoints disagree on readiness**
- Root cause: `/api/metrics` fed a reduced presentation pack (no evidence) to `compute_readiness`, so the arrival conclusion lost pre-arrival readings (`unknown` vs `met`).
- Fix: `/api/metrics` now takes readiness from the same canonical `build_evidence_pack` used by `investigate`; arrival uses only readings observed **and** received by arrival, later readings don't change it, missing/stale coverage yields `unknown`.
- Files: `backend/aria_home/app.py`

**Tests added:** `backend/tests/test_audit3_group2_identity_persistence.py` (10 tests) — exact 68.04/67.96 POST reproduction on a disposable app with patched scenario loader, revision differing/stability/presentation-only, provider mode/model/endpoint vs key-rotation and secret absence in responses + DB bytes, fail→retry persistence/attempt history/repeated retry/follow-up/notification no-duplicates, accepted-result non-downgrade, persistence-failure rollback via trigger, concurrent attempt history, and metrics↔investigation parity before/at/after arrival, latest-after-arrival, delayed receipt, missing coverage, rewind, and all shipped scenarios.

**Real pytest output:** `329 passed in 34.38s`
