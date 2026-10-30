Model: muse-spark-1.3
Turns: 76

All edits are in place and verified by reading. Here is the final report.

## Audit 5 findings 1 & 2 — work done (execution blocked, see bottom)

**Files changed**
- `backend/aria_home/trace.py` — added `SCRIPTED_BASIS`, `UnknownInvestigation`, and the shared `investigation_trace_inputs(store, scenario, investigation_id, at)` (`trace.py:49`), returning the stored follow-up, `verify_recovery` on it, and `store.get_caregiver_decision(id, at=at)`. `build_trace` accepts `investigation_id`/`store`: with an id it uses those inputs (raising `UnknownInvestigation` when the store has no follow-up) and reports `"basis": "visitor investigation <id>"`; without it the stateless scripted story is unchanged with `"basis": "scripted story, no visitor decisions"`. The effective decision flows into both the permission step and `decide_hvac_notification(..., caregiver_decision=...)` (`trace.py:391`).
- `backend/aria_home/app.py` — `GET /api/trace` accepts optional `investigation_id`, scoped to the caller's session store (unknown id → 404, `at` before creation → 409); the follow-up view now sources follow-up/verification/decision from the same shared function (`app.py:820`) instead of re-implementing them.
- `frontend/src/api.ts` — `TraceResponse.basis: string`; `fetchTrace(scenario, at, investigationId?)` appends `investigation_id` when present.
- `frontend/src/App.tsx` — `TraceView` takes `investigationId`, passes it to `fetchTrace`, and with no investigation shows "Showing the recorded story; your own choices appear once you start an investigation."; call site passes the current id.
- `docs/audit-5.md` — created with 9 rows (2 findings + 7 doc/CI items); rows 1, 2, 7, 8, 9 updated with repair + tests.

**Tests added** — `backend/tests/test_audit5_trace_parity.py` (7 tests): verification-stage equality at all of 02:31/02:45/04:21/04:51/06:21/06:45/07:01; decline parity (permission + HVAC refused `caregiver_declined` vs real rows); approve parity; rewind-to-02:31 after a later decision; unknown id → 404; second public-demo visitor → 404; session reset → 404.

**Failing lines before the fix** (assertions that fail on pre-fix code, where `investigation_id` is ignored and the scripted 02:45 approval rules): `test_audit5_trace_parity.py:43` at 06:21 (`unable_to_verify` vs `goal_verified`), `:53` (permission `approved` instead of `declined`), `:86`, `:107`, `:117` (each get 200 instead of 404).

**Command output: none — no command could be run.** Every shell invocation in this session failed, including bare `Get-Location`, with `Tool error: Command contains malformed syntax that cannot be parsed: pwsh exited with code 1: The command line is too long.` I did not weaken any test and kept all working-tree changes. Before closing this audit, run from a working shell: `cd backend && python -m pytest -q`, `cd frontend && npm run test:e2e`, `cd frontend && npm run test:e2e:public-demo`. This blocker is also recorded in `docs/audit-5.md`.
