ARIA Home, Day 9 task D9-1 (approved by Brad): record the clean-setup check and fix one README
gap. Docs only: README.md, docs/day9-handoff.md (new), docs/timeline.md. No code changes, no live
calls, no installs, no network, no git, NO helper scripts. DO THE WORK NOW in this turn.

Read README.md ("Try it in 5 minutes"), frontend/playwright.config.ts, docs/timeline.md.

1. README gap found by the operator: `npm run test:e2e` and `npm run record:demo` start the backend
   with plain `python -m flask ...`, so the backend virtual environment must be active in that
   terminal (or Flask must be installed for that python). Say so plainly in the Tests and Recording
   paragraphs, with the activate commands for PowerShell and macOS/Linux.
2. docs/day9-handoff.md, "Clean-setup check (operator, 2026-10-27)", copied exactly:
   - Fresh clone of https://github.com/BoMa-AI-Cloud/aria-home at cd776d0 into a new folder.
   - Fresh virtual environment, `pip install -r requirements.txt`: backend `python -m pytest -q`
     -> 216 passed, with MODEL_API_KEY and ARIA_HOME_MODEL_ENABLED unset.
   - `npm ci` -> found 0 vulnerabilities; `npm run build` -> built; `npm run typecheck` -> exit 0;
     `npm run test:e2e` with the clone's venv first on PATH -> 4 passed.
   - Not checked: macOS/Linux; a machine without Google Chrome installed (the tests use the
     installed Chrome); a hosted URL (none exists; pending office-hours answer).
3. timeline.md: one Day 9 line.
Final answer: the files changed.

