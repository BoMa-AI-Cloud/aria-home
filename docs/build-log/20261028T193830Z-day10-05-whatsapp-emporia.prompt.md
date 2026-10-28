ARIA Home: two optional real integrations, built the safe way (approved by Brad, 2026-10-28; Brad lifted the
self-imposed feature freeze). DO THE WORK NOW in this turn. IMPORTANT: a message without a tool call ends your
turn, so never write a status or plan sentence on its own; keep editing and running commands until the
done-condition holds. No live calls, no network beyond 127.0.0.1, no git, NO helper scripts outside tests. Tests
use fakes only: never contact graph.facebook.com or Emporia in a test. Do not weaken any test. Shell starts in
C:\aria-home; prefix frontend commands with `cd frontend && `. Do not end your turn until
`cd backend && python -m pytest -q`, `cd frontend && npm run typecheck`, `cd frontend && npm run build` and
`cd frontend && npm run test:e2e` all pass.

Rules that must hold: credentials only from environment variables (never in files, logs, responses, ids or
the DB); the public demo, every test and CI stay synthetic and work with no credentials; nothing ever controls
equipment; real data never lands in the repository (add .gitignore entries for any local live-data path).

A. WhatsApp Cloud API delivery to Brad's own verified phone only.
   - Env: WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_TEST_RECIPIENT, plus an explicit opt-in
     ARIA_HOME_WHATSAPP_LIVE=1. Real delivery happens only when all four are set; otherwise the notice stays
     exactly as today ("Simulated, no message was sent"). Document all of them in .env.example as placeholders.
   - Scope: only the HVAC-company notice, only after the manager-authorisation event, and only to
     WHATSAPP_TEST_RECIPIENT, which stands in for the HVAC company (say so in the message and the UI). Never
     send to any other number; refuse if the recipient differs.
   - Content: exactly the fields the HVAC allowlist already permits (the same function, not a copy); never
     itinerary, owner email, location or calendar. Plain text, first line "ARIA Home test (synthetic scenario)".
   - API: POST https://graph.facebook.com/v25.0/{phone_number_id}/messages with Bearer token, type "text".
     WhatsApp only accepts free-form text inside the 24-hour window after the recipient last messaged the
     sender; map the API error for "outside the window" to a clear recorded status, never a 500.
   - Idempotency: one real send per notification id at most, ever (persist the attempt before calling the API;
     a replay, refresh, retry or second POST never re-sends). Record status (delivered_to_test_number /
     refused / failed:<reason>) and the message id the API returns; never the token.
   - UI: the HVAC card shows "fields sent:" as today plus either "Simulated, no message was sent" or
     "Sent to the owner's test number on WhatsApp (stands in for the HVAC company)".
   - docs/whatsapp-audit.json generated from the code (like docs/fields-audit.json) with a test proving it
     matches; tests with a fake HTTP layer for: not opted in, success, outside-window error, wrong recipient,
     duplicate send attempt, token never present in DB/responses/logs.
B. Emporia Vue read-only live panel (pyemvue is installed in this Python).
   - Env: EMPORIA_EMAIL, EMPORIA_PASSWORD, plus opt-in ARIA_HOME_EMPORIA_LIVE=1. Read the installed pyemvue
     package source to use its real API (login, device list, current usage); call only read methods, never any
     method that changes a device or outlet.
   - New GET /api/live-power (read-only, cached at least 60 s, never called by tests against the real service)
     returning per-circuit watts with source "live-read-only (owner's home)", fetched_at, and status
     unavailable/not_configured when off. It is NOT evidence for readiness, warming or verification and never
     enters the evidence pack (watts are not heat); a test proves readiness and verification are identical with
     the panel on or off.
   - Frontend: a small separate panel "Your real home, right now (live, read-only, Emporia Vue)" shown only when
     the endpoint says configured; hidden otherwise, so the judge demo is unchanged.
C. Doc corrections: docs/evaluation.md says the 2026-10-27 current-code run (snapshot 114be6a) used
   readiness-policy-v2; v2 was introduced after that run (Audit 3, 2026-10-28), so correct it to the policy
   version that 114be6a actually had (read it from git: `git show 114be6a:backend/aria_home/readiness.py` is not
   allowed since git is off, so read the version string from the recorded results file
   backend/eval/results-live-current.json or the evaluation doc's own earlier text). docs/demo-script.md still
   describes a log cabin; the story video now shows a modern single-storey house (flat roof, floor-to-ceiling
   glass, light wood and dark steel, linear fireplace); update the descriptions, keep every rule.
D. Update README, SECURITY.md, docs/architecture-future.md (move WhatsApp test delivery and the Emporia panel from
   future to implemented, optional, off by default) and docs/existing-vs-new.md accurately.
Final answer: what changed per part, files changed, and the REAL output lines of every command.

