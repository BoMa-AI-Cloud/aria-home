# ARIA Home demo video plan and implementation gap map

Status key, judged from what the code does today (not from test or document
names): **implemented** = the code path exists and does this; **partial** =
some of it exists but a material part of the shot does not; **missing** = no
code does this; **unverified** = code exists but the live behaviour has not
been re-run in its current form.

Content types: synthetic (invented fixture data), simulated (a faked action
or message presented as simulated), replayed (fixture records shown at a
chosen replay evaluation time), live inference (a real model call made for
the recording).

## A. Three-minute video plan

Opening line (spoken, on screen at 0:00): "ARIA is my existing
personal-assistant project. Its name, planning notes, and ARIA Home designs
predate this event. All ARIA Home code shown was written this week with
Meta's Muse models." (30 words; reads in 15 s at about 150 words per
minute.)

Storyboard: exactly 180 seconds, contiguous. Voiceover total: 319 words.

| Time | Hook / screen action | Narration (word count) | On-screen text |
|---|---|---|---|
| 0:00–0:15 (15 s) | Cold open: a front door, a cold house, a phone with a generic "automation completed" style tick. Cut to the ARIA Home page: banner, "Investigation", "MOCK - example answer, not live inference" in frame for the mock take. | "ARIA is my existing personal-assistant project. Its name, planning notes, and ARIA Home designs predate this event. All ARIA Home code shown was written this week with Meta's Muse models." (30; 120 wpm) | "A returning homeowner wants one thing: a warm home, without chasing anyone to get it." / "An automation starting is not an expectation met." / "SYNTHETIC DATA - demo scenario, not a real home" |
| 0:15–0:45 (30 s) | Simulated timeline cards only (no email, location, confirmation, or scene UI exists): scroll "Flight confirmation email", "Airport location" ("Consented"), "Confirmation request", then "Preparation authorized", "Scene command", "Scene acknowledged" (unknown-success line), then "Location unavailable". | "A synthetic flight email and calendar entry propose the return. A simulated, consented airport location supports the plan only, never proving boarding. ARIA asks confirmation of property, arrival, sixty-eight degrees, and manager coordination. The homeowner authorizes preparation. The scene acknowledgement is recorded while physical success stays unknown, and later unavailable location draws no inference." (54; 108 wpm) | "Flight confirmation email" / "SIMULATED" / "Airport location" / "Consented" / "Confirmation request" / "Preparation authorized" / "Scene acknowledged" / "Acknowledged, physical success unknown" / "Location unavailable" |
| 0:45–1:10 (25 s) | Select scenario "Trip home, thermostat offline (video)", replay button "16:31". Capture the Outcome headline, then the Investigation split: "Verified facts (checked against the evidence)" above "Interpretation (model-written, not verified)", Readiness block, "Power context" with "Limitations:". | "At sixteen thirty-one, the Outcome reads Thermostat telemetry missing. Independent room readings show no warming, and electrical activity alone proves neither useful heat nor a fault. Model-written interpretation stays separate from facts checked against the evidence. Readiness is computed in code, never by the model." (45; 108 wpm) | "Status: Thermostat telemetry missing" / "Evaluation time:" "4:31 PM" / "Verified facts (checked against the evidence)" / "Interpretation (model-written, not verified)" / "MOCK - example answer, not live inference" |
| 1:10–1:30 (20 s) | Replay button "16:52". "Notifications (simulated delivery)" panel: Property manager card, then the delivered HVAC company card with its "fields sent:" line; click "Acknowledge (simulated)" on the manager card. Outcome headline must not change. | "ARIA alerts the property manager inside that authorization. After the manager authorizes HVAC contact, the simulated request carries only property, access, and observations, never itinerary, email, or location. Every card reads Simulated, no message was sent, and acknowledgement means Acknowledged, not resolved." (42; 126 wpm) | "Notifications (simulated delivery)" / "Simulated delivery" / "Simulated, no message was sent" / "fields sent: property_label, access_note, manager_contact_label, relevant_observations" / "Acknowledged, not resolved" |
| 1:30–2:10 (40 s) | Replay buttons in order: "18:21", "18:51", "19:51", "20:21". Capture the Outcome headline at each step and the verification progression list ("Reached" / "Not reached") plus History times. At "19:51" hold on "Warming observed" to show the goal is not yet verified. | "ARIA does not close the issue when thermostat reporting resumes at eighteen twenty-one on the next sensor update; reconnection alone proves nothing. At eighteen fifty-one warming is observed in later independent readings. At nineteen fifty-one the goal is reached but not yet verified, so the headline stays Warming observed. At twenty twenty-one maintained readings verify it: we verified recovery of the monitored temperature goal." (64; 96 wpm) | "Thermostat reporting restored" / "Warming observed" / "Temperature goal verified" / "Latest reading used: observed" "received" / "Evaluation (replay) time" |
| 2:10–2:25 (15 s) | Title card built from `docs/evaluation.md` totals (not product UI): the combined vs single-source table. | "In twelve builder-labelled cases, all sources together scored twelve of twelve. Thermostat alone reached seven; room sensor alone reached three; electrical and calendar alone reached two each. A small synthetic sample, not a benchmark." (34; 136 wpm) | "12 builder-labeled cases, fully correct" / "combined 12/12" / "thermostat only 7/12" / "room sensor only 3/12" / "electrical only 2/12" / "calendar only 2/12" |
| 2:25–3:00 (35 s) | Replay button "20:46": Simulated timeline "HVAC completion report" card (absent at 20:21). Then "21:01": "Homeowner update" card. Cut to the warm room at the door. | "The HVAC completion report appears only after verification, as corroboration only that never sets the outcome. The homeowner update says the home reached and held sixty-eight degrees before arrival. Not just an automation completed. An expectation met. ARIA Home connects the plan, coordinates the response, and verifies the result, so coming home feels like coming home." (56; 96 wpm) | "HVAC completion report" / "Corroboration only, does not set the outcome" / "Your home reached and held 68 F before you arrived" / "Not just an automation completed. An expectation met." |

Precise-language rules for every segment: say "we verified recovery of the
monitored temperature goal", never that a repair was proven to cause it, that
the equipment is fault-free, or that anything happened "instantaneously" —
say "on the next sensor update". Missing phone location is "unavailable",
never evidence about her schedule. An arrival window may include clearly
labeled driving and airport-exit/baggage allowances; no claim of real
traffic, flight status, or baggage tracking. ARIA Home is not a travel
platform.


## B. Shot list

Screen actions below use the exact UI labels in `frontend/src/App.tsx`. The
video scenario is selected with the "Scenario" control set to "Trip home,
thermostat offline (video)"; selecting it already runs the investigation at
16:31, and the other times are the replay buttons in "Demo controls
(synthetic replay)". Shots with no dedicated UI (email, location, scene,
confirmation, service visit) are filmed from the "Simulated timeline" cards,
each tagged "SIMULATED"; they are not presented as product screens making
real calls.

| # | Viewer sees | Must actually work | Status | Content type | Screen action and exact on-screen text to capture / acceptance check |
|---|---|---|---|---|---|
| 1 | ARIA Home page loads with the synthetic-data banner, Investigation section, verified facts vs interpretation, code-computed readiness | Backend investigation (inv-v2 claim binding, code-rendered verified facts, deterministic readiness) served to the frontend | implemented (mock); unverified (live filming take, see H) | replayed + live inference or labeled mock | Select "Trip home, thermostat offline (video)". Capture: "SYNTHETIC DATA - demo scenario, not a real home", heading "Investigation", "MOCK - example answer, not live inference", "Verified facts (checked against the evidence)", "Readiness:", "Interpretation (model-written, not verified)", "Provider mode:" line. A live take, if used, is identified as live in section H, never by removing the mock label from a mock take. |
| 2 | Synthetic flight-confirmation email and matching calendar entry propose the itinerary | An email/calendar proposal flow | partial — no email source or proposal UI; the email exists only as the simulated timeline event `email_flight_confirmation`, and calendar is an evidence source card | synthetic / simulated | Film the Simulated timeline card only, at the initial 16:31 state (card already available). Capture: "Flight confirmation email", "SIMULATED", "Event time", "Available time (received time)", "Label", "Landing", "fields sent:". Narration never claims boarding. |
| 3 | Consented simulated location event at the departure airport; later, location "unavailable" during the flight | Location events with consent and unavailable states | partial — no location source or consent UI; both states exist only as simulated timeline events `location_airport` and `location_unavailable` | simulated | Film the Simulated timeline cards only. Capture: "Airport location", "SIMULATED", "Consented", and "Location unavailable", "SIMULATED". "Unavailable" is shown with no inference drawn from it. |
| 4 | Confirmation questions: property, arrival plan, desired temperature, permission to coordinate with the property manager | Interactive confirmation that gates readiness | partial — the confirmation fixture and as-of visibility gate readiness in code, and a simulated `confirmation_request` timeline card exists, but there is no confirmation dialogue or granular permission capture | synthetic / simulated | Film the Simulated timeline card only. Capture: "Confirmation request", "SIMULATED", "Asks" with property, arrival plan, target temperature, manager coordination, "fields sent:". Do not show or claim an interactive dialogue. |
| 5 | Authorized arrival-preparation plan; simulated scene/command; acknowledgement recorded separately from physical success | Scene command + acknowledgement records; no equipment operation | partial — no scene/control UI and no equipment is operated; `preparation_authorized`, `scene_command`, and `scene_acknowledged` exist only as simulated timeline events | simulated | Film the Simulated timeline cards only. Capture: "Preparation authorized", "Scene command", "Scene acknowledged", "SIMULATED", "Acknowledged, physical success unknown", "Physical success". The acknowledgement never flips any physical/outcome state; only later sensor readings do. |
| 6 | Not responding: thermostat telemetry missing while thermostat-independent room readings show no warming | An offline-thermostat interval plus an independent room sensor carrying the trend | implemented | synthetic / replayed | Select "Trip home, thermostat offline (video)", replay button "16:31". Capture Outcome: "Status: Thermostat telemetry missing", "Follow-up rule:", "Latest reading used: observed" / "received", "Evaluation (replay) time"; Investigation: "Evaluation time:" "4:31 PM". During the outage no fresh thermostat measurement is shown as current. |
| 7 | Mapped HVAC electrical activity, other circuits fresh, power statement with limitations | Power context: mapped-circuit activity, per-circuit freshness, bounded continuity statement, limitations | partial — the "Power context" block and the "electrical" evidence card are implemented, but there is no labelled blower-channel card; the blower-consistent observation appears as text in the simulated HVAC request observations | replayed | At "16:31" capture Investigation "Power context" and "Limitations:", and the "Evidence sources" card `article[aria-label="electrical source"]` with "Status:". Capture the HVAC request observations text only from shot 8 / the timeline "HVAC request" card at "18:21" ("fields sent:" property, access_note, manager_contact, observations). Never claim useful heat, a fault, or equipment power from watts. |
| 8 | ARIA alerts the property manager within her authorization; manager explicitly authorizes HVAC contact; scoped simulated request (no itinerary/email/location) | Notification records with authorization gates and a scoped payload | implemented (simulated) | simulated | Replay button "16:31": capture "Notifications (simulated delivery)", the "Property manager" card with "Simulated delivery", "Created:", "Simulated, no message was sent"; any HVAC company card at 16:31 is absent or "Refused:". Replay button "16:52": capture the delivered "HVAC company" card with "fields sent: property_label, access_note, manager_contact_label, relevant_observations" and no itinerary/email/location. Click "Acknowledge (simulated)": capture "Acknowledged, not resolved" and confirm the Outcome headline is unchanged. |
| 9 | Simulated service visit | Visit/repair events | implemented (simulated timeline card only) | simulated | Replay button "18:21" (visit available 18:15). Film the Simulated timeline card only. Capture: "Service visit", "SIMULATED", "Event time", "Available time (received time)", label text "simulated service visit 17:30-18:15 (does not by itself close anything)". The card changes no outcome by itself; do not claim a repair is proven. |
| 10 | Independent recovery detection: telemetry resumes → warming → goal verified → still met at arrival | Verification stages over later readings, evaluated at each replay time | implemented | replayed | Replay buttons "18:21", "18:51", "19:51", "20:21", "21:01". Capture Outcome headlines in order: "Thermostat reporting restored" (18:21), "Warming observed" (18:51 and 19:51; at 19:51 the headline must not yet be "Temperature goal verified"), "Temperature goal verified" (20:21), "Arrival expectation met" (21:01); the progression list shows each stage "Reached" / "Not reached", History accumulates the stages, and "Latest reading used: observed" / "received" is visible. |
| 11 | HVAC completion report becomes available to ARIA only after sensor verification | A report record whose available time is after the verified evaluation | implemented (simulated timeline card only) | simulated | Replay button "20:21": the Simulated timeline has no "HVAC completion report" card and no "Corroboration only" text. Replay button "20:46": capture the card "HVAC completion report", "SIMULATED", "Corroboration only, does not set the outcome", "Event time", "Available time (received time)". At no replay time does the report change the outcome. |
| 12 | Ending: concise evidence-backed homeowner update; warm home at arrival | A homeowner-facing summary generated from the verified outcome | implemented | replayed | Replay button "21:01". Capture the "Homeowner update" section card: "Your home reached and held 68 F before you arrived", "Evaluation time:". It claims goal recovery only, not a proven cause or fault-free equipment. |

## C. Scenario timeline

Built as the `demo_video_v1` fixture. All dates are 2026-01-16,
America/New_York (-05:00), and are scenario assumptions for the video —
invented times, not validated physical behaviour. Temperature target 68 F
and the sensor cadences reuse the existing fixtures.

"Received/available" is when ARIA may first use the item (`received_at` for
records, `known_at`/`confirmed_at` for trip context); "evaluation" is a
replay evaluation time (`at`) at or after that. An item never appears at an
evaluation earlier than its received/available time.

| # | Event | Event time | Received / available | Evaluation |
|---|---|---|---|---|
| 1 | Synthetic flight-confirmation email proposes the return (landing 19:45) | 09:00 | 09:02 | shown on the Simulated timeline card |
| 2 | Matching synthetic calendar entry for the trip | 09:03 | 09:03 | calendar evidence source |
| 3 | Consented, simulated location event: at departure airport | 09:10 | 09:11 | supports the plan only |
| 4 | ARIA asks her to confirm property, arrival plan, temperature, manager coordination | 09:15 | 09:15 | Simulated timeline card |
| 5 | Homeowner confirmation: property, property arrival 21:00 (= 19:45 landing + 45 min labeled airport-exit/baggage allowance + 30 min labeled driving allowance), 68 F, manager coordination permitted | 09:20 | 09:20 (`confirmed_at`) | readiness stops being `cannot_tell` for "unconfirmed" |
| 6 | Homeowner authorizes the arrival-preparation plan | 14:00 | 14:00 | Simulated timeline card |
| 7 | Simulated scene/command sent; command acknowledgement recorded (physical success unknown) | command 14:05 | acknowledgement 14:06 | acknowledgement only |
| 8 | Quiet monitoring during the flight; phone location becomes unavailable (no schedule inference); no urgent condition yet | from 14:10 | — | Simulated timeline card |
| 9 | Last fresh thermostat telemetry; independent room sensors continue on cadence | 15:30 | 15:30:20 | — |
| 10 | Thermostat outage interval: no fresh thermostat telemetry; independent room readings flat (no warming); mapped blower channel shows electrical activity; other circuits fresh | 15:30–16:31 | as each reading arrives | 16:31 "Thermostat telemetry missing" |
| 11 | Investigation at the outage: readiness cannot be on track; ARIA states only bounded claims | — | — | 16:31 |
| 12 | ARIA alerts the property manager (simulated), inside the 09:20 authorization | 16:35 | manager receipt (simulated) 16:37 | notification card |
| 13 | Manager explicitly authorizes contacting the HVAC company on file (simulated) | 16:45 | 16:45 | no HVAC contact before this |
| 14 | Scoped simulated HVAC request: approved property/contact/access info + relevant observations only | 16:50 | HVAC receipt (simulated) 16:52 | 16:52 delivered notification card |
| 15 | Simulated service visit | 17:30–18:15 | visit logged 18:15 | not used by ARIA to close anything |
| 16 | Thermostat reconnection: fresh thermostat telemetry resumes on the next sensor update | 18:20 | 18:20:20 | 18:21 → "Thermostat reporting restored"; does not close the issue |
| 17 | Warming evidence from later independent readings | 18:35–18:50 | as readings arrive | 18:51 → "Warming observed" |
| 18 | Target first reached on independent readings (68 F) | 19:50 | 19:50:20 | 19:51 (not yet verified) |
| 19 | Target maintained through the verification window | 19:50–20:20 | as readings arrive | 20:21 → "Temperature goal verified" |
| 20 | HVAC completion report reaches the property manager (simulated), then becomes available to ARIA | report 20:40 | manager 20:42; available to ARIA 20:45 | 20:46 (corroboration only; cannot set or change the verified outcome) |
| 21 | Homeowner property arrival; goal still met | 21:00 | 21:00 | 21:01 → "Arrival expectation met" |

## D. What is built, and known limits

Built (see `docs/freeze.md`, frozen 2026-10-26 at commit 4d3bacb):

- Evidence foundation with as-of visibility: records, trip revisions and
  confirmations are visible only at or after their received/available times.
- Deterministic metrics, readiness (including `arrival_passed` decided at
  arrival from readings received by arrival), power context, follow-up
  scheduling, outcome rules, and recovery verification stages
  (`telemetry_missing` to `arrival_met`), all computed in code. The model
  cannot change the readiness status.
- Evidence-pack investigation engine (inv-v2 claim binding, code-rendered
  verified facts) with mock and gated live Meta providers.
- SQLite store with outcome and verification history surviving restarts.
- Scoped simulated notifications with per-audience allowlists, recorded
  refusals, idempotent outbox, and simulated acknowledgement
  ("Acknowledged, not resolved") that never changes readiness, outcome, or
  verification.
- Frontend: synthetic-data banner, Investigation section, Outcome section in
  verification-stage wording, notifications panel, homeowner arrival update,
  simulated timeline, evidence source cards, scenario selector including
  "Trip home, thermostat offline (video)" with replay times through arrival,
  and human-readable labels with exact payload fields still checkable via
  "fields sent".
- Evaluation: 12 builder-labeled cases across combined vs single-source
  conditions with offline results (combined 12/12 fully correct; thermostat
  only 7/12; room sensor only 3/12; electrical and calendar only 2/12 each),
  plus the 24 operator-run live calls documented in `docs/evaluation.md`. Readiness
  agreement in the live run is enforced by the validator, so it shows the
  models followed the contract, not independent readiness judgment; one run
  per case, small synthetic sample.

Known limits:

- All data is synthetic and every message, scene, visit and report is
  simulated; there are no real channels and ARIA Home controls no equipment.
  Email, location, scene, confirmation, and service-visit shots have no
  dedicated UI and are filmed from the Simulated timeline cards (section B).
- There is no labelled blower-channel card; power claims stay at the
  "Power context" statement and its limitations (shot 7 is partial).
- Room-sensor and blower mappings are synthetic assumptions, not measured
  physical behaviour.
- The notification allowlists are reviewed by hand, not by an external
  privacy review; the HVAC request is gated only by a synthetic manager
  authorization event.
- The committed live results used the pre-Day-7 readiness labels; Day 7
  added `arrival_passed` with target-at-arrival, which the live run did not
  exercise. A live filming take is therefore unverified in its current form
  (section H).
- Claims stay bounded to the monitored temperature goal: verified recovery
  of that goal, never a proven repair cause or fault-free equipment.

## E. Acceptance criteria

Checked on the replayed `demo_video_v1` scenario before filming; the
browser checks in `frontend/e2e/app.spec.ts` cover the on-screen items.

1. No fresh thermostat measurements while offline: during the outage
   interval, no evaluation shows a thermostat reading newer than 15:30 as
   current, and the Outcome at 16:31 reads "Thermostat telemetry missing".
2. Independent room sensors carry the trend: the no-warming statement at
   16:31 and the warming statement at 18:51 cite independent room readings,
   with the thermostat absent or stale — never cached thermostat values.
3. Electrical activity is not proof of useful heat: the power statement
   keeps the bounded continuity wording and limitations; no UI or narration
   text claims useful heat, a fault, or equipment power from circuit watts.
4. Reconnection without warming cannot resolve: the 18:21 evaluation shows
   "Thermostat reporting restored" with the issue still open, and 19:51
   still shows "Warming observed", not "Temperature goal verified".
5. Human reports cannot force physical resolution: manager acknowledgement
   ("Acknowledged, not resolved") and the HVAC completion report, replayed
   at any evaluation, change no outcome status; the report only corroborates
   after verification.
6. Sensor verification precedes report availability: the verified
   evaluation (20:21) is strictly before the report's available time
   (20:45); at 20:21 the timeline has no completion-report card, and at
   20:46 it does, labelled "Corroboration only, does not set the outcome".
7. Target met through arrival: "Temperature goal verified" at 20:21 is
   re-checked at arrival; "Arrival expectation met" is evaluated at 21:01,
   not assumed from 20:21.
8. Every authorization precedes the action it permits: homeowner
   confirmation < preparation authorization < scene acknowledgement;
   manager alert < manager HVAC authorization (16:45) < HVAC request
   (16:50 event, delivered card at 16:52).
9. No future-data leakage: for every replay evaluation, only records,
   revisions, confirmations, events, and notifications available at or
   before that time are shown.
10. No mock/cached output shown as a fresh live model response: any
    investigation on screen is either labeled "MOCK - example answer, not
    live inference", or is a live call made for the recording under
    section H; a rejected or unavailable model answer shows the
    deterministic summary, labeled as computed by code.
11. Language: the words "instantaneously", a proven repair cause, and a
    fault-free-equipment claim appear nowhere in narration, on-screen text,
    or UI captures.

## F. Production and safety rules

- Hard limit 3 minutes (the A storyboard totals exactly 180 s); ARIA is
  my existing personal-assistant project — the name, planning notes and
  product designs for ARIA Home (such as the power-context rules and the
  evidence contract) pre-existed, and all ARIA Home code shown was written
  this week, with Meta's Muse models.
- Label, on screen, at the moment each appears: synthetic data, simulated
  communications, simulated control, and replay time jumps. The existing
  banner ("SYNTHETIC DATA - demo scenario, not a real home") stays visible
  in UI captures.
- Functional claims use real interface footage (the running frontend and
  backend), not mock-ups of screens that do not exist. Simulated actor
  cards (email, messages, scene) are presented as labeled simulations, not
  as the product UI making real calls.
- Inference waits are shortened only with disclosure ("inference wait
  shortened" caption, see section H) or avoided by using pre-computed
  deterministic sections; no mock or cached model output is shown as a
  fresh live response (the UI's MOCK label must remain in frame when mock
  is used).
- No credentials, account pages, real travel details, private code, or
  personal contacts in frame or audio; all names, addresses, flights, and
  contacts are the synthetic fixture ones. No real calls, messages,
  equipment control, or hazardous repair guidance at any point.
- Claims are limited to the monitored temperature goal: verified recovery
  of that goal, not a proven cause, not fault-free equipment, and no
  guarantee beyond the observed readings and interval.

## G. What remains, and decisions already made

What remains (no new features; feature freeze, `docs/freeze.md`):

1. This recording script: film sections A/B following the checklist in
   section H, add the synthetic/simulated/replay-jump labels and the
   edited-wait disclosure, and cut to exactly 180 s.
2. README and submission write-up: setup instructions and status that
   describe the built behaviour above, not a planned-features list.
3. User-test wording fixes only: bug, accessibility, and wording fixes
   found by the user tests (`docs/usability.md`) or the filming
   walk-throughs — labels, readability, human-language rendering of
   reasons, payloads, and events. No new features, evidence sources,
   providers, models, or integrations.

Decided (by the feature freeze, 2026-10-26, commit 4d3bacb; earlier
build decisions as built):

- The video timeline is the built `demo_video_v1` fixture: 21:00 property
  arrival (19:45 landing plus labeled 45-minute airport-exit/baggage and
  30-minute driving allowances), 68 F target, thermostat outage from
  15:30, recovery stages at 18:21 / 18:51 / 20:21 / 21:01.
- The verification progression is the built stage list
  (`telemetry_missing`, `reporting_restored`, `warming_observed`,
  `goal_verified`, `arrival_met`); the goal is verified from maintained
  readings and re-checked at arrival, as section C/E describe.
- The simulated HVAC request carries only the built scoped fields
  (property, access note, manager contact, relevant observations), gated
  by the manager authorization event at 16:45; the HVAC completion report
  is available to ARIA at 20:45, after the 20:21 verification, as
  corroboration only.
- Independent room sensors and the blower-mapped electrical channel are
  synthetic fixture assumptions; email, calendar, GPS, travel estimates,
  service communications, and scene control stay synthetic/simulated by
  design, with no real integrations for this video.
- Notifications are simulated only, with the built per-audience
  allowlists; acknowledgement is "Acknowledged, not resolved" and changes
  no outcome.

The one filming-mode choice left open is mock-with-label versus one live
investigation call; section H gives both, and a live call needs Brad's
approval of that call before filming.

Claims to avoid:

- That she boarded, that a flight/traffic/baggage state is known, or that ARIA Home is a travel platform.
- That command acknowledgement, a manager acknowledgement, or a technician report proves physical success or caused the recovery.
- That electrical activity proves useful heat, a fault, equipment power, or "no outage".
- That recovery was "instantaneous", that the equipment is fault-free, or that the goal is guaranteed beyond the observed readings.
- That any email, call, message, location, or scene control in the video is real.

## H. Filming checklist

Before recording:

- [ ] Fresh database: delete `backend/instance/aria_home.db` so outcome
  and verification history start empty and no earlier replay steps leak
  into the History list.
- [ ] Start the backend and frontend as in the README. For mock takes,
  start the backend with `ARIA_HOME_MODEL_ENABLED=0` so the investigation
  is the labeled mock, and confirm the Investigation section shows
  "MOCK - example answer, not live inference" before recording.
- [ ] Browser window at 1280x720, showing the real running frontend (no
  mock-up screens). Keep the banner "SYNTHETIC DATA - demo scenario, not
  a real home" in frame in every UI capture; no credentials, account
  pages, real travel details, or personal contacts in frame or audio.

Replay sequence for the video scenario (exact order):

- [ ] In "Demo controls (synthetic replay)", set "Scenario" to
  "Trip home, thermostat offline (video)". Selecting it already runs the
  investigation at 16:31; capture the opening Simulated timeline cards
  (email, location, confirmation, scene) in this initial state.
- [ ] Click the replay buttons in this order, capturing the Outcome
  headline (and the panels named in section B) at each step:
  16:31, 16:52, 18:21, 18:51, 19:51, 20:21, 20:46, 21:01.
  Expected headlines: 16:31 "Thermostat telemetry missing";
  18:21 "Thermostat reporting restored"; 18:51 and 19:51
  "Warming observed"; 20:21 "Temperature goal verified";
  21:01 "Arrival expectation met". At 16:52 capture the delivered HVAC
  notification card; at 20:46 capture the "HVAC completion report" card
  ("Corroboration only, does not set the outcome"), which must be absent
  at 20:21.
- [ ] The MOCK label must be in frame whenever a mock investigation is on
  screen: the "MOCK - example answer, not live inference" line in the
  Investigation section and, on notification/timeline captures that
  include the Investigation section, it stays visible and unedited. Mock
  or cached output is never presented as a fresh live response.

How a live take differs:

- [ ] A live take uses exactly one live investigation call, made for the
  recording. It needs Brad's approval of that call before filming; without
  that approval, film the mock take.
- [ ] Film the call's real wait in full or disclose the edit on screen
  (below); do not substitute a pre-computed or cached answer. If the model
  answer is rejected or unavailable, show the deterministic summary
  ("Deterministic summary (computed by code)" / "ARIA's explanation is
  unavailable") as rendered, and say so in the narration.
- [ ] The live take is identified as live by the on-screen "Provider
  mode:" / model provenance line in the Investigation section; the
  committed live evaluation used pre-Day-7 readiness labels, so the live
  behaviour in its current form is unverified (section D).

Disclosure and labels during the edit:

- [ ] Any shortened wait (inference wait, replay loading, or page load)
  is disclosed on screen with the caption "inference wait shortened" (or
  the equivalent wait-shortened caption for non-inference waits) for as
  long as the shortened segment is on screen.
- [ ] Label, on screen at the moment each appears: synthetic data,
  simulated communications (every notification card already reads
  "Simulated, no message was sent"; timeline cards read "SIMULATED"),
  simulated control, and replay time jumps between the section H replay
  buttons.
- [ ] Final cut is exactly 180 s, follows the section A storyboard, and
  contains none of the section G claims to avoid.

Recording footage:

- Run `cd frontend && npm run record:demo`. This uses
  `frontend/playwright.record.config.ts` and `frontend/recording/demo.record.ts`
  to drive the real running frontend and backend at 1280x720, in mock mode
  (`ARIA_HOME_MODEL_ENABLED=0`) on a fresh database under the OS temp dir,
  so the "MOCK - example answer, not live inference" label is in frame
  whenever the Investigation is in frame.
- Clips land in `frontend/recordings/` (ignored by git), one `.webm` per
  storyboard segment: `s1-trip-cards`, `s2-not-responding`,
  `s3-authorized-help`, `s4-recovery`, and `s5-report-and-arrival`.
- The same command also records three title-card clips from
  `frontend/cards.html`: `c1-opening`, `c2-evaluation`, and
  `c3-closing`. These are title cards, not product UI: the opening and
  closing cards carry the section A disclosure / closing lines, and the
  evaluation card shows the offline totals read at runtime from
  `backend/eval/results-offline.json` via `GET /api/evaluation/offline`.
- The footage of the five `s*` segments is the real UI; the front-door /
  warm-room door shots are not product UI and are not recorded by this
  command.
