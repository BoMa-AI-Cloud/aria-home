# ARIA Home

> **Will my property be ready when I arrive, and if something looks wrong, who should respond?**

ARIA Home is a solo entry in the **Meta Global AI Developer Hackathon** (Indie Developer track,
theme "Build for Your World"). It connects a planned trip with thermostat, electrical and weather
evidence, uses Meta's Muse models to explain a readiness concern from supporting and conflicting
evidence, notifies the homeowner and an authorized property manager with scoped messages, and
checks later measurements before it reports an outcome.

## Status

**Nothing is built yet.** This repository was created on 2026-10-26 after the kickoff session
ended. Every file in it is work done during the hackathon; `docs/timeline.md` will record when
each feature landed.

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
