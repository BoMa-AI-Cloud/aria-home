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

## A3. Story cut, three layers (canonical, 2026-10-29)

This section supersedes A2 and A wherever they conflict. It is a production plan, not a statement
that every shot works: each segment carries its implementation status, judged from the code that
serves the `care_home_v1` scenario. Three layers:

1. **AI-generated dramatization** of an older adult at home on a winter night, an adult-child family caregiver, and a technician visit (labelled "AI-generated dramatization"; fictional faces, consistent across clips, not resembling any real person). Story scenes and music: Meta AI.
2. **Real ARIA Home interface recordings** on the synthetic `care_home_v1` scenario (labelled
   "ARIA Home — synthetic scenario"). Every functional claim rests on this layer, never on layer 1.
3. **Narration in ARIA's voice**: Kokoro-82M, voice `af_bella` (Apache-2.0 licensed open-weight model),
   labelled "Narration — synthetic voice". A production tool only; the app never calls it.

**Continuity rule.** The resident is home all night; the story never tracks the person — no location,
no activity, no health cues. The cold house is shown as exterior and equipment cutaways only. The
ending is the resident getting up at 07:00 to a warm home, after the goal is verified.

**Non-negotiable event order** (scenario times, 2026-01-16/17, -05:00, from `care_home_v1`):
warm-by plan and consent confirmed (19:20) → furnace stops, thermostat silent, room cooling (overnight)
→ flagged before the 07:00 warm-by time, resident and caregiver notified (02:31) → caregiver authorizes
HVAC contact (02:45) → simulated request and technician visit (02:50, 03:30–04:15; neither closes
anything) → thermostat reporting restored (04:20 observed, 04:21 evaluated; proves nothing alone) →
independent room readings show warming (04:51) → target first reached (05:50) → target held 30 min and
verified (06:21) → technician voice-note human report (06:40) and HVAC completion report available to
ARIA (06:45, corroboration only) → warm-by time evaluated from readings received by 07:00 (07:01).
The report never sets or overrides the outcome. The
sensor evidence establishes the monitored temperature goal only, not equipment reliability or which
repair caused recovery.

**Layouts.** Full story (emotion, transitions); split screen (story left 45%, real UI right 55% at
readable size, never a small inset); full UI (the decisive verification timeline). Generated phone
screens stay blank or indistinct; real recordings are composited in the edit.

**Labels.** "AI-generated dramatization"; "ARIA Home — synthetic scenario"; "Simulated service contact"; "Scenario replay advanced" on every physical-time jump;
"Processing time shortened" if an inference wait is edited; inference mode stated separately from
data mode ("synthetic sensor data — mock inference" or "— live Meta inference"); never present mock
or cached inference as a fresh live response. Every dramatization frame with people carries the
fictional-faces note from the continuity spec.

### A3.1 Storyboard (exactly 180 s)

Status key as at the top of this file. Times are video times.

| # | Time (s) | Purpose | Dramatized visual | Real UI required | Layout | On-screen labels | Transition | Status / acceptance check |
|---|---|---|---|---|---|---|---|---|
| 0 | 0:00-0:10 (10) | Disclosure | none (title card c1) | c1 opening card | full card | "Synthetic demo data" | fade in | implemented (c1). Check: wording matches README pre-existing vs built. |
| 1 | 0:10-0:24 (14) | A plan exists | Shot 1 evening at home, resident checks the thermostat | Confirmed plan and permissions: demo-house, warm-by 7:00 AM, 68 °F, caregiver coordination allowed, confirmed 7:20 PM; "Confirmation request" card (19:20) | split | AI-generated dramatization; ARIA Home — synthetic scenario; "A plan to check, not a setting to start" | cut | implemented (cards + panel). Check: cards show SIMULATED and available times; panel lists the confirmed fields and permissions together. |
| 2 | 0:24-0:42 (18) | Consent is recorded | Shot 2 caregiver on the phone at home in the evening | Confirmed plan consent lines: resident everything, caregiver home status and observations, HVAC property/access/observations only | split | "Simulated consent record" | match cut on phone | implemented (fixture + panel). Check: no health data, no medical terms, no location of the person. |
| 3 | 0:42-0:56 (14) | The furnace stops overnight | Shot 3 dark house exterior at night, blank thermostat close-up | 02:31: Outcome "Thermostat telemetry missing"; verified facts "Indoor temperature 52.0 F (at 02:30)" from the room sensor | split | "Scenario replay advanced"; "Old numbers are not current" | dissolve | implemented. Check: no thermostat value presented as current; no useful-heat claim. |
| 4 | 0:56-1:20 (24) | Flagged before the warm-by time | Shot 4 cold living room cutaway at night (4 s full story, then split) | 02:31: Readiness "At risk"; Power context with limitations; "Caregiver alert" card | full story → split | "Nobody there may know"; "Scenario replay advanced" | slow push-in | implemented. Check: no location, activity or health cue anywhere. |
| 5 | 1:20-1:36 (16) | Authorized help | Shot 5 caregiver on a call at night | 02:45: Family caregiver card; HVAC company card with "fields sent:" (property_label, access_note, manager_contact_label, relevant_observations); "Acknowledged, not resolved" | split | "Simulated service contact"; "Approved fields only" | cut | implemented. Check: no itinerary/email/location field; HVAC card absent or refused before 02:45. |
| 6 | 1:36-1:46 (10) | A professional visit | Shot 6 technician arrives and works | none (story only) | full story | "AI-generated dramatization"; "Simulated service visit" | cut | n/a (dramatization). Check: no repair instructions, no implication ARIA controls equipment. |
| 7 | 1:46-2:04 (18) | Recovery detected independently | Shot 7 technician packs up (2 s), then UI | 04:21 "Thermostat reporting restored" with progression 1 Reached, 2-4 Not reached (narrated as "verification pending"); 04:51 "Warming observed" | split → full UI | "Scenario replay advanced"; "Reconnection alone closes nothing" | wipe to full UI | implemented. Check: 04:21 does not show verified; History lists stages. |
| 8 | 2:04-2:30 (26) | Goal reached, held, verified | Shot 8 pre-dawn bedroom, resident still asleep, warm light rising | 06:21 "Temperature goal verified" with "Latest reading used: observed … received …" and evaluation time; evidence timeline entries through "Hold completed and goal verified" | full UI → split | "Scenario replay advanced (30-minute hold)"; "ARIA Home — synthetic scenario" | hold, then cut to morning | implemented. Check: 04:51 never shows verified. |
| 9 | 2:30-2:42 (12) | The report comes after | Shot 9 morning kitchen, phone showing the update | 06:45: "HVAC completion report — Corroboration only, does not set the outcome", event 6:40 AM, available 6:45 AM, verification at 6:21 AM; technician voice-note row "Corroboration only" | split | "Report available after verification" | dissolve | implemented (cards). Check: report absent at 06:21. |
| 10 | 2:42-2:54 (12) | Warm by morning | Shot 10 resident gets up at 07:00 to the warm home | 07:01 "Warm-by expectation met" and the homeowner update ("Your home reached and held 68 F before the warm-by time") | full story | "AI-generated dramatization" | slow fade | implemented (stage). Check: warm-by evaluated at 07:01 from readings received by 07:00, not assumed. |
| 11 | 2:54-3:00 (6) | Close | none (c3 card) | c3 closing card with repo URL | full card | none | fade out | implemented (c3). |

Real-UI share: segments 1-5 and 7-9 carry readable real UI for about 120 of 180 s (split or full).

### A3.2 Voiceover draft (about 330 words; timed read not yet performed)

Target pace about 125 words per minute with pauses; the word counts below leave room to read the UI.

0. (32 w) ARIA is my existing assistant project; its name, notes and ARIA Home designs came first. All ARIA Home code was built this week with Meta's models. Story scenes and music: Meta AI.
1. (32 w) An older adult lives alone in a house. On a winter evening, the household confirms its plan: warm by seven, sixty-eight degrees, and a family caregiver to call if something goes wrong.
2. (31 w) Consent is recorded with the plan: the resident sees everything, the caregiver sees home status and observations, and the heating company would see only the property, access, and what was observed.
3. (28 w) Overnight the furnace stops and the thermostat goes silent. ARIA will not treat old numbers as current; an independent room sensor reads fifty-two degrees and is not warming.
4. (38 w) Back at the house, something is wrong. The room keeps cooling toward fifty-two degrees while the warm-by time approaches. There is electrical activity, but activity is not heat. The home is at risk, and nobody there may know.
5. (33 w) Within the recorded consent, ARIA alerts the family caregiver, who authorizes the heating company on file. The request carries only what is needed: the property, access, and what was observed. Acknowledged, not resolved.
6. (10 w) A technician visits. ARIA controls no equipment. It keeps watching.
7. (31 w) On the next sensor update the thermostat is back. That alone closes nothing; verification is pending. ARIA cross-checks the reported state, the heating circuit, and the room sensor. Then warming appears.
8. (44 w) Near six the room reaches sixty-eight degrees, and ARIA still waits. A goal is not verified until it holds. Thirty minutes later every reading is still at target. Now it is verified, from sensor evidence alone. One short update is ready for the morning.
9. (21 w) The technician's spoken note and completion report arrive afterward. Useful corroboration, but after verification, unable to change what the sensors showed.
10. (18 w) At seven they get up to the warm home they expected. They never had to chase the repair.
11. (11 w) Noticed sooner. The right person moving. The goal verified before morning.

### A3.3 Scene prompts (tool-agnostic)

**Shared continuity specification** (paste before every prompt): the same older adult resident at home,
silver-grey short hair, rust-red cardigan over a cream shirt, dark trousers, slippers; fictional face,
consistent across clips, kind and calm, resembling no real or famous person. The same adult-child family
caregiver: mid-forties, dark brown hair tied back, navy sweater, phone in a plain black case. The same
modern single-storey house: flat roof, floor-to-ceiling
glass, light wood and dark steel, a covered entry with two steps and a wall light to the
left of a dark-framed glass door, pine forest, snow on the ground, one linear fireplace
on the living-room wall. Interior: light wood floor, dark steel details, the same
floor-to-ceiling glass, a low armchair with a folded blanket. Technician: an adult in plain dark-grey work jacket
and cap, no name tags or logos, seen from behind or side-on. Story night: one winter night into morning, light snow,
evening at home → night house cutaways and caregiver call → pre-dawn technician departure → morning kitchen and
getting up. Style: cinematic, natural colour, shallow depth of field, no readable text, no logos, no
real brands or places, no legible screens, no credentials or personal details. No location tracking, activity
sensing, health or medical cues: the camera shows rooms and equipment, never the resident's movements as data.

| Shot | Subject / action | Framing and camera | Lighting / mood | Space for UI | Consistency | Motion |
|---|---|---|---|---|---|---|
| 1 Evening home | The resident sits in the armchair in the evening, checks the wall thermostat, phone on the side table | medium wide, slow push-in | soft evening lamplight, calm | right 55% quiet (wall, curtain) | cardigan, armchair, blanket | still + editorial push acceptable |
| 2 Caregiver call | The caregiver at home in the evening, on the phone, listening and nodding | medium, then hold | warm evening interior light | right 55% soft bokeh | navy sweater, phone | motion |
| 3 Night falls | Dark house exterior at night with snow, then the blank thermostat close-up in a dim hall | wide exterior, then close-up static | blue night, quiet | right side snow field | house exterior spec | still + slow drift acceptable |
| 4 Cold house cutaway | The quiet modern living room at night, armchair empty, glass dark with frost at the edges | wide interior, then static | blue-grey, faint frost, no people | right 55% (wall) | interior spec | motion (slow) |
| 5 Caregiver night call | The caregiver on a night-time phone call in a dim kitchen, concerned but calm | medium, static | dim night interior | right 55% wall | navy sweater, phone | still + editorial movement acceptable |
| 6 Technician | Unmarked van parks at the house entry at night; technician walks in carrying a plain tool bag; brief shot working at a plain furnace from behind | wide then medium from behind | night exterior, warm work light inside | none needed | same house, technician spec | motion |
| 7 Packing up | Technician closes the tool bag in the utility room, light now warmer | medium from behind, static | warm | right side for brief overlay | technician spec | still acceptable |
| 8 Pre-dawn | The resident asleep in the bedroom before dawn, warm light just rising through the glass | close, static | cool blue warming to amber | right 55% | cardigan on chair | motion |
| 9 Morning kitchen | Morning kitchen, kettle steaming, the phone on the counter showing an indistinct update screen | interior over-shoulder, gentle sway | bright morning | right side window | kitchen, phone face-up indistinct | motion |
| 10 Morning | The resident gets up at seven, wraps the cardigan, walks into the warm living room; linear fireplace lit | slow follow | warm amber morning | none | resident, interior spec | motion |

### A3.4 UI capture checklist

Verify each state on a fresh database (`backend/instance/aria_home.db` deleted), backend with
`ARIA_HOME_MODEL_ENABLED=0` for mock takes, scenario "Winter night, older adult at home (guided story)".

| State to capture | Replay | Status | Verify before recording |
|---|---|---|---|
| Warm-by plan and consent (demo-house, 07:00 warm-by, 68 °F, caregiver coordination, confirmed 7:20 PM, warmby-care-001-rev1) | 19:20 | implemented | one readable panel lists all confirmed fields, permissions and consent; "Confirmation request" card tagged SIMULATED with event and available times |
| Thermostat offline plus independent room readings | 02:31 | implemented | Outcome "Thermostat telemetry missing"; verified fact cites room sensor 52.0 F at 02:30 |
| Evidence-backed investigation | 02:31 | implemented (mock); **unverified** live under the current readiness rules | verified facts / readiness / interpretation split; MOCK label in frame unless a live take is approved |
| "Caregiver alert" card | 02:31 | implemented | card tagged SIMULATED with event and available times |
| HVAC-contact approval and scoped request | 02:45 | implemented | HVAC card "fields sent:" shows exactly four fields; refused before 02:45 ("caregiver has not authorized HVAC contact") |
| Acknowledgement is not resolution | 02:45 | implemented | "Acknowledged, not resolved"; Outcome headline unchanged |
| Simulated service visit (03:30–04:15) | 04:21 state | implemented (timeline card only) | "Service visit", "SIMULATED", label "(does not by itself close anything)" |
| Thermostat reconnects without resolution | 04:21 | implemented | "Thermostat reporting restored"; later stages Not reached |
| Warming observed | 04:51 | implemented | headline "Warming observed" |
| Target reached and maintained, verified | 06:21 | implemented | "Temperature goal verified"; latest reading used, observed and received times; evidence timeline through "Hold completed and goal verified" |
| Verification timestamp before report receipt | 06:21 vs 06:45 | implemented | report absent at 06:21; report card at 06:45 shows available 6:45 AM; voice-note row "Corroboration only" |
| Homeowner update | 07:01 | implemented | "Your home reached and held 68 F before the warm-by time" |
| Warm-by goal maintained | 07:01 | implemented | "Warm-by expectation met", evaluated from readings received by 07:00 |
| Care camera frames with recorded misses | 02:31, 07:01 | implemented | night frame "Missed by the model"; "Synthetic camera frame (muse-image-1.0) - segmentation by sam-3.1 (recorded)" caption |

### A3.5 Minimum build gap plan

Care-story contacts stay synthetic or
simulated. No GPS, no person tracking, no health or fall sensing, no device control.

- **G1, confirmed plan and permissions panel (implemented).** A read-only panel rendered from the as-of
  confirmation (demo-house, warm-by 7:00 AM, 68 °F, caregiver coordination
  allowed, confirmed 7:20 PM, warmby-care-001-rev1) plus the recorded consent lines, hidden before `confirmed_at`.
- **G2, one evidence timeline (implemented).** A single ordered list for the verification: thermostat
  restored, warming first observed, target first reached, hold completed and verified, technician
  voice-note report available, completion report
  available, warm-by check — each with observed, received and evaluation times, so segments 8-9 can
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

A3 above is the current cut. A2 below documents the older trip-home cut, kept because the trip-home
scenarios stay in the repo as secondary evaluation/test fixtures. Do not film A2.

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
| 2:09–2:22 (13 s) | None — title card only. | `c2-evaluation`, full frame; no inset | "In seventeen builder-labelled synthetic cases, combined sources scored seventeen of seventeen fully correct. Single sources scored twelve, three, two, and two. A small sample, not a benchmark." (27 words; 125 wpm) | "Combined 17/17 · single sources 12 · 3 · 2 · 2" |
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

Superseded by A2 above, which is itself superseded by the care-story cut A3. Section A is kept for the
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
| 2:10–2:25 (15 s) | Title card built from `docs/evaluation.md` totals (not product UI): the combined vs single-source table. | "In seventeen builder-labelled cases, all sources together scored seventeen of seventeen. Thermostat alone reached twelve; room sensor alone reached three; electrical and calendar alone reached two each. A small synthetic sample, not a benchmark." (34; 136 wpm) | "17 builder-labeled cases, fully correct" / "combined 17/17" / "thermostat only 12/17" / "room sensor only 3/17" / "electrical only 2/17" / "calendar only 2/17" |
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
video scenario is selected with the "Scenario" control set to "Winter night,
older adult at home (guided story)"; selecting it already runs the investigation at
19:03, and the other times are the replay buttons in "Demo controls
(synthetic replay)". Shots with no dedicated UI (confirmation, service visit) are filmed from the "Simulated timeline" cards,
each tagged "SIMULATED"; they are not presented as product screens making
real calls.

| # | Viewer sees | Must actually work | Status | Content type | Screen action and exact on-screen text to capture / acceptance check |
|---|---|---|---|---|---|
| 1 | ARIA Home page loads with the synthetic-data banner, Investigation section, verified facts vs interpretation, code-computed readiness | Backend investigation (inv-v3 claim binding, code-rendered verified facts, deterministic readiness) served to the frontend | implemented (mock); unverified (live filming take, see H) | replayed + live inference or labeled mock | Select "Winter night, older adult at home (guided story)". Capture: "SYNTHETIC DATA - demo scenario, not a real home", heading "Investigation", "MOCK - example answer, not live inference", "Verified facts (checked against the evidence)", "Readiness:", "Interpretation (model-written, not verified)", "Provider mode:" line. A live take, if used, is identified as live in section H, never by removing the mock label from a mock take. |
| 2 | Recorded consent and the warm-by plan the household confirmed | A consent record gating who may be told what | implemented (fixture + panel) | synthetic / simulated | Film the "Confirmed plan and permissions" panel at 19:20 plus the Simulated timeline card. Capture: "demo-house", "Warm-by time", "7:00 AM", "68 F", "Caregiver coordination allowed", "warmby-care-001-rev1", "Confirmation request", "SIMULATED", "Asks". Narration never claims health, location, or activity sensing. |
| 3 | Not responding overnight: thermostat telemetry missing while thermostat-independent room readings show no warming | An offline-thermostat interval plus an independent room sensor carrying the trend | implemented | synthetic / replayed | Select "Winter night, older adult at home (guided story)", replay button "02:31". Capture Outcome: "Status: Thermostat telemetry missing", "Follow-up rule:", "Latest reading used: observed" / "received", "Evaluation (replay) time"; Investigation: "Evaluation time:" "2:31 AM". During the outage no fresh thermostat measurement is shown as current. |
| 4 | Mapped HVAC electrical activity, other circuits fresh, power statement with limitations | Power context: mapped-circuit activity, per-circuit freshness, bounded continuity statement, limitations | partial — the "Power context" block and the "electrical" evidence card are implemented, but there is no labelled blower-channel card; the blower-consistent observation appears as text in the simulated HVAC request observations | replayed | At "02:31" capture Investigation "Power context" and "Limitations:", and the "Evidence sources" card `article[aria-label="electrical source"]` with "Status:". Capture the HVAC request observations text only from shot 5 / the timeline "HVAC request" card at "04:21" ("fields sent:" property, access_note, manager_contact, observations). Never claim useful heat, a fault, or equipment power from watts. |
| 5 | ARIA alerts the family caregiver inside the recorded consent; caregiver explicitly authorizes HVAC contact; scoped simulated request (no itinerary/email/location) | Notification records with authorization gates and a scoped payload | implemented (simulated) | simulated | Replay button "02:31": capture "Notifications (simulated delivery)", the "Family caregiver" card with "Simulated delivery", "Created:", "Simulated, no message was sent"; any HVAC company card at 02:31 is absent or "Refused: caregiver has not authorized HVAC contact". Replay button "02:45": capture the delivered "HVAC company" card with "fields sent: property_label, access_note, manager_contact_label, relevant_observations" and no itinerary/email/location. Click "Acknowledge (simulated)": capture "Acknowledged, not resolved" and confirm the Outcome headline is unchanged. |
| 6 | Simulated service visit | Visit/repair events | implemented (simulated timeline card only) | simulated | Replay button "04:21" (visit available 04:15). Film the Simulated timeline card only. Capture: "Service visit", "SIMULATED", "Event time", "Available time (received time)", label text "simulated technician visit 03:30-04:15 (does not by itself close anything)". The card changes no outcome by itself; do not claim a repair is proven. |
| 7 | Independent recovery detection: telemetry resumes → warming → goal verified → still met at warm-by time | Verification stages over later readings, evaluated at each replay time | implemented | replayed | Replay buttons "04:21", "04:51", "06:21", "07:01". Capture Outcome headlines in order: "Thermostat reporting restored" (04:21), "Warming observed" (04:51; the headline must not yet be "Temperature goal verified"), "Temperature goal verified" (06:21), "Warm-by expectation met" (07:01); the progression list shows each stage "Reached" / "Not reached", History accumulates the stages, and "Latest reading used: observed" / "received" is visible. |
| 8 | HVAC completion report and technician voice note become available to ARIA only after sensor verification | Report records whose available times are after the verified evaluation | implemented (simulated timeline card + human-report row only) | simulated | Replay button "06:21": the Simulated timeline has no "HVAC completion report" card and no "Corroboration only" text. Replay button "06:45": capture the card "HVAC completion report", "SIMULATED", "Corroboration only, does not set the outcome", "Event time", "Available time (received time)". At no replay time does the report change the outcome. |
| 9 | Ending: concise evidence-backed resident update; warm home at the warm-by time | A resident-facing summary generated from the verified outcome | implemented | replayed | Replay button "07:01". Capture the "Homeowner update" section card: "Your home reached and held 68 F before the warm-by time", "Evaluation time:". It claims goal recovery only, not a proven cause or fault-free equipment. |
| 10 | Care camera frames with recorded segmentation, including the misses | Replay-only visual evidence gated by received time | implemented | replayed | Replay "02:31": capture the "Visual evidence (synthetic image)" section with "Synthetic camera frame (muse-image-1.0) - segmentation by sam-3.1 (recorded)" and "Missed by the model". Replay "07:01": the morning frame with no miss label. Images never enter any notification. |

## C. Scenario timeline

Built as the `care_home_v1` fixture. All dates are 2026-01-16/17,
America/New_York (-05:00), and are scenario assumptions for the video —
invented times, not validated physical behaviour. Warm-by time 07:00,
temperature target 68 F; thermostat cadence 300 s, room-sensor cadence
300 s, electrical 1800 s, weather 21600 s.

"Received/available" is when ARIA may first use the item (`received_at` for
records, `known_at`/`confirmed_at` for plan context, `available_at` for
simulated events); "evaluation" is a replay evaluation time (`at`) at or
after that. An item never appears at an evaluation earlier than its
received/available time.

| # | Event | Event time | Received / available | Evaluation |
|---|---|---|---|---|
| 1 | Simulated confirmation request: property, warm-by plan, target temperature, caregiver coordination | 19:15 (Jan 16) | 19:15 | Simulated timeline card |
| 2 | Household confirmation: demo-house, warm-by 07:00, 68 F, caregiver coordination permitted (`warmby-care-001-rev1`); resident's consent recorded (resident: everything; caregiver: home status and observations; HVAC: property, access note, observations only) | 19:20 | 19:20 (`confirmed_at`) | readiness stops being `cannot_tell` for "unconfirmed"; "Confirmed plan and permissions" panel |
| 3 | Furnace stops; thermostat outage interval begins: no fresh thermostat telemetry; independent room readings cooling, flat near 52 F | 01:30 (Jan 17) | as each reading arrives | — |
| 4 | Flagged before the warm-by time: room-sensor reading 52.0 F at 02:30, 16 F below goal, flat trend; thermostat telemetry missing | — | — | 02:31 "Thermostat telemetry missing", readiness `at_risk` |
| 5 | ARIA alerts the resident and the family caregiver (simulated), inside the 19:20 consent; "Caregiver alert" card | alert placed 02:35 | notification cards created at the 02:31 evaluation; timeline event available 02:37 | notification cards from the 02:31 evaluation |
| 6 | Caregiver explicitly authorizes contacting the HVAC company on file (simulated) | 02:45 | 02:45 | no HVAC contact before this; HVAC card absent or refused at 02:31 |
| 7 | Scoped simulated HVAC request: property label, access note, caregiver contact label, relevant observations only | request placed 02:50 | notification card created at the 02:45 evaluation (auth available 02:45); timeline event available 02:52 | 02:45 evaluation shows the delivered card; "fields sent: property_label, access_note, manager_contact_label, relevant_observations" |
| 8 | Simulated technician visit | 03:30–04:15 | visit logged 04:15 | not used by ARIA to close anything |
| 9 | Thermostat reconnection: fresh thermostat telemetry resumes on the next sensor update | 04:20 | 04:20:20 | 04:21 → "Thermostat reporting restored"; does not close the issue |
| 10 | Warming evidence from later independent readings (52.0 F at 04:35 to 54.5 F at 04:50) | 04:35–04:50 | as readings arrive | 04:51 → "Warming observed" |
| 11 | Target first reached on independent readings (68 F) | 05:50 | 05:50:20 | 06:21 evaluation (reached, not yet verified on its own) |
| 12 | Target maintained through the 30-minute verification window (every reading 05:50–06:20 at or above 68 F) | 05:50–06:20 | as readings arrive | 06:21 → "Temperature goal verified" |
| 13 | Technician voice-note human report (transcribed, synthetic) and HVAC completion report reach the caregiver (simulated), then become available to ARIA | voice note and report 06:40; caregiver 06:42 | available to ARIA 06:45 | 06:45 (corroboration only; cannot set or change the verified outcome) |
| 14 | Warm-by time passes; latest reading received by 07:00 was 68.2 F at 06:55, at goal | 07:00 | 07:00 | 07:01 → "Warm-by expectation met" |

## D. What is built, and known limits

Built (see `docs/freeze.md`, frozen 2026-10-26 at commit 4d3bacb, plus the
care story approved 2026-10-29):

- Evidence foundation with as-of visibility: records, plan revisions and
  confirmations are visible only at or after their received/available times.
- Deterministic metrics, readiness (including `arrival_passed` decided at
  the warm-by time from readings received by then), power context, follow-up
  scheduling, outcome rules, and recovery verification stages
  (`telemetry_missing` to `arrival_met`, shown as "Warm-by expectation
  met"), all computed in code. The model cannot change the readiness status.
- Evidence-pack investigation engine (inv-v3 claim binding, code-rendered
  verified facts) with mock and gated live Meta providers.
- SQLite store with outcome and verification history surviving restarts.
- Scoped simulated notifications with per-audience allowlists, recorded
  refusals, idempotent outbox, and simulated acknowledgement
  ("Acknowledged, not resolved") that never changes readiness, outcome, or
  verification. In `care_home_v1` the family caregiver replaces the property
  manager: the caregiver sees home status and observations, the HVAC company
  sees property, access note and observations only, and the HVAC request is
  gated by the caregiver's explicit authorization event at 02:45.
- Recorded consent with the confirmed plan: the "Confirmed plan and
  permissions" panel (demo-house, warm-by 7:00 AM, 68 F, caregiver
  coordination allowed, confirmed 7:20 PM, `warmby-care-001-rev1`) plus the
  consent lines (no health data, no medical terms, no location tracking of
  the person, no fall or activity sensing).
- Frontend: synthetic-data banner, Investigation section, Outcome section in
  verification-stage wording, notifications panel, homeowner update
  ("Your home reached and held 68 F before the warm-by time"), simulated
  timeline, evidence source cards, scenario selector with "Winter night,
  older adult at home (guided story)" as the default and guided story, with
  replay times 19:03, 19:15, 19:20, 02:31, 02:45, 04:21, 04:51, 06:21,
  06:45, 07:01, and human-readable labels with exact payload fields still
  checkable via "fields sent".
- Replay-only visual evidence: synthetic camera frames (muse-image-1.0)
  with recorded sam-3.1 segmentation, gated by received time; the night
  frames carry recorded misses shown as "Missed by the model".
  Images never enter any notification.
- Evaluation: 22 builder-labeled cases across 10 scenarios with offline results (combined 22/22 fully correct; thermostat
  only 12/22; room sensor only 4/22; electrical and calendar only 2/22 each; verification scored for the 10
  `demo_video_v1` and `care_home_v1` cases only, target-at-arrival scored for the 7 `arrival_passed` cases),
  plus the operator-run live calls documented in `docs/evaluation.md` (the 17-case run on snapshot 77cafc9 and
  the 6-case after-arrival rerun on efdff57, cited separately, never merged). Both live runs predate the care
  story and used the trip-home scenarios; they are kept verbatim, not re-scored. Readiness
  agreement in the live run is enforced by the validator, so it shows the
  models followed the contract, not independent readiness judgment; one run
  per case, small synthetic sample.

Known limits:

- All data is synthetic and every message, visit, voice note and report is
  simulated; there are no real channels and ARIA Home controls no equipment.
  Confirmation and service-visit shots have no dedicated UI and are filmed
  from the Simulated timeline cards (section B). ARIA Home is not a medical
  or emergency service: no health data, no medical terms, no location
  tracking of the person, no fall or activity sensing.
- There is no labelled blower-channel card; power claims stay at the
  "Power context" statement and its limitations (shot 4 is partial).
- Room-sensor and blower mappings are synthetic assumptions, not measured
  physical behaviour.
- The notification allowlists are reviewed by hand, not by an external
  privacy review; the HVAC request is gated only by a synthetic caregiver
  authorization event.
- The committed live results used the trip-home scenarios under the inv-v2
  contract and predate the care story; they are kept verbatim, not re-scored
  against `care_home_v1`. A live filming take is therefore unverified in its
  current form (section H).
- Claims stay bounded to the monitored temperature goal: verified recovery
  of that goal, never a proven repair cause or fault-free equipment.

## E. Acceptance criteria

Checked on the replayed `care_home_v1` scenario before filming; the
browser checks in `frontend/e2e/app.spec.ts` cover the on-screen items.

1. No fresh thermostat measurements while offline: during the outage
   interval (01:30–04:20), no evaluation shows a fresh thermostat reading
   as current, and the Outcome at 02:31 reads "Thermostat telemetry missing".
2. Independent room sensors carry the trend: the no-warming statement at
   02:31 (52.0 F at 02:30, flat) and the warming statement at 04:51
   (52.0 F at 04:35 to 54.5 F at 04:50) cite independent room readings,
   with the thermostat absent or stale — never cached thermostat values.
3. Electrical activity is not proof of useful heat: the power statement
   keeps the bounded continuity wording and limitations; no UI or narration
   text claims useful heat, a fault, or equipment power from circuit watts.
4. Reconnection without warming cannot resolve: the 04:21 evaluation shows
   "Thermostat reporting restored" with the issue still open, and the
   target first reached at 05:50 is still not verified until the hold
   completes — 04:51 shows "Warming observed", not "Temperature goal verified".
5. Human reports cannot force physical resolution: caregiver acknowledgement
   ("Acknowledged, not resolved"), the technician voice note, and the HVAC
   completion report, replayed at any evaluation, change no outcome status;
   voice note and report only corroborate after verification.
6. Sensor verification precedes report availability: the verified
   evaluation (06:21, 30-minute hold 05:50–06:20) is strictly before the
   voice-note/report available time (06:45); at 06:21 the timeline has no
   completion-report card and no "Corroboration only" text, and at 06:45 it
   does, labelled "Corroboration only, does not set the outcome".
7. Goal met through the warm-by time: "Temperature goal verified" at 06:21
   is re-checked at the warm-by time; "Warm-by expectation met" is evaluated
   at 07:01 from the latest reading received by 07:00 (68.2 F at 06:55),
   not assumed from 06:21.
8. Every authorization precedes the action it permits: household
   confirmation (19:20) < caregiver alert (notification cards from the
   02:31 evaluation) < caregiver HVAC authorization (02:45) < HVAC request
   (placed 02:50, delivered card from the 02:45 evaluation).
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
    or UI captures. No health, medical, location-of-the-person, fall, or
    activity language appears anywhere.

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
- No credentials, account pages, real personal details, private code, or
  personal contacts in frame or audio; all names, addresses, and contacts
  are the synthetic fixture ones. No real calls, messages,
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

- The video timeline is the built `care_home_v1` fixture: warm-by 07:00
  (confirmed 19:20, `warmby-care-001-rev1`), 68 F target, thermostat outage
  01:30–04:20, recovery stages at 04:21 / 04:51 / 06:21 / 07:01, with the
  target first reached 05:50 and held 30 minutes.
- The verification progression is the built stage list
  (`telemetry_missing`, `reporting_restored`, `warming_observed`,
  `goal_verified`, `arrival_met`, shown as "Warm-by expectation met"); the
  goal is verified from maintained readings and re-checked at the warm-by
  time, as section C/E describe.
- The simulated HVAC request carries only the built scoped fields
  (property label, access note, caregiver contact label, relevant
  observations), gated by the caregiver authorization event at 02:45; the
  technician voice note and HVAC completion report are available to ARIA at
  06:45, after the 06:21 verification, as corroboration only.
- Independent room sensors and the blower-mapped electrical channel are
  synthetic fixture assumptions; consent, caregiver coordination, service
  communications, and the voice note stay synthetic/simulated by design,
  with no real integrations for this video. No health data, no medical
  terms, no location tracking of the person, no fall or activity sensing.
- Notifications are simulated only, with the built per-audience
  allowlists; acknowledgement is "Acknowledged, not resolved" and changes
  no outcome.
- The trip-home scenarios (`demo_video_v1` and the other `demo_*`
  fixtures) stay in the repo only as secondary evaluation/test fixtures;
  the older trip-home cuts A2/A above are kept as history and are not filmed.

The one filming-mode choice left open is mock-with-label versus one live
investigation call; section H gives both, and a live call needs Brad's
approval of that call before filming.

Claims to avoid:

- That ARIA Home knows where the resident is, or that it senses falls, activity, or health in any way. ARIA Home is not a medical or emergency service, and the older trip-home fixtures do not make it a travel platform.
- That command acknowledgement, a caregiver acknowledgement, a visit, a voice note, or a technician report proves physical success or caused the recovery.
- That electrical activity proves useful heat, a fault, equipment power, or "no outage".
- That recovery was "instantaneous", that the equipment is fault-free, or that the goal is guaranteed beyond the observed readings.
- That any call, message, visit, voice note, or report in the video is real.
- Only "verified recovery of the monitored temperature goal" — never a proven repair cause. Reconnection alone proves nothing; say "on the next sensor update".

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
  "Winter night, older adult at home (guided story)". Selecting it already
  runs the investigation at 19:03; capture the "Confirmed plan and
  permissions" panel and the "Confirmation request" card in this initial
  state.
- [ ] Click the replay buttons in this order, capturing the Outcome
  headline (and the panels named in section B) at each step:
  19:20, 02:31, 02:45, 04:21, 04:51, 06:21, 06:45, 07:01.
  Expected headlines: 19:20 "On track" (plan confirmed, nothing wrong yet); 02:31 "Thermostat telemetry missing";
  04:21 "Thermostat reporting restored"; 04:51
  "Warming observed"; 06:21 "Temperature goal verified";
  07:01 "Warm-by expectation met". At 02:45 capture the delivered HVAC
  notification card; at 06:45 capture the "HVAC completion report" card
  ("Corroboration only, does not set the outcome") and the technician
  voice-note row, both of which must be absent at 06:21.
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
  committed live evaluation ran the trip-home scenarios under inv-v2, so the live
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
  storyboard segment: `s1-confirm` (19:20 plan and confirmation), `s2-not-responding` (02:31),
  `s3-authorized-help` (02:31 caregiver alert, 02:45 HVAC request, acknowledgement),
  `s4-recovery` (04:21, 04:51, 06:21), and `s5-report-and-warmby` (06:45 report, 07:01 warm-by met).
- The same command also records three title-card clips from
  `frontend/cards.html`: `c1-opening`, `c2-evaluation`, and
  `c3-closing`. These are title cards, not product UI: the opening and
  closing cards carry the section A disclosure / closing lines, and the
  evaluation card shows the offline totals read at runtime from
  `backend/eval/results-offline.json` via `GET /api/evaluation/offline`.
- The footage of the five `s*` segments is the real UI; the front-door /
  warm-room door shots are not product UI and are not recorded by this
  command.
