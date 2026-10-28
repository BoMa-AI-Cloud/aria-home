ARIA Home, Audit 3 repair, GROUP 3a: request lifecycle and acknowledgements (backend) (approved by Brad).
DO THE WORK NOW in this turn. No live calls, no installs, no network beyond 127.0.0.1, no git, NO helper
scripts outside tests. Temporary databases and fake providers only; never call a real model. Do not weaken
any existing assertion. Smallest sound changes; no new features. Groups 1-2 are already in the working tree;
keep them. Shell starts in C:\aria-home; prefix frontend commands with `cd frontend && `. Do not end your turn
until `cd backend && python -m pytest -q` and `cd frontend && npm run test:e2e` pass (update frontend consumers of GET /api/investigation only if needed).

Read first: backend/aria_home/app.py, store.py, investigator.py, docs/inference-idempotency.md,
frontend/src/api.ts, frontend/src/App.tsx, frontend/playwright.config.ts, frontend/playwright.record.config.ts,
frontend/vite.config.ts, frontend/e2e/app.spec.ts, frontend/recording/*.ts.


The first attempt at this task (day10-03) ended after reading files without making any edits. Do the edits this time.
Reproduced on the current code:

8. ABANDONED CLAIM STUCK. Persist a pending inference claim (store.claim_inference(identity)), then create a
   fresh app: both POST /api/investigations and POST with retry=true return 202 forever, 0 provider calls.
   Fix: bounded ownership (owner id + lease expiry) or an explicit operator-authorised recovery. Distinguish
   active, expired/abandoned, failed and completed. Never silently repeat a possibly-paid inference after a
   timeout/crash: an expired claim becomes "recovery_required" and is re-run only on an explicit request (for
   example retry=true), never by an ordinary POST or GET. Two workers can never own one claim; a late
   completion by an old owner must not overwrite a newer accepted result. Document the recovery action and the
   user-visible state in docs/inference-idempotency.md.
   Tests: restart with an abandoned claim, active work not stolen, expired-claim recovery, concurrent recovery,
   late completion by the old owner, no automatic re-run.

9. GET RUNS INFERENCE. Two identical GET /api/investigation requests make two provider.generate calls.
   Fix: GET only reads stored results and/or a deterministic code-computed summary; inference happens only
   through POST. Update frontend consumers if needed. Document no-result GET behaviour.
   Tests: fake-provider call count stays 0 across repeated GETs, POST stays idempotent, stored result retrieval.

10. ACK BODY NOT VALIDATED. On a 2026 property_manager notification: ack with at "2000-01-01T00:00:00Z" -> 200;
   at=123 -> 500; JSON body ["bad"] -> 500; actor "intruder" -> 200.
   Fix: typed JSON object body; reject non-string and timezone-naive timestamps and acks earlier than the
   notification's creation; enforce the demo's explicit allowed-actor policy per audience (document that this
   is a simulation allowlist, not authentication); decide and document whether refused, queued and
   simulated-delivered notices can be acknowledged. Invalid input -> clear 4xx, never 500. Keep replay-time
   visibility and ack idempotency.
   Tests: each reproduction above, valid ack, repeated ack, refused/queued notice.

Final answer: per finding, root cause, files changed, tests added, and the REAL output lines of every command.

