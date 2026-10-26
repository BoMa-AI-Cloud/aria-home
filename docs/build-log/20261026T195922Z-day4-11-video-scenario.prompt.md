ARIA Home, video build step 2 (approved by Brad): the demo_video_v1 scenario data. Data, loader
and tests only; no new outcome logic yet (that is step 3). No live calls, no installs, no network,
no git, NO helper scripts. Do not end your turn until `cd backend && python -m pytest -q` passes.

Read first: docs/demo-script.md sections C and D, backend/aria_home/contracts.py,
backend/aria_home/scenario.py, backend/aria_home/evidence.py, backend/aria_home/metrics.py,
backend/scenarios/README.md and backend/scenarios/demo_v1/*.json.

DECISIONS (approved by Brad 2026-10-26):
- Arrival 21:00 = 19:45 landing + labeled 45 min airport-exit/baggage allowance + labeled 30 min
  driving allowance (store the allowances in the trip record as labeled estimates).
- Goal verification needs the target held for 30 minutes with no counted reading below it.
- An independent room sensor is a separate source kind (add `room_sensor` to SourceKind) with its
  own zone binding to demo-cabin/main; the thermostat is not used as the room sensor.
- The HVAC request may carry only property id/address label, access note, manager contact label
  and the relevant observations. The HVAC completion report becomes available to ARIA only after
  verification.

BUILD backend/scenarios/demo_video_v1/ following section C of docs/demo-script.md exactly
(times, -05:00, 2026-01-16): trip (known_at), homeowner confirmation (confirmed_at 09:20, target
68 F, notify_homeowner, manager_authorized), thermostat records stopping after 15:30 and resuming
18:20, room_sensor indoor_temp every 5 min all day (flat around the cold value until 18:35, then
rising, at or above 68.0 from 19:50 through 21:00), an electrical channel mapped to the blower
(binding status as the fixture mapping supports: "candidate" unless stated) active during the
outage, other circuits fresh, and weather. Put the simulated actor events (email, location,
preparation authorization, scene command and acknowledgement, manager alert, manager HVAC
authorization, HVAC request, visit, completion report) in a new `events.json` with event time
and available time, each with `"simulated": true`; the loader exposes them but nothing consumes
them yet. Label everything synthetic in manifest.json and in backend/scenarios/README.md.
Do not change existing scenarios. metrics.temperature_trend may prefer room_sensor for the zone
when present and fall back to thermostat; existing scenario results must not change.
TESTS: loader reads demo_video_v1; no thermostat record observed between 15:30 and 18:20; room
sensor records continue; events are hidden before their available time; the report's available
time is after 20:21; existing tests unchanged and passing.
Final answer: files, record counts per source, and the REAL final pytest line.

