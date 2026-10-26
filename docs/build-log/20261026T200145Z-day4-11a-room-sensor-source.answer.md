Model: muse-wonder-1.0
Turns: 29

Edits:
- `backend/aria_home/contracts.py` — added `room_sensor` to `SourceKind`.
- `backend/aria_home/scenario.py` — added `ScenarioEvent` (`SimulatedEvent`/`ActorEvent` aliases), `Scenario.events`, optional `room_sensor.json` and `events.json` loading, and `events_as_of(scenario, now)` filtering by `available_at <= now`.
- `backend/aria_home/app.py` — `/api/sources` includes `room_sensor` only when `scenario.records` contains a room-sensor record.
- `backend/aria_home/metrics.py` — `temperature_trend` prefers `room_sensor` `indoor_temp` records for the zone when present, otherwise falls back to thermostat.
- `backend/tests/test_room_sensor.py` — new tests covering room-sensor preference, thermostat fallback, event visibility before/after `available_at`, and unchanged demo_v1 sources.

Real final pytest line:
```
174 passed in 4.14s
```
