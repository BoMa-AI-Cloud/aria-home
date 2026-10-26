ARIA Home, small fix (approved by Brad). Work only inside C:\aria-home. No installs, no network, no git.

In backend/scenarios/demo_v1/manifest.json the field "created" is "2026-01-10". That claims the
synthetic data was made before the hackathon, which is false: it was authored on 2026-10-26.

1. Set "created" to "2026-10-26".
2. Add a manifest field "scenario_period_note": "Scenario timestamps (January 2026) are fictional
   replay times, not when the data was created." Make sure the loader in backend/aria_home/scenario.py
   accepts it (adjust the manifest model if it forbids extra fields).
3. Add a test in backend/tests/test_scenario.py asserting the manifest "created" date is on or after
   2026-10-26.
4. Run from C:\aria-home\backend: python -m pytest -q

Final answer: what changed and the REAL test output.

