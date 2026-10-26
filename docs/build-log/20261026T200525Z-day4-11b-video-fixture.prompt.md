ARIA Home, video build step 2b (approved by Brad). DO THE WORK NOW: create the files in this turn.
Do not stop after describing a plan, do not write helper scripts (write the JSON directly), and
do not end your turn until the files exist and `cd backend && python -m pytest -q` passes. No
live calls, no installs, no network, no git. Data and tests only; do not change aria_home code.

Read: docs/demo-script.md section C (the timeline), backend/scenarios/README.md,
backend/scenarios/demo_v1/*.json (format), backend/aria_home/scenario.py (room_sensor.json and
events.json formats), backend/tests/test_room_sensor.py.

APPROVED DECISIONS: arrival 21:00 = 19:45 landing + labeled 45 min airport-exit/baggage + labeled
30 min driving allowances; goal verified only after 30 minutes at or above target; the room
sensor is its own source; the HVAC request carries only property label, access note, manager
contact label and observations; the HVAC completion report is available to ARIA only after
verification (20:45).

CREATE backend/scenarios/demo_video_v1/ (2026-01-16, -05:00, all synthetic), following section C:
- manifest.json (synthetic label, sources, cadences), calendar.json (trip known_at 09:03 with
  arrival 21:00 and the labeled allowances; confirmation confirmed_at 09:20, 68 F,
  notify_homeowner true, manager_authorized true), weather.json.
- thermostat.json: indoor_temp and state every 5 min from 06:00 to 15:30, then NO records until
  18:20, then every 5 min to 21:30 (received 20 s after observed).
- room_sensor.json: indoor_temp every 5 min 06:00-21:30: about 55 F falling slowly to 52 F
  through the outage, flat until 18:35, rising at least 2.0 F by 18:50, reaching 68.0 at 19:50,
  and 68.0-68.6 from 19:50 through 21:30 (no reading below 68.0 after 19:50).
- electrical.json: a circuit mapped to the blower (binding "candidate") showing blower-level
  watts (about 400-600 W) during 15:30-18:20 and furnace-level watts after 18:20; two other
  circuits with fresh normal activity all day.
- events.json, each simulated: true: email_flight_confirmation 09:00/09:02, location_airport
  09:10/09:11, confirmation_request 09:15/09:15, preparation_authorized 14:00/14:00,
  scene_command 14:05/14:05, scene_acknowledged 14:06/14:06 (payload says physical success
  unknown), location_unavailable 14:10/14:10, manager_alert 16:35/16:37, manager_hvac_authorized
  16:45/16:45, hvac_request 16:50/16:52 (payload only the approved fields), service_visit
  17:30/18:15, hvac_completion_report 20:40/20:45.
Update backend/scenarios/README.md with a demo_video_v1 section. TESTS in a new
backend/tests/test_demo_video_scenario.py: loads; no thermostat record observed after 15:30 and
before 18:20; room sensor continues; every event hidden before available_at; the report's
available time is after 20:21; hvac_request payload has no itinerary/email/location keys;
existing tests unchanged. Final answer: files, record counts, REAL final pytest line.

