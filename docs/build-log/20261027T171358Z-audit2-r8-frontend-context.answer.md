Model: muse-wonder-1.0
Turns: 114

**Rule adopted:** Selected `(scenario, at)` is the single context: `/api/sources` (and metrics/power-context/investigation when given) honour `scenario`+`at`; every API JSON response echoes `scenario`, `at`, `timezone="America/New_York"` (from `manifest.timezone`); frontend uses per-resource request tokens, checks echoed `scenario`/`at`, labels stale evidence while loading, and labels investigations evaluated before replay time as historical. All scenario times render in `America/New_York` as e.g. `4:31 PM ET`, browser-independent. Schema init/migration (`next_check_at`, `schedule_status`, `deadline_passed`) runs in one `BEGIN IMMEDIATE` transaction with column-exists checks, no `executescript`.

**Pre-fix regression:** `tests/test_r8_context_concurrency.py` — `2 failed, 1 passed` (missing `scenario` echo on `/api/sources` and `/api/health`); the 8-thread fresh-DB race passed intermittently pre-fix on this machine.

**Files changed:**
- Backend: `backend/aria_home/app.py`, `store.py`, `scenario.py`, all 6 `backend/scenarios/*/manifest.json` (`timezone` added), new `backend/tests/test_r8_context_concurrency.py` (8 concurrent first-time inits × 5 fresh `tmp_path` DBs, sources-context and every-GET echo tests)
- Frontend: `frontend/src/App.tsx` (ET formatting, sources follow scenario+replay, tokens, stale label, historical label, replay buttons no longer blocked by loading), `frontend/src/api.ts` (`fetchSources(scenario, at)`, echo fields), `frontend/playwright.config.ts` (`utc` + `los-angeles` projects, ports via `PLAYWRIGHT_FRONTEND_PORT`/`PLAYWRIGHT_BACKEND_PORT`, busy ports error rather than being killed), `frontend/vite.config.ts` (proxy honours backend port), `frontend/e2e/app.spec.ts` (3 new tests: scenario/advance/rewind source cards, rapid selections end on last, ET in both timezones)

**Existing assertion changes (3, all exact-equality expansions for the mandated echo, none weakened):**
- `backend/tests/test_health.py::test_health_returns_ok` and `backend/tests/test_sources_api.py::test_health_unchanged`: expected health body now includes `scenario`, `at`, `timezone`
- `backend/tests/test_evaluation_offline.py`: expected body is file contents plus the same three echo fields

**Verification:** `npm run typecheck` pass, `npm run build` pass, `npm run test:e2e` — 18 passed (9 tests × UTC/Los Angeles).

**REAL final pytest line:** `269 passed in 13.38s`
