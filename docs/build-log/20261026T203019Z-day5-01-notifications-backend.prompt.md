ARIA Home, Day 5 task D5-1 (approved by Brad): scoped notifications and acknowledgement, backend.
DO THE WORK NOW in this turn; do not stop after a plan. No helper scripts, no live calls, no
installs, no network, no real messages of any kind, no git. Do not end your turn until
`cd backend && python -m pytest -q` passes.

Read: backend/aria_home/contracts.py (NotificationState), store.py, app.py, investigator.py,
readiness.py, verification.py, scenario.py (context_as_of, events_as_of), docs/demo-script.md
(story steps 4 and 6, sections E and F), docs/readiness-rules.md.

BUILD backend/aria_home/notifications.py (pure decisions) plus store tables and API:
1. Audiences: homeowner, property_manager, hvac_company. A notification is built by code from the
   investigation, the readiness/verification result and the as-of context, never from model
   prose alone. Per audience, an explicit allowlist of fields:
   - homeowner: readiness/stage in words, verified facts, what was done, times.
   - property_manager: property label, the verified facts, readiness, the requested action,
     access note; never the itinerary, email, phone location or flight details.
   - hvac_company: only property label/address label, access note, manager contact label and
     relevant observations (approved decision); nothing about the homeowner's trip.
   A test fails if any payload has a key outside its allowlist.
2. Authorization gates (as-of): property_manager only if the confirmation (visible at now) has
   manager_authorized; hvac_company only after a manager_hvac_authorized event visible at now.
   A refused notification is recorded with its reason, never sent.
3. Outbox: SQLite table notifications (id, investigation_id, audience, kind, idempotency_key
   UNIQUE, payload_json, created_at, delivery "simulated", state). Same key twice adds nothing.
   Delivery is SIMULATED only: state goes queued -> simulated_delivered; no network code at all.
4. Acknowledgement: POST /api/notifications/<id>/ack records who and when (as an event with its
   own time). An acknowledgement NEVER changes readiness, the follow-up outcome or the
   verification stage; the API response says "acknowledged, not resolved".
5. API: POST /api/investigations creates the notifications the rules allow (homeowner always,
   manager when at_risk or cannot_tell and authorized); GET /api/notifications?investigation_id=
   lists them with state and acks. For demo_video_v1, GET /api/follow-ups/<id> at or after 16:52
   may create the hvac_company request (gated as above).
TESTS (real API paths, tmp_path DB): allowlists per audience; manager refused without
authorization; hvac refused before 16:45 and allowed after; idempotency (repeat POST/GET adds no
duplicates); ack never changes outcome/stage at any replay time; no payload contains trip,
email, location or flight keys; nothing calls the network (monkeypatch socket to fail).
Existing tests unchanged. Final answer: rules, tables, endpoints, REAL final pytest line.

