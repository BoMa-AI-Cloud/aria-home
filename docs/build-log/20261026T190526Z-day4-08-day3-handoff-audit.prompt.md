ARIA Home, docs task (approved by Brad): add the verification-repair section to the Day 3
handoff. Docs only: edit docs/day3-handoff.md, and add one line to docs/timeline.md. No code
changes, no live calls, no installs, no network, no git, NO helper scripts.

Read: docs/day3-handoff.md, docs/timeline.md, docs/readiness-rules.md, backend/scenarios/README.md,
and the answer files in docs/build-log/ whose names contain day4-03 through day4-07.

Append a section "Verification repair (2026-10-26)" to docs/day3-handoff.md with:
1. Context, worded exactly as attribution: "An external audit of commit 4f4ed93 reported four
   validation gaps found by offline probes." Do not restate the audit's own pass results as ours.
2. Each finding, what changed, and the tests that cover it: (1) claims bound to evidence,
   contract inv-v2; (2) readiness computed in code (link docs/readiness-rules.md); (3) follow-up
   scheduling computed in code; (4) as-of visibility for trip and confirmation context (link
   backend/scenarios/README.md; the availability timestamps were added to synthetic fixtures on
   2026-10-26, and two synthetic variants demo_revised_v1 and demo_cancelled_v1 were added).
3. "Checks run by the operator on 2026-10-26", copied exactly:
   - Base revision 5229d04 plus uncommitted repair changes (working tree not yet committed).
   - Fresh virtual environment with only backend/requirements.txt: `python -m pytest -q` -> 166 passed.
   - `cd frontend && npm run typecheck` -> passed; `npm run build` -> passed.
   - `cd frontend && npx playwright test` (installed Chrome, backend forced to
     ARIA_HOME_MODEL_ENABLED=0 by playwright.config.ts): first run 1 failed / 1 passed (an
     unexpected browser console error in the overview test, not reproduced); next three runs
     2 passed each. Treat this as a possible flaky cold start, not a clean pass.
4. "Not re-run": no live model calls were made for this repair; the Day 3 live results
   (D3-3, D3-3b) were produced under the inv-v1 contract and have not been repeated under inv-v2.
5. Limitations: the claim check is bounded (structured facts and a phrase/number filter), not a
   semantic verifier of arbitrary prose; readiness thresholds are hand-set for the synthetic
   scenarios and not calibrated on real homes; at_risk is a qualified judgement, not a forecast;
   the browser test flake above is unexplained.
6. Process note: the repair ran as five Muse tasks on the uncommitted local tree (not from a
   clean GitHub checkout); each build-log entry is in docs/build-log/. In one task (day4-04) the
   operator's header naming the local tree was garbled by an escaping bug, since fixed.
timeline.md: one line for 2026-10-26 "Verification repair of four audit findings (see
docs/day3-handoff.md)". Final answer: the files changed.

