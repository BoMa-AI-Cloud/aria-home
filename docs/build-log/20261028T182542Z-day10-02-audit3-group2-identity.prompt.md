ARIA Home, Audit 3 repair, GROUP 2: identity, persistence and API consistency (approved by Brad).
Backend only. DO THE WORK NOW in this turn. No live calls, no installs, no network beyond 127.0.0.1, no
git, NO helper scripts outside tests. Temporary databases, synthetic fixtures and fake providers only;
never call a real model. Do not weaken any existing assertion. Smallest sound changes; no new features.
Group 1 (conflict policy, finite numerics, temperature vs equipment) is already in the working tree; keep it.
Shell starts in C:\aria-home. Do not end your turn until `cd backend && python -m pytest -q` passes.

Read first: backend/aria_home/investigator.py, store.py, app.py, provider.py, notifications code,
docs/inference-idempotency.md, and the existing investigation/idempotency tests.

Reproduced on the current code:

4. ROUNDING HIDES DECISION-RELEVANT CHANGES. Scenario demo_v1 at 2026-01-16T17:56:00-05:00: setting every
   numeric indoor_temp record to 67.96 gives computed_readiness at_risk, 68.04 gives on_track, but
   build_evidence_pack + inference_identity give the SAME identity_key and input_revision. Through the API:
   POST /api/investigations for the 68.04 version, then mutate to 67.96 and POST again -> the second response
   is deduplicated and returns the cached on_track though fresh computation says at_risk.
   Fix: derive input_revision from canonical full-precision decision inputs (values, units, timestamps
   normalized to UTC, provenance, context, eligibility and policy versions), stable ordering; keep display
   rounding separate. Changed decision-relevant evidence must never reuse an obsolete result; presentation-only
   changes should not invalidate it.
   Tests: the exact 68.04/67.96 reproduction through POST (patch the app's scenario loader on a disposable app),
   revisions differ on relevant change, stable under reordering and equivalent timezone offsets, cached
   responses agree with current computation, presentation-only change keeps the identity.

5. PROVIDER NOT IN IDENTITY. A mock result is cached; switching the provider to mode "live" for the same
   scenario/time returns the cached mock result (deduplicated true, 1 provider call).
   Fix: include normalized non-secret provider mode, provider identity, model id, endpoint identity (host/path
   only, no query) and material generation settings in the inference identity. Never put keys, auth headers
   or secret-bearing URL parts into ids, logs or payloads; key rotation alone must not change identity.
   Tests with fake providers only: mode change, model change, endpoint change -> new identity; key change ->
   same identity and the key appears nowhere in stored rows or responses.

6. SUCCESSFUL RETRY NOT PERSISTED. First POST with a failing fake provider returns unavailable; POST with
   retry=true succeeds and returns ok, but Store.get_investigation(id) still has status unavailable and output
   null (save_investigation ignores an existing id).
   Fix: define attempt history plus one canonical accepted result; persist the accepted result consistently
   with the inference state; later consumers (follow-ups, notification construction) read the accepted result.
   Keep already-issued notifications and audit history; do not rewrite history or resend; define whether a new
   notification is appropriate after a retry and enforce idempotency. No DB write lock held during the provider
   call. Document the semantics in docs/inference-idempotency.md.
   Tests: fail then succeed (stored row and attempt history), repeated successful retry, follow-up and
   notification payloads after retry, no duplicate notices, concurrent attempts, failure during persistence.

7. ENDPOINTS DISAGREE ON READINESS. demo_video_v1 at 2026-01-16T22:01:00-05:00: GET /api/metrics reports
   readiness.target_at_arrival "unknown" while GET /api/investigation reports "met".
   Fix: one canonical evidence/readiness input builder used by every endpoint; a reduced presentation pack must
   not change the arrival conclusion; keep the distinction between what was observed at arrival and what became
   known later; respect observed and received/available timestamps.
   Tests: before, at and after arrival; latest reading after arrival; delayed receipt; missing coverage;
   rewind; and a parity test over every shipped scenario at meaningful replay times asserting /api/metrics and
   /api/investigation give the same readiness.

Bump any policy/contract version string you change and update docs/inference-idempotency.md exactly.
Final answer: per finding, root cause, files changed, tests added, and the REAL pytest output line.

