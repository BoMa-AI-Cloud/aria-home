# Architecture — future directions (mostly no code)

Everything on this page is future, except the three optional integrations
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
- **Caregiver permission before HVAC (care story)** — after ARIA confirms
  the home is at risk, the family caregiver is asked "May I contact the HVAC
  company?" with the room temperature and the time the furnace went quiet,
  both read from evidence visible at that moment. Approve or Decline in the
  app records a once-only caregiver decision (actor family_caregiver,
  replay-visible); the HVAC request is created only after approval, and a
  decline blocks it while ARIA keeps monitoring. The same request can be
  sent once to the owner's test number on WhatsApp (standing in for the
  caregiver) through the explicit opt-in POST. The caregiver then gets
  simulated "HVAC contacted" and "Temperature goal verified" updates. The
  decision never changes readiness or verification. See
  `backend/aria_home/notifications.py` and `backend/tests/test_caregiver_permission*.py`.
- **Nest camera snapshot (owner only)** — one frame on request from the
  owner's Nest Cam Indoor in the mechanical room, through the Smart Device
  Management API (stream started, one frame grabbed with ffmpeg, stream
  always stopped). Optionally sent to sam-3.1, with that upload disclosed.
  Shown in its own panel; never evidence for the synthetic scenario. See
  `backend/aria_home/nest.py` and `backend/scripts/nest_auth.py`.
- **Emporia Vue live panel** — a small read-only frontend panel showing
  the owner's real per-circuit watts (`GET /api/live-power`, cached 60 s,
  source "live-read-only (owner's home)"), shown only when explicitly
  opted in and hidden otherwise. Only pyemvue read methods are ever
  called; live watts are display only and never enter readiness, warming,
  verification or the evidence pack (watts are not heat). See
  `backend/aria_home/emporia.py`.
- **SAM 3.1 visual evidence (synthetic images)** — recorded sam-3.1
  segmentation over synthetic muse-image-1.0 fixtures enters as a visual
  observation with observed/received times, provenance, and as-of
  visibility (`GET /api/visual`, `GET /api/visual/image`), shown in the
  frontend with boxes overlaid and the code's verdict. The app is
  replay-only: it never constructs the `SamLiveProvider` reference
  adapter, so setting `ARIA_HOME_VISUAL_LIVE=1` changes nothing. Exactly as the former future item required: visual
  evidence never by itself sets readiness, an outcome, or a verification
  stage — it never yields `on_track`, `warming_observed`,
  `goal_verified` or `arrival_met` — and zero detected objects is no
  detection, never an all-clear (the recorded frost-pipe miss stays
  `at_risk`). Images are never sent anywhere; HVAC payloads may carry
  only the observation line. See `backend/aria_home/visual.py` and
  `docs/readiness-rules.md`.

## Possible future inputs

- **Real sensors** — real thermostat, room-sensor, electrical or weather feeds would replace synthetic fixtures only behind the same eligibility, freshness, cadence and conflict rules. Circuit watts would still never prove useful heat. A first read-only step exists (the optional Emporia live-watts panel above, display only, never evidence). Real data would additionally require the deployment prerequisites in [SECURITY.md](../SECURITY.md) (authentication, authorization, tenant isolation, quotas, retention) before any household data is ingested.

## What does not change

- The code-vs-model split (see README "Code vs model"): code decides; the model explains checked facts.
- "Verified recovery" keeps meaning verified recovery of the monitored temperature goal.
- No future integration operates equipment. ARIA Home notices sooner and helps get the right person moving; it does not repair or control anything.

## Extension point: inbound WhatsApp reply (not built)

Today the caregiver answers in the app. A later step could accept her
answer as a WhatsApp reply: a webhook that takes a YES or NO only when the
request carries a valid Meta signature (X-Hub-Signature-256 over the raw
body with the app secret), only from the configured test number, only as a
reply to the one permission message ARIA sent, and only once, recording the
same caregiver decision the in-app buttons record. Anything else is
refused and logged. Nothing of this exists in code: there is no webhook
route, no app secret variable and no public endpoint.
