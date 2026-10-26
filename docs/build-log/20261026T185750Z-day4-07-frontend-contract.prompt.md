ARIA Home, verification fix V5 (approved by Brad): the frontend follows the new backend contract.
No backend logic changes, no live calls, no installs, no network, no git, NO helper scripts.
Your shell starts in C:\aria-home: prefix frontend commands with `cd frontend && `.
Do not end your turn until typecheck, build and the browser test pass.

Read first: frontend/src/App.tsx, frontend/src/api.ts, frontend/src/index.css,
frontend/e2e/app.spec.ts, frontend/playwright.config.ts, and in backend/aria_home/app.py the JSON
returned by GET /api/metrics, POST /api/investigations and GET /api/follow-ups/<id> (the backend
now returns contract inv-v2: verified_facts, interpretation, hypotheses, the computed readiness
with reasons, follow-up schedule status incl. deadline_passed, and context flags such as
trip_cancelled / confirmation_outdated).

BUILD
1. api.ts types match those responses exactly (no `any`; remove the old `observations` type).
2. Investigation section shows, in this order and visibly separated:
   - "Verified facts (checked against the evidence)": the code-rendered verified_facts;
   - "Readiness": the computed status in words (on_track "On track", at_risk "At risk",
     cannot_tell "Cannot tell") plus its reasons; never colour alone;
   - "Interpretation (model-written, not verified)": the interpretation text;
   - "Possible explanations (not confirmed)": hypotheses as rendered by the backend ("Possible:").
   When the output was rejected, show the deterministic summary and a plain note that the model
   answer was not used.
3. Context flags (cancelled, unconfirmed, outdated confirmation, mismatch) and deadline_passed are
   shown as plain text notes. Keep the Outcome panel, demo controls and evidence cards as they are.
4. playwright.config.ts: the backend webServer is started with ARIA_HOME_MODEL_ENABLED=0
   explicitly set in its env (forced mock mode, never inherited), and the e2e test asserts the
   page reports synthetic/mock data mode.
5. e2e (keep existing assertions): the Verified facts block contains "below target"; the
   Readiness block shows "At risk" for demo_v1 at 18:00; the Interpretation heading says "not
   verified".
RUN `cd frontend && npm run typecheck`, `cd frontend && npm run build`,
`cd frontend && npm run test:e2e` until green. Final answer: changes and REAL outputs.

