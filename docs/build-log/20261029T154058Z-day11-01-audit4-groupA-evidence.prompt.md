ARIA Home, Audit 4 repair, GROUP A: evidence and verification (approved by Brad). DO THE WORK NOW in this turn.
IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; keep
editing and running commands until the done-condition holds. No live calls, no installs, no network beyond
127.0.0.1, no git, NO helper scripts outside tests. Temporary databases, synthetic fixtures, fake providers only.
Do not weaken any assertion, never add "or True", never relax evidence rules or change expected labels just to pass.
Smallest sound repairs. Shell starts in C:\aria-home. Do not end your turn until `cd backend && python -m pytest -q`
passes. Read docs/audit-4.md, docs/readiness-rules.md, backend/aria_home/{verification,eligibility,evidence,
readiness,investigator,outcomes,contracts}.py and the existing tests first.

Keep these claims distinct: thermostat telemetry available; equipment activity observed; independent room temperature
rising; temperature met and held a target; temperature expectation met at arrival; a repair caused recovery (never
claimed). Human acknowledgements, attendance and completion reports never create sensor verification.

1 (P1) SAME-ID CONTRADICTION DISCARDED BEFORE CONFLICT CHECKING. Reproduced: in demo_video_v1 (follow-up at 16:31,
  evaluated 21:01), copying room-temp-2100 with the same id and timestamps but value 40.0 F gives arrival_met when
  appended and goal_not_maintained when prepended; an earlier same-id dedup discards one value. Never resolve by
  insertion order, id sorting or first/last wins. Distinguish identical duplicates from incompatible records sharing
  an id; keep provenance; one conflict policy for source status, readiness, recovery and claim validation; normalized
  units; respect quantity, property, zone, source and time window. A relevant unresolved conflict prevents
  unsupported readiness/verification success; unrelated zones and intervals are unaffected.
  Tests: same-id both insertion orders; different-id both id orders; conflicts inside a hold interval and at arrival;
  identical and equivalent-unit duplicates; conflicts outside zone/window; API-level regression with no unsupported
  arrival_met.
2 (P2) CURRENT CLAIM FALLS BACK ACROSS A NEWER CONFLICT. Construct a distinct-id conflicting room reading at 20:20; at
  20:21 readiness is cannot_tell but a structured current_temperature claim citing the older 20:15 reading passes
  investigation validation. Define "current" once and use it in canonical selection and claim validation; never
  select an older reading as current when newer relevant evidence is unresolved, conflicting or invalid; historical
  evidence shown must be labelled historical with its time. Keep freshness and as-of checks. Tests: newer conflict +
  older fresh reading; conflict resolved by later eligible evidence; stale; delayed receipt; different zones; full
  investigation-contract validation (not only a helper).
3 (P2) TIMELINE BACKDATES KNOWLEDGE. Construct seven 68 F readings 19:00-19:30 every 5 minutes; the 19:00 reading is
  received at 20:00, the rest immediately. At 19:30 the hold cannot be established; at 20:00 the timeline shows
  goal_verified with first_known_at 19:30 instead of 20:00. Keep physical time separate from knowledge time;
  first_known_at is never earlier than the latest availability time of ALL evidence and context the claim needs;
  apply to warming, hold, arrival and every derived entry; keep historical observed_at; do not replace every time
  with the request time; earlier replays never expose future evidence or acknowledgements. Tests: late first, middle
  and endpoint samples; out-of-order receipts; arrival evidence learned after arrival; rewind after a later success;
  timeline and API agree on observed_at and first_known_at; no entry knows before its dependencies.
4 (P2) WRONG-ZONE THERMOSTAT SATISFIES THE RECOVERY GATE. Remove the main thermostat's recovery evidence while keeping
  supported warm room readings (result telemetry_missing); add a fresh thermostat record for another zone and the
  result can become arrival_met. Enforce property, zone, equipment and binding scope for every dependency. If the
  contract couples temperature success to thermostat restoration unnecessarily, separate those claims explicitly
  (document the semantic change and why) rather than keep an arbitrary gate. Idle/off cycling, a quiet circuit or an
  already-warm home must not invalidate a supported temperature goal; keep coverage, hold, relapse and arrival rules.
  Tests: main thermostat absent + other-zone thermostat present; wrong property/equipment binding; correct binding;
  temperature success without any causal repair claim; idle/off at target, already-at-target, fan-only; missing
  arrival coverage; relapse.
Also: backend/tests/test_audit3_evidence_verification.py line ~93 has `... <= 1 or True`. Replace it with a meaningful
behavioural assertion about identical duplicates (keep the rest of that test).

Bump the policy version you change and update docs/readiness-rules.md exactly. The shipped demo_video_v1 sequence
(18:21 reporting restored, 18:51 warming observed, 19:51 not yet verified, 20:21 goal verified, 21:01 arrival met)
must still hold unless a repair changes semantics; if so, explain it. In docs/audit-4.md update rows 1-4 with
reproduction, repair, regression test file and remaining limitation.
Final answer: per finding root cause, files changed, tests added, and the REAL pytest output line.

