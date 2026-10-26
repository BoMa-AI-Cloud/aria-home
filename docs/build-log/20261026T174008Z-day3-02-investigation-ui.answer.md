Model: muse-spark-1.3
Turns: 25

Done writing, blocked on running: this session's permission mode requires your approval for any `npm` command, so I can't execute the RUN step myself.

**Changes** (all inside `C:\aria-home`, no backend/git/network):
- `frontend/src/api.ts` — typed `fetchInvestigation()` plus `InvestigationResponse`/`InvestigationOutput`/`TargetGap`/`InvestigationSummary` types matching `investigator.py` (`status`, `output`, `reasons`, `model_id`, `prompt_version`, `provider_mode`, `summary`).
- `frontend/src/App.tsx` — placeholder replaced with an `InvestigationSection`: readiness line in words (`On track` / `At risk` / `Cannot tell yet`) plus `Indoor <latest> <unit>, target <temp> <unit>` from `summary.metrics.target_gap`; observations with evidence-id chips; hypotheses labeled as hypotheses with Supporting/Conflicting chips; unknowns; clarification under "One question for you"; follow-up under "Next check"; always-visible Power Context statement + limitations; provenance line; prominent `MOCK - example answer, not live inference` label in mock mode; `rejected`/`unavailable`/null-output path shows "ARIA's explanation is unavailable" + reasons + deterministic summary only; loading and error states. Evidence cards untouched.
- `frontend/src/index.css` — styles for readiness line, chips, mock label, power-context block, provenance. Text labels carry meaning, colour never alone.
- `frontend/e2e/app.spec.ts` — existing assertions kept; added: readiness line with `Indoor … target`, first observation chip visible, "One question for you" + clarification text, Power Context statement, MOCK label.

**To verify, approve or run these:**
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- `cd frontend && npm run test:e2e`

Say the word and I'll retry the runs if you grant npm approval.
