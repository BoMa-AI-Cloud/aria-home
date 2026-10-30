ARIA Home: public-demo mode, backend and isolation (approved by Brad, 2026-10-29). DO THE WORK NOW in this turn.
IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; keep
editing and running commands until the done-condition holds. No live calls, no installs, no network beyond
127.0.0.1, no git, NO helper scripts outside tests. Do not weaken any test. Audit 4 work is in the working tree; keep
it. Shell starts in C:\aria-home; prefix frontend commands with `cd frontend && `. Do not end your turn until
`cd backend && python -m pytest -q`, `cd frontend && npm run typecheck`, `cd frontend && npm run build` and
`cd frontend && npm run test:e2e` pass. Read docs/public-demo-plan.md first.

Goal: a judge opens one URL in a browser and uses the real app: no install, account, key or terminal. Use the
existing React frontend and the existing Python logic. Do not port readiness or verification to JavaScript.

1. ARIA_HOME_PUBLIC_DEMO=1 turns on a restricted mode of the same Flask app that also serves the built frontend
   (frontend/dist) from one process. In this mode:
   - Only the routes the demo needs are registered (health, scenarios list, metrics, investigation read, follow-ups,
     events, notifications list/ack, visual metadata/image, evaluation summary, a new session reset). WhatsApp send,
     live power, any provider/config route that is not needed, and every test hook are not registered at all.
   - Live paths cannot run even if credentials are present: force mock/recorded model output, never construct a live
     provider, WhatsApp sender, Emporia client or SAM live adapter; if ARIA_HOME_MODEL_ENABLED=1,
     ARIA_HOME_WHATSAPP_LIVE=1, ARIA_HOME_EMPORIA_LIVE=1, ARIA_HOME_VISUAL_LIVE=1 or ARIA_HOME_E2E_HOOKS=1 is set
     together with ARIA_HOME_PUBLIC_DEMO=1, refuse to start (fail closed) with a clear message.
   - Server-controlled allowlists of scenario ids and replay times (the fixtures' own checkpoints); reject anything
     else with 4xx. Cap request body size (for example 4 KB) and reject non-JSON bodies.
   - No debug mode; same-origin only (no permissive CORS); JSON errors without stack traces.
2. Visitor isolation: each visitor gets a random opaque session id (HttpOnly, SameSite=Lax cookie; Secure when served
   over HTTPS), server-generated, never user-chosen. Per-session state (acknowledgements, authorisations, replay
   state, investigation rows) lives in a per-session SQLite file whose name is derived only from a server-side hash of
   the id inside a dedicated temp directory, or in one DB keyed by session id; never a user-controlled path. Bound
   retention (delete sessions idle more than 2 hours; cap total sessions, for example 500, evicting the oldest).
   POST /api/session/reset clears only the caller's state. Acknowledgement still never alters sensor verification.
3. Recorded model responses: in public-demo mode the investigation shows a recorded muse-spark-1.3 answer only when
   one exists for the exact scenario, time, evidence input_revision, model id and contract/policy version (look in
   backend/eval/results-live-*.json and any recorded answers; build a lookup keyed on those fields). Otherwise show the
   deterministic code summary labelled "No recorded model response for this snapshot" (never an old explanation for
   changed evidence). Expose provenance per answer: model id, provider route, recorded run timestamp from the file
   (never invented), input revision, code snapshot, contract/policy version, validation result.
4. Tests (backend): fresh session works with no credentials; dangerous routes return 404 in public mode; fail-closed
   start with each live flag; allowlisted scenarios/times only; oversized and malformed bodies 4xx; sessions A and B
   isolated (ack in A invisible to B), reset clears only A; retention eviction; network spy proves zero outbound HTTP
   in public mode across a full replay; recorded-answer lookup refuses a mismatched revision/version.
5. A README section "Public demo mode (for hosting)" with the exact start command (for example
   `ARIA_HOME_PUBLIC_DEMO=1 python -m waitress ...` only if waitress is already installed; otherwise the Flask command
   with debug off) and the boundary list. Mark the hosted link "Pending deployment". Update docs/public-demo-plan.md
   steps 2 and 4.
Final answer: files changed, tests added, and the REAL output lines of every command.

