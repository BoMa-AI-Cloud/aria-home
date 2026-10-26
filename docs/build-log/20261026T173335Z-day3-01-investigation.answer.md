Model: muse-wonder-1.0
Turns: 31

Design: Deterministic code builds a time-filtered evidence pack (trip, confirmation, source statuses, metrics, Power Context, stable evidence ids) and owns all numbers/statuses. A versioned `inv-v1` prompt constrains the Meta model to cite only those ids, separate observations from hypotheses, state unknowns, and avoid diagnosis, control steps, probabilities, and banned phrases. `validate()` enforces citations, pack-only numbers (one-decimal rounding), banned phrases, and readiness consistency, falling back to the deterministic summary on rejection or provider error, with mock output explicitly labeled `[MOCK]`.

Files changed: `backend/aria_home/investigator.py` (new), `backend/aria_home/provider.py` (mock investigation JSON), `backend/aria_home/app.py` (`GET /api/investigation`), `backend/tests/test_investigator.py` (new).

Tests: `98 passed in 1.22s`

