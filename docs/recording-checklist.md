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
| 19:20 | Confirmation request card, SIMULATED with event (19:15) and available times, "Asks" property, warm-by plan, target temperature, caregiver coordination. Confirmed plan and permissions panel: demo-house, Warm-by time 7:00 AM, 68 F, Caregiver coordination allowed, confirmed 7:20 PM, `warmby-care-001-rev1`. Resident consent recorded: resident everything; caregiver home status and observations; HVAC property, access note and observations only. No health data, no medical terms, no location tracking, no fall or activity sensing. |
| 02:31 | Outcome "Thermostat telemetry missing". Missing telemetry is not a diagnosis: no thermostat value is presented as current; the verified fact cites the room sensor (52.0 F at 02:30, flat). Readiness "At risk". Power context keeps its limitations; watts are not heat. "Caregiver alert" card, SIMULATED. |
| 02:45 | Family caregiver card (simulated delivery) and the delivered HVAC company card showing exactly "fields sent: property_label, access_note, manager_contact_label, relevant_observations" — allowed fields only, no health/personal details, no itinerary/email/location. The HVAC card is absent or refused at 02:31 ("caregiver has not authorized HVAC contact"). Click "Acknowledge (simulated)": the card reads "Acknowledged, not resolved" and the Outcome headline does not change — a caregiver ack does not close the issue. |
| 04:21 | Outcome "Thermostat reporting restored" with later stages Not reached. Reconnection alone proves nothing; verification is pending. Simulated service-visit card (03:30–04:15, "does not by itself close anything"). |
| 04:51 | Outcome "Warming observed" from later independent room readings (52.0 F at 04:35 to 54.5 F at 04:50; thermostat absent or stale for the trend). Still not "Temperature goal verified". |
| 06:21 | Outcome "Temperature goal verified" with "Latest reading used: observed … received …" and the evaluation time. Target first reached 05:50, held 30 minutes through 06:20 — warming and the hold come only from independent temperature measurements. The simulated timeline has no HVAC completion report card and no voice-note row yet. |
| 06:45 | "HVAC completion report" card appears, labelled "Corroboration only, does not set the outcome", event 06:40, available 06:45; technician voice-note row "Corroboration only". Voice note and report are corroboration: they arrive after verification and change no outcome. |
| 07:01 | Outcome "Warm-by expectation met" and the homeowner update ("Your home reached and held 68 F before the warm-by time"). The warm-by check respects coverage and availability: it is evaluated at 07:01 from readings received by the 07:00 warm-by time (latest 68.2 F at 06:55), not assumed from 06:21. |

Replay rules (any checkpoint): moving to an earlier time shows only what was
known then — scenario/time changes reveal no future state (no later outcomes,
notifications, acks or report cards). A notification created later is absent
from earlier projections, not recreated there.

Visual evidence: replay `care_home_v1` at 02:31 and 07:01 and confirm the
"Visual evidence (synthetic image)" section shows
"Synthetic camera frame (muse-image-1.0) - segmentation by sam-3.1 (recorded)",
with the night frames labelled "Missed by the model"; images never enter any
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
controls, step 19:03, 02:31, 02:45 and 07:01 — the map redraws at each
checkpoint from `GET /api/trace` only; at 02:31 a failed-check streak stops
amber-red with its reason and the thermostat node opens its reading on click;
the ordered steps list is visible at every checkpoint.

## Public-demo browser coverage

`frontend/e2e/public-demo.spec.ts` (config
`frontend/playwright.public-demo.config.ts`, backend
`ARIA_HOME_PUBLIC_DEMO=1` with temp sessions/recorded dirs, UTC and
America/Los_Angeles, 1366x768 and 390x844) drives the same rows through the
guided story: step 4 shows "Thermostat telemetry missing" with the room-sensor
fact; the 02:45 step shows the delivered HVAC card with its API-rendered
"fields sent" line and the ack leaves the Outcome headline unchanged; 04:21
shows "Thermostat reporting restored" with later stages Not reached; 04:51
still shows "Warming observed" (not yet verified); 06:21 shows "Temperature
goal verified" with no report card yet; 06:45 shows the corroboration-only
voice note and report; 07:01 shows "Warm-by expectation met" with the
resident update. Rewind, rapid-step
settling, A/B session isolation with isolated reset, identical visual bytes at
UTC/+05:30/-08:00, and zero calls to graph.facebook.com, api.meta.ai or
Emporia are asserted in the same file.
