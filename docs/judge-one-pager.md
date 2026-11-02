# ARIA Home

Will an older adult's home be warm by morning, and if something looks wrong overnight, who should respond?

**Demo:** https://aria-home-demo.onrender.com (interactive, synthetic data, no sign-in)

## The problem

> "I live in Petoskey, Michigan, where the winters are long and cold. As my in-laws get older, I've started wondering what happens when they can't fix something, or can't tell that something is wrong, and nobody is around to help. As an electrician, I've worked on houses with major damage from a fault that nobody caught in time."

ARIA Home is built to notice sooner and get the right person moving. It does not repair or control anything, and it is not a medical or emergency service.

## What it does

It reads independent sources (room sensor, thermostat, electrical activity, calendar, weather, a camera) against a household's warm-by plan: 68 F by 7:00. In the synthetic story the evening starts warm and on track. At 9:00 PM the room is slowly falling but still on track. At 9:41 PM it is 66 F, 2 F below the target: code flags "at risk", ARIA records a notice and asks nobody. At 10:46 PM it is 62 F, 6 F below, and ARIA asks the family caregiver, "May I contact the HVAC company?" The 2 F and 6 F are configured settings, not safety limits, and a backstop still asks when the house is at risk within 2 hours of the warm-by time. The demo checks at set story times. She approves at 10:47 PM, and only then is a simulated HVAC request sent, with allowed fields only. The thermostat goes silent at 11:00 PM. A technician is on site at 11:30 PM, 44 minutes after the ask, and finishes at 12:15 AM, with the room at 56.6 F. The room rises at once. The thermostat returns at 12:20 AM, which proves nothing. Warming is seen by 12:31 AM, and the goal is verified at 1:40 AM from independent readings held for 30 minutes, under 3 hours after the ask. The technician's voice note at 1:50 AM counts only as a human report. At 7:01: "Warm-by expectation met".

Code decides readiness, verification and who is told; models explain and review, never decide. Every number cites the evidence it came from, replay never shows future data, and every message is simulated.

## Try it in two minutes

1. Open the demo and press **Start the warm-by story**.
2. Step through the 10 steps with **Next**. The **House** tab shows the verdict, the house right now, and who knows.
3. At the 10:46 PM step, press **Approve** or **Decline** on the caregiver's permission request. Decline means no HVAC contact — no request, visit, report or voice note — and the room readings are still checked at each later step; the house stays cold and 07:01 states the miss against the 68 F goal.
4. Open **Reasoning** to see ARIA's view: sources, code checks, where the model contributes, the recorded model answer and its second review.
5. Open **Integrations** for what ARIA connects to and which Meta model does what.
6. **Reset my session** clears only your own session.

## Where Meta models help

| Model | What it does here | What it never does |
|---|---|---|
| muse-spark-1.3 | Explains the code-checked facts at each step under a strict contract (claims checked against evidence; mismatches rejected); also runs as an anomaly watcher over the same evidence, each observation confirmed by code. The hosted demo shows recorded runs, labelled with their provenance. | Decide readiness, verification or who is told |
| muse-wonder-1.0 | A structured second review of each recorded answer. In a control test it flagged a deliberately falsified temperature, citing the real reading. | Change any result |
| sam-3.1 | Segments the synthetic camera frames (recorded). It found the blank thermostat display and missed the frost; the miss is shown as a miss. | Count as an all-clear when it finds nothing |
| muse-voice-transcribe-1.0 | Turns the technician's synthetic voice note into a text report. | Count as a measurement |
| muse-image-1.0 | Generated the synthetic camera frames, offline. | Run in the demo |

Meta's Muse models (muse-spark-1.3 and muse-wonder-1.0) wrote most of the application code; every prompt and answer is in the repository's build log. Claude (Anthropic) wrote the 2 F and 6 F alert rule and the final wording pass under Brad's direction, recorded in `docs/build-log/operator-log.md`.

## Measured results

- Offline, 22 builder-labelled synthetic cases across 10 scenarios: combined evidence 22/22 fully correct. Any single source alone does far worse (thermostat 12/22, room sensor 4/22, electrical 2/22, calendar 2/22), which is why ARIA uses independent sources.
- Recorded-model coverage is per-step: a muse-spark-1.3 answer that passed the contract checks, plus a muse-wonder-1.0 review. The main story has recordings at all 10 steps, on prompt inv-v5 [CONFIRM after the 10-step re-recording]. Recordings match on exact input, so a step without a match shows the labelled "No recorded model response for this snapshot" fallback; the derived decline branch shows the labelled deterministic fallback at its later changed checkpoints.
- Live runs on earlier trip-home scenarios: 11/11 and 5/5 valid answers agreed with code; the claim check caught the rest. That agreement shows contract-following, not independent judgment.
- On 12 simulated scenarios, run as one batch: muse-wonder-1.0 caught 12 of 12 planted false claims from four fixed templates, and the watcher's first answers failed code checks in 9 of 12. These scores were measured on the earlier prompt inv-v3, not re-scored on the current inv-v5.
- These are synthetic regression results, not real-world accuracy. Explanation quality from the current prompt has not been measured, and real-world effectiveness has not been established.

## Limits

- Synthetic data and simulated messages; no equipment control.
- A small, builder-labelled evaluation.
- Fixed thresholds, configured 2 F and 6 F alert settings and a linear projection; allowlists reviewed by hand.
- Optional real paths (WhatsApp to the owner's own number, a read-only Emporia energy panel, an owner-only Nest camera snapshot) are off in the hosted demo.
- The demo video also shows one labelled segment of the owner's own furnace and electrical panel, apart from the synthetic story, where sam-3.1 missed a visible red indicator light.
- Not a medical or emergency service.

Code, build log, tests and audit records: https://github.com/BoMa-AI-Cloud/aria-home
