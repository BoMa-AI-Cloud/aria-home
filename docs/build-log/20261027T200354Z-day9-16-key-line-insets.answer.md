Model: muse-wonder-1.0
Turns: 38

**Files**

- `frontend/src/App.tsx` — test-only `?key=<name>` parsing, `KEY_CAPTIONS` (replay time in ET), `key-active key-<name>` page classes, `.key-caption` line, `key-plan-row` marks on the Target temperature / Manager coordination / Confirmed rows. No effect without `?key`.
- `frontend/src/index.css` — key view: one real element per key (via `aria-labelledby` / `aria-label` selectors), ~44–56 px text, centred, plain light background, other panels/parts hidden, small grey fixed caption.
- `frontend/recording/keys.record.ts` — 13 tests, one per key, each asserting its text and caption, 6 s hold.
- `frontend/playwright.record.config.ts` — `keys` project: 1280×360, `deviceScaleFactor: 2`, output `recordings-keys`.
- `frontend/package.json` — `"record:keys": "playwright test -c playwright.record.config.ts --project=keys"`.
- `frontend/e2e/app.spec.ts` — “without key the full page still renders all panels” (all 8 headings visible, no `key-active`, no caption).
- `.gitignore` — `frontend/recordings-keys/`.

**Clips** (`frontend/recordings-keys/*/video.webm`)

`k-plan`, `k-trip`, `k-location`, `k-at-risk`, `k-help`, `k-ack`, `k-restored`, `k-warming`, `k-not-yet`, `k-verified`, `k-arrival`, `k-report`, `k-home` — e.g. `recordings-keys/keys.record.ts-k-plan-keys/video.webm`, … `recordings-keys/keys.record.ts-k-home-keys/video.webm` (13 files).

**REAL output**

```
  ok  1 [keys] › recording\keys.record.ts:54:1 › k-plan (7.9s)
  ok  2 [keys] › recording\keys.record.ts:67:1 › k-trip (7.7s)
  ok  3 [keys] › recording\keys.record.ts:79:1 › k-location (8.0s)
  ok  4 [keys] › recording\keys.record.ts:91:1 › k-at-risk (7.8s)
  ok  5 [keys] › recording\keys.record.ts:101:1 › k-help (7.7s)
  ok  6 [keys] › recording\keys.record.ts:116:1 › k-ack (8.2s)
  ok  7 [keys] › recording\keys.record.ts:127:1 › k-restored (7.8s)
  ok  8 [keys] › recording\keys.record.ts:131:1 › k-warming (7.7s)
  ok  9 [keys] › recording\keys.record.ts:135:1 › k-not-yet (7.8s)
  ok 10 [keys] › recording\keys.record.ts:139:1 › k-verified (7.7s)
  ok 11 [keys] › recording\keys.record.ts:143:1 › k-arrival (7.8s)
  ok 12 [keys] › recording\keys.record.ts:147:1 › k-report (7.6s)
  ok 13 [keys] › recording\keys.record.ts:158:1 › k-home (7.6s)
  13 passed (1.8m)
```

```
  ok  7 [utc] › e2e\app.spec.ts:374:1 › without key the full page still renders all panels (525ms)
  ok 18 [los-angeles] › e2e\app.spec.ts:374:1 › without key the full page still renders all panels (415ms)
  22 passed (30.6s)
```

Note: `k-location` replays 14:06 then 16:31 (as in `insets.record.ts` i2), because the “Location unavailable” event is only available at 14:10; its caption reads “Replay time: 2:06 PM ET” per the specified 14:06 time.
