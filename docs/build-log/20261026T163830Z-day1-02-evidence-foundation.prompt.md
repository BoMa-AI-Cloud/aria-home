ARIA Home, Day One, Task 2 (approved by Brad): the evidence foundation every later feature builds on.

This is a NEW standalone project for the Meta Global AI Developer Hackathon. Work only inside
C:\aria-home. Do not read, copy or reference anything outside it. Write all code fresh. Read the
existing files in backend/ first and build on them (Flask app factory in backend/aria_home/app.py,
tests in backend/tests/, pytest.ini).

Installed (do NOT install anything): Python 3.12.7, Flask 3.1.3, pydantic 2.12.5, pytest 9.0.3,
httpx 0.28.1. No network. No git commands.

GOAL
A small, strict, well-tested core that later tasks (Meta investigation, follow-up outcomes,
notifications, UI) can plug into without rework. Prefer a few clear modules over many layers.

1. backend/aria_home/clock.py
   - A `Clock` protocol with `now() -> datetime` (timezone-aware, UTC).
   - `FixedClock(at)` and `ScenarioClock(start, step)` that can be advanced explicitly for replay.
   - Reject naive datetimes with a clear error.

2. backend/aria_home/contracts.py (pydantic v2 models, `extra="forbid"`)
   - `DataMode` enum: synthetic, replay, live.
   - `SourceKind` enum: calendar, thermostat, electrical, weather.
   - `EvidenceKind` enum: measurement, device_report, forecast, human_statement, derived.
   - `Availability` enum: available, missing, stale, invalid, conflicting.
   - `EvidenceRecord`: id (stable string), source (SourceKind), kind (EvidenceKind), subject
     (property / zone / circuit / device id), quantity (e.g. "indoor_temp", "setpoint",
     "hvac_reported_state", "circuit_power", "outdoor_temp_forecast"), value (float | str | None),
     unit (str | None), observed_at, received_at (both timezone-aware), expected_cadence_s
     (int | None), mode (DataMode), provenance (fixture id + version), and optional
     `binding` (see below). A missing reading is value=None, NEVER 0. Validators: observed_at must
     not be after received_at; units must match a small allowed table per quantity (F or C for
     temperatures, W for power); forecasts must have kind=forecast.
   - `CircuitBinding`: circuit_id, equipment (str | None), status (confirmed | candidate | unknown),
     confirmed_by (str | None). Only `confirmed` may support equipment-specific statements.
   - `Trip`: id, property_id, title (untrusted text), planned_arrival (aware), revision (int),
     cancelled (bool).
   - `HomeownerConfirmation`: trip_id, property_id, target_temp, target_unit, notify_homeowner
     (bool), manager_authorized (bool), confirmed_at.
   - `SourceStatus` (what a source card shows): source, availability, record_count,
     newest_observed_at (None if no records), age_s at the evaluation time (None if no records),
     mode, notes (list[str]).
   - Notification states as an enum only (no sending): created, attempted, provider_accepted,
     delivered, acknowledged, failed. Document in a docstring that acknowledgement is not
     resolution.

3. backend/aria_home/evidence.py
   - `freshness(record, now)` -> available | stale using expected_cadence_s (stale when age >
     2 x cadence; records with no cadence are never auto-stale). Future observations beyond a
     60 s skew are `invalid`. value=None -> `missing`.
   - `source_status(source, records, now)` -> SourceStatus, computed at the evaluation time, not
     at ingestion. Duplicate ids are removed; same subject+quantity+observed_at with different
     values -> conflicting.

4. backend/aria_home/scenario.py + backend/scenarios/demo_v1/
   - A manifest.json: id, version, mode="synthetic", description, author="ARIA Home (synthetic)",
     created date, and the start of the scenario clock. The loader sets every record's `mode`
     from the manifest; nothing in the request or the data rows can override it.
   - Four JSON files (calendar.json, thermostat.json, electrical.json, weather.json) for ONE
     synthetic property "demo-cabin" (no real names, addresses or people). Story: owner returns
     Friday 18:00 local (America/New_York) with target 68 F; the thermostat reports "heating" but
     indoor temperature stays flat around 52 F over the last 3 hours; the bound furnace circuit is
     quiet while three other circuits show fresh activity; one thermostat reading is missing;
     weather is a labeled forecast near 30 F. Include records arriving later than the evaluation
     time so replay can hide the future.
   - `load_scenario(path)` -> validated records + trip + confirmation + manifest.
   - `visible_records(records, now)`: only records whose received_at <= now (the replay rule).

5. backend/aria_home/app.py: add `GET /api/sources?at=<ISO time>` returning the four SourceStatus
   objects for the demo scenario at that scenario time (default: the manifest start + 3 h). Keep
   /api/health unchanged. The response must include "data_mode": "synthetic".

6. Repo hygiene: add .gitattributes at the repo root forcing LF for text files (`* text=auto eol=lf`).

TESTS (backend/tests/), real assertions, no network:
- naive datetimes rejected; observed_at > received_at rejected; bad unit rejected.
- missing value stays None and yields `missing`, never 0.
- freshness flips to stale as the ScenarioClock advances, with no new records.
- future-dated record -> invalid; duplicate ids deduplicated; conflicting values detected.
- the manifest sets mode; a data row claiming "live" does not change it.
- visible_records hides records received after `now`.
- /api/sources returns four sources with ages computed at the requested time.
- the demo scenario loads and contains no circuit with a binding status other than its file says.

When done, run from C:\aria-home\backend: python -m pytest -q. If you cannot run commands, say
so and give the exact command.

Final answer: files created/changed, design decisions in two or three sentences, the test command
and its REAL output (or that you could not run it). Do not claim tests pass unless you saw it.

