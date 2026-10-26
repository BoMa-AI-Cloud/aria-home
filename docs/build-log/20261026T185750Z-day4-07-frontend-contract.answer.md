Model: muse-wonder-1.0
Turns: 63

Changes are implemented, but verification is blocked by the session permission gate: every code-execution tool call (`npm`, `node <script>`, `python -c`, Flask) returns “requires approval,” so I cannot run typecheck/build/e2e until you approve one of those commands (or switch the session to a mode that allows them). Please approve `cd frontend && npm run typecheck` when prompted, then I’ll continue through build and e2e in the same task.

Implemented so far:
- `frontend/src/api.ts`: inv-v2 types (`verified_facts`, `interpretation`, `hypotheses`, computed `ReadinessResult` with reasons/inputs, context flags, follow-up schedule with `deadline_passed`, metrics/POST/follow-up responses); removed `observations` type; no `any`.
- `frontend/src/App.tsx`: Investigation now shows, in order, Verified facts → Readiness (words + reasons) → Interpretation (model-written, not verified) → Possible explanations (backend “Possible:” text); rejected output shows deterministic summary + “The model answer was not used.”; context-flag and `deadline_passed`/schedule notes as plain text.
- `frontend/playwright.config.ts`: backend `env: { ARIA_HOME_MODEL_ENABLED: "0" }`.
- `frontend/e2e/app.spec.ts`: kept existing assertions (updated the obsolete observations-chip one), added synthetic/mock-mode, “below target”, “At risk”, and “not verified” assertions.
- `frontend/src/index.css`: separated investigation blocks and context notes.

No backend, typecheck, build, or e2e results yet — those are the blocked steps, not passing results.
