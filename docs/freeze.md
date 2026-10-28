# ARIA Home feature freeze

Initial freeze: 2026-10-26 at commit 4d3bacb. Brad lifted the self-imposed
feature freeze on 2026-10-28 for the Audit 3 repair and the integrations that
follow. A final freeze date will be set later.

Frozen from 2026-10-26 (local). The demo is what commit 4d3bacb does; the
remaining work is testing it, filming it, and writing it up.

## Allowed after the freeze

- Bug fixes for anything the user tests ([usability kit](usability.md)) or
  the video walk-throughs uncover.
- Accessibility and wording fixes found in user tests (labels, readability,
  human-language rendering of reasons, payloads and events).
- Docs, the demo video, setup instructions, and the submission itself.

## Not allowed after the freeze

- New features, new evidence sources, new providers or models, and new
  integrations (real email, SMS, location, travel, or equipment control).

## In scope as of commit 4d3bacb (Day 7 D7-2)

- Evidence foundation with as-of visibility: records, trip revisions and
  confirmations are visible only at or after their received/available times.
- Deterministic metrics, readiness (including `arrival_passed` decided at
  arrival from readings received by arrival), power context, follow-up
  scheduling, outcome rules, and recovery verification stages
  (`telemetry_missing` to `arrival_met`), all computed in code.
- Evidence-pack investigation engine (inv-v2 claim binding, code-rendered
  verified facts) with mock and gated live Meta providers; the model cannot
  change the readiness status.
- SQLite store with outcome and verification history surviving restarts.
- Scoped simulated notifications with per-audience allowlists, recorded
  refusals, idempotent outbox, and simulated acknowledgement that never
  changes readiness, outcome, or verification.
- Frontend: synthetic-data banner, Investigation section, Outcome section in
  verification-stage wording, notifications panel, homeowner arrival update,
  simulated timeline, evidence source cards, scenario selector with the
  `demo_video_v1` replay times through arrival, and human-readable labels
  with exact payload fields still checkable via "fields sent".
- Evaluation: 12 builder-labeled cases across combined vs single-source
  conditions with offline results, plus the 24 operator-run live calls
  documented in `docs/evaluation.md`.

## Known limits (from the day handoffs)

- All data is synthetic and every message, scene, visit and report is
  simulated; there are no real channels and ARIA Home controls no equipment.
- Room-sensor and blower mappings are synthetic assumptions, not measured
  physical behaviour.
- The notification allowlists are reviewed by hand, not by an external
  privacy review; the HVAC request is gated only by a synthetic manager
  authorization event.
- The Day 6 live agreement rate shows the models followed the readiness
  contract, not independent readiness judgment; the sample is small (one run
  per case) and input-token counts are unreliable.
- The committed live results used the pre-Day-7 readiness labels; Day 7
  added `arrival_passed` with target-at-arrival, which the live run did not
  exercise.
- Claims stay bounded to the monitored temperature goal: verified recovery
  of that goal, never a proven repair cause or fault-free equipment.
