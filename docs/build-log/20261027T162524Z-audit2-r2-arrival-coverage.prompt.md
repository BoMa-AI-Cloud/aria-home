ARIA Home, audit repair R2 (approved by Brad): P1 arrival coverage. DO THE WORK NOW in this turn.
No helper scripts, no live calls, no installs, no network, no git. Do not end your turn until
`cd backend && python -m pytest -q` passes. Do not touch anything outside C:\aria-home.

Read: backend/aria_home/verification.py, evidence.py, readiness.py, docs/readiness-rules.md,
backend/tests/test_verification.py, backend/scenarios/demo_video_v1/*.

FIRST a failing regression test reproducing the audit: copy demo_video_v1 to tmp_path, remove
room_sensor readings observed after 20:20 through 21:00, keep fresh readings after 21:00, evaluate
at 21:06. Today it returns arrival_met using the 20:20 reading for a 21:00 arrival.

REQUIRED: arrival_met needs coverage through the arrival boundary: from the verification point to
the confirmed arrival, no gap between consecutive eligible readings (including the start and the
final gap from the last reading at or before arrival to the arrival instant) longer than
MAX_GAP_CADENCE_MULTIPLIER x cadence (document the policy and constants). Readings observed after
arrival never cover the pre-arrival interval. Use observed_at for coverage and received_at <= now for
visibility: a delayed reading observed at 20:59 supports arrival only once received, and never in an
earlier replay. Missing coverage gives unable_to_verify (or another explicit non-success state with a
reason), never arrival_met. Document in docs/readiness-rules.md.
TESTS: the reproduction; exact boundary (reading exactly at 21:00; final gap exactly at the limit vs
one second over); an internal excessive gap; delayed delivery (visible only after receipt); mixed
timezone offsets for the same instants. Existing tests pass. Final answer: the policy and REAL output.

