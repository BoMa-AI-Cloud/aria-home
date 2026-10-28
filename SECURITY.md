# Security

This document describes scope and limits. It does not claim the project is secure or compliant.

## Supported scope

- Local development on loopback (127.0.0.1): backend on port 5000, frontend on port 5173.
- Synthetic fixture data only; notifications are simulated delivery ("Simulated, no message was sent") unless the optional WhatsApp test delivery is explicitly opted in (see below).
- No equipment control: the app reads and explains; it never operates a thermostat, scene, or other device. The Emporia integration calls only pyemvue read methods (login, device list, current usage); nothing in the repository calls any method that changes a device or outlet.
- Mock inference is the default. Live inference is gated by environment variables and is off in CI.
- Optional integrations are off by default and stay synthetic in the demo, tests and CI with no credentials:
  - WhatsApp test delivery: only the allowed HVAC-company notice, only after the manager-authorisation event, only to `WHATSAPP_TEST_RECIPIENT` (the owner's own verified test number, which stands in for the HVAC company), at most one real send per notification id ever. Requires `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TEST_RECIPIENT` plus `ARIA_HOME_WHATSAPP_LIVE=1`.
  - Emporia live panel: read-only per-circuit watts via `GET /api/live-power` (cached 60 s), display only, never evidence. Requires `EMPORIA_EMAIL`, `EMPORIA_PASSWORD` plus `ARIA_HOME_EMPORIA_LIVE=1`.
- Credentials only from environment variables (never in files, logs, responses, ids or the database); real data never lands in the repository (local live-data paths are git-ignored).

## What is checked vs not checked

Checked in code/tests (see `backend/tests/`):

- Notification payload allowlists per audience, with refusals recorded; HVAC payloads exclude itinerary, owner email, location and calendar fields (`docs/fields-audit.json`, generated from the code and checked by `backend/tests/test_audit3_group4_fields_audit.py`).
- WhatsApp test delivery (`backend/aria_home/whatsapp.py`, `docs/whatsapp-audit.json`, checked by `backend/tests/test_audit3_whatsapp.py`): same-function allowlisted content, test-number-only recipient with refusal otherwise, attempt persisted before the API call so replay/refresh/retry/second POST never re-sends, outside-24h-window errors recorded as failed without a 500, and the token/recipient absent from the database, responses and logs.
- Emporia read-only panel (`backend/aria_home/emporia.py`, checked by `backend/tests/test_audit3_emporia.py`): off by default, only pyemvue read methods ever called, cached reads, unavailable (never 500) on failure, and live watts provably absent from readiness, verification and the evidence pack.
- As-of visibility: records, events and notifications with a later received/available time are not returned at an earlier replay time.
- Acknowledgement, service visits, human statements and the HVAC completion report never set an outcome or advance verification; outcomes come from later measurements only.
- Claim binding (inv-v2): model facts must cite allowed evidence; readiness/follow-up/outcome are computed in code.

Not checked / not provided:

- No authentication, authorization, tenant isolation, rate limiting or quotas — there are no user accounts in this local demo.
- No external privacy or security review; the allowlists are reviewed by hand.
- The only real delivery channel is the optional WhatsApp test delivery to the owner's own verified test number (explicit four-variable opt-in, off by default); no general real-delivery permission, consent, or retention enforcement exists in code beyond that single-number, single-notice gate.
- Dependency audit output in CI (`npm audit --omit=dev`, `pip-audit`) is reporting only; a clean or reported result is not a claim that the project is secure.
- Synthetic fixtures do not certify that any environment you run this in contains no PII or secrets; keep keys in local environment variables only, never in committed files (`.env` is git-ignored, `.env.example` holds placeholders only).

## Before any shared or real-data deployment (prerequisites, not implemented)

Authentication; authorization; tenant isolation; quotas/rate limits; real-delivery permissions and consent; data retention and deletion rules; secret management; logging/monitoring; and a fresh security review. Do not expose this demo to a shared network or feed it real household data until those exist.

## Reporting

Please report a vulnerability privately through a GitHub security advisory ("Report a vulnerability") on this repository: https://github.com/BoMa-AI-Cloud/aria-home

Do not open a public issue for a sensitive report. No email address is published here.
