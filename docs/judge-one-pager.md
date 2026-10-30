# ARIA Home — judge one-pager

## Problem

I live in Petoskey, Michigan, where the winters are long and cold. As my in-laws get older, I've started wondering what happens when they can't fix something, or can't tell that something is wrong, and nobody is around to help. As an electrician, I've worked on houses with major damage from a fault that nobody caught in time. ARIA Home is built to notice sooner and get the right person moving. It does not repair or control anything, and it is not a medical or emergency service.

## What it does

Answers one question for an older adult's household: will the home be warm by the warm-by time, and if something looks wrong overnight, who should respond? Code computes readiness (`on_track`, `at_risk`, `cannot_tell`, `arrival_passed`), follow-up outcomes from later measurements only, and recovery verification stages (`telemetry_missing` to `arrival_met`, shown as "Warm-by expectation met"). A model investigation explains the code-checked facts. The UI keeps verified facts (rendered by code) apart from interpretation (model-written, not verified). Notifications are simulated and scoped; acknowledgement never resolves anything. The resident's consent is recorded in the fixture: the resident sees everything, the family caregiver sees home status and observations, the HVAC company sees property, access note and observations only. See [Architecture diagram](architecture.svg).

## How Meta models are used

- **muse-spark-1.3** (runtime): explains code-checked facts under contract **inv-v3**; claim checks reject mismatches. Mock mode is the default; live runs go through the Meta Model API behind a gated provider.
- **sam-3.1** (visual evidence): the synthetic images carry recorded segmentation; the app is replay-only and never calls sam-3.1 at runtime.
- **muse-image-1.0**: only to create the synthetic fixture images; never called at runtime.
- All code was written by **muse-wonder-1.0** and **muse-spark-1.3**; every prompt and answer is in `docs/build-log/`.

## Safety rules

Synthetic data only; simulated delivery (cards read "Simulated, no message was sent"); per-audience field allowlists with refusals recorded; HVAC requests only after a caregiver authorization event; acknowledgement, visits and the completion report never set outcomes; no future data in replay; watts never prove heat; recovery means the monitored temperature goal, not a proven repair. No health data, no medical terms, no location tracking of the person, no fall or activity sensing.

## Evaluation (from docs/evaluation.md)

Builder-labeled cases on synthetic data; a small sample, not a benchmark of real homes. Offline (deterministic, no model): **22 cases across 10 scenarios** — combined 22/22 fully correct; thermostat-only 12; room-sensor-only 4; electrical-only 2; calendar-only 2. Single-source shortfalls fall back to unsupported answers rather than asserting the opposite. Live (operator-run, approved by Brad), cited separately and never merged: the 17-case run on snapshot 77cafc9 (inv-v2, muse-spark-1.3 via the Meta Model API) gave 11 valid with 11/11 readiness agreement and 6 rejected (stale or superseded readings cited as current); the after-arrival rerun on snapshot efdff57 (inv-v3, only the six after-arrival cases) gave 5 valid with 5/5 agreement and 1 rejected on a genuine claim-check catch. Both live runs predate the care story and used the trip-home scenarios; they are kept verbatim, not re-scored. Readiness agreement is enforced by the contract, so it shows contract-following, not independent judgment. Earlier runs are kept in docs/evaluation.md and are superseded, not current.

## How to run in 5 minutes

Python 3.12 and Node 22. Terminal 1: `cd backend`, make a venv, `pip install -r requirements.lock`, `pip install -r requirements-optional.lock`, `pip install -r requirements-dev.lock`, then `python -m flask --app aria_home.app:create_app run --port 5000`. Terminal 2: `cd frontend`, `npm ci`, `npm run dev`. Open the port-5173 page. Tests: `cd backend && python -m pytest -q`.

## What to click

1. Start the backend (port 5000) and frontend (port 5173) as above. 2. On port 5173, in "Demo controls (synthetic replay)", set "Scenario" to "Winter night, older adult at home (guided story)". 3. Click the replay buttons in order: 19:20, 02:31, 02:45, 04:21, 04:51, 06:21, 06:45, 07:01. 4. At 02:45, check the HVAC company card under "Notifications (simulated delivery)" and its "fields sent:" line; click "Acknowledge (simulated)" on the family caregiver card and confirm the Outcome headline does not change. At 06:45, find the "HVAC completion report" card — it appears only after the 06:21 verification, as corroboration only.

## Known limits

Synthetic data and simulated messages throughout; the app controls no equipment and is not a medical or emergency service. Room-sensor and blower mappings are assumptions; thresholds are fixed constants and projection is linear. Allowlists are hand-reviewed. The sample is small (22 offline cases, live runs on the older trip-home scenarios only) and agreement reflects contract-following. The claim check is bounded, not a semantic verifier. WhatsApp test delivery and the Emporia read-only panel are implemented but off by default; visual segmentation is replay-only recorded responses, never a live call.
