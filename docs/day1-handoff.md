# Day 1 handoff

## What works

- Backend health endpoint (`GET /api/health`), from Task 1 backend health (commit 79d2730). Checked by pytest.
- Evidence foundation: contracts, scenario clock, freshness, synthetic demo scenario, `GET /api/sources` (commit 20f67ec). Checked by pytest.
- Provider adapter: MockProvider and gated MetaProvider, `/api/provider` (commit 3e2a6fa). Checked by pytest.
- Provider reply reporting: reply block types, stop reason and usage, new no_text error (commit 817fb25). Checked by pytest and the two live smoke calls below.
- Frontend: Vite React TypeScript shell with four synthetic source cards (commit 0ba5213). Built after the operator ran npm install with Brad's approval; reviewed by the operator.
- Loose ends (commit 09b1dbd): missing-reading counts on source cards, key only from MODEL_API_KEY, app smoke test. Checked by pytest.

## What was tested

- `python -m pytest -q` from `backend/`: 54 passed in 1.41s.
- Live smoke test 001 at 16:52Z through the app's adapter, approved by Brad: max_tokens 16, model muse-spark-1.3 answered but returned no text (the limit was spent on hidden reasoning).
- Live smoke test 002 at 16:54Z through the app's adapter, approved by Brad: max_tokens 256, ok, text "ready", 2.4 s, 15 input / 152 output tokens, blocks [redacted_thinking, text], stop_reason end_turn.
- The operator reviewed each change against the evidence rules and ran the tests and `npm run build` (both pass).
- The operator ran the backend and frontend together in a browser once: the SYNTHETIC banner, the central question and four source cards rendered with no console errors.

## Checks actually performed

- `pytest`: 54 passed at 37321b9.
- `npm run build` and `npm run typecheck`: passed.
- One manual browser check of the four cards, with no console errors.
- The live-call results below are historical operator runs from 2026-10-26 (approved by Brad) and were not repeated.

## What is mock vs live

- Mock: MockProvider, synthetic demo scenario data (thermostat, electrical, weather, calendar), four synthetic source cards in the frontend.
- Live: gated MetaProvider reading its key only from MODEL_API_KEY; the two live smoke calls above went through the app's adapter to model muse-spark-1.3.

## Known gaps

- No automated browser test yet (closed on Day 2: see docs/day2-handoff.md) (the browser check above was manual; `backend/tests/test_smoke_app.py` covers the API contract the page uses).
- The Investigation section is a placeholder until Day 3.
- Open organizer questions, to be asked in Discord office hours: whether a hosted URL is expected for the live product; whether a clearly labeled simulated data feed is acceptable live; whether a submission can be edited before the deadline.

## Next

- Day 2: richer metrics and the Property Power Context check.
- Day 3: the Meta investigation and first full browser journey.
