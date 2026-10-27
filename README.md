# ARIA Home

ARIA Home answers one question for a returning homeowner: **Will my property be ready when I arrive, and if something looks wrong, who should respond?**

It is a solo entry in the Meta Global AI Developer Hackathon (Indie Developer track, theme "Build for Your World").

The core idea is simple: an automation starting is not the homeowner's expectation met. ARIA Home connects the evidence — a planned trip, thermostat, room-sensor, electrical and weather records — coordinates authorized help when something looks wrong, independently detects recovery from later readings, and verifies the result before it reports an outcome.

What works now: a code-computed readiness status explained by a model investigation, deterministic power context with stated limitations, scoped simulated notifications to the homeowner and property manager, follow-up outcomes checked against later measurements, recovery verification stages from `telemetry_missing` to `arrival_met`, and a labeled simulated timeline with replay through arrival. Key endpoints include `GET /api/health`, `GET /api/sources`, `GET /api/provider`, `GET /api/metrics`, `GET /api/power-context`, `GET /api/investigation`, `POST /api/investigations`, `GET /api/follow-ups/<id>`, and `GET /api/events`.

## Built during the hackathon vs pre-existing

As the demo video's opening line says: "ARIA is my existing personal-assistant project. Its name, planning notes, and ARIA Home designs predate this event. All ARIA Home code shown was written this week with Meta's Muse models."

In short:

- **Built during the hackathon:** all code in this repository — backend, frontend, tests, synthetic scenarios and fixtures, and these docs. No code, data, fixtures or assets from any earlier project are in this repository. The full file-by-file list is in [Existing vs new](docs/existing-vs-new.md).
- **Pre-existing:** the name "ARIA" and private pre-event planning notes and ARIA Home designs (designs, no code). This repository itself contains no code from any earlier project.

## How Meta models are used

At runtime the app calls one Meta model, **muse-spark-1.3**, through the Meta Model API, behind a gated live provider. Mock mode is the default and needs no key. Every model the app calls at runtime is a Meta model.

The investigation uses the **inv-v2** contract, which binds the model's claims to the evidence. The model returns structured `facts[]`; each claim type may cite only its allowed evidence fields, values are checked against the evidence pack, and the facts shown as "Verified facts (checked against the evidence)" are rendered by code, not by the model. The model's own wording stays separate under "Interpretation (model-written, not verified)".

The model may explain a computed status, describe supporting and conflicting evidence, and suggest what observation to make at a follow-up. It may not decide:

- **Readiness** — computed in code in `backend/aria_home/readiness.py` (`on_track`, `at_risk`, `cannot_tell`, `arrival_passed`). The prompt states the computed status and any answer that disagrees is rejected. If no valid answer is produced, the app shows a deterministic summary computed by code.
- **Follow-up scheduling** — computed in code; any time the model supplies is checked and replaced if it falls outside the allowed window.
- **Outcomes and recovery verification** — computed in code from later measurements only (`backend/aria_home/outcomes.py`, `backend/aria_home/verification.py`). Human statements and events never set an outcome or advance a verification stage.

The full rules and thresholds are in [Readiness rules](docs/readiness-rules.md).

The application code itself was written by **muse-wonder-1.0** and **muse-spark-1.3** through Claude Code. Every prompt and answer, failed runs included, is in [docs/build-log/](docs/build-log/README.md). The operator (Claude, directed by Brad Wentzel) wrote the prompts, reviewed and tested each change, ran the approved installs and live smoke tests, and pushed the commits.

## Results

These are builder-labeled cases on synthetic data — a small sample, not a benchmark of real homes. Full details: [Evaluation](docs/evaluation.md).

**Offline (deterministic, no model):** 12 cases across 7 synthetic scenarios, each run with all sources combined and with only one source kind at a time.

| Condition | Fully correct (of 12) |
|---|---|
| Combined (all sources) | 12 |
| Thermostat only | 8 |
| Room sensor only | 3 |
| Electrical only | 3 |
| Calendar only | 3 |

Combined evidence matches every expected readiness label and every scored verification stage. Single-source conditions mostly fall back to unsupported answers (`cannot_tell`, `telemetry_missing`, `unable_to_verify`) rather than asserting the opposite. Two findings stand out: during the thermostat outage, thermostat-only evidence cannot support even a current-temperature claim, while independent room readings still show no warming; and electrical activity alone never supports a useful-heat claim — only temperature evidence can show warming.

**Live (operator-run, approved by Brad):** 24 calls — the 12 cases on muse-spark-1.3 and on muse-wonder-1.0, no retries. Both models returned 12/12 valid answers with **0 of 24 rejected** by the claim checks. Read the agreement figure honestly: readiness agreement is enforced (the model is told the computed status and a mismatch is rejected), so 24/24 agreement shows the models followed the contract, not that they judged readiness independently. The meaningful result is the 0 rejections. It was one run per case, input-token counts are unreliable, and the live run used the pre-Day-7 readiness labels, so it did not exercise the later `arrival_passed` target-at-arrival rule. No winner is declared on quality.

## Try it in 5 minutes

Mock mode is the default: no environment variables and no API key are needed, and the investigation is labeled "MOCK - example answer, not live inference".

Terminal 1 — backend, from the repo root:

```
# Windows PowerShell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```
# macOS / Linux shells
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```
python -m flask --app aria_home.app:create_app run --port 5000
```

Terminal 2 — frontend, from the repo root:

```
cd frontend
npm ci
npm run dev
```

Open the page it serves on port 5173 (it proxies `/api` to port 5000). Stop each server with Ctrl+C.

**The video scenario:** in "Demo controls (synthetic replay)", set "Scenario" to "Trip home, thermostat offline (video)" — selecting it runs the investigation at 16:31. Then click the replay buttons in order: **16:31, 16:52, 18:21, 18:51, 19:51, 20:21, 20:46, 21:01**. Watch the Outcome headline move from "Thermostat telemetry missing" to "Thermostat reporting restored" (18:21 — reconnection alone closes nothing), "Warming observed" (18:51 and still at 19:51, goal reached but not yet verified), "Temperature goal verified" (20:21), and "Arrival expectation met" (21:01). At 16:52, check the delivered HVAC company card under "Notifications (simulated delivery)" and its "fields sent:" line; click "Acknowledge (simulated)" on the property manager card and confirm the Outcome headline does not change. At 20:46, find the "HVAC completion report" card on the simulated timeline — it appears only after the 20:21 verification, as corroboration only. The full shot list is in [Demo video plan](docs/demo-script.md).

**Tests:** with the backend environment active, `python -m pytest -q` runs the backend tests. In a third terminal from `frontend/`:

```
npm run build
npm run typecheck
npm run test:e2e
```

`npm run test:e2e` starts its own backend and frontend servers on ports 5000 and 5173, so stop the dev servers first. It starts the backend with plain `python -m flask ...`, so the backend virtual environment must be active in that terminal (or Flask must be installed for that python). Activate it first: PowerShell `..\backend\.venv\Scripts\Activate.ps1`, macOS/Linux `source ../backend/.venv/bin/activate`. It runs the Playwright end-to-end test in the installed Google Chrome (no browser download).

**Recording footage:** `cd frontend && npm run record:demo` drives the real running frontend and backend at 1280x720 in mock mode on a fresh database, and writes one `.webm` clip per storyboard segment to `frontend/recordings/` (ignored by git). It starts the backend with plain `python -m flask ...`, so the backend virtual environment must be active in that terminal (or Flask must be installed for that python): PowerShell `..\backend\.venv\Scripts\Activate.ps1`, macOS/Linux `source ../backend/.venv/bin/activate`.

**Live mode (optional):** set `ARIA_HOME_MODEL_ENABLED=1` to enable live model calls (anything else stays in mock mode), `ARIA_HOME_PROVIDER_URL` to the model API base host, `ARIA_HOME_MODEL_ID` to the model to call, and `MODEL_API_KEY` to the API key (sent as `Authorization: Bearer <key>`). Keys live only in local environment variables; `.env` files are ignored.

## Safety and honesty rules

- **Synthetic data only.** Every thermostat, electrical, weather, calendar and contact record is invented for the demo and labeled synthetic. No credentials, real travel details or personal contacts appear anywhere.
- **Simulated delivery and control.** Notifications are simulated only — every card reads "Simulated, no message was sent", and there is no real email, SMS or push channel. The app reads and explains; it never operates equipment, and scene/command acknowledgements are simulated timeline events that change no physical state.
- **Scoped notifications.** Each audience (homeowner, property manager, HVAC company) has an allowlist of fields it may receive, enforced in code with refusals recorded. The HVAC request carries only property, access, manager contact and relevant observations — never itinerary, email or location — and is sent only after a manager authorization event.
- **Acknowledgement is not resolution.** A simulated acknowledgement is recorded as its own event and never changes readiness, outcome or verification. The same applies to service visits and the HVAC completion report, which is corroboration only and never sets an outcome.
- **No future data in replay.** Records, trip revisions, confirmations, events and notifications are visible only at or after their received/available times, so a replay at any moment shows only what ARIA could have known then.
- **Bounded claims.** Circuit watts never prove useful heat, a fault or equipment power. Verified recovery means recovery of the monitored temperature goal, never a proven repair cause or fault-free equipment. A mock answer is never presented as a fresh live response.

## Known limits

From the day handoffs and the [feature freeze](docs/freeze.md) (frozen 2026-10-26; the demo is what commit 4d3bacb does):

- All data is synthetic and every message, scene, visit and report is simulated; there are no real channels and ARIA Home controls no equipment. Email, location, scene, confirmation and service-visit moments have no dedicated UI and appear as labeled simulated timeline cards.
- Room-sensor and blower mappings are synthetic assumptions, not measured physical behaviour. Readiness thresholds are fixed constants, not fitted to a home, and projection is a linear extrapolation that ignores weather, equipment cycling and occupancy.
- The notification allowlists are reviewed by hand, not by an external privacy review; the HVAC request is gated only by a synthetic manager authorization event.
- The evaluation sample is small and builder-labeled: 12 offline cases, one live run per case. The live agreement rate shows the models followed the readiness contract, not independent readiness judgment, and input-token counts are unreliable.
- The committed live results used the pre-Day-7 readiness labels; Day 7 added `arrival_passed` with target-at-arrival, which the live run did not exercise.
- The older follow-up rule and the verification stage can disagree; the UI headlines the verification stage.
- The claim check is bounded — structured facts plus a phrase/number filter — not a semantic verifier of arbitrary prose.
- No new features, evidence sources, providers, models or integrations (real email, SMS, location, travel or equipment control) will be added after the freeze; remaining work is user testing, filming and the submission.

Day-by-day record: [Day 1 handoff](docs/day1-handoff.md) · [Day 2 handoff](docs/day2-handoff.md) · [Day 3 handoff](docs/day3-handoff.md) · [Day 4 handoff](docs/day4-handoff.md) · [Day 5 handoff](docs/day5-handoff.md) · [Day 6 handoff](docs/day6-handoff.md) · [Timeline](docs/timeline.md) · [User-test kit](docs/usability.md) · [Feature freeze](docs/freeze.md)

## License

No license has been chosen yet. Until one is added, all rights are reserved by the author.
