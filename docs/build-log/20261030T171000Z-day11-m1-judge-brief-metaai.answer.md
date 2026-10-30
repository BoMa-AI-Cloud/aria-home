Operator's note: Judge one-pager draft; operator removed entity tags, restored Brad's own words, dropped an unsupported camera-threshold claim.

--- Meta AI reply (verbatim) ---
# ARIA Home
Will the home be warm by morning (7:00 at 68 F) and who should respond if not?
https://aria-home-demo.onrender.com (interactive, synthetic data, no sign-in)

## The problem
In Petoskey, Michigan, winters are long and cold and a fault nobody catches can become major damage. As an electrician, the builder has seen that damage; he notes, "I've started wondering what happens when they can't fix something". ARIA Home is built to notice sooner and get the right person moving. It does not repair or control anything, and it is not a medical or emergency service.

## What it does
ARIA Home answers: will an older adult's home be warm by morning, and if something looks wrong overnight, who should respond? It checks independent sources — thermostat, room sensor, electrical, calendar, camera — against code thresholds and a linear projection to a warm-by time. In the synthetic story, furnace and thermostat go silent at 1:30, room falls to 52 F, code flags at-risk at 2:31, ARIA asks the daughter caregiver for approval to contact HVAC, sends a simulated request with allowed fields only (property, access note, observations; no personal details), sees warming at 4:51, verifies the goal at 6:21 from independent readings held 30 minutes, and shows technician voice note at 6:45 as human report, corroboration only, with warm-by expectation met at 7:01. Code decides readiness, verification and who is notified; models explain and review but never decide; every number shown cites the evidence it came from; replay never shows future data; messages are marked "Simulated, no message was sent"; it controls no equipment.

## Try it in two minutes
1. Open the demo — start on House tab to see the verdict, the house right now, and who knows.
2. Use Back/Next through the 10-step guided story.
3. Open Reasoning tab to see ARIA's view: live map of sources, code checks, model contribution, recorded model answer and its second review.
4. On the caregiver card press Approve to see simulated HVAC request, or Decline to see no request and continued monitoring.
5. Open Integrations tab to see what it connects to and the 【entity-Meta¦canonical_name=Meta】 models.
6. Press Reset my session to clear only that visitor's session.

## Where 【entity-Meta¦canonical_name=Meta】 models help
| model | what it does here | what it never does |
| --- | --- | --- |
| muse-spark-1.3 | explains code-checked facts each step under strict contract (claims checked against evidence; mismatches rejected); overnight anomaly watcher confirmed by code checks; in hosted demo answers are recorded runs labelled as recorded with provenance; also used to write application code with prompts kept in build log | does not decide readiness, verification, or notification; does not control equipment |
| muse-wonder-1.0 | structured second review of each recorded answer; in control test flagged deliberately falsified temperature as contradiction citing real reading; also used to write application code with prompts kept in build log | does not decide readiness or send messages |
| sam-3.1 | segments synthetic camera frames (recorded); found blank thermostat display and missed frost, miss shown as miss | does not decide readiness or verification |
| muse-voice-transcribe-1.0 | turned technician synthetic voice note into text report, used as corroboration only | does not verify warming |
| muse-image-1.0 | generated synthetic camera frames offline only | does not run in live demo; does not decide |

## Measured results
- Scope: offline 22 builder-labelled synthetic cases across 10 scenarios — combined evidence 22/22 fully correct; single source alone far fewer (thermostat only 12/22, room sensor only 4/22, electrical only 2/22, calendar only 2/22), showing why independent sources matter.
- Scope: 10 care-story steps — all 10 have recorded muse-spark-1.3 answers that passed contract checks, and all 10 have a muse-wonder-1.0 review.
- Scope: live runs on older trip-home scenarios — 11/11 and 5/5 valid answers agreed with code, with rejected answers caught by claim check; agreement reflects contract-following, not independent judgment.
- Scope note: these are synthetic regression results, not real-world accuracy.

## Limits
- Synthetic data and simulated messages.
- Small builder-labelled evaluation.
- Fixed thresholds and linear projection; allowlists hand-reviewed.
- Not a medical or emergency service.
- No equipment control.

code, build log and tests are in the public GitHub repository github.com/BoMa-AI-Cloud/aria-home.