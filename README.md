# ARIA Home

> **Will my property be ready when I arrive, and if something looks wrong, who should respond?**

ARIA Home is a solo entry in the **Meta Global AI Developer Hackathon** (Indie Developer track,
theme "Build for Your World"). It connects a planned trip with thermostat, electrical and weather
evidence, uses Meta's Muse models to explain a readiness concern from supporting and conflicting
evidence, notifies the homeowner and an authorized property manager with scoped messages, and
checks later measurements before it reports an outcome.

## Status

### Working now

- Backend health endpoint (`GET /api/health`).
- Evidence foundation: contracts, scenario clock, freshness, synthetic demo scenario, `GET /api/sources`.
- Provider adapter: mock provider and gated live Meta provider, `GET /api/provider`.
- Provider reply reporting: reply block types, stop reason, usage, `no_text` error.
- Metrics: indoor trend, target gap, circuit activity, cadence-based coverage, `GET /api/metrics`.
- Property Power Context: per-circuit status, meter lineage, continuity check, limitations, `GET /api/power-context`.
- Frontend: Vite React TypeScript shell with four synthetic source cards and missing-reading counts.
- App smoke test covering the API contract the page uses.
- Meta investigation over the evidence (Day 3): evidence-pack investigation engine with validated output, `GET /api/investigation`, and the Investigation section in the browser.
- Follow-up outcomes checked against later measurements: deterministic outcome rules (warming observed / target reached / not observed by deadline / unable to verify), a SQLite store that survives restarts with per-evaluation outcome history, `POST /api/investigations` and `GET /api/follow-ups/<id>`, and scenario replay buttons with the outcome panel in the browser.
- Recovery verification for the video scenario (thermostat reporting restored, warming observed, temperature goal verified, arrival expectation met), the `demo_video_v1` fixture with a committed deterministic stream generator, `GET /api/events`, and a labeled simulated timeline in the browser.

### Planned

- Day 3 onward: scoped notifications to homeowner and property manager.
- Day 3 onward: evaluation.
- [Demo video plan and implementation gap map](docs/demo-script.md)

## Project status

- [Timeline](docs/timeline.md)
- [Existing vs new](docs/existing-vs-new.md)
- [Day 1 handoff](docs/day1-handoff.md)
- [Day 2 handoff](docs/day2-handoff.md)
- [Day 3 handoff](docs/day3-handoff.md)
- [Day 4 handoff](docs/day4-handoff.md)
- [Build log](docs/build-log/README.md)

## What was pre-existing

- No code. This repository contains no code from any earlier project.
- The name "ARIA" and pre-event planning notes (designs, no code) existed before the event. The
  demo video's opening line says so.

## Ground rules

- **Synthetic data only.** Every thermostat, electrical, weather, calendar and contact record is
  invented for the demo and labeled synthetic.
- **No secrets.** API keys live only in local environment variables; `.env` files are ignored.
- **No physical control.** The app reads and explains; it never operates equipment.
- **Meta models at runtime.** Every model the app calls is a Meta model (Muse via the Meta Model
  API).

## Tools used to build it

Application code was written by Claude Code sessions running Meta's Muse models
(muse-wonder-1.0 and muse-spark-1.3). An operator, Claude Code running Anthropic's Claude model and
directed by Brad Wentzel, wrote the prompts, reviewed and tested each change, ran approved
installs and live smoke tests, and made the commits. Every prompt and answer is in
[docs/build-log](docs/build-log/README.md). At runtime the app calls only Meta models.

## License

No license has been chosen yet. Until one is added, all rights are reserved by the author.

## Setup and run

Terminal 1: backend. From the repo root:

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
python -m pytest -q
python -m flask --app aria_home.app:create_app run --port 5000
```

Stop the backend server with Ctrl+C.

Terminal 2: frontend. From the repo root:

```
cd frontend
npm ci
npm run dev
```

`npm run dev` stays running; stop with Ctrl+C. It serves on port 5173 and proxies `/api` to port 5000.

In a third terminal, also from frontend/:

```
npm run build
npm run typecheck
npm run test:e2e
```

`npm run test:e2e` starts its own backend and frontend servers on ports 5000 and 5173, so stop the dev servers first. It runs the Playwright end-to-end test in the installed Google Chrome (no browser download).

Mock mode needs no environment variables. Live mode uses four variables:

- `ARIA_HOME_MODEL_ENABLED`: set to `1` to enable live model calls (anything else stays in mock mode).
- `ARIA_HOME_PROVIDER_URL`: the model API base host.
- `ARIA_HOME_MODEL_ID`: which model to call.
- `MODEL_API_KEY`: the API key, sent as `Authorization: Bearer <key>`.
