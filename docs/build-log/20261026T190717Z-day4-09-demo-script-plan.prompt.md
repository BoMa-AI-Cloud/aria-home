ARIA Home, planning task (approved by Brad): write the video plan and its implementation gap map.
DOCUMENTATION ONLY. Create docs/demo-script.md and add one link line to README.md (under
Planned) and one line to docs/timeline.md. Do not change code, tests, scenarios or any working
behavior. No live calls, no installs, no network, no git, NO helper scripts.

Inspect first, so the gap map is accurate: README.md, docs/timeline.md, docs/day3-handoff.md
(including "Verification repair"), docs/readiness-rules.md, docs/existing-vs-new.md,
backend/scenarios/README.md and each scenario's manifest.json/calendar.json, and skim
backend/aria_home/*.py (evidence, power_context, readiness, scheduling, outcomes, scenario,
investigator, store, app) and frontend/src/App.tsx. A plan is not a feature: mark each item by
what the code does today, not by test or document names.

VIDEO PURPOSE: a 3-minute demo of "An automation starting does not mean the homeowner's
expectation was met. ARIA connects the evidence, coordinates authorized help, independently
detects recovery, and verifies the result." Ending: a woman returns from her trip to a home that
reached and maintained her confirmed temperature goal; she did not have to chase the repair.

AGREED STORY (target demonstration, not proof it works):
1. Trip home: a synthetic flight-confirmation email and matching calendar entry propose a return
   itinerary; a consented, simulated location event places her at the departure airport. These
   support the plan, they do not prove boarding. ARIA asks her to confirm property, arrival
   plan, desired temperature and permission to coordinate with the property manager. An arrival
   window may include clearly labeled driving and airport-exit/baggage allowances; no claims of
   real traffic, flight status or baggage tracking. Not a travel platform.
2. Home preparation: she authorizes the arrival-preparation plan; the scene/command is simulated
   and labeled; command acknowledgement is recorded separately from physical success. During the
   flight monitoring continues quietly; missing phone location is "unavailable", not proof of
   schedule. Authorized urgent escalation is never suppressed to keep the story quiet.
3. Not responding (physical truth: thermostat offline, blower running without useful heat). ARIA
   states only: thermostat telemetry missing/stale; independent room sensors show no warming; a
   mapped HVAC electrical channel shows activity consistent with the blower where the fixture
   mapping supports it; electrical activity alone does not prove useful heat or the fault; other
   circuits show fresh activity, weighing against property-wide power loss in the observed
   interval, without ruling out partial or earlier outages or backup power. An independent room
   sensor is required; cached thermostat values are never current measurements; no invented
   failure mechanism.
4. Authorized help: ARIA alerts the manager within her authorization; the manager explicitly
   authorizes contacting the HVAC company on file; the request carries only approved, necessary
   property/contact/access info and relevant observations, never itinerary, email or location.
   Contact, visit and repair are simulated and labeled. No equipment control, hazardous repair
   guidance, real calls or messages.
5. Independent recovery detection (central moment): the technician repairs it; ARIA does not wait
   for a human report. On the next sensor update or scheduled poll, fresh thermostat telemetry
   resumes; reconnection triggers cross-source verification and does not close the issue alone.
   ARIA checks reported operating state, mapped electrical activity and independent room
   readings; later readings show warming, then the target reached and maintained for the
   documented verification period, and still met through arrival. Visible progression:
   "Thermostat reporting restored" -> "Warming observed" -> "Temperature goal verified" ->
   "Arrival expectation met".
6. The HVAC completion report reaches the manager after ARIA's sensor verification and becomes
   available to ARIA only afterward, if ingested at all; ordering explicit with timestamps.
   Neither a manager acknowledgement nor a technician report can set the verified outcome; a
   report may corroborate later. No future report information in an earlier replay or model
   context.
7. Ending: after landing she sees a concise, evidence-backed update and arrives to the warm home.
   Close: "Not just an automation completed. An expectation met." Suggested narration: "ARIA Home
   connects the plan, coordinates the response, and verifies the result, so coming home feels
   like coming home." Precise language: we verified recovery of the monitored temperature goal;
   we did not prove a repair caused it; no guarantee the equipment is fault-free; say "on the
   next sensor update", never "instantaneously".

docs/demo-script.md SECTIONS
A. Three-minute video plan: a timestamped storyboard totaling exactly 180 seconds; for each
   segment the hook/screen action/narration/on-screen text. It opens with one line stating what
   was pre-existing and what was built this week (organizer rule). A voiceover draft that fits
   at about 150 words per minute (state the word count per segment). Emphasize her problem and
   independent verification, not a dashboard tour; give real time to recovery and arrival.
B. Shot list: per shot, what the viewer sees, what must actually work, status (implemented /
   partial / missing / unverified, judged from the code), content type (synthetic / simulated /
   replayed / live inference), and an acceptance check.
C. Scenario timeline: ordered events with separate event time, received/available time and
   evaluation time for: trip confirmation and authorizations; preparation acknowledgement;
   thermostat outage and no warming; manager escalation and HVAC-contact authorization;
   simulated service visit; thermostat reconnection; warming evidence; target reached and
   maintained; repair report available; homeowner arrival. Any timing or threshold is a labeled
   scenario assumption, not validated physical behavior; reuse existing documented thresholds
   where they apply and say so.
D. Implementation gap map against the current repo: reusable working capabilities, small
   changes, missing capabilities, risks and unresolved decisions, minimum demo build vs optional
   real integrations. Email, calendar, GPS, travel estimates, service communications and scene
   control stay synthetic/simulated; do not propose real integrations for the video.
E. Acceptance criteria, at least: no fresh thermostat measurements while offline; independent
   room sensors carry the trend; electrical activity is not proof of useful heat; reconnection
   without warming cannot resolve; missing/stale follow-up readings give unable_to_verify; human
   reports cannot force physical resolution; sensor verification precedes report availability;
   target met through arrival; every authorization precedes the action it permits; no future-data
   leakage; no mock/cached output shown as a fresh live model response.
F. Production and safety rules: 3 minutes; only hackathon-built functionality, pre-existing
   concepts distinguished; label synthetic data, simulated communications/control and replay
   time jumps; real interface footage for functional claims; disclose shortened inference waits;
   exclude credentials, account pages, real travel details, private code and personal contacts.
G. The smallest build sequence to film it, decisions that need Brad, and claims to avoid.
Final answer: the files changed, and section G verbatim.

