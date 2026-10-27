# Inference idempotency (R7)

`POST /api/investigations` deduplicates before inference. Two identical
requests must not call the provider twice.

## Identity

The inference identity is the canonical JSON of:

- `scenario_id` — scenario manifest `id`
- `scenario_fixture_version` — scenario manifest `version`
- `evaluated_at_utc` — evaluation time converted to UTC (`...Z`); the same
  instant in another offset has the same identity
- `input_revision` — SHA-256 of the canonical JSON of the visible evidence
  (records visible at the evaluation time), trip, confirmation, context
  flags, source statuses, and metrics from the evidence pack
- `prompt_version` — `inv-v2` (`PROMPT_VERSION`)
- `readiness_policy_version` — `readiness-policy-v1`

`identity_key` is the SHA-256 of that identity. The investigation id is
`inv-<first 12 hex of identity_key>`, so a changed time or changed input
yields a new investigation id as well as a new provider call.

## Claim / pending / completed / failed

State is stored in the `inference_requests` SQLite table (unique
`identity_key`), so it survives restart.

1. A short `BEGIN IMMEDIATE` transaction inserts the identity as `pending`
   (unique key). Only the inserter owns the claim. No write lock is held
   during the model call.
2. The owner calls the provider, then stores the full result as
   `completed` (result status `ok`) or `failed` (any other status, e.g.
   provider `unavailable` or validation `rejected`).
3. An identical request that finds `completed` or `failed` returns the
   stored result (same investigation id and investigation payload, with
   `deduplicated: true`) and does not call the provider. Downstream
   follow-up/notification writes remain idempotent (`ON CONFLICT DO NOTHING`
   / `INSERT OR IGNORE`).
4. An identical request that finds `pending` returns **202** with
   `{"status": "pending", "investigation_status": "pending",
   "investigation_id": ..., "identity": {...}, "identity_key": ...}` and
   does not call the provider. Callers may poll by repeating the request;
   once the owner completes, the repeat returns the stored 200 result.
   A `pending` row left by a crashed owner stays `pending` after restart
   (states are kept, not silently re-run).
5. A `failed` attempt is not silently retried. It is retried only with an
   explicit `retry` parameter (`?retry=true`, also `1`/`yes`), which
   atomically re-claims the failed identity as `pending` and makes exactly
   one more provider call. `retry` on a `completed` identity still returns
   the stored result.

## Tests

`backend/tests/test_inference_idempotency.py` uses a counting mock provider
and isolated `tmp_path` databases: sequential duplicates (1 call), 8
concurrent duplicates (1 call, seven 202s), changed time/input (new call,
new `input_revision`/id), failure without silent retry plus explicit retry
(exactly 1 more call), and a restarted store returning the stored result.
