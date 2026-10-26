Model: muse-spark-1.3
Turns: 13

Done — 6 files created, 1 updated. I could not run the tests: this session blocks directory changes, environment-variable changes, and ad-hoc `python -c` commands, so I can't execute anything here. Run this exact command to verify:

```
cd C:\aria-home\backend && python -m pytest -q
```

Files:

- `backend/aria_home/__init__.py` — package marker with module docstring.
- `backend/aria_home/app.py` — `create_app()` factory; `GET /api/health` returns `{"status": "ok", "service": "aria-home-backend", "data_mode": "synthetic"}`. No env reads, no network.
- `backend/requirements.txt` — pins `Flask==3.1.3`, `pytest==9.0.3`.
- `backend/tests/test_health.py` — asserts the health route returns 200 with the exact JSON; reloads `aria_home.app` with the four env vars deleted to prove no env vars are needed.
- `backend/pytest.ini` — `testpaths = tests` so `python -m pytest` from `backend/` finds tests without warnings.
- `.env.example` (repo root) — the four variable names with empty values, one comment line each.
- `README.md` — appended a `Run the backend` section; existing content untouched.

Test output: none — I was not able to run `python -m pytest -q` in this session. Do not treat tests as passing until you run the command above and see `2 passed`.

