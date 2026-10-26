# Readiness rules

Readiness is decided by deterministic code in `backend/aria_home/readiness.py`
(`compute_readiness(pack, now, flags=None)`), not by the model. The investigator
puts the result in the evidence pack (`readiness` and `computed_readiness`),
states it in the prompt, and rejects any model answer whose `readiness` differs
from the computed status. The model only explains the computed status.

Statuses: `on_track`, `at_risk`, `cannot_tell`.

## Thresholds

All thresholds are named module-level constants in `readiness.py`:

| Constant | Value | Meaning |
|---|---|---|
| `MIN_SAMPLES` | 3 | Fewer indoor samples than this gives `cannot_tell`. |
| `MIN_COVERAGE` | 0.5 | Cadence coverage below this gives `cannot_tell`. |
| `STALE_READING_AGE_S` | 3600 s | Latest indoor reading older than this gives `cannot_tell`; a thermostat source status of `missing`, `stale`, or `invalid` also gives `cannot_tell`. |
| `SMALL_GAP_F` | 2.0 F | Only a gap at or below this can qualify for projected `on_track`. |
| `MIN_TREND_WINDOW_S` | 3600 s | Warming must be observed over at least this first-to-last sample window to project. |
| `MIN_RISE_F` | 1.0 F | First-to-last rise over the trend window must be at least this to project. |
| `MIN_RATE_PER_HOUR_F` | 0.5 F/hour | Trend rate must be at least this to project. |
| `PROJECTION_MARGIN_F` | 0.5 F | Projected temperature at arrival must reach target plus this margin. |
| `ARRIVAL_TIME_MARGIN_S` | 1800 s | The gap must be projected to close at least this long before arrival. |

Temperature gaps, rises, and rates in Celsius are converted to Fahrenheit
equivalents before comparison with the `*_F` thresholds.

## Rules

### cannot_tell

Returned when any of these holds; all applicable reasons are listed:

- No trip, no planned arrival, no confirmation/target temperature, or no
  target gap.
- Trip cancelled (from the pack or the `trip_cancelled` flag), trip or
  confirmation unconfirmed (`trip_unconfirmed` flag, or missing trip or
  confirmation), trip/confirmation mismatched (trip or property ids differ, or
  the `trip_mismatched` flag), or confirmation outdated
  (`confirmation_outdated` flag). Context rules that set these flags are added
  by another task; `compute_readiness` accepts them as the `flags` argument, a
  `readiness_flags`/`flags` entry in the pack, or keyword arguments.
- Indoor reading missing (no latest value, or thermostat availability
  `missing`), stale (availability `stale`/`invalid`, or latest reading older
  than `STALE_READING_AGE_S`), or conflicting (thermostat availability
  `conflicting`).
- Coverage below `MIN_COVERAGE`, coverage unavailable, or fewer than
  `MIN_SAMPLES` samples.

### on_track

Returned only when no `cannot_tell` condition holds and either:

- The latest fresh reading already meets or exceeds the target (gap >= 0), or
- The gap is small (at most `SMALL_GAP_F`), warming is sustained (window at
  least `MIN_TREND_WINDOW_S`, rise at least `MIN_RISE_F`, rate at least
  `MIN_RATE_PER_HOUR_F`), and linear projection at that rate both reaches
  target plus `PROJECTION_MARGIN_F` by arrival and closes the gap at least
  `ARRIVAL_TIME_MARGIN_S` before arrival.

A positive slope alone never gives `on_track`, and no projection is made from
a window shorter than `MIN_TREND_WINDOW_S` or a rise below `MIN_RISE_F`.

### at_risk

Returned otherwise. Its reasons state that it is not a guaranteed prediction,
for example: "At current readings the target may not be reached by arrival;
this is not a guaranteed prediction."

The demo scenario `demo_v1` at 18:00 is `at_risk`: gap -15.9 F with a trend of
about +0.034 F/hour fails the small-gap and sustained-warming thresholds.

## Follow-up scheduling

Follow-up scheduling is decided by deterministic code in
`backend/aria_home/scheduling.py` (`compute_follow_up_schedule`), not by the
model. The model may only describe what observation to make
(`follow_up.observation`); any time it supplies is checked and replaced.

Named constants in `scheduling.py`:

| Constant | Value | Meaning |
|---|---|---|
| `MIN_FOLLOW_UP_DELAY` (`MIN_FOLLOW_UP_DELAY_S`) | 15 min (900 s) | Next check is at least this long after the evaluation time. |
| `MAX_FOLLOW_UP_DELAY` (`MAX_FOLLOW_UP_DELAY_S`) | 24 h (86400 s) | Next check is at most this long after the evaluation time. |
| `DEFAULT_FOLLOW_UP_CADENCE` (`DEFAULT_FOLLOW_UP_CADENCE_S`) | 30 min (1800 s) | Cadence used when the scenario gives no sensor cadence. |
| `DEADLINE_GRACE` | 2 h | Follow-up deadline is the planned arrival plus this grace. |

Rules:

- The computed next check is `evaluation + cadence` (the indoor-temperature
  sensor cadence when available, otherwise the default), clamped into the
  window: at least `MIN_FOLLOW_UP_DELAY` after evaluation and at most the
  earlier of the deadline (arrival + `DEADLINE_GRACE`) and evaluation +
  `MAX_FOLLOW_UP_DELAY`.
- Any model-supplied time must be timezone-aware, strictly after the
  evaluation time, and inside that window. A past, equal-to-evaluation,
  timezone-naive, too-soon, or too-distant time is rejected and the
  code-computed time is used instead. No invalid time reaches the store.
- When the arrival/deadline has already passed at evaluation (deadline at or
  before the evaluation time, or no time remains inside the window), the
  schedule status/flag is `deadline_passed`, `deadline_passed` is true, and no
  future check is scheduled (`next_check_at` is null). The
  `POST /api/investigations` path returns this flag explicitly and persists
  no follow-up with an invalid time.
- The store and the API validate too: a persisted follow-up must have
  timezone-aware `created_at`/`deadline`/`next_check_at`, a deadline strictly
  after `created_at`, and a `next_check_at` inside the window above;
  otherwise it is rejected and not persisted.

## Follow-up outcomes

Follow-up outcomes are decided by deterministic code in
`backend/aria_home/outcomes.py` (`evaluate_outcome`), not by the model.

- Only `indoor_temp` measurement records for the follow-up zone count, and
  only when the value is non-null, `received_at <= now`, and
  `created_at < observed_at <= deadline`. Records are deduplicated by
  `(source, observed_at)`, so a duplicated reading never counts twice.
  Readings observed after the deadline never contribute to any status,
  including `target_reached`.
- Statuses are decided in this order: `target_reached` (the last two counted
  readings are at or above the target), `warming_observed` (at least
  `min_samples` counted readings with a first-to-last rise of at least
  `min_rise_f`), `awaiting_measurement` (before the deadline), then after the
  deadline `not_observed_by_deadline` (at least `min_samples` counted
  readings) or `unable_to_verify` (fewer counted readings).
- When otherwise-countable readings were observed after the deadline, the
  outcome note includes "Readings after the deadline are not counted toward
  this follow-up." For example, `demo_recovery_v1` reaches 68 F only at
  20:15/20:30, after its 20:00 deadline, so at 20:31 it is
  `warming_observed`, not `target_reached`.
- A human statement never sets a status. When the status is
  `warming_observed` or `target_reached` and a human statement was received
  after the follow-up was created, the note also carries "An observed change
  after a reported action does not prove what caused it."

## Limitations

- Projection is a linear extrapolation of the observed trend; it assumes the
  rate persists and ignores weather, equipment cycling, and occupancy.
- Coverage is cadence coverage from the metrics layer; sparse or irregular
  sensors can be marked insufficient even if readings look consistent.
- Freshness uses the latest reading timestamp and source availability only;
  it does not detect a sensor stuck repeating one value.
- Confirmation currency, trip confirmation, and mismatch context are computed
  as-of the evaluation time by `context_as_of` in `scenario.py` and passed to
  `compute_readiness` as flags (see `backend/scenarios/README.md`).
- Thresholds are fixed constants, not fitted to a home; a very large or leaky
  home may warm far slower than the observed short-term rate suggests.
