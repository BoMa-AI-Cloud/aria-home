Sent to Meta AI in the web chat (meta.ai, account saf_integration) by the operator on 2026-10-30.

Rewrite the opening of a GitHub README for hackathon judges. Reply ONLY with Markdown in one code block: the new text from the "# ARIA Home" title up to (not including) the next section, which is "## Built during the hackathon vs pre-existing".

Order:
1. "# ARIA Home" and a one-line subtitle (the question it answers).
2. A line with the live demo link https://aria-home-demo.onrender.com and "(synthetic data, no sign-in)", and a line "Video: <video link>" (keep that placeholder exactly).
3. The builder's paragraph, kept word for word (it is in CURRENT TEXT).
4. "## What judges should click": at most 6 numbered steps for the hosted demo, matching the JUDGE BRIEF's steps (tabs House / Reasoning / Integrations; Approve or Decline at 2:31; Reset my session). Then one short sentence: "To run it locally, see Try it in 5 minutes below."
5. One short paragraph "What it is" (4 sentences at most): the question, code decides / models explain, scoped simulated notifications, verification from later independent readings (temperature-goal verification, not proof of a repair), not a medical or emergency service.
Remove the long endpoint list and the old local click-through from this opening (the local steps stay further down the README). Keep the hackathon line: solo entry in the Meta Global AI Developer Hackathon (Indie Developer track, theme "Build for Your World").
Rules: plain and factual, no marketing adjectives, no emojis, no claims beyond the two texts below; exact model names (muse-spark-1.3, muse-wonder-1.0, sam-3.1, muse-voice-transcribe-1.0, muse-image-1.0), never "llama". At most 320 words.

CURRENT TEXT:
# ARIA Home

I live in Petoskey, Michigan, where the winters are long and cold. As my in-laws get older, I've started wondering what happens when they can't fix something, or can't tell that something is wrong, and nobody is around to help. As an electrician, I've worked on houses with major damage from a fault that nobody caught in time. ARIA Home is built to notice sooner and get the right person moving. It does not repair or control anything, and it is not a medical or emergency service.

## What judges should click

On the public demo link (Pending deployment — see "Public demo mode" below): the landing states the purpose and disclosure ("Interactive demo · Synthetic home data · Simulated notifications · Recorded model responses where indicated · No equipment control"). Click "Start the warm-by story" and step through all ten checkpoints to "Warm-by expectation met", opening "Explore evidence" at any step for sources, deterministic readiness/verification reasons, the recorded-or-fallback interpretation, per-audience fields sent and refused, and the model-role matrix. At any step, "See ARIA's view of this step" opens the live decision map: sources on the left, code checks next, the code-computed decision, then notices, with streaks that glow on pass, stop amber-red on a failed check, and violet only for the model watcher. "Reset my session" clears only your session. Or run it locally:

1. Start the backend (port 5000) and frontend (port 5173) as in "Try it in 5 minutes" below.
2. Open the page on port 5173. In "Demo controls (synthetic replay)", set "Scenario" to "Winter night, older adult at home (guided story)".
3. Click the replay buttons in order: 19:20, 02:31, 02:45, 04:21, 04:51, 06:21, 06:45, 07:01.
4. At 02:45, check the HVAC company card under "Notifications (simulated delivery)" and its "fields sent:" line; click "Acknowledge (simulated)" on the family caregiver card and confirm the Outcome headline does not change. At 06:45, find the "HVAC completion report" card — it appears only after the 06:21 verification, as corroboration only.

ARIA Home answers one question for an older adult's household: **Will the home be warm by the warm-by time, and if something looks wrong overnight, who should respond?**

It is a solo entry in the Meta Global AI Developer Hackathon (Indie Developer track, theme "Build for Your World").

The core idea is simple: a furnace stopping overnight is not the household's expectation met. ARIA Home connects the evidence — the resident's warm-by plan and consent, thermostat, an independent room sensor, electrical and weather records (weather is forecast context only and never decides readiness), plus synthetic visual segmentation evidence — coordinates authorized help when something looks wrong, independently detects recovery from later readings, and verifies the result before it reports an outcome. It watches a winter night for an older adult living alone, flags the risk before the household warm-by time, and verifies the recovery — temperature-goal verification, not proof of a repair. It is not a medical or emergency service: no health data, no medical terms, no location tracking of the person, no fall or activity sensing.

What works now: a code-computed readiness status explained by a model investigation, deterministic power context with stated limitations, scoped simulated notifications to the resident and family caregiver, follow-up outcomes checked against later measurements, recovery verification stages from `telemetry_missing` to `arrival_met` (shown as "Warm-by expectation met"), and a labeled simulated timeline with replay through the warm-by time. Key endpoints include `GET /api/health`, `GET /api/sources`, `GET /api/provider`, `GET /api/metrics`, `GET /api/power-context`, `GET /api/investigation`, `POST /api/investigations`, `GET /api/follow-ups/<id>`, `GET /api/events`, `GET /api/trace` (read-only decision map behind "ARIA's view", deterministic code only, never a model call), `GET /api/visual` and `GET /api/visual/image` (synthetic SAM segmentation evidence, recorded by default), and `GET /api/live-power` (optional Emporia read-only panel, off by default).



JUDGE BRIEF:
# ARIA Home

Will an older adult's home be warm by morning, and if something looks wrong overnight, who should respond?

**Demo:** https://aria-home-demo.onrender.com (interactive, synthetic data, no sign-in)

## The problem

> "I live in Petoskey, Michigan, where the winters are long and cold. As my in-laws get older, I've started wondering what happens when they can't fix something, or can't tell that something is wrong, and nobody is around to help. As an electrician, I've worked on houses with major damage from a fault that nobody caught in time."

ARIA Home is built to notice sooner and get the right person moving. It does not repair or control anything, and it is not a medical or emergency service.

## What it does

It watches independent sources (room sensor, thermostat, electrical activity, calendar, weather, a camera) against a household's warm-by plan: 68 F by 7:00. In the synthetic story the furnace stops and the thermostat goes silent at 1:30. The room sensor shows the room falling to 52 F, and at 2:31 code flags "at risk before 7:00". ARIA asks the family caregiver, "May I contact the HVAC company?" Only after she approves is a simulated HVAC request sent, with allowed fields only. Warming is seen at 4:51, and the goal is verified at 6:21 from independent readings held for 30 minutes. The technician's voice note at 6:45 counts only as a human report. At 7:01: "Warm-by expectation met".

Code decides readiness, verification and who is told; models explain and review, never decide. Every number cites the evidence it came from, replay never shows future data, and every message is simulated.

## Try it in two minutes

1. Open the demo and press **Start the warm-by story**.
2. Step through the 10 steps with **Next**. The **House** tab shows the verdict, the house right now, and who knows.
3. At 2:31, press **Approve** or **Decline** on the caregiver's permission request. Decline means no HVAC request, and ARIA keeps monitoring.
4. Open **Reasoning** to see ARIA's view: sources, code checks, where the model contributes, the recorded model answer and its second review.
5. Open **Integrations** for what ARIA connects to and which Meta model does what.
6. **Reset my session** clears only your own session.

## Where Meta models help

| Model | What it does here | What it never does |
|---|---|---|
| muse-spark-1.3 | Explains the code-checked facts at each step under a strict contract (claims checked against evidence; mismatches rejected); also watches for overnight anomalies, each confirmed by code. The hosted demo shows recorded runs, labelled with their provenance. | Decide readiness, verification or who is told |
| muse-wonder-1.0 | A structured second review of each recorded answer. In a control test it flagged a deliberately falsified temperature, citing the real reading. | Change any result |
| sam-3.1 | Segments the synthetic camera frames (recorded). It found the blank thermostat display and missed the frost; the miss is shown as a miss. | Count as an all-clear when it finds nothing |
| muse-voice-transcribe-1.0 | Turns the technician's synthetic voice note into a text report. | Count as a measurement |
| muse-image-1.0 | Generated the synthetic camera frames, offline. | Run in the demo |

The application code was written with muse-spark-1.3 and muse-wonder-1.0; every prompt and answer is in the repository's build log.

## Measured results

- Offline, 22 builder-labelled synthetic cases across 10 scenarios: combined evidence 22/22 fully correct. Any single source alone does far worse (thermostat 12/22, room sensor 4/22, electrical 2/22, calendar 2/22), which is why ARIA uses independent sources.
- All 10 care-story steps have recorded muse-spark-1.3 answers that passed the contract checks, and a muse-wonder-1.0 review each.
- Live runs on earlier trip-home scenarios: 11/11 and 5/5 valid answers agreed with code; the claim check caught the rest. That agreement shows contract-following, not independent judgment.
- These are synthetic regression results, not real-world accuracy.

## Limits

- Synthetic data and simulated messages; no equipment control.
- A small, builder-labelled evaluation.
- Fixed thresholds and a linear projection; allowlists reviewed by hand.
- Optional real paths (WhatsApp to the owner's own number, a read-only Emporia energy panel, an owner-only Nest camera snapshot) are off in the hosted demo.
- Not a medical or emergency service.

Code, build log, tests and audit records: https://github.com/BoMa-AI-Cloud/aria-home
