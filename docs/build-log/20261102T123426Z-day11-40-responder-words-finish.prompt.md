ARIA Home: finish the story-wording job. Your previous run (day11-39) ended early when it wrote a sentence with no tool call. Its edits are in the working tree: do not redo them. DO THE WORK NOW in this turn. IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; every message must carry a tool call until your final report. No live calls, no paid calls, no installs, no git, no network beyond 127.0.0.1. Do not weaken any test without replacing what it proved. Never edit backend/eval/ or backend/scenarios/. Do not edit docs other than what the runner writes itself. Shell starts in C:\aria-home. Use the Bash tool for every command, one per call, no pipes: `cd backend && python -m pytest -q`, `cd frontend && npm run typecheck`, `cd frontend && npm run build`, `cd frontend && npm run test:e2e`, `cd frontend && npm run test:e2e:public-demo`, `cd frontend && npm run test:e2e:alt-ports`. You cannot run other Python scripts in this session.

Background: the care_home_v1 story is a family caregiver and a resident's home with a warm-by time. It has no property manager and no trip. Prompt is now inv-v5. The evidence pack carries `responder`. `_responder_wording_reasons` in backend/aria_home/investigator.py rejects "manager" and "planned arrival" in care_home_v1 prose.

Measured so far: 76 targeted tests passed. The full backend suite has not been run on these edits, and no frontend suite has.

Do these in order:
1. Frontend wording. Search frontend/src for viewer-facing text that says arrival, trip or manager and can appear in the care_home_v1 story. Fix what a care story viewer can see, using warm-by time and family caregiver. Leave internal identifiers and demo_recovery_v1's own labels alone. If nothing needs fixing, say so.
2. Check `CAREGIVER_SCENARIOS` against how eval variants of the care story are identified. If a care variant would get "property manager" as its responder, say so in your report. Do not change the stored variants.
3. Red-proof the gate: make `_responder_wording_reasons` return [] right at its start, run `cd backend && python -m pytest tests/test_investigator.py -q`, and read that test_care_gate_rejects_manager_wording and test_care_gate_rejects_planned_arrival_wording fail on an assertion. Remove that line with an edit, then rerun the same command.
4. Run all six commands. A failing test: read it and fix the cause. If its expected text is the old arrival wording for a viewer sentence you changed, update that text and nothing else about it.

If a test fails only because a generated doc such as docs/evaluation.md needs regenerating, do not edit the doc and do not touch the test. Name it and the operator will regenerate it.

Done means: all six commands pass, and your final message lists every file changed across both runs, the red-proof output, the exact pass counts, whether input_revision changed for care_home_v1 (the value recorded before these edits at 23:30 was 0ef9716f9d4b551836f41980579d5d804d6d77caa0767857bb78d25837641d00; say "not measured" if you cannot measure it), and anything that could still read wrong to a judge.

