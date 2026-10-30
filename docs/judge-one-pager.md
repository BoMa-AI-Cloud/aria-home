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
