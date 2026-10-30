# Security

This document describes scope and limits. It does not claim the project is secure or compliant.

## Supported scope

- Local development on loopback (127.0.0.1): backend on port 5000, frontend on port 5173.
- Synthetic fixture data only; notifications are simulated delivery ("Simulated, no message was sent") unless the optional WhatsApp test delivery is explicitly opted in (see below).
- No equipment control: the app reads and explains; it never operates a thermostat, scene, or other device. The Emporia integration calls only pyemvue read methods (login, device list, current usage); nothing in the repository calls any method that changes a device or outlet.
- Mock inference is the default. Live inference is gated by environment variables and is off in CI.
- Optional integrations are off by default and stay synthetic in the demo, tests and CI with no credentials:
  - WhatsApp test delivery: only the allowed HVAC-company notice (after the manager or caregiver authorisation) and the caregiver permission request (the caregiver_alert notice, standing in for the family caregiver), each only to `WHATSAPP_TEST_RECIPIENT` (the owner's own verified test number, which stands in for the HVAC company or the caregiver), at most one real send per notification id ever. Requires `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TEST_RECIPIENT` plus `ARIA_HOME_WHATSAPP_LIVE=1`.
  - Emporia live panel: read-only per-circuit watts via `GET /api/live-power` (cached 60 s), display only, never evidence. Requires `EMPORIA_EMAIL`, `EMPORIA_PASSWORD` plus `ARIA_HOME_EMPORIA_LIVE=1`.
  - Visual evidence for the synthetic story is replay-only: recorded sam-3.1 responses are replayed and no network happens; setting `ARIA_HOME_VISUAL_LIVE=1` changes nothing. No synthetic image is sent anywhere; notification payloads may carry only the visual observation line (the unintegrated adapter would POST image bytes if anyone ever wired it in).
- Credentials only from environment variables (never in files, logs, responses, ids or the database); real data never lands in the repository (local live-data paths are git-ignored).

## What is checked vs not checked

Checked in code/tests (see `backend/tests/`):

- Notification payload allowlists per audience, with refusals recorded; HVAC payloads exclude itinerary, owner email, location and calendar fields (`docs/fields-audit.json`, generated from the code and checked by `backend/tests/test_audit3_group4_fields_audit.py`).
- WhatsApp test delivery (`backend/aria_home/whatsapp.py`, `docs/whatsapp-audit.json`, checked by `backend/tests/test_audit3_whatsapp.py`): same-function allowlisted content, test-number-only recipient with refusal otherwise, explicit `POST /api/notifications/<id>/whatsapp` trigger only (`GET /api/follow-ups/...` never sends, repeated GETs make zero HTTP calls), attempt persisted before the API call so replay/refresh/retry/repeated GETs/second POST never re-sends, an HTTP success without a message id recorded as unknown (never success), exceptions after the claim persisted as unknown, outside-24h-window errors recorded as failed without a 500, and the token/recipient absent from the database, responses and logs.
- Emporia read-only panel (`backend/aria_home/emporia.py`, checked by `backend/tests/test_audit3_emporia.py`): off by default, only pyemvue read methods ever called, cached reads, unavailable (never 500) on failure, and live watts provably absent from readiness, verification and the evidence pack.
- Visual evidence (`backend/aria_home/visual.py`, checked by `backend/tests/test_visual.py`): synthetic images and recorded sam-3.1 responses only in tests (never a network call); the app is replay-only and never constructs the live adapter, so setting `ARIA_HOME_VISUAL_LIVE=1` changes nothing; the live model id allowlisted to sam-3.1; `GET /api/visual` and `GET /api/visual/image` gated by `received_at <= at` and constrained to the fixtures directory; HVAC and WhatsApp payloads provably carry the observation line and no image data; visual evidence provably never yields `on_track`, a warming stage, or a verification success, and zero objects never reads as an all-clear.
- As-of visibility: records, events and notifications with a later received/available time are not returned at an earlier replay time.
- Acknowledgement, service visits, human statements and the HVAC completion report never set an outcome or advance verification; outcomes come from later measurements only.
- Claim binding (inv-v3): model facts must cite allowed evidence, with temperature at arrival (never a current temperature) after arrival; readiness/follow-up/outcome are computed in code.

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

## Nest camera snapshot (optional, owner only)

What leaves the house, and when:

- Nothing, unless the owner sets `ARIA_HOME_NEST_LIVE=1` and the Nest credentials. The routes do not exist in public-demo mode, and public-demo mode refuses to start with that flag set.
- On each "Take one snapshot" press (an explicit `POST /api/camera/snapshot`, never a GET): a token refresh to `oauth2.googleapis.com`, a device list and a start/stop stream command to `smartdevicemanagement.googleapis.com`, and one RTSP frame pulled from Google's stream by ffmpeg. The stream is always stopped, even when ffmpeg fails. The frame is saved only to the git-ignored `backend/instance/nest-snapshots/`.
- Only on "Take one snapshot and send it to sam-3.1" (`{"segment": true}`): that one JPEG is uploaded to Meta's Model API (`api.meta.ai`, sam-3.1), three times, once per phrase. The response and the panel both say "this real image was uploaded to Meta's sam-3.1".
- Credentials come only from environment variables. The client secret, the refresh and access tokens, the stream URL (it carries a token) and the stream extension token never appear in responses, logs, error text or the database; the one-time sign-in script stores only the refresh token, as a Windows user environment variable, and prints none of them (`backend/tests/test_nest.py`).
- The live frame is never evidence for the synthetic scenario's readiness or verification.
