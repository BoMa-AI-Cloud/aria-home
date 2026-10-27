Model: muse-wonder-1.0
Turns: 29

## Checklist

1. **Headings / landmarks — fixed.** One `<h1>` (`frontend/src/App.tsx:1097`), then `<h2>` sections and nested `<h3>` — already logical. Demo controls were a `role="group"` `<div>` inside `<main>`; now a labelled region outside it: `<section className="demo-controls" aria-label="Demo controls">` (`App.tsx:1058`) wraps nothing of the product, with `<main>` (`App.tsx:1089`) as sibling under the `.page` div.
2. **Accessible names — fixed.** Scenario `<select>` keeps `aria-label="Scenario"` + visible label; “Acknowledge (simulated)” already had text. Replay buttons now have `aria-label={`Replay to ${time.label}`}` (`App.tsx:1082`) while visible text stays e.g. `21:01`. Existing name-substring assertions (`{ name: "19:00" }` etc.) still pass.
3. **Live announcements — fixed.** `aria-live="polite"` on both outcome headlines (`.outcome-status`, verification and plain branches) and on the notification list (`.notification-cards`, including the persistent empty-state wrapper so the region exists before cards arrive).
4. **Colour not the only signal — already fine.** Verified by reading: progression items say “— Reached / Not reached”, refused cards say “Refused: …”, sources say “Status: Available/Missing/…”, readiness/outcome say “Status: …”. No change needed.
5. **Contrast — fixed (one failing pair, see table).** Card/chip/tag border `#b9b3a6` failed; replaced with `#7d7767` throughout `frontend/src/index.css`. All other text/UI pairs passed.
6. **Keyboard focus / tab order — fixed.** Added global `:focus-visible { outline: 3px solid #0057b8; outline-offset: 2px; }` (`index.css`). Tab order is DOM order: Scenario → replay buttons → Acknowledge.
7. **`lang` / `<title>` — already fine.** `frontend/index.html:2,6`: `<html lang="en">`, `<title>ARIA Home — Evidence</title>` unchanged.

## Contrast table (WCAG ratio, computed from the CSS pairs actually used)

| Foreground | Background | Ratio | Requirement | Result |
|---|---|---|---|---|
| `#1a1a1a` body | `#f7f5f0` page | 16.0:1 | 4.5 | pass |
| `#1a1a1a` | `#ffffff` cards | 17.4:1 | 4.5 | pass |
| `#1a1a1a` | `#e8e2d4` chip/tag | 13.5:1 | 4.5 | pass |
| `#1a1a1a` | `#efe9f7` demo panel | 14.6:1 | 4.5 | pass |
| `#3d3d3d` secondary | `#ffffff` | 10.8:1 | 4.5 | pass |
| `#3d3d3d` | `#f7f5f0` / `#fff8e6` | 10.0 / 10.1:1 | 4.5 | pass |
| `#ffffff` banner | `#7a4d00` | 7.3:1 | 4.5 | pass |
| `#ffffff` mock label | `#5c1a1a` | 13.0:1 | 4.5 | pass |
| `#ffffff` pressed replay | `#6a3fb5` | 7.0:1 | 4.5 | pass |
| `#b3261e` error / invalid | `#ffffff` | 6.6:1 | 4.5 | pass |
| `#9a6a00` stale / warming (text) | `#ffffff` | 4.7:1 | 4.5 | pass |
| `#1e7b34` available / target | `#ffffff` | 5.3:1 | 4.5 | pass |
| `#5f5f00` awaiting (text) | `#ffffff` | 6.7:1 | 4.5 | pass |
| `#6a3fb5` unable/conflicting | `#ffffff` | 7.0:1 | 4.5 | pass |
| `#6b6b6b` missing | `#ffffff` | 5.4:1 | 4.5 | pass |
| `#345f7a` readiness border | `#ffffff` | 6.9:1 | 3.0 | pass |
| `#6a3fb5` button/demo border | `#ffffff` / `#efe9f7` / `#f7f5f0` | 7.0 / 5.9 / 6.5:1 | 3.0 | pass |
| `#b9b3a6` card/chip border (old) | `#ffffff` / `#f7f5f0` | 2.1 / 1.9:1 | 3.0 | **failed → fixed** |
| `#7d7767` border (new) | `#ffffff` / `#f7f5f0` / `#e8e2d4` | 4.5 / 4.1 / 3.5:1 | 3.0 | pass |
| `#0057b8` focus outline (new) | `#ffffff` / `#f7f5f0` / `#efe9f7` | 6.9 / 6.3 / 5.8:1 | 3.0 | pass |

Disabled replay buttons (`opacity: 0.5`) are inactive controls, exempt from contrast requirements; all status colours are also ≥3:1 as graphical borders/dots. Outcome headline is 1.1rem bold — treated as body text (4.5:1), and every status colour passes that stricter bar.

## E2E

Added `keyboard replay to 21:01 shows arrival expectation met` (`frontend/e2e/app.spec.ts:308`): Tab → Scenario select focused, 3× ArrowDown → `demo_video_v1`, wait for `Replay to 21:01` enabled, 10× Tab → that button focused, Enter → “Arrival expectation met”. All existing assertions kept.

## Real output

```
> aria-home-frontend@0.1.0 typecheck
> tsc --noEmit
```
(no errors)
```
✓ built in 1.00s
```
```
  ok 5 [chrome] › e2e\app.spec.ts:308:1 › keyboard replay to 21:01 shows arrival expectation met (811ms)
  5 passed (12.6s)
```
```
  ok 8 [chrome] › recording\demo.record.ts:177:1 › s5-report-and-arrival (21.0s)
  8 passed (2.3m)
```

All four commands pass: `npm run typecheck`, `npm run build`, `npm run test:e2e`, `npm run record:demo` (run from `frontend/`; first invoked as `cd frontend && npm run typecheck` per instructions). Changed files: `frontend/src/App.tsx`, `frontend/src/index.css`, `frontend/e2e/app.spec.ts`.
