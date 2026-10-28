# Inference idempotency (R7)

`POST /api/investigations` deduplicates before inference. Two identical
requests must not call the provider twice.

## Identity

Identity version is `inference-identity-v2`. The inference identity is the
canonical JSON of:

- `scenario_id` — scenario manifest `id`
- `scenario_fixture_version` — scenario manifest `version`
- `evaluated_at_utc` — evaluation time converted to UTC (`...Z`); the same
  instant in another offset has the same identity
- `input_revision` — SHA-256 of the canonical full-precision decision inputs
  (see below)
- `prompt_version` — `inv-v2` (`PROMPT_VERSION`)
- `readiness_policy_version` — `readiness-policy-v2`
- `provider` — normalized non-secret provider identity (see below)
- `identity_version` — `inference-identity-v2`

`identity_key` is the SHA-256 of that identity. The investigation id is
`inv-<first 12 hex of identity_key>`, so a changed time, changed decision
input, or changed provider identity yields a new investigation id as well
as a new provider call.

### Input revision

`input_revision` uses input-revision version `input-revision-v2`. It is
derived, in stable sorted order, from the unrounded decision inputs built
from the scenario at the evaluation time:

- every visible record's id, source, kind, subject, quantity, full-precision
  value, unit, `observed_at` and `received_at` normalized to UTC, expected
  cadence, provenance and binding (these fields also determine eligibility)
- the as-of trip (excluding its display title) and homeowner confirmation
- context/readiness flags, full-precision source statuses, and the
  full-precision trend, target-gap and circuit metrics
- canonical readiness status and readiness inputs, plus the prompt,
  readiness-policy and input-revision versions

Display rounding is separate: `build_evidence_pack` still rounds values for
presentation, but rounding (or another presentation-only change such as a
trip title or a rounded display metric) never feeds `input_revision`.
Thus 67.96 and 68.04, which both display as 68.0, produce different
revisions and different readiness (`at_risk` vs `on_track`), while record
reordering and equivalent timezone offsets produce the same revision.

### Provider identity

The normalized provider identity contains only:

- `mode` (e.g. `mock` / `live`), provider class/identity, and `model_id`
- endpoint identity as host (with port if present) and path only — scheme,
  query, fragment and userinfo are dropped
- material generation settings (`max_tokens` from the provider and the
  investigation token limit)

API keys, authorization headers and other secret-bearing values are never
read into the identity, stored rows, logs or payloads. Rotating a key (or
changing only a URL query string) therefore does not change identity;
changing mode, provider, model, endpoint host/path, or a material
generation setting does.

## Claim / pending / completed / failed

State is stored in the `inference_requests` SQLite table (unique
`identity_key`), so it survives restart.

1. A short `BEGIN IMMEDIATE` transaction inserts the identity as `pending`
   (unique key) with a generated `owner_id` and a bounded lease
   (`lease_expires_at`, 120 seconds). Only the inserter owns the claim and
   only that owner may complete it. No write lock is held during the model
   call.
2. The owner calls the provider, then stores the full result as
   `completed` (result status `ok`) or `failed` (any other status, e.g.
   provider `unavailable` or validation `rejected`). A completion carrying a
   different/stale `owner_id`, or arriving after its lease was reclaimed, is
   rejected (`completion_accepted: false`) and never overwrites the accepted
   result or the canonical investigation row.
3. An identical request that finds `completed` or `failed` returns the
   stored result (same investigation id and investigation payload, with
   `deduplicated: true`) and does not call the provider. Downstream
   follow-up/notification writes remain idempotent (`ON CONFLICT DO NOTHING`
   / `INSERT OR IGNORE`).
4. An identical request that finds an active (unexpired) `pending` claim
   returns **202** with
   `{"status": "pending", "investigation_status": "pending",
   "investigation_id": ..., "identity": {...}, "identity_key": ...}` and
   does not call the provider or steal the claim — including with
   `retry=true`. Callers may poll by repeating the request; once the owner
   completes, the repeat returns the stored 200 result.
5. If the lease expires before completion, the claim is abandoned/expired:
   it becomes the distinct user-visible state **`recovery_required`**. An
   ordinary POST then returns **409** with `status: "recovery_required"`
   and a GET reports the same state; neither silently re-runs a possibly
   paid inference. Recovery is an explicit operator action: repeat the POST
   with `retry=true`. That atomically re-claims the expired (or `failed`)
   identity under a new owner/lease — concurrent recovery attempts get one
   owner and one provider call, the rest get 202 `pending` — and makes
   exactly one more provider call. `retry` on a `completed` identity still
   returns the stored result. Legacy `pending` rows with no lease are
   treated the same as expired leases.

## Attempts, accepted result, and notifications (retry semantics)

Every claim creates one row in `inference_attempts`
(`identity_key`, attempt number, state, result status, result, start/finish
times); attempts are append-only audit history and are never rewritten.
`inference_requests` keeps one canonical **accepted result**: the result of
the `completed` attempt (status `ok`), stored in `accepted_result_json`.
A failed attempt is recorded in history and as the last result for
deduplication, but it never becomes or overwrites the accepted result.

`complete_inference` writes the inference state, the attempt outcome, the
accepted result, and the canonical `investigations` row in one short
transaction, so a failure during persistence rolls all of them back and
leaves the identity `pending` with no investigation row. `save_investigation`
upserts a non-`ok` row when a retry succeeds, and an `ok` (accepted) row is
never downgraded by a later failed save. Follow-ups and notification
construction after a successful retry therefore read the accepted result
(stored `investigations.output`, follow-up outcome evaluation, and the
retry response payload).

Notifications are **not** re-issued after a retry. Notification
idempotency keys are per investigation/audience/kind (not per attempt), so
a retry returns the already-issued notification rows unchanged and creates
no duplicate or replacement notice, even though the accepted payload is
now used by later consumers that construct a notification for the first
time (for example a first HVAC notification from a follow-up).

## Canonical readiness inputs

`build_evidence_pack` (investigator) is the one canonical
evidence/readiness input builder. `GET /api/metrics` and
`GET /api/investigation` both take readiness from it; a reduced presentation pack must not be fed to
`compute_readiness`. Arrival conclusions (`target_at_arrival`) therefore
use the full evidence: only readings both observed and received/available
by the planned arrival count for what was known at arrival, later readings
do not change the arrival conclusion, and missing or stale coverage at
arrival yields `unknown`.

## GET /api/investigation never runs inference

`GET /api/investigation` is read-only. It computes only the deterministic
evidence pack/readiness in code and either returns the stored investigation
result for that identity or, when no result is stored, a 200 deterministic
summary with `status: "unavailable"`, `inference_state: "not_started"`,
`output: null` and the reason `no stored investigation for this scenario
and time; create one with POST /api/investigations`. An active claim returns
202 `pending` and an expired claim returns 409 `recovery_required`; a GET
never claims, recovers or calls `provider.generate`. Inference happens
only through `POST /api/investigations`.

## WhatsApp delivery is never a GET side effect

`GET /api/follow-ups/<investigation_id>` is read-only for the WhatsApp
channel: it creates the HVAC-company notice row when the
manager-authorisation gate allows it, but never calls the HTTP layer —
repeated GETs make zero delivery calls even with live credentials set.
Real delivery happens only through the explicit
`POST /api/notifications/<notification_id>/whatsapp`, which sends only
that HVAC notice and returns its recorded delivery state. The POST is
409 with `not_configured` when live delivery is not fully opted in
(changing nothing), 404 for an unknown id, 409 for a non-HVAC notice,
and 409 when the notice is not yet visible at the given `at`. At most
one real send per notification id ever: the attempt row is persisted
before the API call, so a second POST never re-sends.
`GET /api/whatsapp/status` is read-only and reports only whether live
delivery is configured, never any value.

## Notification acknowledgement validation

`POST /api/notifications/<id>/ack` requires a JSON object body such as
`{"actor": "property_manager", "at": "2026-01-16T16:37:00-05:00"}`.
Non-object bodies and non-string, malformed or timezone-naive timestamps
are **400**, an acknowledgement earlier than the notification's
`created_at` is **400**, and an unknown notification is **404**; invalid
input never returns 500. The allowed actor is an explicit demo simulation
allowlist (not authentication): `homeowner` notices may be acknowledged
only by `homeowner`, `property_manager` notices only by
`property_manager`, and `hvac_company` notices only by `hvac_company`;
any other actor is **403**. Only `simulated_delivered` notifications can
be acknowledged: acks of `refused` or `queued` notices are **409** and
record nothing. A valid repeated ack (same actor and time) is idempotent
and returns the single existing ack, and acks remain visible only at or
after their acknowledgement time in replay (`acks: []` before it).

## Tests

`backend/tests/test_inference_idempotency.py` uses a counting mock provider
and isolated `tmp_path` databases: sequential duplicates (1 call), 8
concurrent duplicates (1 call, seven 202s), changed time/input (new call,
new `input_revision`/id), failure without silent retry plus explicit retry
(exactly 1 more call), and a restarted store returning the stored result.

`backend/tests/test_audit3_group3_lifecycle.py` covers restart with an
abandoned/expired claim (ordinary POST and GET report `recovery_required`
with zero provider calls, explicit `retry=true` recovers once), active
claims not being stolen, concurrent recovery (one owner/call), late
completion by an old owner not overwriting the newer accepted result,
repeated GETs making zero provider calls with stored-result retrieval
after POST, and acknowledgement validation (early/non-string/naive times,
non-object body, disallowed actor, valid and repeated acks, and
refused/queued notices returning 409).

`backend/tests/test_audit3_group2_identity_persistence.py` covers the
68.04/67.96 rounding reproduction through `POST /api/investigations`,
revision stability under reordering and equivalent timezone offsets,
presentation-only changes keeping identity, provider mode/model/endpoint
changes creating new identities with key rotation keeping identity and
secrets absent from responses and stored rows, fail-then-retry persistence
(accepted result, attempt history, repeated retry, follow-up and
notification payloads with no duplicate notices, concurrent attempts, and
rollback on failure during persistence), and `/api/metrics` vs
`/api/investigation` readiness parity before/at/after arrival, with a
latest-after-arrival reading, delayed receipt, missing coverage, rewind,
and every shipped scenario at replay times around arrival.
