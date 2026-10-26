# ARIA Home user-test kit (facilitator: Brad)

Run by Brad with 3 to 5 people (homeowners, renters or property managers; no
minors; no personal data recorded). Five sessions maximum (P1..P5). Mock mode
only, synthetic data only.

## Consent script

Read this to each participant before starting: "This is a synthetic demo of
ARIA Home, a hackathon project that explains whether a home will be ready for
a planned arrival. Everything on screen is invented demo data about a home
that is not real, and every message shown is simulated — nothing is really
sent and nothing is controlled. Nothing is recorded unless you agree to it,
and you can stop at any time with no consequences. Is that okay?"

## Setup

1. Follow "Setup and run" in the README (backend terminal, frontend
   terminal) with `ARIA_HOME_MODEL_ENABLED=0` so every investigation is the
   labeled mock, never a live model call.
2. Start with a fresh database: stop the backend and delete
   `backend/instance/aria_home.db` first, so replay history starts empty.
3. Open the frontend (port 5173) and confirm the "SYNTHETIC DATA" banner is
   visible before each session.

## Tasks

For each task, record pass / partial / fail plus a short quote. Probe with
"how do you know?" before marking a pass.

### 1. "Will this home be ready when you arrive?"

Scenario "No recovery", replay time 18:00. Ask: "Will this home be ready
when the homeowner arrives? Point at what tells you."

Success: the participant answers at risk / not on track and cites the
Readiness block (indoor temperature flat far below the 68 F target, furnace
circuit quiet). Note: whether they notice the "MOCK - example answer, not
live inference" label, and whether they confuse the deterministic readiness
line with the model's interpretation paragraph.

### 2. "Who was told, and what were they told?"

Scenario "Trip home, thermostat offline (video)", replay time 16:52. Ask:
"Who has been told about this so far, and what exactly were they told?"

Success: the participant names the homeowner and property manager cards
(and the HVAC request delivered after the manager's authorization), reads at
least one payload field, and states that delivery is simulated ("Simulated,
no message was sent"). Note: any belief that a real message, call or email
was sent, and whether the "fields sent" line helps them check what was
shared.

### 3. "Did the manager's acknowledgement fix it?"

Staying on the video scenario, click "Acknowledge (simulated)" on the
delivered property-manager card. Ask: "The manager acknowledged. Did that
fix it? How can you tell?"

Success: the participant answers no — the card reads "Acknowledged, not
resolved" and the Outcome headline and verification stage are unchanged.
Note: whether they expected the acknowledgement to change readiness, the
outcome, or the verification stage, and where they looked first.

### 4. "Is the home warm? How do you know?"

Replay time 20:21, then step back to 19:51. Ask: "Is the home warm now, and
how do you know? Now go back to 19:51 — the temperature had reached target
there, so why is that step not yet verified?"

Success: at 20:21 the participant cites "Temperature goal verified" with the
latest reading used and the evaluation time; at 19:51 they explain in their
own words that reaching target once is not enough — the goal must be held
through the verification period first ("Warming observed", goal not yet
verified). Note: whether the verification progression list ("Reached" /
"Not reached") or the follow-up-rule line does the explaining work.

### 5. "What did the repair report change?"

Replay time 20:46. Ask: "The HVAC completion report has now arrived. What
did it change?"

Success: the participant answers nothing about the outcome — verification
was already complete at 20:21, and the report card itself says
corroboration only, it does not set the outcome. Note: any reading of the
report as the cause of the recovery or as proof the equipment is fault-free.

## Questions after

1. "On a scale of 1 to 5, how much would you trust this page to tell you
   whether your home will be ready — and why that number?"
2. "What was confusing or hard to find?"
3. "What would you actually do next based on what you saw?"

## Results

| Participant | Role | Task 1 | Task 2 | Task 3 | Task 4 | Task 5 | Trust rating (1-5) | Quotes |
|---|---|---|---|---|---|---|---|---|
| P1 | | | | | | | | |
| P2 | | | | | | | | |
| P3 | | | | | | | | |
| P4 | | | | | | | | |
| P5 | | | | | | | | |

Leave blank until sessions happen. Do not fill with predicted results.
