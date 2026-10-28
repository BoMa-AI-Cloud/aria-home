ARIA Home, small follow-up fix (approved by Brad). DO THE WORK NOW in this turn. IMPORTANT: a message without a
tool call ends your turn, so never write a status or plan sentence on its own; keep editing and running commands
until the done-condition holds. No live calls, no installs, no network beyond 127.0.0.1, no git, NO helper
scripts. Tests use a fake HTTP layer only. Do not weaken any test. Shell starts in C:\aria-home; prefix frontend
commands with `cd frontend && `. Do not end your turn until `cd backend && python -m pytest -q`,
`cd frontend && npm run typecheck` and `cd frontend && npm run test:e2e` pass.

Finding (operator review, after one approved real send): backend/aria_home/app.py calls
attempt_hvac_whatsapp_delivery from GET /api/follow-ups/<investigation_id>. A GET must never cause an outside
effect (Audit 3 finding 9 rule), even with the once-per-notice guard.

Fix: remove the send from every GET path. Add an explicit POST /api/notifications/<notification_id>/whatsapp
that attempts the real WhatsApp delivery for that HVAC notice only (same rules as today: live only with all
credentials plus ARIA_HOME_WHATSAPP_LIVE=1, only the hvac_company notice, only after manager authorisation, only
to WHATSAPP_TEST_RECIPIENT, existing allowlist text, at most one real send per notification id ever, token never
in DB/responses/logs). It returns the recorded delivery state; when not configured it returns 409 with
"not_configured" and changes nothing; unknown id 404; non-HVAC notice 409. Replay-time visibility rules apply (a
notice not yet visible at the given `at` cannot be sent). The frontend does not call it automatically; add a
small button on the HVAC card, shown only when /api/whatsapp/status (add it, GET, read-only, reports only
whether live delivery is configured, never any value) says configured: "Send to my test phone (WhatsApp)".
Update docs/whatsapp-audit.json generation, README and docs/inference-idempotency.md or the WhatsApp docs.
Tests: GET follow-ups never calls the HTTP layer (fake call count 0 across repeated GETs, flag on); POST sends
once; second POST does not re-send; not configured 409; wrong audience 409; unknown 404; not yet visible 409.
Final answer: files changed and the REAL output lines of every command.

