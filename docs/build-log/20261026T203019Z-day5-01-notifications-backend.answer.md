Model: muse-wonder-1.0
Turns: 46

**Rules (`backend/aria_home/notifications.py`, pure decisions, code-built only)**
- Allowlists enforced by `validate_payload` (raises on extra/forbidden keys — `trip/itinerary/email/phone/location/flight` recursively):
  - `homeowner`: `audience, kind, readiness, readiness_in_words, stage, stage_in_words, verified_facts, what_was_done, evaluated_at, planned_arrival`
  - `property_manager`: `audience, kind, property_label, verified_facts, readiness, requested_action, access_note` — never itinerary/email/phone/location/flight
  - `hvac_company`: `audience, kind, property_label, access_note, manager_contact_label, relevant_observations` — nothing about the trip
- Verified facts come from code-rendered `investigation.output.verified_facts` (fallback: deterministic readiness reasons), never model prose alone.
- Gates (as-of via `context_as_of`/`events_as_of`): manager only if visible confirmation has `manager_authorized`; HVAC only if a `manager_hvac_authorized` event is visible at `now`. Refusals are recorded (`state=refused`, `refusal_reason=manager_not_authorized|manager_hvac_not_authorized`), never delivered.
- Delivery is simulated only: `queued -> simulated_delivered`, no network/socket code anywhere.

**Tables (`store.py`)**
- `notifications(id, investigation_id, audience, kind, idempotency_key UNIQUE, payload_json, created_at, delivery='simulated', state, refusal_reason)` — repeat key inserts nothing; refused keys are reason-suffixed so a later authorized delivery still succeeds.
- `notification_acks(id, notification_id, actor, acknowledged_at, UNIQUE(notification_id, actor, acknowledged_at))` — ack is its own timed event; it touches no follow-up/outcome/verification state.

**Endpoints (`app.py`)**
- `POST /api/investigations` — creates homeowner (always) + manager (only `at_risk`/`cannot_tell` and authorized, else refused record) notifications in every response branch, included as `notifications`.
- `GET /api/notifications?investigation_id=` — lists notifications with `state`, `refusal_reason`, and `acks`.
- `GET /api/follow-ups/<id>` — for `demo_video_v1`, attempts the HVAC request (refused before 16:45 authorization, `simulated_delivered` at/after, e.g. 16:52) and includes `notifications`.
- `POST /api/notifications/<id>/ack` `{actor, at}` — records the ack; response `message: "acknowledged, not resolved"`.

**Tests** — new `backend/tests/test_notifications.py` (real API paths, `tmp_path` DB): per-audience allowlists, manager refused without authorization, HVAC refused before 16:45 / allowed at 16:52, idempotency on repeat POST/GET, ack never changes outcome/stage at any replay time, no forbidden keys in any payload, network blocked via monkeypatched `socket`.

Real final pytest line: `198 passed in 4.87s`
