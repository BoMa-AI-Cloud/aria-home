# Day 3 handoff

## What works

- D3-1 investigation engine (commit 353415a, written by muse-wonder-1.0): evidence pack built only from records visible at the evaluation time, trip title quoted as untrusted text, versioned prompt inv-v1, strict output schema, validate() (unknown evidence ids, uncited observations, numbers not in the pack, banned phrases, readiness inconsistent with the computed gap), fallback to the deterministic summary, `/api/investigation`. Mock provider labeled "[MOCK]". Checked by pytest.
- D3-2 browser Investigation section (commit c2d00ca, written by muse-spark-1.3): the browser opens on the Investigation section (readiness in words with temperatures, cited observations, hypotheses labeled as such, unknowns, one question, next check, Power Context with limitations, provenance line, mock label); evidence cards below. Checked by the Playwright browser test.
- Playwright browser test on installed Chrome (commit 814ca9e): closed the Day 2 gap; favicon 404 fix; verified test counts; setup instructions split by terminal.
- Configurable investigation output limit (commit dbe4ab6): ARIA_HOME_INVESTIGATION_MAX_TOKENS, default 8000, with an explicit no_text reason when the limit is reached. The default limit is now 12000 (commit 5df95cb).
- Evidence-pack numbers rounded for the model, e.g. -15.9, 0.034 (commit 5df95cb); validation against rounded values. Validator accepts the absolute value of a signed pack number, 15.9 for -15.9 (commit e1b488d, found by the operator's probe), with regression tests (commit 603773e).
- Public build log of every Muse prompt and answer (commit 8736673, docs/build-log/).
- Runtime model chosen: muse-spark-1.3. In live run 2 both models passed validation at the same rate in a small sample and muse-spark-1.3 ran at about half the latency. Four calls on one scenario is not an evaluation; the full comparison is planned for Day 6.

## What was tested

- Backend: 109 passed at 603773e.
- Browser test (`npm run test:e2e`, Playwright, installed Chrome): 1 passed.
- Live investigation run 2 (operator run approved by Brad, 17:47-17:49Z): 4 of 4 passed validation, all readiness "at_risk". muse-spark-1.3: 22.7-23.5 s, 6,917-7,350 output tokens. muse-wonder-1.0: 39.0-49.3 s, 5,713-7,943 output tokens. 8000 output tokens, 90 s timeout, no retries, demo scenario.

## Mock vs live

- Mock provider: labeled "[MOCK]" in the browser; used by the browser test and all pytest runs.
- Live run 1 (operator run approved by Brad, 17:43-17:44Z): 6 calls (3 muse-spark-1.3, 3 muse-wonder-1.0), demo scenario, 1500 output tokens, no retries. 0 of 6 produced an answer; every reply was hidden reasoning only and stopped at the output limit. Led to the configurable limit (dbe4ab6).
- Live run 2 (operator run approved by Brad, 17:47-17:49Z): 4 calls (2 per model), 8000 output tokens, 90 s timeout, no retries. 4 of 4 passed validation, all readiness "at_risk"; timings and token counts above.

## Known gaps

- Organizer questions still open, to be asked in Discord office hours: build-start time, hosted URL, labeled simulated data live, editing a submission.
- Investigation output persistence and follow-up outcomes are not built yet.

## Next

- Day 4: persistent follow-through: store each investigation and its expected follow-up, ingest later measurements, and decide warming observed / target reached / not observed by the deadline / unable to verify, surviving restarts.

## Verification repair (2026-10-26)

An external audit of commit 4f4ed93 reported four validation gaps found by offline probes.

1. Claims bound to evidence: model observations replaced by `facts[]` with a per-claim-type evidence field allowlist, values checked against pack rounding, and code-rendered `verified_facts`; contract inv-v1 to inv-v2. Covered by `backend/tests/test_investigator.py`.
2. Readiness computed in code (`backend/aria_home/readiness.py`), documented in docs/readiness-rules.md. Covered by `backend/tests/test_readiness.py`.
3. Follow-up scheduling computed in code (`backend/aria_home/scheduling.py`). Covered by `backend/tests/test_scheduling.py`.
4. As-of visibility for trip and confirmation context (`context_as_of` in `backend/aria_home/scenario.py`), documented in backend/scenarios/README.md; the availability timestamps were added to synthetic fixtures on 2026-10-26, and two synthetic variants demo_revised_v1 and demo_cancelled_v1 were added. Covered by `backend/tests/test_as_of_context.py`.

Checks run by the operator on 2026-10-26:

- Base revision 5229d04 plus uncommitted repair changes (working tree not yet committed).
- Fresh virtual environment with only backend/requirements.txt: `python -m pytest -q` -> 166 passed.
- `cd frontend && npm run typecheck` -> passed; `npm run build` -> passed.
- `cd frontend && npx playwright test` (installed Chrome, backend forced to ARIA_HOME_MODEL_ENABLED=0 by playwright.config.ts): first run 1 failed / 1 passed (an unexpected browser console error in the overview test, not reproduced); next three runs 2 passed each. Treat this as a possible flaky cold start, not a clean pass.

Not re-run: no live model calls were made for this repair; the Day 3 live results (D3-3, D3-3b) were produced under the inv-v1 contract and have not been repeated under inv-v2.

Limitations: the claim check is bounded (structured facts and a phrase/number filter), not a semantic verifier of arbitrary prose; readiness thresholds are hand-set for the synthetic scenarios and not calibrated on real homes; at_risk is a qualified judgement, not a forecast; the browser test flake above is unexplained.

Process note: the repair ran as five Muse tasks on the uncommitted local tree (not from a clean GitHub checkout); each build-log entry is in docs/build-log/. In one task (day4-04) the operator's header naming the local tree was garbled by an escaping bug, since fixed.
