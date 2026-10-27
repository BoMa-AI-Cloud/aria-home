ARIA Home, Day 8 task D8-1 (approved by Brad): bring docs/demo-script.md up to date with what is
built. Docs only (docs/demo-script.md). No code changes, no live calls, no installs, no network,
no git, NO helper scripts. DO THE WORK NOW in this turn.

Read: docs/demo-script.md, docs/freeze.md, docs/evaluation.md, docs/day4-handoff.md,
docs/day5-handoff.md, docs/day6-handoff.md, frontend/src/App.tsx (exact on-screen labels and
button times), frontend/e2e/app.spec.ts, backend/scenarios/demo_video_v1/events.json.

CHANGES:
1. Section B: re-judge every shot's status from the code as it is now (implemented / partial /
   missing / unverified); for each implemented shot give the exact screen action (scenario name as
   shown, replay button) and the exact on-screen text to capture. Shots with no UI (email card,
   location, scene) are filmed from the Simulated timeline cards, labelled SIMULATED.
2. Section A: keep 180 s and the closing lines verbatim; align narration and on-screen text with
   the real labels (e.g. "Thermostat telemetry missing", "Temperature goal verified", "Arrival
   expectation met", "Acknowledged, not resolved", "Simulated, no message was sent"). Shorten the
   opening disclosure so it reads in 15 s at about 150 wpm (at most 38 words), keeping its meaning:
   ARIA is an existing project; the name, planning notes and designs predate the event; all ARIA
   Home code shown was written this week with Meta's Muse models. Add one 10-15 s beat for the
   evaluation result (combined 12/12 vs single sources) taken from docs/evaluation.md, and shorten
   another segment to keep the total at exactly 180 s.
3. New section H "Filming checklist": fresh database (delete backend/instance/aria_home.db), backend
   with ARIA_HOME_MODEL_ENABLED=0 for mock takes, browser at 1280x720, the exact replay sequence
   for the video scenario (16:31, 16:52, 18:21, 18:51, 19:51, 20:21, 20:46, 21:01), when the MOCK
   label must be in frame, how a live take differs (one live investigation call, its real wait,
   needs Brad's approval of that call), and that edited waits are disclosed on screen.
4. Section G: replace the build sequence with what remains (recording script, README, user-test
   wording fixes) and remove decisions already made, listing them as decided with the date.
Final answer: the new section A table and section H.

