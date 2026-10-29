# Audit 3 defect matrix

An independent audit of ARIA Home reported 12 defects against `d883778`.
The operator ran the auditor's probe scripts against that commit with fake
providers and temporary databases (no live calls); all 12 reproduced
([operator log](build-log/operator-log.md), 2026-10-28 entry). Backend defects
1–10 were fixed by Meta-model tasks day10-01 through day10-03a and committed
as `c3acce9`; frontend defects 11–12 were fixed by day10-03b2 and committed as
`8605c1e`, with follow-ups day10-06 (test-hook gate) and day10-07 (POST-only
WhatsApp send). The audit report itself is an external document and is not
included in this repository; this file records only the defects, their
reproduction, fixes and covering tests.

| # | Defect | Where reproduced | Fix (task, commit) | Regression tests |
|---|---|---|---|---|
| 1 | Conflicting measurements certify success | Auditor probes vs `d883778`; day10-01: same-time conflicting readings, the winner depended on record id. Operator verified the fix: conflicting readings give `unable_to_verify` for both id orderings. | day10-01, `c3acce9`: one shared policy in `eligibility.measurement_conflict_groups` (group by source/subject/quantity/`observed_at` after unit normalization, collapse identical duplicates, exclude unresolved groups); readiness reports `cannot_tell`, verification returns `unable_to_verify`. | `backend/tests/test_audit3_evidence_verification.py` |
| 2 | Non-finite numerics accepted | Auditor probes vs `d883778`; day10-01: NaN/±inf passed validation and an `inf` reading satisfied target comparisons. Operator verified: non-finite readings rejected at validation. | day10-01, `c3acce9`: `contracts.py` rejects non-finite values at the `EvidenceRecord` boundary; finite checks added in `eligibility.py`, `metrics.py`, `outcomes.py`, `readiness.py`, `verification.py`. | `backend/tests/test_audit3_evidence_verification.py` |
| 3 | Temperature success tied to equipment state | Auditor probes vs `d883778`; day10-01: idle-at-target, quiet circuits and already-warm homes failed verification because the goal was gated on HVAC state and circuit activity. Operator verified: idle-at-target and already-at-target give `arrival_met`. | day10-01, `c3acce9`: `verification.py` evaluates temperature claims from room-sensor readings alone; HVAC state and mapped circuit activity are supporting observations only, never vetoes. | `backend/tests/test_audit3_evidence_verification.py` |
| 4 | Rounding hides decision-relevant changes | Auditor probes vs `d883778`; day10-02: 68.04/67.96 both rounded to 68.0 in the evidence pack, so the second reading was deduplicated. Operator verified: the pair is no longer deduplicated (second readiness `at_risk`, as computed). | day10-02, `c3acce9`: `input_revision` (`input-revision-v2`) hashes canonical full-precision visible records; display rounding is presentation-only. | `backend/tests/test_audit3_group2_identity_persistence.py` |
| 5 | Provider not in inference identity | Auditor probes vs `d883778`; day10-02: identity held only scenario/time/input/prompt/policy, so a provider switch reused a stale claim. Operator verified: switching provider mode makes a new identity (2 provider calls). | day10-02, `c3acce9`: `normalized_provider_identity` (`inference-identity-v2`) adds non-secret mode, provider class, model id, endpoint host/path and material generation settings; persisted on `inference_requests`. | `backend/tests/test_audit3_group2_identity_persistence.py` |
| 6 | Successful retry not persisted | Auditor probes vs `d883778`; day10-02: `save_investigation` used `ON CONFLICT DO NOTHING`, so the first `unavailable` row blocked the accepted retry. Operator verified: the retried investigation is stored as `ok` with its output. | day10-02, `c3acce9`: append-only `inference_attempts` history plus one canonical accepted result; `save_investigation` upserts non-`ok` rows and never downgrades `ok`. | `backend/tests/test_audit3_group2_identity_persistence.py` |
| 7 | Endpoints disagree on readiness | Auditor probes vs `d883778`; day10-02: `/api/metrics` fed a reduced presentation pack to `compute_readiness`, losing pre-arrival readings (`unknown` vs `met`). Operator verified: both endpoints report `met` at 22:01. | day10-02, `c3acce9`: `/api/metrics` takes readiness from the same canonical `build_evidence_pack` used by `investigate`. | `backend/tests/test_audit3_group2_identity_persistence.py` |
| 8 | Abandoned claim stuck | Auditor probes vs `d883778`; day10-03a: pending rows had no owner or expiry, so a dead claim stayed active forever. (The auditor's abandoned-claim probe as written no longer applies after the fix because the identity now includes the provider; recovery is covered by the task's own tests.) | day10-03a, `c3acce9`: `owner_id` + `lease_expires_at` (120 s lease); ordinary POST on an expired claim returns 409 `recovery_required`, re-claim only with `retry=true`; stale-owner completion is rejected. | `backend/tests/test_audit3_group3_lifecycle.py` |
| 9 | GET runs inference | Auditor probes vs `d883778`; day10-03a: `GET /api/investigation` called `investigate()` unconditionally. Operator verified: two GETs make 0 provider calls. | day10-03a, `c3acce9`: GET builds the deterministic evidence pack and returns the stored result (or 202/409/200 no-result); it never calls `provider.generate`. | `backend/tests/test_audit3_group3_lifecycle.py` |
| 10 | Acknowledgement body not validated | Auditor probes vs `d883778`; day10-03a: the ack endpoint coerced any/missing body, defaulted unknown actors and passed non-string times into parsing/store code. Operator verified: malformed acks return 400/403. | day10-03a, `c3acce9`: JSON-object body required (400 otherwise); actor must be on the per-audience simulation allowlist (403 otherwise); `at` must be a timezone-aware ISO string not earlier than `created_at` (400); only `simulated_delivered` notices can be acked. | `backend/tests/test_audit3_group3_lifecycle.py` |
| 11 | UI gives up on pending inference early | Auditor probes vs `d883778`; day10-03b2: `createInvestigation` polled ~10 s while the provider timeout is 20 s and the claim lease 120 s, so a 13 s inference was abandoned; 409 `recovery_required` was thrown as a generic failure. | day10-03b2, `8605c1e`: elapsed-time deadline `INFERENCE_POLL_DEADLINE_MS` (120 s lease + 15 s margin), exponential backoff capped at 2 s, typed `RecoveryRequiredError` with its own message, abort/token guards against stale overwrites. Follow-up day10-06 gated the task's test-only hooks (`test_delay_s`, `test_fail`, `lease_s`) behind `ARIA_HOME_E2E_HOOKS=1`. | `frontend/e2e/pending.spec.ts`, `backend/tests/test_audit3_group3b_hooks.py` |
| 12 | Hard-coded browser test ports | Auditor probes vs `d883778`; day10-03b2: 11 absolute `http://127.0.0.1:5173/` navigations in `e2e/app.spec.ts` (plus 6 in `recording/`) bypassed the configured `baseURL`. Operator verified: no hard-coded 5173 URLs left; alternate-port smoke passes. | day10-03b2, `8605c1e`: relative routes in `e2e/app.spec.ts` and the recording scripts; record config honors `PLAYWRIGHT_FRONTEND_PORT`/`PLAYWRIGHT_BACKEND_PORT`; new `playwright.alt.config.ts` with `test:e2e:alt-ports` on 15173/15000. | `frontend/e2e/app.spec.ts`, `frontend/playwright.alt.config.ts` |

## Follow-ups

- day10-06 (hook gate): the test-only POST parameters added by day10-03b2
  (`test_delay_s`, `test_fail`, `lease_s`) were honoured in default mock mode;
  they are now honoured only when `ARIA_HOME_E2E_HOOKS=1`, which only the
  Playwright configs set. Covered by `backend/tests/test_audit3_group3b_hooks.py`.
- day10-07 (POST-only send, `fa39f93`): review finding from the WhatsApp
  integration that the real send was triggered from `GET /api/follow-ups/<id>`,
  a read endpoint — the same read-endpoints-must-not-send principle as defect 9.
  Delivery now runs only from `POST /api/notifications/<id>/whatsapp`; repeated
  GETs make zero HTTP calls. Covered by `backend/tests/test_audit3_whatsapp.py`.

## Operator re-run of the auditor's probes, 2026-10-29

From the [operator log](build-log/operator-log.md): "Re-ran the auditor's
probes against HEAD: conflicts give unable_to_verify for both id orders; idle
and already-at-target give arrival_met; retry persisted as ok with output;
provider mode change makes a new identity; metrics and investigation agree
(met); repeated GETs make 0 provider calls; malformed acks 400/403; non-finite
values rejected; 67.96/68.04 get different identities. Probe 4 (abandoned
claim) is covered by tests because the identity now includes the provider."
