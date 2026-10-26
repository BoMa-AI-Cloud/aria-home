ARIA Home, small fix to D2-1 (approved by Brad). Work only inside C:\aria-home. No installs,
no network, no git. Read only backend/aria_home/metrics.py and backend/tests/test_metrics.py.

PROBLEM: coverage is computed as the span from first to last sample over the window. For the demo
furnace circuit (3 samples, expected cadence 1800 s, a 7200 s gap) it reports 0.97, which
overstates the evidence.

FIX in both temperature_trend and circuit_activity:
- Coverage = (sum of the parts of the window that are covered) / window length, where each
  sample covers from its observed_at up to the next sample's observed_at ONLY if that gap is at
  most 2 x expected_cadence_s; a larger gap contributes nothing beyond one cadence after the
  sample. The last sample covers at most one cadence (clipped to the window end). With no
  cadence on the records, fall back to treating each sample as covering zero time and say so in
  a `coverage_basis` field ("cadence" or "no_cadence").
- Add `gaps_over_cadence` (count of gaps larger than 2 x cadence).
- Keep `sufficient` False when coverage < 0.5.
TESTS: the demo furnace circuit coverage is now below 0.6 and gaps_over_cadence == 1; a regular
series has coverage near 1.0; a single sample covers one cadence; no-cadence records report
coverage_basis "no_cadence". Existing tests must still pass (update expectations only where the
old coverage value was asserted, and say which).

Run from C:\aria-home\backend: python -m pytest -q. Final answer: changes and REAL output.

