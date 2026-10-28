# Architecture — future directions (mostly no code)

Everything on this page is future, except the two optional integrations
listed under "Implemented (optional, off by default)". None of the
future items is implemented, integrated, tested, or promised. Everything
here and implemented would be built under the same trust rules as the
current system: readiness, follow-up, outcome and verification computed
in code; models may explain checked facts only; scoped notifications
with recorded refusals; simulated-before-real delivery; no equipment
control; acknowledgement is not resolution; verified means the monitored
temperature goal, not a proven repair cause.

## Implemented (optional, off by default)

- **WhatsApp test delivery** — the allowed HVAC-company notice, sent once
  via the WhatsApp Cloud API only after the manager-authorisation event
  and only to the owner's own verified test number (which stands in for
  the HVAC company). Same allowlists (no itinerary, owner email, location
  or calendar fields), recorded refusals, idempotent sending (at most one
  real send per notification id ever), credentials only from environment
  variables. Delivery still never changes readiness, outcome or
  verification. See `backend/aria_home/whatsapp.py` and
  `docs/whatsapp-audit.json` (generated from the code).
- **Emporia Vue live panel** — a small read-only frontend panel showing
  the owner's real per-circuit watts (`GET /api/live-power`, cached 60 s,
  source "live-read-only (owner's home)"), shown only when explicitly
  opted in and hidden otherwise. Only pyemvue read methods are ever
  called; live watts are display only and never enter readiness, warming,
  verification or the evidence pack (watts are not heat). See
  `backend/aria_home/emporia.py`.

## Possible future inputs

- **SAM 3.1 / Muse Image (Meta image models)** — a future image input (for example a photo of a thermostat display or a nameplate) would enter as one more evidence record with observed/received times, provenance, and as-of visibility. An image reading could support only claims its evidence allows; it could never by itself set readiness, an outcome, or a verification stage, and an unreadable or stale image would fall back to `cannot_tell` / `telemetry_missing` like any other missing source.
- **Real sensors** — real thermostat, room-sensor, electrical or weather feeds would replace synthetic fixtures only behind the same eligibility, freshness, cadence and conflict rules. Circuit watts would still never prove useful heat. A first read-only step exists (the optional Emporia live-watts panel above, display only, never evidence). Real data would additionally require the deployment prerequisites in [SECURITY.md](../SECURITY.md) (authentication, authorization, tenant isolation, quotas, retention) before any household data is ingested.

## What does not change

- The code-vs-model split (see README "Code vs model"): code decides; the model explains checked facts.
- "Verified recovery" keeps meaning verified recovery of the monitored temperature goal.
- No future integration operates equipment. ARIA Home notices sooner and helps get the right person moving; it does not repair or control anything.
