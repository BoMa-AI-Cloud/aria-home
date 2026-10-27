# Readiness rules

Readiness is decided by deterministic code in `backend/aria_home/readiness.py`
(`compute_readiness(pack, now, flags=None)`), not by the model. The investigator
puts the result in the evidence pack (`readiness` and `computed_readiness`),
states it in the prompt, and rejects any model answer whose `readiness` differs
from the computed status. The model only explains the computed status.

Statuses: `on_track`, `at_risk`, `cannot_tell`, `arrival_passed`. The
investigator contract stays `inv-v2`; its schema/prompt status list now also
includes `arrival_passed`, and the model must return exactly the computed
status as before.

## Canonical decision precision vs display rounding

Readiness is computed once, from canonical (unrounded) inputs, in
`compute_readiness`. Every result is stamped with
`READINESS_POLICY_VERSION` (`readiness-policy-v1`, also in
`inputs.policy_version` and the pack's `readiness_policy_version`). The
evidence pack keeps that decision in `canonical_readiness` (unrounded) and
`computed_readiness`; the `metrics`/`evidence` values shown to the model are
display-rounded to one decimal (with a rounded zero always shown as `0.0`,
never `-0.0`). Display rounding never feeds a decision: for example flat
67.96 F readings against a 68 F target have a canonical gap of -0.04 F and
are `at_risk`, even though the displayed gap rounds to `0.0`.

Validation (`investigator.validate`) compares the model's `readiness`
against the stored computed status (`canonical_readiness`, then `readiness`
/ `computed_readiness`) and never recomputes readiness from the rounded
display values; a pack with no stored computed status is rejected for that
reason rather than recomputed. The model's own status is never trusted on
its own. The only tolerance in the target decision is the explicit named
policy constant `TARGET_GAP_TOLERANCE_F` (default `0.0` F, also in
`THRESHOLDS`/`inputs.target_gap_tolerance_f`): a reading meets the target
when `gap_f >= -TARGET_GAP_TOLERANCE_F`. With the default, any reading
strictly below target — even by 0.01 F — does not meet it; changing the
tolerance is a deliberate policy change to that constant, never a side
effect of rounding. Celsius values are converted before comparison
(trend/target-gap conversion in `metrics.py`; gap/rise/rate deltas are
scaled C→F in `readiness.py`), so a Celsius record is decided on its
Fahrenheit-equivalent gap.

## Thresholds

All thresholds are named module-level constants in `readiness.py`:

| Constant | Value | Meaning |
|---|---|---|
| `MIN_SAMPLES` | 3 | Fewer indoor samples than this gives `cannot_tell`. |
| `MIN_COVERAGE` | 0.5 | Cadence coverage below this gives `cannot_tell`. |
| `STALE_READING_AGE_S` | 3600 s | Latest indoor reading older than this gives `cannot_tell`; the indoor source status of `missing`, `stale`, or `invalid` also gives `cannot_tell` (room sensor when it is the indoor source, otherwise thermostat). |
| `SMALL_GAP_F` | 2.0 F | Only a gap at or below this can qualify for projected `on_track`. |
| `MIN_TREND_WINDOW_S` | 3600 s | Warming must be observed over at least this first-to-last sample window to project. |
| `MIN_RISE_F` | 1.0 F | First-to-last rise over the trend window must be at least this to project. |
| `MIN_RATE_PER_HOUR_F` | 0.5 F/hour | Trend rate must be at least this to project. |
| `PROJECTION_MARGIN_F` | 0.5 F | Projected temperature at arrival must reach target plus this margin. |
| `ARRIVAL_TIME_MARGIN_S` | 1800 s | The gap must be projected to close at least this long before arrival. |
| `TARGET_GAP_TOLERANCE_F` | 0.0 F | Explicit tolerance in the meets-target decision (`gap_f >= -TARGET_GAP_TOLERANCE_F`); default zero, never implied by display rounding. See Canonical decision precision above. |
| `READINESS_POLICY_VERSION` | `readiness-policy-v1` | Version stamped on every readiness result and evidence pack. |

Temperature gaps, rises, and rates in Celsius are converted to Fahrenheit
equivalents before comparison with the `*_F` thresholds.

## Measurement eligibility

All physical-measurement paths use the single policy in
`backend/aria_home/eligibility.py` (`is_measurement_eligible`,
`eligible_records`, `indoor_records`, `circuit_records`, `latest_current`,
`is_current_record`). A record is eligible only when all of these hold:

- Its quantity is a physical measurement and its source is allowed for that
  quantity (table below).
- Its record kind is `measurement`. `human_statement`, `device_report`,
  `forecast`, and `derived` records never count as physical measurements;
  human statements may corroborate only (for example the outcome note in
  `outcomes.py`) and never set a temperature, trend, readiness, recovery, or
  electrical-activity value.
- It matches the quantity and, where applicable, the zone/property (record
  `subject` equals the zone, whose prefix is the property) or the circuit
  (`binding.circuit_id` or `subject`).
- `received_at <= now` and `observed_at <= received_at`; a delayed reading is
  visible only after receipt, never in an earlier replay. A reading observed
  more than 60 s in the future is not eligible.
- For a current claim it is fresh under the cadence policy and not superseded:
  age at evaluation is at most `2 x expected_cadence_s` when a cadence is
  known, otherwise at most 3600 s (readiness also caps this at
  `STALE_READING_AGE_S`). A claim exactly at the limit passes; one second over
  fails. Only the latest eligible reading (by observed, then received, time)
  for the chosen source is current; an older eligible reading may only be
  described as historical, never as `current_temperature`, and a stale reading
  likewise is historical only.

Allowed source/kind per measurement path:

| Measurement path | Quantity | Allowed sources | Allowed kind |
|---|---|---|---|
| Indoor trend, target gap, readiness indoor reading, arrival verification | `indoor_temp` | `room_sensor`, `thermostat` (device telemetry) | `measurement` only |
| Recovery/outcome room readings | `indoor_temp` | `room_sensor` preferred; `thermostat` only when no room sensor (trends/outcomes use the same indoor selection) | `measurement` only |
| Recovery thermostat telemetry gate | `indoor_temp` | `thermostat` | `measurement` only |
| Circuit activity, power context, electrical claims | `circuit_power` | `electrical` | `measurement` only |

Thermostat `hvac_reported_state`/`setpoint` records are `device_report`, not
physical measurements: they may support/contradict heating as reported state
but never supply an indoor temperature. Evidence-pack record items keep
`expected_cadence_s` and `provenance` alongside value/unit/times so this
policy is auditable from the pack. Trends and circuit activity likewise carry
`source`, `expected_cadence_s`, `last_id`, `last_received_at`, `provenance`,
and `fresh`/`is_fresh` for their latest eligible sample. If no eligible sensor
measurement exists (missing sensor, or only human statements), readiness is
`cannot_tell`, trends have zero samples, recovery is
`telemetry_missing`/`unable_to_verify`, and current-value facts are rejected.

## Rules

### Indoor source

When a scenario has room-sensor `indoor_temp` records for the zone, readiness
uses the room sensor — as `metrics.temperature_trend` already does — for the
indoor reading, freshness, coverage, and trend. A missing, stale, or invalid
thermostat does not then make readiness `cannot_tell`; instead the result
carries the separate reason "thermostat telemetry missing; room sensor used"
(`inputs.indoor_source` is `room_sensor`). Scenarios without a room sensor for
the zone are unchanged and judge freshness on the thermostat. For example,
`demo_video_v1` at 16:31 is `at_risk`: the fresh room reading is 52.0 F at
16:30, 16 F below target with a flat trend, while the thermostat is offline.

### arrival_passed

When `now` is strictly after the confirmed arrival (`now >` arrival; at or
before arrival this rule does not apply and the earlier rules below apply
unchanged) and the trip/confirmation context is valid: not cancelled,
unconfirmed, mismatched, or outdated, with a confirmed target, readiness is
decided at arrival, not at `now`. The status is `arrival_passed` — never
`on_track` (or any before-arrival status) after arrival — and its single
reason states whether the target was met at arrival time, using only
readings received by arrival (latest such eligible indoor reading — see
Measurement eligibility above, room-sensor readings preferred over thermostat,
fresh within the cadence freshness limit, capped at `STALE_READING_AGE_S`, of
arrival): the target was met at arrival time, was not met at arrival time,
or whether it was met at arrival time is unknown (no fresh indoor reading
received by arrival). The readiness result also carries this outcome as
`target_at_arrival` (`met` / `not_met` / `unknown`); it is `null` for
non-`arrival_passed` statuses. Readings received after arrival never change
this. Cases with no confirmed arrival (for example cancelled or outdated
trips) keep the `cannot_tell` rules below instead.

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
- Indoor reading missing (no latest value, or the indoor source availability
  `missing`), stale (availability `stale`/`invalid`, or latest reading older
  than `STALE_READING_AGE_S`), or conflicting (the indoor source availability
  `conflicting`). With a room sensor for the zone the indoor source is the
  room sensor, not the thermostat (see Indoor source above).
- Coverage below `MIN_COVERAGE`, coverage unavailable, or fewer than
  `MIN_SAMPLES` samples.

### on_track

Returned only before arrival, when no `cannot_tell` condition holds and either:

- The latest fresh reading already meets or exceeds the target (canonical gap >= `-TARGET_GAP_TOLERANCE_F`; with the default 0.0 tolerance, gap >= 0), or
- The gap is small (at most `SMALL_GAP_F`), warming is sustained (window at
  least `MIN_TREND_WINDOW_S`, rise at least `MIN_RISE_F`, rate at least
  `MIN_RATE_PER_HOUR_F`), and linear projection at that rate both reaches
  target plus `PROJECTION_MARGIN_F` by arrival and closes the gap at least
  `ARRIVAL_TIME_MARGIN_S` before arrival.

A positive slope alone never gives `on_track`, and no projection is made from
a window shorter than `MIN_TREND_WINDOW_S` or a rise below `MIN_RISE_F`.

### at_risk

Returned otherwise (before arrival). Its reasons state that it is not a guaranteed prediction,
for example: "At current readings the target may not be reached by arrival;
this is not a guaranteed prediction."

The demo scenario `demo_v1` at 18:00 is `at_risk`: gap -15.9 F with a trend of
about +0.034 F/hour fails the small-gap and sustained-warming thresholds.
Only strictly after its 18:00 arrival is it `arrival_passed` (target not met
at arrival), per the rule above.

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

## Recovery verification

Recovery verification is decided by deterministic code in
`backend/aria_home/verification.py` (`verify_recovery(scenario, followup, now)`
-> `{stage, reasons, supporting_ids, corroboration_ids, evaluated_at,
goal_verified_at, arrival_met_at}`), not by the model. `GET
/api/follow-ups/<id>` also returns it as `verification` for scenarios with
room-sensor records. It uses only records with `received_at <= now` and
events with `available_at <= now`.

`stage` is the current maintenance state at `now`; it is not a permanent
record that the goal was once met. The historical milestone is kept
separately: `goal_verified_at` is the instant the most recent full
`GOAL_HOLD_S` hold completed (null if no hold has completed), and
`arrival_met_at` is the confirmed arrival instant when the current stage is
`arrival_met` (otherwise null). A result can therefore carry a non-null
`goal_verified_at` while its current `stage` has regressed.

Named constants in `verification.py`:

| Constant | Value | Meaning |
|---|---|---|
| `GOAL_HOLD_S` | 1800 s | Every room-sensor reading at/above target for at least this long is required for `goal_verified`. |
| `MAX_GAP_CADENCE_MULTIPLIER` | 2 | A gap over 2x cadence breaks freshness/gap checks, the goal-hold window, and arrival coverage (freshness itself is stale after 2x cadence in `evidence.py`). |
| `REPORT_EVENT_KIND` | `hvac_completion_report` | The only event kind listed as corroboration. |
| `CORROBORATION_EVENT_KINDS` | `(hvac_completion_report,)` | Visible events listed in `corroboration_ids`, never in `supporting_ids`. |
| `NON_CORROBORATING_EVENT_KINDS` | manager acknowledgement / HVAC authorization / `service_visit` kinds | Human/simulated events that never change the stage. |
| `HEATING_REPORTED_STATES` / `NON_HEATING_REPORTED_STATES` | `heating` / `idle`, `off`, `cooling`, etc. | Reported thermostat states that support or contradict heating. |
| `MAPPED_HEATING_EQUIPMENT` | `furnace`, `blower`, `heating`, `hvac`, `heat_pump`, `heater` | Circuit bindings treated as the mapped heating circuit. Its noise floor reuses `metrics.NOISE_FLOOR_W` (15 W). |
| Warming thresholds | `FollowUp.min_samples` (3), `FollowUp.min_rise_f` (2.0 F) | Reused from `outcomes.py`, applied to room-sensor readings only. |

Stages, in order (each requires the previous):

1. `telemetry_missing`: no fresh thermostat `indoor_temp` telemetry; freshness
   is `evidence.freshness` (missing value, or age over 2x expected cadence).
2. `reporting_restored`: fresh thermostat telemetry after a gap over 2x
   cadence. It never closes anything alone.
3. `warming_observed`: at least `min_samples` room-sensor (not thermostat)
   `indoor_temp` readings after the follow-up's `created_at`, first-to-last
   rise at least `min_rise_f`, and neither the latest reported thermostat
   state nor the latest fresh mapped-circuit activity contradicts heating
   (a non-heating reported state, or no active mapped circuit when one is
   freshly checked, contradicts). Electrical activity is supporting only:
   its ids may appear in `supporting_ids`, but watts alone never advance
   the stage, and it is never proof of useful heat.
4. `goal_verified`: the latest eligible segment is a contiguous set of
   room-sensor readings, all observed at or before the follow-up deadline,
   where every reading is at/above the target for at least `GOAL_HOLD_S`,
   with no gap longer than 2x cadence, and no later eligible reading breaks
   that maintenance (see Goal maintenance below). Any dip below target or
   over-cadence gap restarts the window.
5. `arrival_met`: the goal is currently verified, evaluated at or after the
   confirmed planned arrival (`context_as_of` trip), with complete
   room-sensor coverage from the latest verification point through that
   arrival (see Arrival coverage below), and every eligible reading in that
   span at/above target.

### Goal maintenance (relapse after a successful hold)

Verification is evaluated on the latest relevant segment, never on an
earlier completed hold alone:

- Any eligible room-sensor reading below target after `goal_verified_at`
  (observed at or before the follow-up deadline, visible at `now`) makes
  the current stage `goal_not_maintained` — for example a 64 F reading
  against a 68 F target after a successful 30-minute hold. The homeowner
  wording (`notifications.py`) and the frontend stage label
  (`goal_not_maintained`: "Temperature goal no longer maintained") report
  this same current stage, while `goal_verified_at` still records when the
  earlier hold completed.
- After a relapse, renewed `goal_verified` requires a new full hold: a
  fresh contiguous at/above-target segment of at least `GOAL_HOLD_S` with
  no gap over 2x cadence. Until that new hold completes the stage stays
  `goal_not_maintained`; when it completes, `goal_verified_at` updates to
  the new completion instant.
- If readings after a successful hold are stale or missing (room-sensor
  freshness per `evidence.freshness`, or an over-cadence gap after
  verification with no dip observed), the current stage is
  `unable_to_verify`, not `goal_verified`/`arrival_met`;
  `goal_verified_at` still records the earlier completed hold.
- `arrival_met` requires the target maintained through arrival on the
  latest segment: a below-target reading after verification and at or
  before arrival (or a coverage gap in that span) prevents `arrival_met`
  unless a new full hold completes at or before arrival. A relapse that
  spans the arrival therefore gives `goal_not_maintained` (dip) or
  `unable_to_verify` (coverage gap), never `arrival_met`; a hold first
  completed after arrival gives `goal_verified`, not `arrival_met`.

### Arrival coverage

`arrival_met` requires coverage through the arrival boundary, not just a
qualifying reading sometime before arrival. Eligible readings are
room-sensor readings visible at evaluation (`received_at <= now`, as for
all of `verify_recovery`) whose `observed_at` lies in the closed interval
from the verification point (`verified_at`, when the goal hold completed)
to the confirmed arrival. Coverage is judged on `observed_at` instants —
timezone offsets do not matter, only the instant — with `received_at`
used only for visibility: a delayed reading observed at 20:59 supports
arrival only in evaluations at or after its receipt, never in an earlier
replay.

No gap in that coverage may exceed
`MAX_GAP_CADENCE_MULTIPLIER x cadence` (2 x 300 s = 600 s in
`demo_video_v1`). The checked gaps are: verification point to the first
eligible reading, each pair of consecutive eligible readings, and the
final gap from the last eligible reading at or before arrival to the
arrival instant itself. A gap exactly at the limit passes; one second
over fails. A reading observed exactly at the arrival instant is
eligible and closes the final gap. Readings observed after arrival never
cover the pre-arrival interval: a fresh post-arrival reading (for example
at 21:05 for a 21:00 arrival) cannot support `arrival_met`, appear in its
`supporting_ids`, or substitute for a missing pre-arrival reading.

Missing or incomplete coverage — no eligible readings, an excessive
internal or final gap, or an unavailable cadence — gives
`unable_to_verify` with a coverage-gap reason, never `arrival_met`. For
example, removing the room readings after 20:20 through 21:00 in
`demo_video_v1` and evaluating at 21:06 is `unable_to_verify`, even though
the 20:20 reading was at target and a fresh reading exists at 21:05:
the 20:20-to-21:00 final gap (2400 s) exceeds 600 s.

If room-sensor readings are missing or stale (per `evidence.freshness`) at a
stage that needs them — after reporting is restored, including before
`goal_verified`/`arrival_met` can be claimed — the stage is
`unable_to_verify`, never a success stage. Missing room readings after the
follow-up was created also give `unable_to_verify`. The same applies to
arrival coverage: incomplete coverage through the arrival boundary (see
Arrival coverage above) gives `unable_to_verify`, never `arrival_met`.

Human statements and events (manager acknowledgement, `service_visit`,
`hvac_completion_report`, and all other events) never change the stage. A
visible `hvac_completion_report` is listed only in `corroboration_ids`
(also mirrored as `corroboration`), never in `supporting_ids`, with the
reason that it is corroboration only. In `demo_video_v1` the report is
available at 20:45, after `goal_verified` at 20:21, so it cannot create or
advance that verification.

For `demo_video_v1` with a follow-up created by `POST /api/investigations`
at 16:31: 16:31 `telemetry_missing`, 18:21 `reporting_restored`, 18:51
`warming_observed`, 19:51 still `warming_observed` (target first reached at
19:50, hold not yet complete), 20:21 `goal_verified`, 21:01 `arrival_met`.

## Homeowner notification preference

A homeowner notification is queued only when the confirmation visible
as of the evaluation time (`context_as_of`) has `notify_homeowner: true`.
`notify_homeowner: false` is refused as `homeowner_opted_out`; a missing
confirmation or a missing/unknown preference value is refused as
`homeowner_preference_missing` — neither is permission. A later
confirmation revision supersedes an earlier one only from its
`confirmed_at`. Refused homeowner notifications are persisted as
`state: refused` audit rows with `refusal_reason` set and are never
marked delivered. There is no emergency or readiness-status override,
and this gate is independent of `manager_authorized`: property-manager
(and HVAC) notifications are decided by their own authorization rules
either way.

## Replay projection

The complete audit history is stored permanently and is never deleted or
rewritten by a replay: all `outcome_events`, `notifications`, and
`notification_acks` rows remain in the store (for example,
`Store.list_outcomes(id)` / `Store.list_notifications(id)` with no `at`
return the full history, including after a restart on the same file).

A replay response is a projection of that history at the requested `at`.
Every record in a replay response must carry its own time at or before
`at`:

- outcome events: `evaluated_at <= at` (`GET /api/follow-ups/<id>` `history`,
  `verification_history`, and the displayed follow-up
  `status`/`last_status`/`last_evaluated_at`/`supporting_ids`);
- notifications: `created_at <= at` (`GET /api/follow-ups/<id>`
  `notifications` and `GET /api/notifications?at=...`);
- acknowledgements: `acknowledged_at <= at` — a notification shown at a
  time before its acknowledgement has `acks: []` and its delivery state as
  of that time (for example `simulated_delivered`), never an acknowledged
  presentation created by a later ack;
- scenario events and reports (for example the HVAC completion report in
  verification `corroboration_ids`): `available_at <= at`, via
  `events_as_of` / `verify_recovery` as-of filtering.

Reading an earlier replay is read-only with respect to later state: when
`at` is earlier than the latest stored evaluation for that follow-up,
the request performs no writes — it creates no notifications and does not
record an outcome or overwrite `last_status`/`last_evaluated_at`. Writes
only occur at or after the latest stored evaluation, and repeated reads
at the same `at` are idempotent (no new rows). A replay therefore cannot
synthesize records that were never created by their projected time: a
notification actually created at 21:01 is simply absent from a 16:31
projection, not recreated at 16:31.

Requests with `at` before the investigation's `created_at` return
`409 {"error": "investigation not yet created at this time"}` from
`GET /api/follow-ups/<id>` and from
`GET /api/notifications?investigation_id=<id>&at=...`, never data.

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
