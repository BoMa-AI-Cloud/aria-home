Model: muse-spark-1.3
Turns: 93

Both suites pass. The work is done — writing the final summary.

**Root cause:** after the confirmed arrival, every reading is old by design, but the inv-v2 contract still asked the model for a `current_temperature`. The model complied, and the claim checks correctly rejected the stale/superseded readings — all 6 live rejections were `arrival_passed` cases. Contract gap, not just model error.

**Fix (contract inv-v2 → inv-v3):** when computed readiness is `arrival_passed` (or eval time is past arrival), the model must state the temperature *at arrival* — the last eligible reading observed *and* received by arrival — as a new `temperature_at_arrival` fact, and must not state `current_temperature`. Checks still reject stale/superseded `current_*` claims, and reject an arrival fact citing a post-arrival, non-last, ineligible/conflicted reading; electrical activity is never a temperature fact.

**Files changed:**
- `backend/aria_home/investigator.py` — `PROMPT_VERSION=inv-v3`, `INFERENCE_IDENTITY_VERSION=inference-identity-v3` (identity keys change accordingly), new prompt/schema/`ClaimType`, `_arrival_selection` (mirrors the readiness arrival branch incl. room-sensor preference, freshness cap, conflict exclusion), arrival claim checks, arrival fact rendering, fallback summary gains `temperature_at_arrival` after arrival
- `backend/aria_home/provider.py` — mock follows inv-v3: arrival packs get `temperature_at_arrival` + target only, no stale current claims
- `backend/aria_home/evaluation.py` — `render_markdown` notes the inv-v3 contract / inv-v2 live runs
- `backend/tests/test_investigator.py` — `inv-v3` assert; 10 new tests (below)
- `frontend/src/api.ts` — `ClaimType` gains `temperature_at_arrival`
- Docs: `evaluation.md` (contract note + 77cafc9 run marked inv-v2), `readiness-rules.md`, `inference-idempotency.md`, `submission.md` (now 17 cases / 9 scenarios), `README.md` (9 scenarios, inv-v3), `SECURITY.md`, `freeze.md`, `demo-script.md`, `red-team.md`

**Tests added** (`test_investigator.py`): mock answer passes for each of the 6 arrival cases; stale-as-current still rejected; post-arrival-citing arrival fact rejected; superseded-reading arrival fact rejected; electrical-as-temperature rejected; pre-arrival behavior covered by unchanged existing tests.

**Offline recompute:** the sandbox refused to execute the evaluation CLI directly, so I verified equivalence instead — `results-offline.json` is byte-identical to code output and `evaluation.md` matches the renderer (`test_committed_offline_results_match_run_offline`, `test_committed_evaluation_docs_start_with_rendered_offline` pass). Exact code counts: **17 cases, 9 scenarios** — combined 17/17, thermostat-only 12/17, room-sensor-only 3/17, electrical-only 2/17, calendar-only 2/17; verification scored 5/17.

**Real output lines:**
- Backend: `400 passed in 40.73s` (`python -m pytest -q`)
- Frontend: `34 passed (1.3m)` (`npm run test:e2e`)
