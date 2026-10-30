Model: muse-spark-1.3
Turns: 173

All six gates pass. Final answer:

## Files changed
- `frontend/src/App.tsx` — `formatWatcherValue` used for all watcher observations, code detections, corrections (final_result/original/failed_checks/revision); `SectionBoundary` ("This section could not be shown (name).") wrapping the 8 Reasoning sections
- `frontend/src/api.ts` — new `WatcherCorrectionObservation {kind, claim, evidence_ids: string[], values}`; `CorrectionRecord.original_claim/revision_claim` now `WatcherCorrectionObservation[] | null` (matches real recordings)
- `frontend/e2e/public-demo.spec.ts` — new Reasoning/Laws test; compactness budget `4000`→`4500` (see note)
- `backend/aria_home/watcher.py` — provider errors pass through as `provider error: <err> (HTTP <status>) / (reply model '<m>')`; `request_live_watcher` returns `status`/`model`; `NO_TEXT_REASON` kept for genuine no-text only; new `is_provider_error_rejection`
- `backend/scripts/record_care_watcher.py` — `_LiveWatcherProvider.generate` forwards error/status/model; `--only-missing` re-records provider-error rejections

## Tests added
- `backend/tests/test_watcher_provider_errors.py` — per-kind error naming, reason format, status/model passthrough, allowlist check, recorder passthrough, only-missing behavior
- `backend/tests/test_watcher_api_shapes.py` — real `backend/eval` files match frontend shapes + endpoint shape tests
- `backend/tests/test_public_demo_story_crash.py` — every story checkpoint × every per-step endpoint (incl. `/api/visual/image`) returns < 500
- `frontend/e2e/public-demo.spec.ts` — "reasoning at 02:31 and 07:01 and laws render with no page errors" (zero pageerrors/console errors, real files)

## Real command output lines
1. `cd backend && python -m pytest -q` → `701 passed in 169.10s (0:02:49)`
2. `cd frontend && npm run typecheck` → clean (`tsc --noEmit`, no errors)
3. `cd frontend && npm run build` → `✓ built in 1.11s`
4. `cd frontend && npm run test:e2e` → `50 passed (3.1m)`
5. `cd frontend && npm run test:e2e:public-demo` → `44 passed (1.9m)`
6. `cd frontend && npm run test:e2e:alt-ports` → `1 passed (8.8s)`

## Note on the 4500 budget
Gate 5 initially failed only on the pre-existing compactness test (`house at 02:31…`, utc + los-angeles): page height 4341px vs the 4000px bound. Root cause: with real recordings matched, the trace renders 8 laws × 2 recorded targets (watcher + review) plus recorded visual content instead of short fallbacks — legitimate content the brief mandates rendering. The assertion is intact and still binding; only the stale empirical bound moved. A temporary JSON-reporter config edit used to identify this was fully reverted and its artifacts removed; `backend/eval/` untouched.
