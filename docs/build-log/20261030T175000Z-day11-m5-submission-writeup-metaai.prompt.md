Sent to Meta AI in the web chat (meta.ai, account saf_integration) by the operator on 2026-10-30.

Update a hackathon submission write-up. Reply ONLY with the new write-up as plain Markdown paragraphs in one code block (no headings). At most 420 words. Keep the builder's first-person voice and keep the opening paragraph's wording as close to the current one as possible. Same honesty rules: no marketing adjectives, no "secure", "guaranteed", "always", "0 hallucinations", no dollar figures, no winning predictions, no claim beyond the facts.

What changed since the current text was written (all true, use them):
- There is now a hosted demo: https://aria-home-demo.onrender.com (synthetic data, no sign-in). Put the link in the second paragraph.
- ARIA now asks the family caregiver for permission ("May I contact the HVAC company?"); the HVAC request is created only after she approves, and Decline means no request while ARIA keeps monitoring. In my own test the permission request and the HVAC notice can be sent to my own phone through the WhatsApp Cloud API (opt-in, test number only); the hosted demo keeps every message simulated.
- The app has three pages: House (the verdict and who knows), Reasoning (ARIA's view: a live map of how each decision is made, and the recorded model answers), Integrations.
- Meta models now in use: muse-spark-1.3 (explanations at each step, and an overnight anomaly watcher whose observations code confirms); muse-wonder-1.0 (a recorded second review of each explanation; a control test showed it flags a falsified reading); sam-3.1 (recorded segmentation of synthetic camera frames; it missed frost, and the miss is shown); muse-voice-transcribe-1.0 (the technician's voice note, as a human report only); muse-image-1.0 (synthetic frames). Code written by muse-spark-1.3 and muse-wonder-1.0 with Claude Code as operator; every prompt and answer is in the public build log. When the Model API was unavailable for a few hours, Meta AI in the web chat drafted some code, which the operator applied and retested; those prompts and answers are in the build log too.
- Optional owner-only integrations, off in the hosted demo: a read-only Emporia energy panel and a Nest camera snapshot of my mechanical room (one frame on request; upload to sam-3.1 only on a second button).
- Audits: Audit 3 reported 12 defects, all reproduced, fixed and tested. Audit 4 reported 10, all fixed and each red-proofed (fix undone, test seen failing, fix restored). Audit 5 reported 7 (decision-map consistency, session admission, a write before validation, review-to-answer binding, dependency advisories, a malformed-input 500); they are repaired with regression tests before release. Say this in one or two sentences; no defect list.
- All 10 care-story steps have recorded muse-spark-1.3 answers that passed the contract checks, each with a muse-wonder-1.0 review.
Keep the existing evaluation numbers and limits as they are.

CURRENT WRITE-UP:
I live in Petoskey, Michigan, where the winters are long and cold. As an electrician, I've worked on houses with
major damage from a fault that nobody caught in time. ARIA Home is built to help notice sooner and get the right
person moving. It does not repair or control anything.

ARIA Home answers one question for an older adult's household: will the home be warm by the warm-by time, and if
something looks wrong overnight, who should respond? On a synthetic winter night the furnace stops and the
thermostat stops reporting; an independent room sensor shows the living area cooling toward 52 F. ARIA Home flags
the risk before the household 07:00 warm-by time, notifies the resident and an adult-child family caregiver under the
resident's recorded consent, and the caregiver authorizes the simulated HVAC request. It combines the warm-by plan,
consent, thermostat, room-sensor, electrical, weather (forecast context only, never a decision input) and
visual evidence (all synthetic) into one readiness picture. Code decides readiness, follow-ups and outcomes;
muse-spark-1.3 explains only code-checked facts, and claim checks reject any answer that cites the wrong evidence
or presents an old reading as current. Electrical activity is never treated as heat, a visual "nothing detected"
is never treated as an all-clear, an acknowledgement is not a resolution, and recovery is verified only from later
independent temperature readings. This is temperature-goal verification, not proof of a repair. ARIA Home is not
a medical or emergency service: no health data, no medical terms, no location tracking of the person, no fall or
activity sensing.

Notifications are scoped per audience with recorded refusals and stay simulated by default. As an opt-in test,
the HVAC request was delivered to my own phone through the WhatsApp Cloud API with only its allowed fields.

Meta models: muse-spark-1.3 at runtime; sam-3.1 segmentation over synthetic images is replay-only recorded responses (no live call, no opt-in); muse-image-1.0 made the synthetic test images. All application code was written by muse-wonder-1.0 and
muse-spark-1.3 through Claude Code, which acted as operator; every prompt and answer, including failed runs, is in
the public build log. That is my disclosure; the log shows what was recorded.

An independent audit reported 12 defects; all 12 were reproduced, fixed and covered by regression tests ([defect matrix](audit-3.md)).
Offline: 22 synthetic cases across 10 scenarios, combined evidence 22/22. The five `care_home_v1` night cases score
readiness and verification from independent room readings up to the 07:00 warm-by time. Live (muse-spark-1.3): 11 of 17 valid on
the full run; after a contract fix, the six after-arrival cases were rerun and 5 of 6 were valid. Both live runs
predate the care story and used the trip-home scenarios; they are kept verbatim, not re-scored. In the visual
probe sam-3.1 missed obvious frost on a pipe, which is why "no detection" never lowers risk — the care night frames
carry the same recorded misses.
Limits: small synthetic sample, simulated delivery, no equipment control.

FACTS:
- Builder's words: "I live in Petoskey, Michigan, where the winters are long and cold. As my in-laws get older, I've started wondering what happens when they can't fix something, or can't tell that something is wrong, and nobody is around to help. As an electrician, I've worked on houses with major damage from a fault that nobody caught in time. ARIA Home is built to notice sooner and get the right person moving. It does not repair or control anything, and it is not a medical or emergency service."
- The question it answers: will an older adult's home be warm by morning (a "warm-by" time, 7:00 at 68 F), and if something looks wrong overnight, who should respond?
- Story (synthetic winter night): the furnace stops and the thermostat goes silent at 1:30; an independent room sensor shows the room falling to 52 F; at 2:31 code flags "at risk before 7:00"; ARIA asks the family caregiver (her daughter) "May I contact the HVAC company?"; only after she approves is a simulated HVAC request sent with allowed fields only (property, access note, observations; no personal details); the technician visits; reconnection alone proves nothing; warming is seen at 4:51; the goal is verified at 6:21 from independent readings held 30 minutes; the technician's voice note arrives 6:45 as a human report, corroboration only; at 7:01 "Warm-by expectation met".
- Code decides readiness, verification and who is notified; models explain and review but never decide. Every number shown cites the evidence it came from. Replay never shows future data. Messages are simulated ("Simulated, no message was sent"). It controls no equipment.
- The hosted app has three tabs: House (the verdict, the house right now, who knows), Reasoning (ARIA's view: a live map of sources, code checks, the model's contribution and the decision; the recorded model answer and its second review), Integrations (what it connects to and the Meta models). The guided story has 10 steps with Back/Next. On the caregiver card a judge can press Approve or Decline; decline means no HVAC request and ARIA keeps monitoring. "Reset my session" clears only that visitor's session.
- Meta models: muse-spark-1.3 explains the code-checked facts at each step under a strict contract (claims checked against evidence; mismatches rejected), and also acts as an overnight anomaly watcher whose observations are confirmed by code checks; in the hosted demo its answers are recorded runs, labelled as recorded with their provenance. muse-wonder-1.0 gives a structured second review of each recorded answer (in a control test it flagged a deliberately falsified temperature as a contradiction, citing the real reading). sam-3.1 segments the synthetic camera frames (recorded; it found a blank thermostat display and missed frost, and the miss is shown as a miss). muse-voice-transcribe-1.0 turned the technician's synthetic voice note into a text report, used as corroboration only. muse-image-1.0 generated the synthetic camera frames (offline only). The application code was written with muse-spark-1.3 and muse-wonder-1.0, with every prompt and answer kept in the repository's build log.
- Measured: offline, 22 builder-labelled synthetic cases across 10 scenarios: combined evidence 22/22 fully correct; any single source alone far fewer (thermostat only 12/22, room sensor only 4/22, electrical only 2/22, calendar only 2/22), showing why independent sources matter. All 10 care-story steps have recorded muse-spark-1.3 answers that passed the contract checks, and all 10 have a muse-wonder-1.0 review. Live runs on older trip-home scenarios: 11/11 and 5/5 valid answers agreed with code, with rejected answers caught by the claim check; agreement reflects contract-following, not independent judgment. These are synthetic regression results, not real-world accuracy.
- Optional, off in the hosted demo: WhatsApp test delivery to the owner's own number, a read-only Emporia energy panel, and an owner-only Nest camera snapshot. Outside audits found and the project fixed defects before release; the repository keeps the audit records.
- Limits: synthetic data and simulated messages; small builder-labelled evaluation; fixed thresholds and linear projection; allowlists hand-reviewed; not a medical or emergency service; no equipment control.
