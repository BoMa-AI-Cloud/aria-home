Model: muse-wonder-1.0
Turns: 37

**Cause of earlier failure:** `openInset()` asserted the Outcome panel via `section(page, "Outcome")`, which is `locator("section", { has: getByRole("heading", …) })`. With `?inset=timeline` (or `notifications`), `index.css` sets that section to `display: none`, removing it from the accessibility tree, so the role-based `has` matched 0 elements: `Expected: 1, Received: 0` at `insets.record.ts:20`. Two more defects surfaced on the full run: the default 5s `toBeEnabled` timeout was too short when nine clips run sequentially against the shared backend, and i2 replayed to 14:06 while the Location unavailable event is only available at 14:10 (`backend/scenarios/demo_video_v1/events.json:9`).

**Files changed (this turn):** only `frontend/recording/insets.record.ts` — Outcome assertions now use the CSS locator `.outcome-status` (finds hidden panels), `openInset`/`replay` wait up to 30s and `replay` waits for the button to re-enable after each fetch, i4 reads the hidden Outcome headline the same way, and i2 replays 14:06 → 16:31 so the 14:10 card is present. The prior run's files (`src/App.tsx`, `src/index.css`, `playwright.record.config.ts`, `package.json`, `.gitignore`, `e2e/app.spec.ts`) were kept unchanged.

**Clips (all in `frontend/recordings-insets/…/video.webm`):** i1-trip, i2-location, i3-not-responding, i4-help, i5-restored, i6-warming, i7-verified, i8-report, i9-arrival

**REAL output lines:**
```
  ok 9 [insets] › recording\insets.record.ts:124:1 › i9-arrival (9.7s)
  9 passed (1.5m)
  ok 6 [chrome] › e2e\app.spec.ts:323:1 › keyboard replay to 21:01 shows arrival expectation met (824ms)
  6 passed (14.6s)
> tsc --noEmit
```

