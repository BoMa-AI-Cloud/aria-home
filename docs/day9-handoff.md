# Day 9 handoff

## Clean-setup check (operator, 2026-10-27)

- Fresh clone of https://github.com/BoMa-AI-Cloud/aria-home at cd776d0 into a new folder.
- Fresh virtual environment, `pip install -r requirements.txt`: backend `python -m pytest -q` -> 216 passed, with MODEL_API_KEY and ARIA_HOME_MODEL_ENABLED unset.
- `npm ci` -> found 0 vulnerabilities; `npm run build` -> built; `npm run typecheck` -> exit 0; `npm run test:e2e` with the clone's venv first on PATH -> 4 passed.
- Not checked: macOS/Linux; a machine without Google Chrome installed (the tests use the installed Chrome); a hosted URL (none exists; pending office-hours answer).
