ARIA Home: public-demo guided story and evidence views (approved by Brad, 2026-10-29). DO THE WORK NOW in this turn.
IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; keep
editing and running commands until the done-condition holds. No live calls, no installs, no network beyond
127.0.0.1, no git, NO helper scripts outside tests. Do not weaken any test. Public-demo backend mode
(ARIA_HOME_PUBLIC_DEMO=1) is in the working tree; keep it. Shell starts in C:\aria-home; prefix frontend commands with
`cd frontend && `. Do not end your turn until `cd backend && python -m pytest -q`, `cd frontend && npm run typecheck`,
`cd frontend && npm run build`, `cd frontend && npm run test:e2e` and the new public-demo browser tests pass.

1. Landing view (public mode only): title, one-line purpose, Brad's README hook, and this disclosure adjusted to the
   actual behaviour: "Interactive demo · Synthetic home data · Simulated notifications · Recorded model responses
   where indicated · No equipment control." A primary button "Start the homecoming story" and a secondary
   "Explore the app freely". A visible "Reset my session" control at all times.
2. Guided story: a step panel over the real app driving the existing replay through demo_video_v1's actual fixture
   checkpoints (read the times and labels from the fixture/API, do not hard-code old ones): missing thermostat
   telemetry and uncertain readiness; scoped homeowner/property-manager notices; the fields actually sent in the
   simulated HVAC notice (rendered from the API payload, not a hard-coded summary) and the refusals; manager
   acknowledgement without resolution (the visitor clicks Acknowledge; the outcome must not change); thermostat
   reporting restored without temperature recovery; independent warming; a covered, held temperature goal; the
   completion report as corroboration; the arrival expectation. Each step states what was observed and when it
   became known (observed_at vs first_known_at). Back/rewind never shows later state.
3. "Explore evidence" drawer: sources with timestamps, freshness, conflicts and provenance; the deterministic
   readiness and verification reasons; the model interpretation and its limits with provenance (or the labelled
   no-recording fallback); audience-specific fields sent and refused; a "Model contributions" panel listing each
   Meta model's actual role and status (muse-spark-1.3 runtime explanation, recorded here; sam-3.1 recorded
   segmentation of synthetic images including the missed frost; muse-image-1.0 generated the synthetic images only;
   muse-wonder-1.0 and muse-spark-1.3 wrote the code). Only reviewed synthetic, non-secret fields; no raw audit JSON.
4. Usable at 1366x768 and 390x844; keyboard reachable buttons with visible focus; status text not colour-only.
5. Browser tests (new playwright project or spec running the backend with ARIA_HOME_PUBLIC_DEMO=1 and a temp dir):
   fresh session without credentials; guided story completes; recorded vs computed labels correct; two browser
   contexts A and B isolated, reset isolated; rewind leaks nothing; rapid step changes show no stale response; visual
   image loads at UTC and +/- offsets; a request spy shows no calls to graph.facebook.com, api.meta.ai or Emporia;
   both configured timezones; phone and laptop viewport smoke.
6. Update docs/public-demo-plan.md steps 3 and 7, README "What judges can test", and docs/recording-checklist.md.
Final answer: files changed, tests added, and the REAL output lines of every command.

