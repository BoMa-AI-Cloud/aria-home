Model: muse-wonder-1.0
Turns: 9

# ARIA Home ΓÇö Day One plan (no implementation started)

## A. Workspace inspection (read-only)

- **Path:** `C:\aria-home` ΓÇö confirmed. Contains only `README.md` and `.gitignore` (plus `.git/`). No app code, no `package.json`/`pyproject.toml`/lockfiles. Not empty, but effectively a blank scaffold.
- **Repo:** Exists. Branch `main`, clean at session start, one commit `f333d48` ("Start ARIA Home after the hackathon kickoff"). `README.md` already records: nothing built yet, synthetic-only, no secrets, Meta models at runtime.
- **OS/shell:** Windows 11 Home (10.0.26300), win32. PowerShell primary, Bash also available.
- **Python/Node/package managers: could not verify this session.** Both shell tools failed with "muse-wonder-1.0 is temporarily unavailable" (safety classifier), so I won't guess versions. Please run these read-only commands and paste the output:

```powershell
python --version; node --version; npm --version; git --version
```

- **Coding model:** This session's harness reports `muse-wonder-1.0`. I can't independently verify it beyond that.
- Nothing was read beyond `README.md`/`.gitignore`, and nothing was modified in the workspace. (Plan written to the designated plan file outside the repo.)

## B. Proposed architecture, in plain language

A React+TypeScript+Vite page talks over JSON to a small Flask backend. The browser never holds any API key. The backend serves four clearly labeled synthetic sources ΓÇö trip/calendar, thermostat, circuit-level electricity, weather ΓÇö from one versioned scenario file replayed against a **fixed scenario clock**, so the demo is reproducible. Every record carries three distinct times: when it was observed, when we received it, and the scenario time at which we're evaluating it.

Deterministic Python code ΓÇö never the model ΓÇö owns temperature math, data-freshness checks, who is allowed to see what, and later, whether the target temperature was reached. The Meta model receives a pre-built "evidence pack" and may only synthesize an explanation that separates **observations, hypotheses, missing information, and uncertainty**, plus ask a relevant clarifying question. It cannot invent a diagnosis.

Evidence rules are enforced in the data schema, not just the prompt: thermostat "heating" state is not proof of delivered heat; circuit activity is not proof of useful heating; activity on other circuits only weighs against a *complete* outage during the observed interval; a missing reading stays `null`, never `0`; no circuit is called "normal" without a defined baseline; circuitΓåÆequipment mapping is an explicit field; forecasts are labeled as not on-property measurements. Notifications exist as drafts with distinct created/sent/delivered/acknowledged/resolved states ΓÇö nothing is actually sent on Day One. SQLite is deferred until persistence is genuinely needed; scenario state starts as a JSON file. Provider access sits behind one interface: a `MockProvider` (default, always labeled MOCK) and a `MetaProvider` stub that stays off until we verify the real endpoint, SDK, and model ID from official documentation.

## C. Day One task sequence

| # | Task | Coding model | Files | Pass/fail checkpoint | Approval needed |
|---|------|-------------|-------|---------------------|-----------------|
| 0 | You run the version commands above | ΓÇö | none | Versions visible | No |
| 1 | Flask backend + `GET /api/health` + pytest | Spark | `backend/app.py`, `backend/requirements.txt`, `backend/tests/test_health.py`, `.env.example` (placeholder only) | `pytest` green; health returns `{"status":"ok"}` | **Yes: `pip install flask pytest`** |
| 2 | Synthetic scenario + 4 sources, fixed clock | Wonder (evidence schema) ΓåÆ Spark (fixtures) | `backend/aria/scenario.py`, `backend/aria/sources.py`, `backend/data/scenario_v1.json`, `backend/tests/test_sources.py` | Tests pass: missing Γëá 0; replay at a fixed time is deterministic; every source reports timestamps + availability | No |
| 3 | Vite React+TS frontend, 4 source cards | Spark | `frontend/` scaffold, `src/App.tsx`, `src/api.ts` | `npm run build` passes; cards show timestamps/availability under a "Synthetic data" banner | **Yes: Vite scaffold + `npm install`** |
| 4 | Provider interface + mock | Wonder (contract) ΓåÆ Spark | `backend/aria/provider.py`, `backend/tests/test_provider_mock.py` | Mock tests green; mock output visibly labeled "MOCK ΓÇö not live inference" | No spend |
| 5 | Browser smoke test | Spark | checklist in handoff doc | Page loads, health OK, 4 cards render | No |
| 6 | **Optional** single bounded live Meta test | Wonder | `docs/live-test-001.md` | One tiny prompt within your $10 Day One budget, ideally on confirmed promo credits ΓÇö or an explicit documented blocker | **Yes, separately, before any paid call**, and only after verifying Baseten `meta-models/muse-spark-open-1026` vs. Meta Model API access from official docs |
| 7 | Honest handoff | Spark | `docs/day1-handoff.md`, `docs/timeline.md` | States what works, what was tested, mock-vs-live truthfully | Commit/push only if you ask |

Explicitly **not** today: the full agent, live integrations, notification delivery, elaborate charts, full outcome verification.

## D. Decisions that materially block the next step

1. **Tool versions** (Task 0 output) ΓÇö the only blocker for scaffolding.
2. **Your approval to install dependencies** (pip + npm) ΓÇö blocks Tasks 1 and 3.
3. **Runtime provider + verified account access** (Meta Model API vs. Baseten, confirmed model ID) ΓÇö blocks only the optional live test, not the mock-first build. Don't paste keys in chat; we'll use local env vars when we get there.

Non-blocking defaults I'll assume unless you object: SQLite deferred in favor of a scenario JSON file; notifications as data shapes only; standard Flask/Vite local ports.

## E. Stopping here

No files created in `C:\aria-home`, nothing installed, no paid calls, no commits. Approve the plan (and run the Task 0 commands when you can), and Day One starts at Task 1.
