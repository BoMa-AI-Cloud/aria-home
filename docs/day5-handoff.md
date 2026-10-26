# Day 5 handoff

## What Day 5 built

- D5-1 scoped notifications (commit 4723bba): per-audience allowlists in
  `backend/aria_home/notifications.py` (homeowner / property_manager /
  hvac_company, enforced by `validate_payload` with recursive
  trip/itinerary/email/phone/location/flight refusal), as-of authorization
  gates (`manager_authorized` confirmation for the manager alert,
  `manager_hvac_authorized` event for the HVAC request) with recorded
  refusals (`state=refused`, never delivered), idempotent outbox
  (`notifications` table, `idempotency_key UNIQUE`, repeat key inserts
  nothing) with simulated delivery only (`queued -> simulated_delivered`,
  no network/socket code), acknowledgement as its own timed event
  (`notification_acks`, `POST /api/notifications/<id>/ack` answering
  "acknowledged, not resolved") that never changes
  readiness/outcome/verification. `POST /api/investigations` creates
  homeowner + manager notifications in every branch;
  `GET /api/follow-ups/<id>` attempts the HVAC request for `demo_video_v1`
  (refused before the 16:45 authorization, delivered at/after, e.g. 16:52);
  `GET /api/notifications?investigation_id=` lists state, refusal reason
  and acks. Covered by `backend/tests/test_notifications.py`.
- D5-2 notifications panel, simulated acknowledgement and homeowner arrival
  update (commit e512a55, no backend changes): "Notifications (simulated
  delivery)" panel in `frontend/src/App.tsx` (audience/state in words,
  created time, exact payload fields, "Simulated, no message was sent" on
  every card), "Acknowledge (simulated)" on delivered manager cards showing
  "Acknowledged, not resolved" with time without touching the Outcome
  headline, replay-time visibility filter for cards, `16:52` video replay
  button, and the homeowner update card at `arrival_met` ("Your home
  reached and held 68 F before you arrived" + evaluation time, derived from
  verification + follow-up target/verified facts). Types and calls in
  `frontend/src/api.ts`, styles in `frontend/src/index.css`. Covered by the
  new video-notifications test in `frontend/e2e/app.spec.ts`.

## Operator checks (at commit e512a55)

Backend 198 passed, typecheck and build passed, browser tests 4 passed.

## Live model calls

None on Day 5.

## Known limits

- Delivery is simulated; there is no real email/SMS/push channel.
- The allowlists are reviewed by hand, not by an external privacy review.
- The HVAC request is gated only by a synthetic manager authorization event.

## Next

- Model comparison / evaluation (the full comparison is planned for Day 6).
- Filming the video against the demo-script acceptance checks.
