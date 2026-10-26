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

### Planned

- Day 3 onward: Meta investigation over the evidence.
- Day 3 onward: follow-up outcomes checked against later measurements.
- Day 3 onward: scoped notifications to homeowner and property manager.
- Day 3 onward: evaluation.

## Project status

- [Timeline](docs/timeline.md)
- [Existing vs new](docs/existing-vs-new.md)
- [Day 1 handoff](docs/day1-handoff.md)
- [Day 2 handoff](docs/day2-handoff.md)

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

Claude Code, including sessions configured to run Meta's Muse models.

## License

No license has been chosen yet. Until one is added, all rights are reserved by the author.

## Setup and run

Backend (from `backend/`):

```
# Windows PowerShell (run from backend/)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```
# macOS / Linux shells (run from backend/)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then, from `backend/` with the virtual environment active:

```
python -m pytest -q
python -m flask --app aria_home.app:create_app run --port 5000
```

Stop the server with Ctrl+C.

Frontend (from the repo root or `frontend/`):

```
npm ci
npm run dev
npm run build
npm run typecheck
```

`npm run dev` serves on port 5173 and proxies `/api` to port 5000. Stop the dev server with Ctrl+C.

Mock mode needs no environment variables. Live mode uses four variables:

- `ARIA_HOME_MODEL_ENABLED`: set to `1` to enable live model calls (anything else stays in mock mode).
- `ARIA_HOME_PROVIDER_URL`: the model API base host.
- `ARIA_HOME_MODEL_ID`: which model to call.
- `MODEL_API_KEY`: the API key, sent as `Authorization: Bearer <key>`.
