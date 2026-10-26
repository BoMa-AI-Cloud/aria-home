Model: muse-wonder-1.0
Turns: 30

**Files created/changed**

- Created: `backend/aria_home/clock.py`, `backend/aria_home/contracts.py`, `backend/aria_home/evidence.py`, `backend/aria_home/scenario.py`
- Changed: `backend/aria_home/app.py` — added `GET /api/sources`, `/api/health` unchanged
- Created: `backend/scenarios/demo_v1/{manifest,calendar,thermostat,electrical,weather}.json`
- Created: `backend/tests/{conftest,test_clock,test_evidence,test_scenario,test_sources_api}.py`
- Created: `.gitattributes` (`* text=auto eol=lf`)

**Design decisions**

The scenario loader overwrites every record's `mode` from the manifest before validation, so data rows cannot claim `live`. Freshness/conflict status is computed at evaluation time from `visible_records` (`received_at <= now`), with duplicate IDs deduplicated first and conflicts detected on subject+quantity+observed_at.

**Test command and real output**

Run from `C:\aria-home\backend`: `python -m pytest -q`

```
...........................                                              [100%]
27 passed in 1.01s
```

