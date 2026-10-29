# ARIA Home — judge one-pager

## Problem

I live in Petoskey, Michigan, where the winters are long and cold. As an electrician, I've worked on houses with major damage from a fault that nobody caught in time. ARIA Home is built to help notice sooner and get the right person moving. It does not repair or control anything.

## What it does

Answers one question for a returning homeowner: will the property be ready on arrival, and if something looks wrong, who should respond? Code computes readiness (`on_track`, `at_risk`, `cannot_tell`, `arrival_passed`), follow-up outcomes from later measurements only, and recovery verification stages (`telemetry_missing` to `arrival_met`). A model investigation explains the code-checked facts. The UI keeps verified facts (rendered by code) apart from interpretation (model-written, not verified). Notifications are simulated and scoped; acknowledgement never resolves anything. See [Architecture diagram](architecture.svg).

## How Meta models are used

- **muse-spark-1.3** (runtime): explains code-checked facts under contract **inv-v3**; claim checks reject mismatches. Mock mode is the default; live runs go through the Meta Model API behind a gated provider.
- **sam-3.1** (visual evidence): segments the synthetic images; recorded replay is the default and live segmentation is opt-in.
- **muse-image-1.0**: only to create the synthetic fixture images; never called at runtime.
- All code was written by **muse-wonder-1.0** and **muse-spark-1.3**; every prompt and answer is in `docs/build-log/`.

## Safety rules

Synthetic data only; simulated delivery (cards read "Simulated, no message was sent"); per-audience field allowlists with refusals recorded; HVAC requests only after a manager authorization event; acknowledgement, visits and the completion report never set outcomes; no future data in replay; watts never prove heat; recovery means the monitored temperature goal, not a proven repair.

## Evaluation (from docs/evaluation.md)

Builder-labeled cases on synthetic data; a small sample, not a benchmark of real homes. Offline (deterministic, no model): **17 cases across 9 scenarios** — combined 17/17 fully correct; thermostat-only 12; room-sensor-only 3; electrical-only 2; calendar-only 2. Single-source shortfalls fall back to unsupported answers rather than asserting the opposite. Live (operator-run, approved by Brad), cited separately and never merged: the 17-case run on snapshot 77cafc9 (inv-v2, muse-spark-1.3 via the Meta Model API) gave 11 valid with 11/11 readiness agreement and 6 rejected (stale or superseded readings cited as current); the after-arrival rerun on snapshot efdff57 (inv-v3, only the six after-arrival cases) gave 5 valid with 5/5 agreement and 1 rejected on a genuine claim-check catch. Readiness agreement is enforced by the contract, so it shows contract-following, not independent judgment. Earlier runs are kept in docs/evaluation.md and are superseded, not current.

## How to run in 5 minutes

Python 3.12 and Node 22. Terminal 1: `cd backend`, make a venv, `pip install -r requirements.lock`, `pip install -r requirements-dev.txt`, then `python -m flask --app aria_home.app:create_app run --port 5000`. Terminal 2: `cd frontend`, `npm ci`, `npm run dev`. Open the port-5173 page. Tests: `cd backend && python -m pytest -q`.

## What to click

1. Start the backend (port 5000) and frontend (port 5173) as above. 2. On port 5173, in "Demo controls (synthetic replay)", set "Scenario" to "Trip home, thermostat offline (video)". 3. Click the replay buttons in order: 16:31, 16:52, 18:21, 18:51, 19:51, 20:21, 20:46, 21:01. 4. At 16:52, check the HVAC company card under "Notifications (simulated delivery)" and its "fields sent:" line; click "Acknowledge (simulated)" on the property manager card and confirm the Outcome headline does not change. At 20:46, find the "HVAC completion report" card — it appears only after the 20:21 verification, as corroboration only.

## Known limits

Synthetic data and simulated messages throughout; the app controls no equipment. Room-sensor and blower mappings are assumptions; thresholds are fixed constants and projection is linear. Allowlists are hand-reviewed. The sample is small (17 offline cases, one live run per case) and agreement reflects contract-following. The claim check is bounded, not a semantic verifier. WhatsApp test delivery, the Emporia read-only panel and live sam-3.1 segmentation are implemented but off by default.
