Model: muse-wonder-1.0
Turns: 127

**Defect 1 — Conflicting measurements certified success**
- Root cause: `verification._room_records` deduped same-time readings by `(observed_at, received_at, id)`, so the winner depended on record id; `evidence.source_status`, eligibility, and readiness each handled conflicts differently/inconsistently.
- Fix: one shared policy in `eligibility.measurement_conflict_groups` — group by (source, subject, quantity, `observed_at`) after unit normalization (C→F), collapse genuinely identical duplicates, exclude unresolved conflict groups from eligible measurements. `evidence.py` now uses normalized values (and string conflicts are no longer overwritten), `readiness.py` computes zone/source-scoped `indoor_conflicts`, blocks `arrival_passed` for conflicted input and reports `cannot_tell`, and `verification.py` treats conflict times as hold-breakers and returns `unable_to_verify` for conflicts inside/after a hold or arrival interval. Policy version bumped to `readiness-policy-v2` (`readiness.py`, `docs/readiness-rules.md`, `docs/inference-idempotency.md`).
- Tests: both `zz-`/`aa-` id orderings, reversed insertion, conflict inside the hold interval, identical duplicates, F/C-equivalent duplicates, other-zone conflict, pre-follow-up conflict, and readiness/verification agreement on the same conflicted input.

**Defect 2 — Non-finite numerics accepted**
- Root cause: pydantic `float` accepts NaN/±inf and eligibility/conversion helpers passed them through, so an `inf` reading satisfied target comparisons.
- Fix: `contracts.py` rejects non-finite numeric values at the `EvidenceRecord` boundary (string HVAC state stays valid, invalid units already rejected there); `eligibility.py` requires finite values and finite post-conversion results; finite checks also added in `metrics.py`, `outcomes.py`, `readiness.py`, `verification.py`. `app.py` now returns 404 (not 500) when a named scenario fails to load.
- Tests: NaN/+inf/−inf rejected, string state valid, invalid unit rejected, valid temperature/power accepted, 1e308 °C overflow ineligible and never verifies, non-finite scenario rejected at load, API returns 4xx for a bad scenario.

**Defect 3 — Temperature success tied to equipment state**
- Root cause: `verify_recovery` gated the goal on the latest HVAC state (no zone/freshness scoping) and latest circuit activity, and required a warming rise before any goal check, so idle-at-target, quiet circuits, and already-warm homes failed.
- Fix (`verification.py`): temperature claims are evaluated first from room-sensor readings alone; HVAC state (zone-scoped, fresh via shared `is_fresh`) and mapped circuit activity (property/binding-scoped, fresh) are recorded only as separate supporting equipment observations in reasons and never veto or create a temperature stage. Already-at-target readings need only the required hold; coverage, hold-duration, relapse, and arrival requirements are unchanged; human/technician/completion events remain corroboration only.
- Tests: idle and off at target, quiet blower circuit, stale HVAC state, already-at-target (goal at 20:21, arrival at 21:01), fan-only without warming, relapse, missing readings near arrival, completion report alone, and independent verification before the completion report. The shipped `demo_video_v1` stage sequence (18:21 reporting restored, 18:51 warming, 19:51 not yet verified, 20:21 goal verified, 21:01 arrival met) still passes unchanged.

**Files changed:** `backend/aria_home/{app,contracts,eligibility,evidence,metrics,outcomes,readiness,verification}.py`, `docs/readiness-rules.md`, `docs/inference-idempotency.md`; tests added in `backend/tests/test_audit3_evidence_verification.py` (30 tests).

**Real pytest output:** `319 passed in 18.89s`
