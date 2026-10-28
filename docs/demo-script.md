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

## A3. Story cut, three layers (canonical, 2026-10-27)

This section supersedes A2 and A wherever they conflict. It is a production plan, not a statement
that every shot works: each segment carries its implementation status, judged from the code at
commit 6a659ca. Three layers:

1. **AI-generated dramatization** of one woman travelling home (labelled "AI-generated dramatization"). Story scenes and music: Meta AI.
2. **Real ARIA Home interface recordings** on the synthetic `demo_video_v1` scenario (labelled
   "ARIA Home — synthetic scenario"). Every functional claim rests on this layer, never on layer 1.
3. **Narration in ARIA's voice**: Kokoro-82M, voice `af_bella` (Apache-2.0 licensed open-weight model),
   labelled "Narration — synthetic voice". A production tool only; the app never calls it.

**Continuity rule.** She never arrives at a cold house. The cold house appears only as a remote
cutaway while she is in transit; her first arrival is the ending, after the goal is verified.

**Non-negotiable event order** (scenario times, 2026-01-16, -05:00, from `demo_video_v1`):
thermostat reporting restored (18:20 observed, 18:21 evaluated) → independent room readings show
warming (18:51) → target first reached (19:50, not yet verified at 19:51) → target held 30 min and
verified (20:21) → HVAC completion report available to ARIA (20:45, corroboration only) → target
still met at arrival (21:00, evaluated 21:01). The report never sets or overrides the outcome. The
sensor evidence establishes the monitored temperature goal only, not equipment reliability or which
repair caused recovery.

**Layouts.** Full story (emotion, transitions); split screen (story left 45%, real UI right 55% at
readable size, never a small inset); full UI (the decisive verification timeline). Generated phone
screens stay blank or indistinct; real recordings are composited in the edit.

**Labels.** "AI-generated dramatization"; "ARIA Home — synthetic scenario"; "Simulated preparation
command"; "Simulated service contact"; "Scenario replay advanced" on every physical-time jump;
"Processing time shortened" if an inference wait is edited; inference mode stated separately from
data mode ("synthetic sensor data — mock inference" or "— live Meta inference"); never present mock
or cached inference as a fresh live response.

### A3.1 Storyboard (exactly 180 s)

Status key as at the top of this file. Times are video times.

| # | Time (s) | Purpose | Dramatized visual | Real UI required | Layout | On-screen labels | Transition | Status / acceptance check |
|---|---|---|---|---|---|---|---|---|
| 0 | 0:00-0:10 (10) | Disclosure | none (title card c1) | c1 opening card | full card | "Synthetic demo data" | fade in | implemented (c1). Check: wording matches README pre-existing vs built. |
| 1 | 0:10-0:24 (14) | A plan exists | Shot 1 hotel phone check | Simulated timeline: "Flight confirmation email", calendar trip (09:20) | split | AI-generated dramatization; ARIA Home — synthetic scenario; "Proposal, not proof of boarding" | cut | implemented (cards). Check: cards show SIMULATED and available times. |
| 2 | 0:24-0:42 (18) | She confirms and authorizes | Shot 2 departure airport | Confirmed plan and permissions: property, arrival 9:00 PM, 68 °F, manager coordination allowed, confirmed 9:20 AM; "Airport location (simulated)" card | split | "Simulated location" | match cut on phone | **partial**: confirmation exists as fixture data and a "Confirmation request" card; no screen shows the confirmed fields and permissions together. Gap G1. |
| 3 | 0:42-0:56 (14) | Preparation starts quietly | Shot 3 takeoff / window | "Preparation authorized", "Scene command", "Scene acknowledged — Acknowledged, physical success unknown"; "Location unavailable" | split | "Simulated preparation command"; "Acknowledgement is not proof of warming" | dissolve | implemented (timeline cards). Check: no card claims warming. |
| 4 | 0:56-1:20 (24) | The home is not responding | Shot 4 cold house cutaway (4 s full story, then split) | 16:31: Outcome "Thermostat telemetry missing"; Readiness "At risk"; verified facts "Indoor temperature 52.0 F (at 16:30)" from the room sensor; Power context with limitations | full story → split | "Remote cutaway — she is still travelling"; "Scenario replay advanced" | slow push-in | implemented (D9-6 fix, 97aa0ee). Check: no thermostat value presented as current; no useful-heat claim. |
| 5 | 1:20-1:36 (16) | Authorized help | Shot 5 property manager on a call | 16:52: Property manager card; HVAC company card with "fields sent:" (property_label, access_note, manager_contact_label, relevant_observations); "Acknowledged, not resolved" | split | "Simulated service contact"; "Approved fields only" | cut | implemented (D5). Check: no itinerary/email/location field; HVAC card absent or refused before 16:45. |
| 6 | 1:36-1:46 (10) | A professional visit | Shot 6 technician arrives and works | none (story only) | full story | "AI-generated dramatization"; "Simulated service visit" | cut | n/a (dramatization). Check: no repair instructions, no implication ARIA controls equipment. |
| 7 | 1:46-2:04 (18) | Recovery detected independently | Shot 7 technician packs up (2 s), then UI | 18:21 "Thermostat reporting restored" with progression 1 Reached, 2-4 Not reached (narrated as "verification pending"); 18:51 "Warming observed" | split → full UI | "Scenario replay advanced"; "Reconnection alone closes nothing" | wipe to full UI | implemented. Check: 18:21 does not show verified; History lists stages. |
| 8 | 2:04-2:30 (26) | Goal reached, held, verified | Shot 8 landing, phone in hand (blank screen) at the end | 19:51 "Warming observed" (goal reached, not yet verified); 20:21 "Temperature goal verified" with "Latest reading used: observed … received …" and evaluation time; then homeowner update card | full UI → split | "Scenario replay advanced (30-minute hold)"; "ARIA Home — synthetic scenario" | hold, then cut to landing | implemented; **partial** for a single readable evidence timeline (Gap G2). Check: 19:51 never shows verified. |
| 9 | 2:30-2:42 (12) | The report comes after | Shot 9 night drive | 20:46: "HVAC completion report — Corroboration only, does not set the outcome", event 8:40 PM, available 8:45 PM, verification at 8:21 PM | split | "Report available after verification"; "Travel times are scenario estimates" | dissolve | implemented (card); ordering shown across two places (Gap G2). Check: report absent at 20:21. |
| 10 | 2:42-2:54 (12) | Return to warmth | Shot 10 she opens the door to the warm house | 21:01 "Arrival expectation met" (small status card, real wording) | full story | "AI-generated dramatization" | slow fade | implemented (stage). Check: arrival evaluated at 21:01, not assumed. |
| 11 | 2:54-3:00 (6) | Close | none (c3 card) | c3 closing card with repo URL | full card | none | fade out | implemented (c3). |

Real-UI share: segments 1-5 and 7-9 carry readable real UI for about 120 of 180 s (split or full).

### A3.2 Voiceover draft (about 330 words; timed read not yet performed)

Target pace about 125 words per minute with pauses; the word counts below leave room to read the UI.

0. (32 w) ARIA is my existing assistant project; its name, notes and ARIA Home designs came first. All ARIA Home code was built this week with Meta's models. Story scenes and music: Meta AI.
1. (24 w) She's heading home today. Her flight email and calendar suggest an arrival tonight, but a suggestion isn't a plan, and it certainly isn't proof she boarded.
2. (30 w) So ARIA asks. She confirms the house, a nine o'clock arrival, sixty-eight degrees, and that her property manager may be contacted if something goes wrong. Her location supports the plan. Nothing more.
3. (25 w) Preparation starts quietly. The command is acknowledged, but an acknowledgement isn't warmth. In the air, her location is simply unavailable, and ARIA assumes nothing about her schedule.
4. (40 w) Back at the house, something's wrong. The thermostat has gone silent. ARIA won't treat old thermostat numbers as current; an independent room sensor reads fifty-two degrees and isn't warming. There's electrical activity, but activity isn't heat. The home is at risk.
5. (30 w) Within her permission, ARIA alerts the property manager, who authorizes the HVAC company on file. The request carries only what's needed: the property, access, and what was observed. Acknowledged, not resolved.
6. (10 w) A technician arrives. ARIA doesn't control the equipment. It keeps watching.
7. (30 w) On the next sensor update, the thermostat is back. That alone closes nothing; verification is pending. ARIA cross-checks the reported state, the heating circuit, and the room sensor. Then warming appears.
8. (45 w) At seven fifty-one the room reaches sixty-eight degrees, and ARIA still waits. A goal isn't verified until it holds. Thirty minutes later, every reading is still at target. Now it's verified, from sensor evidence alone. As she lands, one short update tells her it's done.
9. (28 w) The technician's report reaches the manager afterward. It's useful corroboration, but it arrived after verification, and it can't change what the sensors already showed. Her drive-time estimate is just that, an estimate.
10. (18 w) She opens the door to the warm home she expected. She never had to chase the repair.
11. (12 w) Not just an automation completed. An expectation met.

### A3.3 Scene prompts (tool-agnostic)

**Shared continuity specification** (paste before every prompt): the same adult woman, mid-thirties,
shoulder-length dark brown hair, camel wool coat, cream scarf, dark jeans, black ankle boots; a navy
hard-shell carry-on and a phone in a plain black case; always seen from behind or in profile without
a visible face. The same modern single-storey house: flat roof, floor-to-ceiling
glass, light wood and dark steel, a covered entry with two steps and a wall light to the
left of a dark-framed glass door, pine forest, snow on the ground, one linear fireplace
on the living-room wall. Interior: light wood floor, dark steel details, the same
floor-to-ceiling glass, a low armchair. Technician: an adult in plain dark-grey work jacket
and cap, no name tags or logos, seen from behind or side-on. Story day: one winter day, light snow,
morning hotel → afternoon airport and flight → dusk house cutaways → night landing, drive and
arrival. Style: cinematic, natural colour, shallow depth of field, no readable text, no logos, no
real brands or places, no legible screens, no credentials or personal details.

| Shot | Subject / action | Framing and camera | Lighting / mood | Space for UI | Consistency | Motion |
|---|---|---|---|---|---|---|
| 1 Hotel | She stands by a hotel window holding her phone, carry-on by the door | medium wide from behind, slow push-in | soft morning daylight, calm | right 55% quiet (wall, curtain) | coat, carry-on, phone | still + editorial push acceptable |
| 2 Airport | She walks through an anonymous concourse, pauses to look at her phone | tracking from behind, then hold | warm afternoon interior light, blurred signage | right 55% soft bokeh | same clothes and bag | motion |
| 3 Flight | Window view over wing and clouds, her shoulder and hair in foreground, phone face-down on tray | close over-shoulder, static | cool blue, quiet | right side sky | hair, coat colour | still + slow drift acceptable |
| 4 Cold house cutaway | The empty modern house at dusk, dark glass, then dim cold interior with the armchair | wide exterior, then interior static | blue-grey, faint frost, no people | right 55% (snow field / wall) | house exterior and interior spec | motion (slow) |
| 5 Manager | An adult on a phone call in a plain office doorway, from behind | medium, static | neutral daylight | right 55% wall | plain clothes, no logos | still + editorial movement acceptable |
| 6 Technician | Unmarked van parks at the house entry; technician walks in carrying a plain tool bag; brief shot working at a plain furnace from behind | wide then medium from behind | late-afternoon, warm work light inside | none needed | same house, technician spec | motion |
| 7 Packing up | Technician closes the tool bag in the utility room, light now warmer | medium from behind, static | warm | right side for brief overlay | technician spec | still acceptable |
| 8 Landing | She walks into a night arrivals hall, glances at a phone with a blank screen | tracking from behind | warm night interior | right 55% | clothes, bag, phone | motion |
| 9 Drive | Night drive on a snowy forest road, dashboard glow, her hands on the wheel | interior over-shoulder, gentle sway | dark, headlights on snow | right side windscreen | coat sleeve, phone mounted face-down | motion |
| 10 Return | She climbs the two entry steps and opens the glass door; warm firelit interior, linear fireplace lit | from behind, slow follow | warm amber against blue night | none | house entrance, wall light, interior spec | motion |

### A3.4 UI capture checklist

Verify each state on a fresh database (`backend/instance/aria_home.db` deleted), backend with
`ARIA_HOME_MODEL_ENABLED=0` for mock takes, scenario "Trip home, thermostat offline (video)".

| State to capture | Replay | Status | Verify before recording |
|---|---|---|---|
| Trip proposal cards (flight email, calendar) | 09:20 | implemented | cards tagged SIMULATED with event and available times |
| Confirmation and authorization (property, arrival, 68 °F, manager coordination, confirmed time) | 09:20 | **partial** (fixture + request card only; Gap G1) | one readable panel lists all confirmed fields and permissions |
| Simulated preparation command and acknowledgement | 14:06 | implemented | "Acknowledged, physical success unknown" visible |
| Location unavailable | 14:06 | implemented | "Location unavailable" card, no schedule inference |
| Thermostat offline plus independent room readings | 16:31 | implemented | Outcome "Thermostat telemetry missing"; verified fact cites room sensor 52.0 F at 16:30 |
| Evidence-backed investigation | 16:31 | implemented (mock); **unverified** live under the current readiness rules | verified facts / readiness / interpretation split; MOCK label in frame unless a live take is approved |
| HVAC-contact approval and scoped request | 16:52 | implemented | HVAC card "fields sent:" shows exactly four fields; refused before 16:45 |
| Acknowledgement is not resolution | 16:52 | implemented | "Acknowledged, not resolved"; Outcome headline unchanged |
| Thermostat reconnects without resolution | 18:21 | implemented | "Thermostat reporting restored"; stages 2-4 Not reached |
| Warming observed | 18:51 | implemented | headline "Warming observed" |
| Reached but not yet verified | 19:51 | implemented | headline still "Warming observed" |
| Target reached and maintained, verified | 20:21 | implemented | "Temperature goal verified"; latest reading used, observed and received times |
| Verification timestamp before report receipt | 20:21 vs 20:46 | implemented across two views; **partial** as one timeline (Gap G2) | report absent at 20:21; report card at 20:46 shows available 8:45 PM |
| Homeowner update | 21:01 | implemented | "Your home reached and held 68 F before you arrived" |
| Arrival goal maintained | 21:01 | implemented | "Arrival expectation met" |

### A3.5 Minimum build gap plan

Travel, email and location feeds, preparation commands and service contacts stay synthetic or
simulated. No email OAuth, GPS, flight tracking, routing or device control.

- **G1, confirmed plan and permissions panel (missing).** A read-only panel rendered from the as-of
  confirmation (property, arrival 9:00 PM with its labelled allowances, 68 °F, manager coordination
  allowed, confirmed time, revision), hidden before `confirmed_at`. No interactive flow needed.
- **G2, one evidence timeline (partial).** A single ordered list for the verification: thermostat
  restored, warming first observed, target first reached, hold completed and verified, report
  available, arrival check — each with observed, received and evaluation times, so segment 8-9 can
  be filmed full-frame and read in one shot.
- **G3, legible close-up capture (partial).** The interrupted D9-9 work (stashed on 2026-10-27 as
  "day9-09 inset close-ups") records one panel at a time at 2x scale; finish it, or capture with the
  browser zoom, so split-screen UI is readable at normal playback size.

### A3.6 Production sequence

1. Lock this storyboard and the continuity specification.
2. Test one or two generated scenes against the continuity spec.
3. Generate the remaining scenes while capturing the real UI states separately.
4. Assemble a rough cut with temporary narration.
5. Record the final narration after timing is stable.
6. Verify labels, legibility, every functional claim against A3.4, exactly 180 s, captions for
   accessibility, and that the video link is publicly accessible.

## A2. Story cut (superseded by A3)

This cut follows the homeowner — a woman, never named, face never shown — as
she travels home. Every dramatization scene is labelled on screen
"Dramatization - AI-generated with Meta AI". Every functional claim is made
only while the real ARIA Home screen is visible as an inset panel, labelled
"Real ARIA Home screen - synthetic data"; no functional claim relies on the
dramatization alone. Title cards are `c1-opening`, `c2-evaluation`, and
`c3-closing` from the recording command in section H; the `s*` insets are the
recorded real-UI clips named there. Narration is third person about "she",
except the beat 1 disclosure. Total: exactly 180 s, contiguous.

| Time | Dramatization scene | Inset | Narration (word count; rate) | On-screen caption |
|---|---|---|---|---|
| 0:00–0:12 (12 s) | None — title card only. | `c1-opening`, full frame; no inset | "ARIA — name, notes and ARIA Home designs — predates this event. All ARIA Home code shown was written this week with Meta's Muse models. Meta AI-generated scenes; synthetic data." (28 words; 140 wpm) | "ARIA Home — disclosure · synthetic data" |
| 0:12–0:26 (14 s) | A woman seen from behind in a hotel room at dawn, packing a case, phone in hand with an illegible screen. | `s1-trip-cards` (recorded at the 16:31 replay state; confirmation and trip cards) | "Morning, far from home, she confirms her trip home today and the sixty-eight-degree target she wants on arrival. ARIA Home now has a plan to check, not just a setting to start." (32 words; 137 wpm) | "She confirms: home today · 68 F" |
| 0:26–0:37 (11 s) | A woman from behind walking an anonymous airport concourse, rolling case beside her, all signage blurred. | `s1-trip-cards` (16:31 replay state; "Airport location" card) | "At the airport, her consented location supports the travel plan only. It is never treated as proof that she boarded." (20 words; 109 wpm) | "Location supports the plan only" |
| 0:37–0:48 (11 s) | An aircraft window over cloud, a woman's shoulder and hair seen from behind, her phone dark on the tray. | `s1-trip-cards`, tail (16:31 replay state; "Location unavailable" card) | "In flight, ARIA Home keeps watching the house quietly. Her phone location is unavailable, and no inference is drawn from that absence." (22 words; 120 wpm) | "Location unavailable — no inference" |
| 0:48–1:04 (16 s) | A cold, empty modern house at winter dusk, then its dark, still interior; a blank wall device out of focus. | `s2-not-responding` (16:31) | "Back at the empty house, the thermostat has gone silent. Independent room readings show no warming, and electrical activity alone is not proof of useful heat." (26 words; 98 wpm) | "No warming · activity is not proof of heat" |
| 1:04–1:20 (16 s) | A property manager seen from behind, on a phone call; an unmarked service van arriving outside a modern house. | `s3-authorized-help` (16:31 manager alert, then 16:52 HVAC request card) | "Within her permission, ARIA Home alerts the property manager. After the manager authorizes HVAC contact, the request carries only the approved fields — never her itinerary, email, or location." (28 words; 105 wpm) | "Approved fields only" |
| 1:20–1:34 (14 s) | A technician seen from behind, working at a generic furnace; no manuals, instructions, or screens visible. | `s4-recovery` (18:21) | "ARIA Home does not wait for a technician's report. On the next sensor update, thermostat telemetry resumes — but reconnection alone closes nothing." (22 words; 94 wpm) | "Reporting restored — issue still open" |
| 1:34–2:09 (35 s) | Warm light returning to the empty modern living room, curtains lifting slightly, the room visibly settling. | `s4-recovery` (18:51, then 19:51, then 20:21) | "Warmth begins to return. Later independent readings show warming. At nineteen fifty-one, sixty-eight degrees is reached, but not yet verified; the headline stays Warming observed. Only after the temperature holds does ARIA Home verify the goal at twenty twenty-one: we verified recovery of the monitored temperature goal." (47 words; 81 wpm) | "19:51 reached, not verified · 20:21 verified" |
| 2:09–2:22 (13 s) | None — title card only. | `c2-evaluation`, full frame; no inset | "In twelve builder-labelled synthetic cases, combined sources scored twelve of twelve fully correct. Single sources scored seven, three, two, and two. A small sample, not a benchmark." (27 words; 125 wpm) | "Combined 12/12 · single sources 7 · 3 · 2 · 2" |
| 2:22–2:42 (20 s) | A woman from behind reading a phone with an illegible screen in an arrivals hall, then a night drive on an anonymous road. | `s5-report-and-arrival` (20:46 completion-report card, then 21:01 homeowner update) | "She lands and reads one concise update. The HVAC completion report reached the manager only after sensor verification, as corroboration; it cannot set the outcome. Then she drives home through the night." (32 words; 96 wpm) | "Report after verification — corroboration only" |
| 2:42–3:00 (18 s) | A woman from behind opening a front door into a warm-lit interior, face never shown. | `s5-report-and-arrival` tail (21:01) under the opening seconds, then `c3-closing` full frame | "She opens the door to a warm home. Not just an automation completed. An expectation met. ARIA Home connects the plan, coordinates the response, and verifies the result, so coming home feels like coming home." (35 words; 117 wpm) | "Not just an automation completed. An expectation met." |

Meta AI prompts for the dramatization scenes (use verbatim; beats 1 and 9
have no scene, so no prompt):

- Beat 2 (0:12): "Cinematic 10-second video: a hotel room at dawn, a woman filmed only from behind packing a suitcase on the bed, phone with a blank illegible screen in one hand, soft window light, shallow depth of field. No faces, no logos, no legible screens or text, no real places or brands."
- Beat 3 (0:26): "Cinematic 10-second video: a woman filmed only from behind walking through an anonymous airport concourse with a rolling suitcase, all signage blurred and unreadable, neutral architecture, morning light. No faces, no logos, no legible screens or text, no real places or brands."
- Beat 4 (0:37): "Cinematic 10-second video: view over an aircraft wing and cloud layer through a cabin window, a woman's shoulder and hair seen from behind in the foreground, a dark phone on the tray table, calm blue light. No faces, no logos, no legible screens or text, no real places or brands."
- Beat 5 (0:48): "Cinematic 10-second video: a cold empty modern single-storey house at winter dusk with unlit glass, cut to its dark still interior, breath-faint cold air, a blank wall device out of focus, blue-grey palette, no people. No faces, no logos, no legible screens or text, no real places or brands."
- Beat 6 (1:04): "Cinematic 10-second video: a person filmed only from behind making a phone call in a plain office doorway, cut to an unmarked service van arriving outside a modern single-storey house in flat daylight, no people visible in the second shot. No faces, no logos, no legible screens or text, no real places or brands."
- Beat 7 (1:20): "Cinematic 10-second video: a technician filmed only from behind working with generic tools at a plain furnace in a utility space, warm work-light, no manuals, no paperwork, nothing instructional visible. No faces, no logos, no legible screens or text, no real places or brands."
- Beat 8 (1:34): "Cinematic 10-second video: warm golden light gradually returning to an empty modern living room, curtains lifting slightly, dust motes in the light, the room visibly settling from cold blue to warm amber, no people. No faces, no logos, no legible screens or text, no real places or brands."
- Beat 10 (2:22): "Cinematic 10-second video: a woman filmed only from behind in an anonymous arrivals hall reading a phone with a blank illegible screen, cut to a night drive on an unmarked road, dashboard glow and headlights, no other people. No faces, no logos, no legible screens or text, no real places or brands."
- Beat 11 (2:42): "Cinematic 10-second video: a woman filmed only from behind opening a front door at night into a warm-lit home interior, warm light spilling out around her silhouette, quiet and unhurried, face never shown. No faces, no logos, no legible screens or text, no real places or brands."

The precise-language rules below section A apply to every row: say "we
verified recovery of the monitored temperature goal", never that a repair was
proven to cause it, that the equipment is fault-free, or that anything
happened "instantaneously" — say "on the next sensor update". Missing phone
location is "unavailable", never evidence about her schedule. No claim of
boarding, real traffic, flight status, or baggage tracking; ARIA Home is not
a travel platform.

## A. Three-minute video plan (superseded by A2)

Superseded by A2 above, which is the current cut. Section A is kept for the
shot-level UI detail it shares with sections B and H.


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
| 1 | ARIA Home page loads with the synthetic-data banner, Investigation section, verified facts vs interpretation, code-computed readiness | Backend investigation (inv-v3 claim binding, code-rendered verified facts, deterministic readiness) served to the frontend | implemented (mock); unverified (live filming take, see H) | replayed + live inference or labeled mock | Select "Trip home, thermostat offline (video)". Capture: "SYNTHETIC DATA - demo scenario, not a real home", heading "Investigation", "MOCK - example answer, not live inference", "Verified facts (checked against the evidence)", "Readiness:", "Interpretation (model-written, not verified)", "Provider mode:" line. A live take, if used, is identified as live in section H, never by removing the mock label from a mock take. |
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
- Evidence-pack investigation engine (inv-v3 claim binding, code-rendered
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
