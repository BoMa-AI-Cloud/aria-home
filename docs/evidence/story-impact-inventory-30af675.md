# Story restructure impact inventory (2026-11-01, commit 30af675)

No paid calls. Candidate fixtures were written to temporary copies; nothing in `backend/scenarios/` changed. Identities
were computed with `investigator.inference_identity` and `_canonical_decision_inputs` at each checkpoint.

## Result

Changing any room or thermostat value before 23:31, even with ids, times, counts and `manifest.version` kept, changes
the input revision at **all ten** proposed checkpoints. The plan's expectation that 02:31-07:01 could be reused is false.

Cause: every evidence pack carries every visible record since 16:00 (427 records at 02:31, 576 at 07:01), and the input
revision hashes each record's value. At 02:31-07:01 the only differing input is `records`.

| Artifact | Entries | Match current fixture | Match a changed fixture |
|---|---|---|---|
| `eval/recorded/care-2026-10-30.json` | 10 | 10 | 0 |
| `eval/recorded/care-2026-10-30-1.json` | 9 | 9 | 0 |
| `eval/reviews-care-2026-10-30.json` | 10 | 10 | 0 |
| `eval/reviews-care-2026-10-30-1.json` | 10 | 10 | 0 |
| `eval/watchers-care-2026-10-30.json` | 8 | 8 | 0 |
| `eval/watchers-care-2026-10-30-1.json` | 2 | 2 | 0 |
| `eval/corrections-*.json` | 2 | 2 | 0 |

Reusable: visual evidence is unchanged in the input (checked at 06:45). The technician transcript is bound by scenario
and model only (from the code, not recomputed here).

## What readiness allows

`on_track` at a falling step needs the room at 68 F or above. Measured with the 21:00 room value and the evening start:

| Start at 16:00 | Room at 21:00 | 19:20 | 21:00 | 23:30 |
|---|---|---|---|---|
| 68.5 | 68.0 | on_track | on_track | at_risk |
| 70 | 68.0 | on_track | on_track | at_risk |
| 70 | 67.5 | on_track | at_risk | at_risk |
| 70 | 66.5 | at_risk | at_risk | at_risk |

Keeping every value after 23:31 would force a fall from 68 F at 21:00 to 52.6 F at 23:30 (about 6 F an hour), then about
0.2 F an hour. Since nothing is reusable anyway, that constraint buys nothing.

A curve that also changes values up to 01:45 (233 values; 68.5 F until 21:00, about 3.7 F an hour to 52 F at 01:30, later
data unchanged) gave:

| Time | Readiness | Room | Rate per hour |
|---|---|---|---|
| 19:20 | on_track | 68.5 | 0.0 |
| 21:00 | on_track | 68.5 | 0.0 |
| 23:30 | at_risk | 59.6 | -3.05 |
| 02:31 | at_risk | 52.0 | -2.40 |
| 02:45 | at_risk | 52.0 | -2.19 |
| 04:21 | at_risk | 52.0 | -0.10 |
| 04:51 | at_risk | 54.5 | 0.86 |
| 06:21 | on_track | 68.0 | 5.49 |
| 06:45 | on_track | 68.4 | 5.62 |
| 07:01 | arrival_passed | 68.4 | 5.62 |

This curve shows no decline at 21:00. The step 2 "small decline" needs a start near 70 F, with the room still at or above
68 F at 21:00. That full curve has not been run through this table.

## Measured through the real app on a temporary copy (2026-11-01)

Curve: 70.0 F at 16:00, 68.4 F at 21:00, about 3.6 F an hour to 52 F at 01:30, later data unchanged; thermostat 0.2 F
above the room; 233 values changed.

| Time | Readiness | Room | Rate per hour |
|---|---|---|---|
| 19:20 | on_track | 69.0 | -0.31 |
| 21:00 | on_track | 68.4 | -0.34 |
| 23:30 | at_risk | 59.6 | -3.09 |
| 02:31 | at_risk | 52.0 | -2.40 |
| 06:21 | on_track | 68.0 | 5.49 |
| 07:01 | arrival_passed | 68.4 | 5.62 |

With the investigation created at 23:30, the request reads "your mother's home is cooling (60 F, 8 F below the 68 F
target, furnace reported idle since 16:00)" and stays word for word at every later step in all three branches. Stages
run telemetry_missing, reporting_restored, goal_verified, arrival_met. A decline at 02:31 stays declined and still
reaches goal_verified.

**Blocker found.** An investigation created at 19:20 while on track already gets a follow-up. Replayed forward, it never
asks the caregiver, shows `goal_verified` at 21:00 and `goal_not_maintained` at 23:30, and lists an HVAC request before
any permission exists. So no follow-up or notice may exist before the first at-risk step, and that needs a code change.

**Event to move.** `evt-care-caregiver-alert` is at 02:35 and would contradict a request asked at 23:30.

## Not measured

- Whether `eval/model-value` variants depend on the changed values.
- Test impact beyond a text search: 31 tests and docs mention 54 F, 52 F, 7:20 PM or 19:20.

## Published offline results on the changed data (measured 2026-11-01, temporary copy)

`evaluation.evaluate_cases` gave the same totals on the current and the changed fixture: combined 22/22, thermostat 12,
room sensor 4, electrical 2, calendar 2, and no row changed its result. The claims quoted in the README and the video stay
true. One written reason in `backend/eval/expected.json` needs updating: the 02:31 case says "flat trend", but the
three-hour trend at 02:31 becomes -2.4 F an hour even though the room has held 52 F since 01:30.
