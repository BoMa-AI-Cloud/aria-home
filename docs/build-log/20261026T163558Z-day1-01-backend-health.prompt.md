ARIA Home, Day One, Task 1 (approved by Brad): Flask backend with a health endpoint and pytest.

Context: your earlier plan for this workspace is approved. This is a NEW standalone project for the
Meta Global AI Developer Hackathon. Work only inside C:\aria-home. Do not read, copy or reference
any file outside it. Write all code fresh.

Already installed on this machine (do NOT install anything): Python 3.12.7 with Flask 3.1.3,
pytest 9.0.3, pydantic 2.12.5, httpx 0.28.1. Node 25.9.0 / npm 11.12.1 exist but the frontend is
NOT part of this task.

Create exactly:
- backend/aria_home/__init__.py
- backend/aria_home/app.py: a Flask app factory `create_app()`; `GET /api/health` returns JSON
  {"status": "ok", "service": "aria-home-backend", "data_mode": "synthetic"}. No model calls, no
  network, no secrets read. The app must start without any environment variables set.
- backend/requirements.txt: pin the versions listed above that the backend uses (flask, pytest).
- backend/tests/test_health.py: tests that the health route returns 200 with that JSON, and that
  importing the app needs no environment variables.
- backend/pytest.ini (or pyproject section) so `python -m pytest` run from backend/ finds the tests
  without warnings.
- .env.example at the repo root: variable NAMES only, no values: ARIA_HOME_PROVIDER_URL,
  ARIA_HOME_MODEL_ID, MODEL_API_KEY, ARIA_HOME_MODEL_ENABLED. One comment line each.
- Append a "Run the backend" section to README.md (keep everything already in README.md).

Rules: no other files; no dependency installs; no network; no git commands; no commits. Keep code
small and commented only where the reason is non-obvious. Every Python file starts with a
one-line module docstring.

When done, run from C:\aria-home\backend: python -m pytest -q
If you cannot run commands, say so plainly and list the exact command for me to run.

Final answer: files created, what each does, the exact test command and its real output (or that
you could not run it). Do not claim tests passed unless you saw them pass.

