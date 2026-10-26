ARIA Home, Day 3, Task D3-2 (approved by Brad): fill the Investigation section in the browser.
No new backend features. Work only inside C:\aria-home. No installs, no network, no git. Your
shell starts in C:\aria-home: prefix frontend commands with `cd frontend && `.

Read: backend/aria_home/investigator.py (the /api/investigation response shape), frontend/src/
App.tsx, api.ts, index.css, frontend/e2e/app.spec.ts.

The product's main feature is this investigation, not the evidence cards (organizers list
"dashboards as the main feature" as an anti-project). Build it so the page opens on the answer.

BUILD
1. frontend/src/api.ts: typed fetch for GET /api/investigation (status, output, reasons,
   model_id, prompt_version, provider_mode, summary).
2. frontend/src/App.tsx, replace the "Coming in Day 3" placeholder with:
   - A readiness line in words: on_track -> "On track", at_risk -> "At risk",
     cannot_tell -> "Cannot tell yet", plus the target and the latest indoor temperature from the
     deterministic summary (target_gap), e.g. "Indoor 52.1 F, target 68 F".
   - "What ARIA observed": each observation with its cited evidence ids shown as small chips.
   - "Possible explanations": each hypothesis with supporting and conflicting ids, labeled as
     hypotheses (not findings).
   - "What we don't know", "One question for you" (the clarification) and "Next check" (follow_up
     observation and time).
   - The Power Context statement and its limitations, always visible, in a compact block.
   - A provenance line: provider mode, model id, prompt version. When provider_mode is "mock",
     show a prominent label "MOCK - example answer, not live inference".
   - When status is "rejected" or "unavailable": show "ARIA's explanation is unavailable" with the
     reasons, then the deterministic summary only. Never show model text in that case.
   - Loading and error states. Text labels with colour, never colour alone.
3. Keep the four evidence cards below the Investigation section, unchanged.
4. frontend/e2e/app.spec.ts: add assertions (keep the existing ones): the Investigation section
   shows a readiness line, at least one observation with an evidence chip, the clarification, the
   Power Context statement, and the "MOCK - example answer, not live inference" label.

RUN: `cd frontend && npm run typecheck`, `cd frontend && npm run build`,
`cd frontend && npm run test:e2e` until green. Final answer: changes and REAL outputs.

