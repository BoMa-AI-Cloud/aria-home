Model: muse-spark-1.3
Turns: 49

Done. All five gates pass.

**Files changed**
- `frontend/src/App.tsx`
  - Owner-only status routes (`/api/live-power`, `/api/whatsapp/status`, `/api/camera/status`) now fetch only when `publicMode === false`; normal mode unchanged.
  - Sources/context effects skip while in story public mode until `selectedAt` is one of the `/api/scenarios` checkpoints; when checkpoints arrive, `selectedAt` snaps to the first checkpoint, so the first fetch uses it.
  - `VisualEvidencePanel` takes `enabled` (false in story public mode until the time is a checkpoint), gating its `/api/visual` + `/api/investigation` fetches.
  - Follow-ups: `createFresh()` in `handleReplayTime` no longer fetches when the create response said `follow_up === null` (records the id in `noFollowUpIds`, sets outcome/replay state, returns null); reuse-fetch is skipped for ids in `noFollowUpIds`/with null `follow_up` and for `at` earlier than the investigation's creation (`createdAtRef`), avoiding 404/409s.
- `frontend/e2e/public-demo.spec.ts` — two tests added (existing tests kept).
- `docs/build-log/README.md` — added the missing row for the earlier `day11-15d-review-output-budget` prompt/answer pair (pre-existing `pytest` failure: the file was on disk but unlinked; no test touched).

**Tests added** (`frontend/e2e/public-demo.spec.ts`)
- `landing loads with no console errors and no failed requests` — landing alone, asserts zero `error` console messages and zero responses ≥ 400.
- `guided story runs with no console errors and no failed requests` — full ten-step story to `Warm-by expectation met`, same assertions.

**Real output lines**
- `cd backend && python -m pytest -q` → `620 passed in 100.93s (0:01:40)`
- `cd frontend && npm run typecheck` → `tsc --noEmit` clean, no errors
- `cd frontend && npm run build` → `✓ built in 1.28s` (33 modules)
- `cd frontend && npm run test:e2e` → `50 passed (2.2m)`
- `cd frontend && npm run test:e2e:public-demo` → `30 passed (1.3m)`; server log shows the first scenario-data requests now at `at=2026-01-16T19:03:00-05:00` (first checkpoint, all 200), with no 400/404 anywhere.
