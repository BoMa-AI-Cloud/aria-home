# Public demo and model-coverage plan (work list)

Received 2026-10-29 from Brad. Three goals: broad, meaningful Meta-model use; evidence-grounded verification and
truthful follow-through; one-click browser access for judges (no install, account, API key or terminal). This file
is the work list and is updated as each step lands. Nothing here is deployed; the hosted link stays
"Pending deployment" until a deployment is approved and tested in a clean browser.

## Baseline (2026-10-29)

- Branch main, HEAD 077e849faa8be3092e754a3265b80762ec57290a; working tree holds the uncommitted Audit 4 group A
  repairs and the group B work in progress (see [audit-4.md](audit-4.md)).
- Public-demo mode: none exists.
- Model integrations as connected today:
  - muse-spark-1.3: runtime explanation through the Meta Model API (POST /v1/messages), mock by default.
  - sam-3.1: recorded replay of four segmentations; the live adapter is not wired into the app (Audit 4 finding 7
    makes this explicit as replay-only). The six `care_home_v1` night/morning frames and their recorded responses
    (`backend/fixtures/visual/care/`) landed later the same day, replay-only the same way.
  - muse-image-1.0: generated the synthetic fixture images only (four trip-home frames, then six care frames); not a runtime integration.
  - muse-wonder-1.0: wrote application code; allowed in the provider but not used for any runtime role.
  - muse-voice-transcribe-1.0: available on the key; not integrated.
- Audit 4: findings 1-4 repaired and verified (backend 418 passed); 5-9 in progress; 10 queued.

## Steps

| # | Step | Status |
|---|---|---|
| 1 | Finish Audit 4 findings 1-10 with regressions | done 2026-10-29 (uncommitted): all ten repaired and operator-verified, see audit-4.md |
| 2 | Public-demo mode: restricted backend serving the existing React app and Python logic; per-visitor isolated state; server-side scenario/time allowlists; no live, delivery, sensor or paid paths reachable; fail closed; disclosure; reset | done 2026-10-29: `ARIA_HOME_PUBLIC_DEMO=1`, one process serves `frontend/dist` plus the restricted API, 15 backend tests in `backend/tests/test_public_demo.py` |
| 3 | Guided "Start the warm-by story" path over the real care scenario, plus "Explore evidence" views (sources, freshness, conflicts, reasoning, fields sent and refused, model contributions with provenance) | done 2026-10-29: public-mode landing (purpose, Brad hook, disclosure, start/explore/reset), 10-step story over the live `/api/scenarios` checkpoints of `care_home_v1` (19:03, 19:15, 19:20, 02:31, 02:45, 04:21, 04:51, 06:21, 06:45, 07:01) with observed/first-known times from the evidence timeline and API-rendered HVAC fields, "Explore evidence" drawer (sources, deterministic readiness/verification reasons, recorded-or-fallback interpretation, per-audience fields, model-role matrix) |
| 4 | Recorded model responses matched by scenario, evidence revision, model and contract version; clearly labelled fallback when none matches | done 2026-10-29: exact-match lookup in `backend/aria_home/recorded.py` (scenario, replay time, input revision, model id, prompt/policy versions, serve-time re-validation) with provenance per answer, else the deterministic summary labeled "No recorded model response for this snapshot" |
| 5 | muse-wonder-1.0 structured second review of recorded explanations (needs an approved paid batch to record) | approved 2026-10-29 (16 muse-wonder-1.0 calls); code built offline in task day11-06 (`backend/aria_home/review.py`, review-v1 contract, display beside the matching recorded answer, never changing readiness/verification/outcomes), calls run after it |
| 6 | muse-voice-transcribe-1.0: transcribe a synthetic technician voice note into a human-report record (needs a synthetic audio fixture and an approved paid call) | approved 2026-10-29 (1 call); synthetic fixture made; code built offline in task day11-06 (`backend/aria_home/transcribe.py`, human_report attached at completion-report time as corroboration only, never a measurement source), call runs after it |
| 7 | Public-demo acceptance tests (fresh session, isolation, rewind, stale responses, zero external calls, 4xx on bad input, both timezones, phone/laptop sizes, keyboard basics) | done 2026-10-29: `frontend/e2e/public-demo.spec.ts` on `playwright.public-demo.config.ts` (backend `ARIA_HOME_PUBLIC_DEMO=1`, temp sessions/recorded dirs, UTC + America/Los_Angeles, 1366x768 + 390x844): landing, full story, recorded-vs-computed labels, A/B isolation with isolated reset, rewind, rapid-step settling, identical visual bytes at UTC/+05:30/-08:00, no graph.facebook.com/api.meta.ai/Emporia calls, ET rendering, keyboard flow |
| 8 | Documentation: README top order, architecture distinguishing generation / recorded / deterministic / replay / optional live, model-role matrix | planned |
| 9 | Hosting evaluation and an approval handoff (provider, costs and limits with uncertainty, account actions, exposure, verification and rollback) | planned |
| 10 | After separately approved deployment: test the public URL in a clean browser, record final app footage, rebuild the 3-minute video | blocked on approval |
| 11 | "ARIA's Laws" view: registry of 8 active model laws plus 7 process laws, recorded watcher observations with provenance and code detections, correction ledger; recorded-only in public demo, live watcher call operator-only and unreachable from routes | done 2026-10-29 (uncommitted): `backend/laws/laws.json` + `backend/aria_home/laws.py` (violations reject and name the law), `backend/aria_home/watcher.py` (one-revision correction loop, empty never lowers risk), `GET /api/laws` + `GET /api/watcher` (recorded-only) + `GET /api/corrections`, Laws view in `frontend/src/App.tsx` with `frontend/e2e/laws.spec.ts` |
| 12 | "ARIA's view" decision map: animated SVG/CSS-only map drawn only from `GET /api/trace` (ordered steps built from the same decision functions, as-of only, zero model calls, checkpoint-scoped in public demo); sources left as colour nodes, streaks source to checks to decision to notices, violet only for the model watcher; tab in app plus "See ARIA's view of this step" in the guided story | done 2026-10-29 (uncommitted): `backend/aria_home/trace.py` (trace-v1, 9 tests in `backend/tests/test_trace.py`), TraceView in `frontend/src/App.tsx` with `frontend/e2e/trace.spec.ts`, `v1-arias-view` clip in `frontend/recording/trace.record.ts` |

Not in scope: a public "run live investigation" button, Ecobee, other hackathons, a 90-second video, invented
personal history, competitor claims, or absolute safety claims.

## Brad's items (not automatable)

| Item | Status |
|---|---|
| Watch and listen to the A6 video end to end | open |
| Confirm the official deadline (earlier organizer material: 9 PM ET, Nov 4; internal target 5 PM ET) | open |
| Approve or change the proposed freeze (end of day Nov 2) and recording (Nov 3) schedule | approved 2026-10-29 |
| Approve pushing the uncommitted Audit 4 and public-demo work | approved 2026-10-29; runs after the queued jobs finish |
| Approve a hosting provider and the deployment step | open (handoff not yet written) |
| Upload the video, fill in the submission form, optional X post | open |
| Ecobee read-only | parked: no developer access; HomeKit not visible on the network |
