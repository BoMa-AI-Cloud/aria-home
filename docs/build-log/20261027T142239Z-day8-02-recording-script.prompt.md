ARIA Home, Day 8 task D8-2 (approved by Brad): record real interface footage for the video.
Tooling only, no product changes. DO THE WORK NOW in this turn. No live calls, no installs (use the
Playwright already in frontend/), no network beyond 127.0.0.1, no git, NO helper scripts outside
the files named here. Shell starts in C:\aria-home: prefix frontend commands with `cd frontend && `.
Do not end your turn until `cd frontend && npm run record:demo` has produced the clips and
`cd frontend && npm run test:e2e` still passes.

Read: docs/demo-script.md (sections A, B and H), frontend/playwright.config.ts,
frontend/e2e/app.spec.ts, frontend/package.json, .gitignore, frontend/src/App.tsx (labels).

BUILD:
1. frontend/playwright.record.config.ts: same webServer setup as playwright.config.ts but the
   backend env forces ARIA_HOME_MODEL_ENABLED=0 and ARIA_HOME_DB_PATH to a fresh file under the
   OS temp dir (deleted before the run), viewport 1280x720, video "on" at 1280x720, slowMo about
   250 ms, one worker, testDir frontend/recording, outputDir frontend/recordings.
2. frontend/recording/demo.record.ts: one test per storyboard segment that drives the real UI
   exactly as section A/H describe (scenario picks and replay buttons), scrolls the relevant panel
   into view, and waits on each key label before holding it on screen for a readable pause (2-4 s).
   Segments: s1-trip-cards (Simulated timeline cards 09:20 and 14:06), s2-not-responding (16:31),
   s3-authorized-help (16:52 and the simulated acknowledgement), s4-recovery (18:21, 18:51, 19:51,
   20:21), s5-report-and-arrival (20:46, 21:01). Each asserts its key text, so a broken screen
   fails instead of recording nonsense, and asserts "MOCK - example answer, not live inference" is
   visible whenever the Investigation is in frame.
3. package.json script "record:demo": runs that config. Add frontend/recordings/ to .gitignore.
4. A short section "Recording footage" in docs/demo-script.md section H: the command, where clips
   land (one .webm per segment), that the footage is the real UI in mock mode on a fresh database,
   and that the evaluation title card and the door shots are not product UI.
Final answer: files created, the clip filenames and sizes, and the REAL output lines.

