Model: muse-wonder-1.0
Turns: 66

Files changed:
- `backend/aria_home/app.py` — `GET /api/context?scenario=&at=` using `context_as_of`; before/outdated returns `{confirmed:false, reason, reason_in_words, flags/context_flags/readiness_flags, confirmed_at:null, revision_id:null, current_trip_revision_id}` with scenario/at/timezone echo; after returns property label, planned arrival, landing, labelled 45 min airport-exit/baggage + 30 min driving allowances from calendar `arrival_plan`, scenario-estimates note, target temp, `notify_homeowner`/`homeowner_notification_preference`, `manager_authorized`/`manager_coordination_permission`, `confirmed_at`, revision id, trip + confirmation.
- `backend/aria_home/scenario.py` — loads and retains calendar `arrival_plan` on `Scenario`.
- `backend/tests/test_context_api.py` — before 09:19, at/after 09:20, revised-trip `confirmation_outdated` at 18:00 vs confirmed 16:30, 404/naive-at echo.
- `frontend/src/api.ts` — `ContextResponse`/`ArrivalPlan`/`fetchContext`.
- `frontend/src/App.tsx` — read-only “Confirmed plan and permissions” panel after the header, ET via existing formatter, “Not yet confirmed” / outdated states, race-guarded fetch keyed to scenario + selected replay time, `?inset=plan` target.
- `frontend/src/index.css` — panel styling.
- `frontend/e2e/app.spec.ts` — 09:20 video-scenario panel test; panel added to full-page headings check.
- `frontend/recording/insets.record.ts` — `i0-plan` close-up at 09:20.

REAL outputs:
- `cd backend && python -m pytest -q` → `273 passed in 20.74s` (new file alone: `4 passed in 1.42s`)
- `cd frontend && npm run typecheck` → `tsc --noEmit`, no errors
- `cd frontend && npm run test:e2e` → `20 passed (35.2s)`

The single `i0-plan` recorder run was blocked by a tool-approval error, so no recording was generated or claimed; the recorder code mirrors the passing e2e assertions.
