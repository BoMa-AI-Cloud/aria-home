Model: muse-spark-1.3
Turns: 99

Done. All four gates pass.

**Files changed**
- `backend/aria_home/public_demo.py` (new): demo flag, fail-closed check, session cookie/db paths, idle 2h + 500-cap sweep, 7-scenario/checkpoint allowlists, 4KB body cap
- `backend/aria_home/recorded.py` (new): exact-match recorded-answer lookup (scenario, time, input revision, model id, prompt/policy versions) with serve-time re-validation and per-answer provenance; fallback labeled exactly "No recorded model response for this snapshot"
- `backend/aria_home/app.py`: public-mode route gating (provider, power-context, live-power, WhatsApp, test hooks unregistered), `provider=None` investigation paths, session guard/cookie, body limits, checkpoint checks, JSON error handlers, `/api/scenarios`, `/api/session/reset`, `frontend/dist` serving, recorded-or-fallback investigation with provenance
- `backend/tests/test_public_demo.py` (new, 15 tests)
- `README.md`: "Public demo mode (for hosting)" section; `docs/public-demo-plan.md`: steps 2 and 4 marked done

**Tests added** (`test_public_demo.py`): fresh no-credential session; dangerous-route 404s with JSON bodies; fail-closed for each of the 5 live flags; scenario/time allowlists; oversized/malformed bodies 4xx; A/B isolation + reset-clears-only-A; ack-does-not-alter-verification; retention eviction; zero-outbound-HTTP spy (httpx/urllib/socket) over a full 8-checkpoint replay; recorded exact-match + 5 mismatch refusals + spark preference; cookie opacity/tamper rotation; dist serving.

**Real command outputs**
- `cd backend && python -m pytest tests/test_public_demo.py -q` → `15 passed in 8.20s` (final run, against built dist)
- `cd backend && python -m pytest -q` → `464 passed in 95.21s (0:01:35)`
- `cd frontend && npm run typecheck` → `tsc --noEmit`, no errors
- `cd frontend && npm run build` → `✓ built in 783ms` (dist/index.html + assets)
- `cd frontend && npm run test:e2e` → `34 passed (1.5m)`

Three bugs found and fixed along the way: `scenario_list` NameError, POST-to-unregistered-`/api/*` returning 405 via the GET catch-all (added explicit non-GET `/api/<path>` 404 route), and non-allowlisted-but-real scenarios returning 400 instead of 404 (guard now rejects any non-allowlisted scenario id up front).
