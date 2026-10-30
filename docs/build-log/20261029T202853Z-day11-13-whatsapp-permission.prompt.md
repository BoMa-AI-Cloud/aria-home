ARIA Home: ARIA asks the family caregiver for permission on WhatsApp before contacting HVAC (approved by Brad,
2026-10-29; step 1, no inbound webhook). DO THE WORK NOW in this turn. IMPORTANT: a message without a tool call ends
your turn, so never write a status or plan sentence on its own; keep editing and running commands until the
done-condition holds. No live calls, no installs, no network beyond 127.0.0.1, no git, NO helper scripts outside tests.
Tests use a fake HTTP layer only. Do not weaken any test. Keep all working-tree changes. Shell starts in C:\aria-home;
prefix frontend commands with `cd frontend && `. Do not end your turn until `cd backend && python -m pytest -q`,
`cd frontend && npm run typecheck`, `cd frontend && npm run build`, `cd frontend && npm run test:e2e` and
`cd frontend && npm run test:e2e:public-demo` pass.

In care_home_v1, after ARIA confirms the home is at risk:
1. Permission request to the family caregiver: a notice "ARIA Home (synthetic scenario): your mother's home is
   cooling (<room temp> F, furnace quiet since <time>). May I contact the HVAC company? Approve or decline in ARIA
   Home." built from the caregiver allowlist only (no health or personal details). With WhatsApp live configured
   (existing opt-in rules), it can be sent to the owner's test number, which stands in for the caregiver, through an
   explicit POST like the existing HVAC send (never from a GET, at most once per notice); otherwise simulated.
2. The caregiver card in the app has Approve and Decline. Approve records a caregiver authorisation event (actor
   family_caregiver, timestamp, replay-visible); only then is the HVAC request created, with the existing HVAC
   allowlist. Decline records a refusal: no HVAC request, ARIA keeps monitoring and the code's own alerts continue.
   Approval never changes readiness or verification.
3. After the HVAC request, a caregiver update "HVAC contacted" (simulated or the same opt-in WhatsApp path), and later
   "Temperature goal verified" when verification says so.
4. The trace and ARIA's view show the permission step (request sent, waiting, approved/declined by the caregiver) in
   its own colour; the guided story includes it.
5. Leave a clearly separated, unbuilt "inbound reply" extension point documented in docs/architecture-future.md: a
   WhatsApp webhook would accept a YES/NO reply only when Meta-signed and from the test number; not built.
6. Tests: approve -> HVAC request with allowed fields only; decline -> no HVAC request; no HVAC request before
   approval; approval does not change readiness/verification; WhatsApp permission send obeys opt-in, test-number-only,
   once-only, POST-only; public-demo mode keeps it simulated; replay/rewind hides future approvals.
Final answer: files changed, tests added, and the REAL output lines of every command.

