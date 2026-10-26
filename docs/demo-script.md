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
personal-assistant project. Before this event I had the name, planning
notes and product designs for ARIA Home, such as the power-context rules
and the evidence contract. All of the ARIA Home code you will see was
written this week, with Meta's Muse models."

Storyboard: exactly 180 seconds. Voiceover total: 380 words at about
127 words per minute.

| Time | Hook / screen action | Narration (word count) | On-screen text |
|---|---|---|---|
| 0:00–0:15 (15 s) | Cold open: a front door, a cold house, a phone with a generic "automation completed" style tick. Cut to the ARIA Home page. | "ARIA is my existing personal-assistant project. Before this event I had the name, planning notes and product designs for ARIA Home, such as the power-context rules and the evidence contract. All of the ARIA Home code you will see was written this week, with Meta's Muse models." (47) | "A returning homeowner wants one thing: a warm home, without chasing anyone to get it." / "An automation starting is not an expectation met." / "Synthetic demo data" |
| 0:15–0:40 (25 s) | Simulated inbox/calendar cards (clearly labeled synthetic/simulated) propose the return; a simulated airport location chip appears; the confirmation questions appear one by one. | "A synthetic flight confirmation and calendar entry propose her return. A consented, simulated location event places her at the departure airport — supporting the plan, not proving boarding. ARIA asks her to confirm property, arrival, sixty-eight degrees, and manager coordination. Allowances are labeled estimates, never live travel claims." (48) | "Synthetic email + calendar — proposal, not proof of boarding" / "Simulated location" / "Confirm: property · arrival · 68 °F · manager coordination" |
| 0:40–1:05 (25 s) | She taps authorize (simulated scene card); an "acknowledged" chip appears, physically separate from a greyed "physical success: unknown" chip. Clock jumps, labeled as a replay time jump; the house stays cold on the evidence cards. | "She authorizes the arrival-preparation plan. The scene is simulated and labeled; acknowledgement is recorded separately from physical success. While she flies, ARIA monitors quietly. Missing phone location is unavailable, never proof of schedule — and authorized urgent escalation is never suppressed. The command ran; that is not the outcome." (49) | "Simulated scene — acknowledgement ≠ physical success" / "Replay time jump" / "Location: unavailable" |
| 1:05–1:30 (25 s) | The Investigation view: thermostat card stale/missing, independent room readings flat, the mapped electrical channel active, other circuits fresh. The model's words stay inside the verified-facts / interpretation split. | "ARIA states only what evidence supports: thermostat telemetry is missing or stale. Independent room sensors show no warming. A mapped electrical channel shows blower-consistent activity, but proves neither useful heat nor the fault. Other circuits are fresh, weighing against property-wide loss — without ruling out partial or earlier outages." (49) | "Thermostat telemetry: missing/stale" / "Electrical activity ≠ useful heat" / "No invented failure mechanism" |
| 1:30–1:55 (25 s) | Simulated message cards only: ARIA → manager, manager's explicit "contact HVAC" authorization, then the scoped simulated HVAC request with itinerary/email/location visibly absent. | "Within her authorization, ARIA alerts the property manager, who explicitly authorizes contacting the HVAC company on file. The simulated request carries only approved property, contact and access details, plus relevant observations — never itinerary, email or location. ARIA controls no equipment. No real call or message is sent." (48) | "Simulated messages" / "Manager authorization required" / "Shared: property, access, observations only" |
| 1:55–2:35 (40 s) | The central moment, given the longest segment. Replay clock advances step by step: thermostat telemetry resumes ("reporting restored", issue still open), cross-check panel (reported state, mapped electrical, independent rooms), then warming, then the maintained goal. | "The technician repairs it — but ARIA does not wait for the report. On the next sensor update, fresh thermostat telemetry resumes; reconnection alone does not close the issue. ARIA cross-checks reported operating state, mapped electrical activity, and independent room readings. Later readings show warming, then the goal reached and maintained through verification, still met at arrival: reporting restored, warming observed, temperature goal verified, arrival expectation met. Each reading counts only after it arrives." (74) | "Thermostat reporting restored → Warming observed → Temperature goal verified → Arrival expectation met" / "Reconnection alone does not verify recovery" |
| 2:35–3:00 (25 s) | The HVAC completion report card appears only now, timestamped after verification; she lands, reads one concise evidence-backed update, opens the door to a warm room. | "Only after sensor verification does the HVAC completion report reach the manager and become available to ARIA; it can corroborate, never create, the verified outcome. She lands to a concise, evidence-backed update, and arrives to the warm home. Not just an automation completed. An expectation met. ARIA Home connects the plan, coordinates the response, and verifies the result, so coming home feels like coming home." (65) | "Report available after verification — corroboration only" / "Not just an automation completed. An expectation met." |

Precise-language rules for every segment: say "we verified recovery of the
monitored temperature goal", never that a repair was proven to cause it, that
the equipment is fault-free, or that anything happened "instantaneously" —
say "on the next sensor update". Missing phone location is "unavailable",
never evidence about her schedule. An arrival window may include clearly
labeled driving and airport-exit/baggage allowances; no claim of real
traffic, flight status, or baggage tracking. ARIA Home is not a travel
platform.

## B. Shot list

| # | Viewer sees | Must actually work | Status | Content type | Acceptance check |
|---|---|---|---|---|---|
| 1 | ARIA Home page loads with the synthetic-data banner, Investigation section, verified facts vs interpretation, code-computed readiness | Backend investigation (`investigator.py` inv-v2 claim binding, code-rendered `verified_facts`, deterministic readiness in `readiness.py`) served to `frontend/src/App.tsx` | implemented (mock); unverified (live, see D) | replayed + live inference or labeled mock | Mock run shows the "MOCK - example answer, not live inference" label; a live run, if used, is identified as live with provider/model in the provenance line |
| 2 | Synthetic flight-confirmation email and matching calendar entry propose the itinerary | Email/calendar ingestion that produces a *proposal* | missing — only a static calendar fixture (`calendar.json`: trip + confirmation) is loaded by `scenario.py`; no email source exists (`SourceKind` is calendar/thermostat/electrical/weather only) | synthetic | Proposal appears only after both records' available times; narration never claims boarding |
| 3 | Consented simulated location event at the departure airport; later, location "unavailable" during the flight | Location event type, consent state, unavailable state | missing — no location source, event, or consent record in contracts or fixtures | simulated | "Unavailable" is shown with no inference drawn from it |
| 4 | Confirmation dialogue: property, arrival plan, desired temperature, permission to coordinate with the property manager | Interactive confirmation that gates readiness | partial — `HomeownerConfirmation` (target, `notify_homeowner`, `manager_authorized`, `confirmed_at`, revision binding) and `context_as_of` as-of visibility exist, but as a static fixture; there is no dialogue, no granular permission capture, and no arrival-plan (landing + allowances) model | synthetic | Readiness is `cannot_tell` before `confirmed_at` and uses only the confirmed revision (`context_as_of`, `readiness.py` flags) |
| 5 | Authorized arrival-preparation plan; simulated scene/command; acknowledgement recorded separately from physical success | Scene command + acknowledgement records; no equipment operation | missing — README ground rule "No physical control" holds in code: no command, scene, or acknowledgement path exists | simulated | Acknowledgement chip never flips any physical/outcome state; only later sensor readings do |
| 6 | Not responding: thermostat telemetry missing/stale while thermostat-independent room readings show no warming | An offline-thermostat interval plus an independent room sensor carrying the trend | missing — every `indoor_temp` record in all fixtures has source `thermostat`, subject `demo-cabin/main`; `temperature_trend` filters `source == thermostat`; `demo_v1` has the thermostat *reporting* "heating" with the furnace circuit quiet (5/0/3 W), which is a different physical story from offline + blower running | synthetic / replayed | During the offline interval no fresh thermostat measurement is shown as current; cached values are never presented as current; the no-warming claim cites independent room readings only |
| 7 | Mapped HVAC electrical channel active (blower-consistent), other circuits fresh, power statement with limitations | `power_context.py`: confirmed furnace binding, per-circuit fresh/stale status, continuity statement, limitations, banned phrases | partial — the machinery is implemented for a *furnace* circuit and other-circuit continuity, but no fixture has a blower channel or blower-level activity during a thermostat outage, and `demo_v1`'s mapped furnace channel is quiet | replayed | Statement weighs only against property-wide loss in the observed interval, carries the documented limitations, and never claims useful heat or a fault |
| 8 | ARIA alerts the property manager within her authorization; manager explicitly authorizes HVAC contact; scoped simulated request (no itinerary/email/location) | Notification records with authorization gates and a scoped payload | missing — `NotificationState` exists in `contracts.py` but nothing creates, sends, or scopes a notification; no manager/HVAC actors, contact, or authorization event exist | simulated | No simulated alert is timestamped before the homeowner authorization it relies on; no HVAC request before the manager's explicit authorization; the request payload shown contains no itinerary, email, or location field |
| 9 | Simulated service visit and repair | Visit/repair events | missing as events — the closest record is `demo_recovery_v1`'s calendar `manager_report` "Reset the furnace switch" at 18:10 (a manager report, before warming), not a technician visit | simulated | Visit/repair cards are labeled simulated and change no outcome by themselves |
| 10 | Independent recovery detection: on the next sensor update telemetry resumes → cross-source check → warming → goal reached and maintained → still met at arrival | Reconnection detection, cross-source verification (reported state + electrical + independent rooms), a maintained-for period, and an arrival check | partial — `outcomes.py` uses only later `indoor_temp` readings in one zone (`observed_at > created_at`, `received_at <= now`): `warming_observed` (≥3 samples, ≥2.0 °F rise) and `target_reached` (last 2 readings ≥ target) exist; there is no reconnection status, no cross-source check, no maintained duration (last-2-readings only), and no arrival evaluation. Frontend outcome labels and the 18:00/18:30/19:00/20:31 replay buttons exist for three scenarios | replayed | Reconnection with flat independent readings stays unresolved; `target_reached` requires the maintained period in C and is re-checked at arrival |
| 11 | HVAC completion report reaches the manager after sensor verification and becomes available to ARIA only afterward | A report record whose *available* time is after the sensor-verified evaluation time | missing — no HVAC report type exists; `demo_recovery_v1`'s manager report (18:10, available 18:10:30) precedes the warming readings, the opposite ordering; `outcomes.py` only adds the note that a change after a reported action does not prove cause | synthetic | At every replay evaluation before the report's available time, the report is absent from the evidence pack and from any model context |
| 12 | Ending: concise evidence-backed post-landing update; warm home at arrival | A homeowner-facing summary generated from the verified outcome | missing — the UI shows Investigation + Outcome + source cards only; no post-landing summary view | replayed | The summary cites the same readings and evaluation times as the outcome history; it claims goal recovery, not a proven cause or fault-free equipment |

## C. Scenario timeline

Proposed synthetic replay for a new `demo_video_v1` fixture. All dates are
2026-01-16, America/New_York (-05:00), and are scenario assumptions for the
video — invented times, not validated physical behaviour. Temperature target
68 °F and the sensor cadences reuse the existing fixtures. Thresholds reused
from documented code, and labeled as such: freshness/staleness
(`evidence.py`: stale after 2× cadence; `readiness.py` `STALE_READING_AGE_S`
3600 s, `MIN_SAMPLES` 3, `MIN_COVERAGE` 0.5), follow-up warming
(`outcomes.py` `FollowUp`: `min_samples` 3, `min_rise_f` 2.0 °F), scheduling
(`scheduling.py`: next check ≥15 min, ≤24 h, deadline = arrival + 2 h grace).
New assumptions, not in today's code: the 30-minute maintained-goal
verification period (today `target_reached` needs only the last 2 readings
≥ target), the airport-exit/baggage (45 min) and driving (30 min) allowances,
and every actor/communication event below.

"Received/available" is when ARIA may first use the item (`received_at` for
records, `known_at`/`confirmed_at` for trip context); "evaluation" is a
replay evaluation time (`at`) at or after that. An item never appears at an
evaluation earlier than its received/available time.

| # | Event | Event time | Received / available | Evaluation |
|---|---|---|---|---|
| 1 | Synthetic flight-confirmation email proposes the return (landing 19:45) | 09:00 | 09:02 | 09:05 (proposal shown) |
| 2 | Matching synthetic calendar entry for the trip | 09:03 | 09:03 | 09:05 |
| 3 | Consented, simulated location event: at departure airport | 09:10 | 09:11 | 09:15 (supports the plan only) |
| 4 | ARIA asks her to confirm property, arrival plan, temperature, manager coordination | 09:15 | 09:15 | 09:15 |
| 5 | Homeowner confirmation: property, property arrival 21:00 (= 19:45 landing + 45 min labeled airport-exit/baggage allowance + 30 min labeled driving allowance), 68 °F, manager coordination permitted | 09:20 | 09:20 (`confirmed_at`) | 09:20 (readiness stops being `cannot_tell` for "unconfirmed") |
| 6 | Homeowner authorizes the arrival-preparation plan | 14:00 | 14:00 | 14:00 |
| 7 | Simulated scene/command sent; command acknowledgement recorded (physical success unknown) | command 14:05 | acknowledgement 14:06 | 14:06 (acknowledgement only) |
| 8 | Quiet monitoring during the flight; phone location becomes unavailable (no schedule inference); no urgent condition yet | from 14:10 | — | each scheduled poll |
| 9 | Last fresh thermostat telemetry; independent room sensors continue on cadence | 15:30 | 15:30:20 | 15:31 |
| 10 | Thermostat outage interval: no fresh thermostat telemetry; independent room readings flat (no warming); mapped blower channel shows electrical activity; other circuits fresh | 15:30–16:31 | as each reading arrives | 16:31 (age > 3600 s: telemetry stated missing/stale; no mechanism invented) |
| 11 | Investigation at the outage: readiness cannot be on track; ARIA states only the bounded claims of story step 3 | — | — | 16:31 |
| 12 | ARIA alerts the property manager (simulated), inside the 09:20 authorization | 16:35 | manager receipt (simulated) 16:37 | 16:37 |
| 13 | Manager explicitly authorizes contacting the HVAC company on file (simulated) | 16:45 | 16:45 | 16:45 (no HVAC contact before this) |
| 14 | Scoped simulated HVAC request: approved property/contact/access info + relevant observations only | 16:50 | HVAC receipt (simulated) 16:52 | 16:52 |
| 15 | Simulated service visit and repair | 17:30–18:15 | visit logged 18:15 | not used by ARIA to close anything |
| 16 | Thermostat reconnection: fresh thermostat telemetry resumes on the next sensor update | 18:20 | 18:20:20 | 18:21 → "Thermostat reporting restored"; reconnection triggers cross-source verification and does not close the issue |
| 17 | Cross-source check: reported operating state + mapped electrical activity + independent room readings agree the system is running; independent rooms still near-flat | 18:20–18:35 | as readings arrive | 18:36 (issue still open) |
| 18 | Warming evidence: ≥3 later independent readings, rise ≥2.0 °F (reused `min_samples`/`min_rise_f`) | 18:35–18:50 | as readings arrive | 18:51 → "Warming observed" |
| 19 | Target first reached on independent readings (68 °F) | 19:50 | 19:50:20 | 19:51 (not yet verified) |
| 20 | Target maintained for the proposed 30-minute verification period (readings at/above 68 °F through 20:20) | 19:50–20:20 | as readings arrive | 20:21 → "Temperature goal verified" |
| 21 | HVAC completion report reaches the property manager (simulated), then becomes available to ARIA | report 20:40 | manager 20:42; available to ARIA 20:45 | 20:46 (corroboration only; cannot set or change the verified outcome) |
| 22 | Still at/above goal on landing update | 19:45 landing; reading 20:50 | 20:50:20 | 20:51 (concise update she reads after landing) |
| 23 | Homeowner property arrival; goal still met | 21:00 | 21:00 | 21:01 → "Arrival expectation met" |

Note the deliberate break from the current fixtures: in `demo_v1` /
`demo_recovery_v1` the planned arrival is 18:00, the follow-up deadline is
therefore 20:00 (`arrival + 2 h`), and `demo_recovery_v1` first reaches
68.2 °F at 20:15 — after both arrival and deadline — while its manager report
is available at 18:10:30, before any warming. The current fixtures cannot
show "verified before arrival" or "report after verification"; C above is
the timeline the video needs, not a description of `demo_recovery_v1`.

## D. Implementation gap map against the current repo

### Reusable working capabilities

- As-of evidence discipline: `EvidenceRecord` carries `observed_at` /
  `received_at`; `visible_records` admits only `received_at <= now`;
  `context_as_of` admits trip revisions only from `known_at` and a
  confirmation only from `confirmed_at` while it still matches property,
  trip, and revision (with cancelled / revised / outdated variants already
  fixtured in `demo_cancelled_v1` / `demo_revised_v1`). This is the
  no-future-leakage backbone for shots 4, 10, 11.
- Freshness: `freshness` marks missing values and readings older than
  2× cadence stale; `source_status` reports missing/stale/conflicting per
  source; readiness adds the 3600 s stale-age rule. Cached values are never
  promoted to current by these functions.
- Deterministic metrics and readiness: `temperature_trend`, `target_gap`,
  `circuit_activity` ("electrical activity only; not proof of useful heat",
  15 W noise floor), and `compute_readiness` with the thresholds documented
  in `docs/readiness-rules.md`. The model cannot change the readiness status
  (`validate` rejects a mismatch).
- Power context: mapped-circuit binding status (confirmed / candidate /
  unknown), per-circuit fresh activity, the exact bounded continuity
  statement, mandatory limitations, and banned phrases ("power is normal",
  "the furnace has power", …) — the language guardrails for shot 7.
- Investigation: inv-v2 claim binding (each model fact bound to one evidence
  field, values checked against the pack, `verified_facts` rendered by
  code), number/direction checks on prose, certainty-phrase bans, prompt
  rules against equipment control and repair guidance, deterministic
  fallback summary, and provider/mock provenance shown in the UI.
- Follow-up outcomes: `evaluate_outcome` counts only readings with
  `observed_at > created_at` and `received_at <= now`; statuses
  `awaiting_measurement`, `warming_observed`, `target_reached`,
  `not_observed_by_deadline`, `unable_to_verify`; a human statement can only
  trigger the note "An observed change after a reported action does not
  prove what caused it", never a status. Scheduling is code-computed
  (15 min–24 h window, arrival + 2 h deadline); SQLite persistence
  (`store.py`, short-lived connection per operation) with `outcome_events`
  history survives restarts; `POST /api/investigations` and
  `GET /api/follow-ups/<id>` are wired to the frontend replay buttons.
- Frontend replay: scenario selector (demo_v1 / demo_recovery_v1 /
  demo_no_followup_v1), replay-time buttons, outcome history list, source
  cards with missing-reading counts, synthetic banner, mock label.
- Provider: mock provider plus gated live Meta provider; only Meta models
  are called at runtime; the Day 3 live runs (inv-v1) passed validation
  4/4 in a small sample.

### Small changes (no new subsystem)

- A `demo_video_v1` fixture implementing C: offline-thermostat interval,
  continued independent readings during it, a recovery ramp that reaches
  68 °F and holds it before a later planned arrival, and a report record
  whose available time is after verification.
- Frontend: add the video scenario to the selector, extend the replay-time
  list through arrival, and map outcome states to the four progression
  labels ("Thermostat reporting restored" is a new label for an existing
  freshness transition; the other three map to outcome/readiness states).
- Display the three clocks (event / received / evaluation) next to replay
  steps, reusing timestamps already in the API payloads.
- Reword the `demo_recovery_v1` selector label if it stays in shot: today it
  says "Manager visit, heat restored", but the fixture's report is a manager
  statement and its recovery reaches target after the 18:00 arrival.

### Missing capabilities

- Travel inputs: no email source, no calendar-to-proposal flow, no location
  events or consent, no landing/allowance arrival-plan computation.
- Confirmation UX and granular permissions: the confirmation is a static
  fixture with two booleans; there is no asking, no per-action permission
  (alert manager vs contact HVAC are not separate grants), no revocation.
- Scene/command layer: no simulated command, no acknowledgement record, no
  separation of acknowledgement from physical success.
- Independent room sensors: no second temperature source or zone. This is
  load-bearing for the story: `temperature_trend` reads only the thermostat
  source, and readiness goes `cannot_tell` on a stale thermostat because
  there is nothing independent to carry the trend.
- The story's physical truth: no fixture has "thermostat offline + blower
  running without useful heat". `demo_v1` is thermostat-reporting +
  furnace-circuit-quiet; `demo_recovery_v1` keeps the thermostat reporting
  throughout and restores a quiet-then-910 W furnace circuit.
- Coordination workflow: no notifications, manager actor, HVAC-contact
  authorization event, scoped-payload enforcement (itinerary/email/location
  exclusion), simulated message transport, visit, or repair events.
- Cross-source verification: outcomes look at one zone's `indoor_temp`
  only. Nothing checks reported operating state, mapped electrical
  activity, and independent readings together; no reconnection detector or
  "reporting restored" state; no maintained-for verification period (last
  2 readings suffice today); no still-met-at-arrival evaluation.
- Delayed report availability: no HVAC completion report, and no rule that
  a manager acknowledgement or technician report cannot set the outcome —
  today that holds only by absence (outcomes ignore statements) plus the
  causation note.

### Risks and unresolved decisions

- Current outcome logic, unmodified, would certify the wrong story:
  `target_reached` ignores the deadline and freshness (in
  `demo_recovery_v1` it fires at 20:31 replay on readings that reached
  target after the 18:00 arrival and after the 20:00 deadline), counts any
  `indoor_temp` record in the zone regardless of source or kind, and does
  not deduplicate. Filming it as "verified before arrival" would be false.
- Live inference is unverified under inv-v2: the Day 3 live results were
  produced under inv-v1 and have not been repeated (see
  `docs/day3-handoff.md`, "Verification repair"). Live latencies were
  22.7–23.5 s (muse-spark-1.3) per call; the browser test also had one
  unexplained cold-start failure in four runs. Neither may be papered over
  in the edit.
- "Maintained" is undefined in code: duration, cadence, allowed dips below
  target, and behaviour when readings stop mid-window all need a decision
  (C assumes 30 min, no dips).
- Independent-sensor semantics are undefined: source kind, zone mapping,
  disagreement with a reconnected thermostat, and which source carries the
  verified claim.
- The blower channel needs a mapping decision: the electrical binding model
  maps a circuit to equipment with a confirmation status; "activity
  consistent with the blower" must stay at that strength unless the fixture
  mapping supports more.
- Scope-of-sharing list (which property/contact/access fields the HVAC
  request may carry) and the report's exact availability rule (manager
  receipt vs ARIA ingestion) need Brad's sign-off before filming the cards.
- README's planned items still list scoped notifications and follow-up
  outcomes as "Day 3 onward"; outcomes have since landed, so narration must
  describe behaviour, not the README's status list.

### Minimum demo build vs optional real integrations

Minimum demo build (section G): the C fixture, an independent room-sensor
record stream, deterministic reconnection + cross-source + maintained +
arrival checks, labeled simulated actor cards (email, location, scene,
messages, visit, report) driven by the existing as-of visibility, and the
frontend progression/replay through arrival. Optional real integrations:
none for this video. Email, calendar, GPS, travel estimates, service
communications, and scene control stay synthetic/simulated by design; real
integrations are out of scope and must not be proposed as part of filming.

## E. Acceptance criteria

Each criterion is checked on the replayed scenario, at the stated evaluation
time, before filming:

1. No fresh thermostat measurements while offline: during the C outage
   interval, no evaluation shows a thermostat `indoor_temp` newer than
   15:30 as current, and source status reads missing/stale.
2. Independent room sensors carry the trend: the no-warming statement at
   16:31 and the warming statement at 18:51 cite independent room readings,
   with the thermostat absent or stale — never cached thermostat values.
3. Electrical activity is not proof of useful heat: the power statement
   keeps the bounded continuity wording and limitations; no UI or narration
   text claims useful heat, a fault, or equipment power from circuit watts.
4. Reconnection without warming cannot resolve: an evaluation right after
   18:21 shows "Thermostat reporting restored" with the issue still open; a
   variant replay with reconnection but flat independent readings never
   reaches "Temperature goal verified".
5. Missing/stale follow-up readings give `unable_to_verify`: replaying the
   no-follow-up shape (as in `demo_no_followup_v1`) past the deadline gives
   `unable_to_verify`, distinct from `not_observed_by_deadline` when enough
   flat readings exist.
6. Human reports cannot force physical resolution: manager acknowledgement
   and the HVAC completion report, replayed at any evaluation, change no
   outcome status; at most the report corroborates after verification and
   triggers the does-not-prove-cause note.
7. Sensor verification precedes report availability: the verified evaluation
   (20:21) is strictly before the report's available time (20:45), and no
   earlier evidence pack or model context contains the report.
8. Target met through arrival: readings at/above 68 °F span the 30-minute
   verification period and the 20:50 and 21:00 readings; "Arrival
   expectation met" is evaluated at 21:01, not assumed from 20:21.
9. Every authorization precedes the action it permits: homeowner
   confirmation (09:20) < preparation authorization (14:00) < scene
   acknowledgement (14:06); homeowner manager permission (09:20) < manager
   alert (16:35) < manager HVAC authorization (16:45) < HVAC request
   (16:50), all by event and available times.
10. No future-data leakage: for every replay evaluation, the evidence pack
    contains only records with `received_at <= at`, trip revisions with
    `known_at <= at`, and confirmations with `confirmed_at <= at`
    (the existing `visible_records` / `context_as_of` rules), including the
    future-dated fixture records already present in `demo_v1`.
11. No mock/cached output shown as a fresh live model response: any
    investigation on screen is either labeled MOCK, or is a live call made
    for the recording with its wait disclosed (section F); a rejected or
    unavailable model answer shows the deterministic summary, labeled as
    computed by code.
12. Language: the words "instantaneously", a proven repair cause, and a
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
  shortened" caption) or avoided by using pre-computed deterministic
  sections; no mock or cached model output is shown as a fresh live
  response (the UI's MOCK label must remain in frame when mock is used).
- No credentials, account pages, real travel details, private code, or
  personal contacts in frame or audio; all names, addresses, flights, and
  contacts are the synthetic fixture ones. No real calls, messages,
  equipment control, or hazardous repair guidance at any point.
- Claims are limited to the monitored temperature goal: verified recovery of
  that goal, not a proven cause, not fault-free equipment, and no
  guarantee beyond the observed readings and interval.

## G. The smallest build sequence to film it, decisions that need Brad, and claims to avoid

Smallest build sequence:

1. Freeze the C timeline, the maintained-period rule, and the sharing scope (decisions below).
2. Add the `demo_video_v1` fixture: offline thermostat, independent room stream, blower-mapped electrical channel, recovery ramp reaching and holding 68 °F before a 21:00 arrival, report available only after verification.
3. Add deterministic checks reusing `outcomes.py` / `readiness.py` patterns: reconnection ("reporting restored"), cross-source agreement, maintained-for-30-minutes verification, still-met-at-arrival.
4. Add labeled simulated actor cards (email, location, scene acknowledgement, manager/HVAC messages, visit, report) gated by the existing as-of visibility — no real integrations.
5. Frontend: video scenario in the selector, replay times through 21:01, the four progression labels, event/received/evaluation timestamps.
6. Run the E acceptance checks as replay tests, then film the real UI; use mock only with its label in frame, or one disclosed live call.
7. Record the A voiceover (380 words), add synthetic/simulated/replay-jump labels and the inference-wait disclosure, and cut to exactly 180 s.

Decisions that need Brad:

- The 30-minute maintained period (and no-dips rule) — new assumption, not today's last-2-readings rule.
- The proposed 21:00 arrival with labeled 45-minute airport-exit/baggage and 30-minute driving allowances, replacing the fixtures' 18:00 arrival for the video scenario.
- The exact property/contact/access fields the simulated HVAC request may carry, and that the report becomes available to ARIA only after verification (20:45 in C).
- Independent room sensor definition (source, placement/zone) and the blower channel's fixture mapping strength.
- Mock-with-label versus a fresh live call for the filmed investigation, given inv-v2 live behaviour is unverified and Day 3 latencies were ~23 s.

Claims to avoid:

- That she boarded, that a flight/traffic/baggage state is known, or that ARIA Home is a travel platform.
- That command acknowledgement, a manager acknowledgement, or a technician report proves physical success or caused the recovery.
- That electrical activity proves useful heat, a fault, equipment power, or "no outage".
- That recovery was "instantaneous", that the equipment is fault-free, or that the goal is guaranteed beyond the observed readings.
- That any email, call, message, location, or scene control in the video is real.
