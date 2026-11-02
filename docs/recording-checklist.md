# Recording checklist (care_home_v1, mock/replay mode)

Replay the `care_home_v1` scenario on a fresh temporary database in default
mock/replay mode (`ARIA_HOME_MODEL_ENABLED=0`, no live keys, no paid paths).
`npm run record:demo` does exactly this (fresh DB under the OS temp dir).
Manual equivalent: delete `backend/instance/aria_home.db`, start the backend
with `ARIA_HOME_MODEL_ENABLED=0`, start the frontend, open the page, set
"Scenario" to "Winter night, older adult at home (guided story)".

At every checkpoint: the banner reads "SYNTHETIC DATA - demo scenario, not a
real home"; the Investigation shows "MOCK - example answer, not live
inference"; no real message is sent and no paid inference runs.

| Replay | Must show |
|---|---|
| 19:20 | On track at 69.0 F with no caregiver request. Confirmation request card, SIMULATED with event (19:15) and available times, "Asks" property, warm-by plan, target temperature, caregiver coordination. Confirmed plan and permissions panel: demo-house, Warm-by time 7:00 AM, 68 F, Caregiver coordination allowed, confirmed 7:20 PM, `warmby-care-001-rev1`. Resident consent recorded: resident everything; caregiver home status and observations; HVAC property, access note and observations only. No health data, no medical terms, no location tracking, no fall or activity sensing. |
| 21:00 | Still on track at 68.4 F, trend falling, no caregiver request, and the activity line names the decline. |
| 21:41 | At risk at 66.0 F, 2 F below the 68 F target. The activity line records the notice and says no one is asked yet. No permission request and no caregiver or HVAC notification. |
| 22:46 | At risk at 62.0 F, 6 F below the target. The permission request is created: "cooling (62 F, 6 F below the 68 F target, furnace reported idle since 16:00)", asked 10:46 PM. |
| 23:31 | Outcome "Thermostat telemetry missing": room 59.3 F at 23:30, thermostat silent since 23:00, no thermostat value presented as current. Readiness "At risk". The recorded story answered at 22:47. Family caregiver card and the delivered HVAC company card showing exactly "fields sent: property_label, access_note, manager_contact_label, relevant_observations" — allowed fields only, no health/personal details, no itinerary/email/location; at 22:46 the HVAC card is refused. The HVAC notice reads 10:50 PM. Technician-on-site card at 23:30, 44 minutes after the ask; arrival closes nothing. Click "Acknowledge (simulated)": "Acknowledged, not resolved" and the Outcome headline does not change. The 10:46 PM request is unchanged, word for word. |
| 00:21 | Outcome "Thermostat reporting restored" with later stages Not reached; room 57.6 F. Reconnection alone proves nothing. Simulated service-visit card (23:30–00:15, "does not by itself close anything"). |
| 00:31 | Outcome "Warming observed" from independent room readings (56.6 F at 00:15 to 59.7 F at 00:30). Still not "Temperature goal verified". |
| 01:41 | Outcome "Temperature goal verified" with "Latest reading used: observed … received …" and the evaluation time. Target first reached 01:10, held 30 minutes through 01:40, under 3 hours after the 22:46 ask. No HVAC completion report card and no voice-note row yet. |
| 01:51 | "HVAC completion report" card, labelled "Corroboration only, does not set the outcome", event 01:45, available 01:50; technician voice-note row "Corroboration only", saying the furnace restarted about 12:15. They change no outcome. |
| 07:01 | Outcome "Warm-by expectation met" and the update ("reached and held 68 F before the warm-by time"). Evaluated at 07:01 from readings received by the 07:00 warm-by time (latest 68.0 F at 06:55), not assumed from 01:41. |

Declined branch (same checkpoints, caregiver declines at 22:46): no HVAC request is sent (the HVAC card reads refused, "caregiver declined"); no technician, service-visit card, completion-report card or voice-note row appears at any later step; the room keeps falling to 52.0 F by about 01:30, holds, then eases down 0.2 F/hr from 04:00 (51.4 F at 07:01); the thermostat never returns; verification stays "Thermostat telemetry missing" with the outcome still checking ("awaiting measurement"); 07:01 states the miss against the 68 F goal with the actual reading. Rewinding before the decision shows the original night.

2 F and 6 F are configured settings, not safety limits. The backstop still asks when the house is at risk within 2
hours of the warm-by time; this night reaches 6 F first, so the backstop does not fire before the 22:46 request.

Watcher: no verified correction on this night, so film none. Instead, at 12:21 and 12:31 AM the model was caught and nothing it said was accepted: it invented a
`temperature_rise` category, then revised to `temperature_drop` while the room rose. Code rejected both, and the
Reasoning tab shows `[rejected]`. The other 8 runs are confirmed, with observations at 21:41, 22:46 and 23:31.

Replay rules (any checkpoint): moving to an earlier time shows only what was
known then — scenario/time changes reveal no future state (no later outcomes,
notifications, acks or report cards). A notification created later is absent
from earlier projections, not recreated there.

Visual evidence: replay `care_home_v1` at 00:21 and 07:01 and confirm the
"Visual evidence (synthetic image)" section shows
"Synthetic camera frame (muse-image-1.0) - segmentation by sam-3.1 (recorded)",
with the frost frames labelled "Missed by the model"; images never enter any
notification. The `visual_*` scenarios keep the same treatment: confirm the
image loads at a UTC `at` and at positive and negative UTC offsets (the
returned `image_url` is fetched exactly and serves identical bytes), with the
"(recorded)" caption and "absence of a detection is not an all-clear" wording
for zero-object cases.

Optional live panels off: the page shows no "Your real home, right now" panel
(Emporia), no WhatsApp send button (cards read "Simulated, no message was
sent"), and setting `ARIA_HOME_VISUAL_LIVE=1` changes nothing (replay-only).

ARIA's view clip (`v1-arias-view` in `frontend/recording/trace.record.ts`,
1280x720 dsf2, part of `npm run record:demo`): open "ARIA's view" from the demo
controls, step 19:20, 22:46, 23:31 and 07:01 — the map redraws at each
checkpoint from `GET /api/trace` only; at 23:31 a failed-check streak stops
amber-red with its reason and the thermostat node opens its reading on click;
the ordered steps list is visible at every checkpoint.

## Public-demo browser coverage

`frontend/e2e/public-demo.spec.ts` (config
`frontend/playwright.public-demo.config.ts`, backend
`ARIA_HOME_PUBLIC_DEMO=1` with temp sessions/recorded dirs, UTC and
America/Los_Angeles, 1366x768 and 390x844) drives the same rows through the
guided story: the 23:31 step shows "Thermostat telemetry missing" with the room-sensor
fact and the delivered HVAC card with its API-rendered
"fields sent" line and the ack leaves the Outcome headline unchanged; 00:21
shows "Thermostat reporting restored" with later stages Not reached; 00:31
still shows "Warming observed" (not yet verified); 01:41 shows "Temperature
goal verified" with no report card yet; 01:51 shows the corroboration-only
voice note and report; 07:01 shows "Warm-by expectation met" with the
resident update. The decline branch is driven the same way: no delivered HVAC
card, no visit/report/voice-note language on House or Reasoning, and 07:01
states the miss. Rewind, rapid-step
settling, A/B session isolation with isolated reset, identical visual bytes at
UTC/+05:30/-08:00, and zero calls to graph.facebook.com, api.meta.ai or
Emporia are asserted in the same file.
