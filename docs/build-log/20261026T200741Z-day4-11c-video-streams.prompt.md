ARIA Home, video build step 2c (approved by Brad): finish backend/scenarios/demo_video_v1.
DO THE WORK NOW in this turn; do not stop after a plan or a progress note. Do not end your turn
until the files exist and `cd backend && python -m pytest -q` passes. No live calls, no installs,
no network, no git.

The previous task wrote manifest.json, calendar.json, weather.json and events.json but stopped
before the sensor streams. Writing hundreds of records by hand is not required: write ONE small,
committed, deterministic generator at backend/scenarios/demo_video_v1/generate_streams.py (stdlib
only, no randomness, writes only thermostat.json, room_sensor.json and electrical.json in its own
folder, a docstring saying the data is synthetic and how to rerun it), then RUN it with
`python backend/scenarios/demo_video_v1/generate_streams.py`.

Read: the existing demo_video_v1 files, docs/demo-script.md section C,
backend/scenarios/demo_v1/thermostat.json and electrical.json (format),
backend/aria_home/scenario.py (room_sensor.json format).

Streams (2026-01-16, -05:00, received_at = observed_at + 20 s):
- thermostat: indoor_temp and state every 5 min 06:00-15:30, then NO records until 18:20, then
  every 5 min to 21:30, values matching the room sensor within 0.5 F.
- room_sensor: indoor_temp every 5 min 06:00-21:30: about 55 F falling to 52 F by 15:30, flat
  near 52 F until 18:35, rising at least 2.0 F by 18:50, reaching 68.0 at 19:50, then 68.0-68.6
  through 21:30 (never below 68.0 after 19:50).
- electrical: a circuit mapped to the blower (binding "candidate") at about 400-600 W from 15:30
  to 18:20 and furnace-level (about 900 W) after 18:20; two other circuits with fresh normal
  activity all day; cadence as in demo_v1.
Update manifest.json and backend/scenarios/README.md if they need the stream names. TESTS in a new
backend/tests/test_demo_video_scenario.py: loads; no thermostat record observed after 15:30 and
before 18:20; room sensor continues through the outage; every room reading after 19:50 >= 68.0;
every event hidden before available_at; the report's available time is after 20:21; hvac_request
payload has no itinerary/email/location keys; existing tests unchanged.
Final answer: files, record counts per stream, REAL final pytest line.

