Model: muse-wonder-1.0
Turns: 63

G2 done. All three gates pass.

**Files**
- `backend/aria_home/verification.py` — `build_evidence_timeline()` (alias `evidence_timeline`), built only from the as-of projection (`received_at <= now`, events `available_at <= now`); reuses `_goal_analysis`, gap detection, `min_samples`/`min_rise_f`; sorted by `first_known_at`, so goal verified (20:20:20) lands strictly before the report (20:45)
- `backend/aria_home/app.py` — follow-up response gains `evidence_timeline`
- `backend/tests/test_evidence_timeline.py` — new: ordering/strictly-before, absence before each milestone time, no-future-entries invariant, API shape
- `frontend/src/api.ts` — `EvidenceTimelineEntry`/`EvidenceTimelineKind`, `evidence_timeline?` on `FollowUpResponse`
- `frontend/src/App.tsx` — "Evidence timeline" panel directly under Outcome (ET times, supporting ids, report row marked "Corroboration only"); inset target `evidence-timeline`
- `frontend/src/index.css` — timeline styles
- `frontend/e2e/app.spec.ts` — at 20:21: 4 rows, no report row; at 21:01: all 6 rows in order, report row shows "Corroboration only" and "8:45 PM ET"
- `frontend/recording/insets.record.ts` — `i10-timeline` close-up at 21:01

**Real outputs**
- `cd backend && python -m pytest tests/test_evidence_timeline.py -q` → `4 passed in 1.24s`
- `cd backend && python -m pytest -q` → `277 passed in 19.53s`
- `cd frontend && npm run typecheck` → `tsc --noEmit`, no errors
- `cd frontend && npm run test:e2e` → `20 passed (24.4s)`
