ARIA Home: finish the interrupted day11-06 task (approved by Brad, 2026-10-29). DO THE WORK NOW in this turn.
IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; keep
editing and running commands until the done-condition holds. No live calls, no installs, no git, NO helper scripts
outside tests. Do not weaken any test. Keep all working-tree changes. Shell starts in C:\aria-home; prefix frontend
commands with `cd frontend && `. Do not end your turn until `cd backend && python -m pytest -q`,
`cd frontend && npm run typecheck`, `cd frontend && npm run build`, `cd frontend && npm run test:e2e` and
`cd frontend && npm run test:e2e:public-demo` all pass.

The previous task (day11-06: muse-wonder-1.0 review in backend/aria_home/review.py and muse-voice-transcribe-1.0 in
backend/aria_home/transcribe.py) stopped at "Now wiring app.py". Its prompt is
docs/build-log/*day11-06-wonder-review-transcribe.prompt.md; read it and finish every part it lists (A-D).
The backend suite now has 3 failures, each `assert 5 == 4` on the number of evidence sources:
tests/test_room_sensor.py::test_demo_v1_sources_unchanged, tests/test_smoke_app.py::test_smoke_page_contract and
tests/test_sources_api.py (line 11). Decide from the day11-06 rules whether that 5th source is correct: a transcribed
technician report is a human_report, never a sensor measurement, so it must not be added to the measurement source
list for demo_v1 or counted as a sensor source. Fix the code, not the expected count, unless the code is right and the
test expectation genuinely needs the new source; explain which and why.
Final answer: what was unfinished, what you changed, and the REAL output lines of every command.

