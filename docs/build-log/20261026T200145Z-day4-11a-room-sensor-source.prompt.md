ARIA Home, video build step 2a (approved by Brad). DO THE WORK NOW: edit the files in this turn.
Do not stop after describing a plan, do not write helper scripts, and do not end your turn until
your edits are made and `cd backend && python -m pytest -q` passes. No live calls, no installs,
no network, no git.

Read: backend/aria_home/contracts.py, backend/aria_home/scenario.py, backend/aria_home/metrics.py,
backend/aria_home/app.py (/api/sources), backend/tests/test_sources_api.py.

CHANGE (code only, no new scenario yet):
1. contracts.py: add `room_sensor` to SourceKind (an independent indoor-temperature sensor,
   separate from the thermostat).
2. scenario.py: load an optional `room_sensor.json` and an optional `events.json` (simulated actor
   events: id, kind, event_time, available_at, simulated: true, payload dict). Expose
   `events_as_of(scenario, now)` returning only events with available_at <= now. Missing files
   mean no records/events.
3. /api/sources lists room_sensor only when the scenario has room-sensor records, so demo_v1 still
   shows exactly its 4 sources.
4. metrics.temperature_trend: for the zone, use room_sensor records when the scenario has any,
   otherwise thermostat (unchanged for every existing scenario).
TESTS (new file backend/tests/test_room_sensor.py using a tmp_path scenario copy of demo_v1 plus a
small room_sensor.json and events.json): room sensor preferred for the trend; thermostat used when
absent; events hidden before available_at; demo_v1 sources unchanged.
Final answer: the edits and the REAL final pytest line.

