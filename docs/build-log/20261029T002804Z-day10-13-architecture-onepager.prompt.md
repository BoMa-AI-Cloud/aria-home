ARIA Home: architecture diagram and judge one-pager (docs only, approved by Brad). DO THE WORK NOW in this turn.
IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; keep
editing until the done-condition holds. No live calls, no installs, no git, NO helper scripts. Shell starts in
C:\aria-home. Do not end your turn until `cd backend && python -m pytest -q` passes.

1. docs/architecture.svg: a hand-written, readable SVG (light background, dark text, fits 1600x900, no text
   overflowing any box) showing: synthetic evidence sources (trip/calendar, thermostat, room sensor, electrical,
   weather, visual: synthetic images segmented by sam-3.1) -> code computes readiness, follow-up, verification
   (readiness.py, outcomes.py, verification.py; policy version as in the code) -> muse-spark-1.3 explains code-checked
   facts under contract inv-v3, claim checks reject mismatches -> UI separates verified facts (code) from
   interpretation (model) -> scoped simulated notifications (allowlist, refusals recorded, ack is not resolution),
   optional WhatsApp test delivery to the owner's phone and optional Emporia read-only panel, both off by default.
   Every model id, version and number must match the code and docs/evaluation.md exactly: 17 offline cases across 9
   scenarios; live runs as recorded there, cited separately, never merged. Link it from the README.
2. docs/judge-one-pager.md (one screen): problem (Brad's hook from the README, verbatim), what it does, how Meta
   models are used (muse-spark-1.3 runtime; sam-3.1 for visual evidence, recorded replay by default; muse-image-1.0
   only to create the synthetic fixtures; all code written by muse-wonder-1.0 and muse-spark-1.3), safety rules,
   evaluation (exact, from docs/evaluation.md), how to run in 5 minutes, what to click (the README list), known
   limits. No dollar figures, no absolute claims. Link it from the README.
Final answer: files changed and the REAL pytest line.

