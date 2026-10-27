Model: muse-wonder-1.0
Turns: 54

Files created:
- `frontend/playwright.record.config.ts` — same webServers as `playwright.config.ts`, backend forced `ARIA_HOME_MODEL_ENABLED=0` with a fresh DB at `%TEMP%\aria-home-recording.db` (deleted on load), 1280×720 viewport, `video: "on"` at 1280×720, `slowMo: 250`, 1 worker, `testDir: recording`, `outputDir: recordings`. Note: Playwright's bundled ffmpeg was missing and downloads were off-limits, so the config seeds Playwright's expected ffmpeg path by copying the already-installed system ffmpeg found via `where.exe` (`<user-home>\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe`) — no install, no network.
- `frontend/recording/demo.record.ts` — 5 tests (`s1-trip-cards` 09:20/14:06, `s2-not-responding` 16:31, `s3-authorized-help` 16:52 + `Acknowledge (simulated)`, `s4-recovery` 18:21/18:51/19:51/20:21, `s5-report-and-arrival` 20:46/21:01), each scrolling panels into view, asserting key labels, asserting `MOCK - example answer, not live inference` whenever Investigation is shown, and holding 2.5–4s per beat.

Files modified:
- `frontend/package.json` — added `"record:demo": "playwright test -c playwright.record.config.ts"`
- `.gitignore` — added `frontend/recordings/`
- `docs/demo-script.md` — added “Recording footage” under section H

Clips produced (one `.webm` per segment):
- `frontend/recordings/demo.record.ts-s1-trip-cards-chrome/video.webm` — 3,633,352 bytes
- `frontend/recordings/demo.record.ts-s2-not-responding-chrome/video.webm` — 1,855,874 bytes
- `frontend/recordings/demo.record.ts-s3-authorized-help-chrome/video.webm` — 3,392,733 bytes
- `frontend/recordings/demo.record.ts-s4-recovery-chrome/video.webm` — 3,529,122 bytes
- `frontend/recordings/demo.record.ts-s5-report-and-arrival-chrome/video.webm` — 2,770,186 bytes

Real output — `npm run record:demo`:
```
  ok 1 [chrome] › recording\demo.record.ts:39:1 › s1-trip-cards (31.7s)
  ok 2 [chrome] › recording\demo.record.ts:66:1 › s2-not-responding (16.3s)
  ok 3 [chrome] › recording\demo.record.ts:89:1 › s3-authorized-help (19.3s)
  ok 4 [chrome] › recording\demo.record.ts:120:1 › s4-recovery (27.0s)
  ok 5 [chrome] › recording\demo.record.ts:144:1 › s5-report-and-arrival (21.0s)
  5 passed (2.0m)
```

Real output — `npm run test:e2e`:
```
  ok 1 [chrome] › e2e\app.spec.ts:5:1 › synthetic evidence overview renders without errors (579ms)
  ok 2 [chrome] › e2e\app.spec.ts:81:1 › demo replay controls drive the outcome panel (1.0s)
  ok 3 [chrome] › e2e\app.spec.ts:125:1 › video scenario shows verification stages and simulated timeline (2.0s)
  ok 4 [chrome] › e2e\app.spec.ts:218:1 › video scenario shows scoped simulated notifications and homeowner update (1.3s)
  4 passed (11.6s)
```
