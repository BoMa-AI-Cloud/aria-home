# Model-Value Evaluation Report

> Note 2026-11-02: every score in this file was measured on the earlier prompt inv-v3, not re-scored on the current inv-v5. They do not validate the current prompt, and no claim is made that current explanations were measured. The `HUMAN ... =?` rows and `observation_correct` below stay unscored. The Part A table at the end is one pass on inv-v3, drafted by Claude and confirmed by Brad. Human-scored quality of current explanations and real-world effectiveness have not been established.

Code snapshot: d5a0da3; generated 20261031T181441Z; live variants n=12.

## A — Spark vs deterministic summary

Deterministic checks passing: 12/12.
Needs human scoring per variant (never guessed): problem_named, next_action_right.
- HUMAN ev-arrival-met: problem_named=?, next_action_right=?
- HUMAN ev-conflict-sensors: problem_named=?, next_action_right=?
- HUMAN ev-normal-night: problem_named=?, next_action_right=?
- HUMAN ev-outage-0130: problem_named=?, next_action_right=?
- HUMAN ev-outage-0340: problem_named=?, next_action_right=?
- HUMAN ev-outage-2310: problem_named=?, next_action_right=?
- HUMAN ev-recovery-fails: problem_named=?, next_action_right=?
- HUMAN ev-report-no-warm: problem_named=?, next_action_right=?
- HUMAN ev-slow-cool-ontrack: problem_named=?, next_action_right=?
- HUMAN ev-stale-room: problem_named=?, next_action_right=?
- HUMAN ev-thermostat-gap-steady: problem_named=?, next_action_right=?
- HUMAN ev-wrong-zone: problem_named=?, next_action_right=?

## B — Spark vs Spark+Wonder

Catch rate on planted claims: 12/12 flagged.
False-alarm rate on genuine answers: 0/12 flagged.
- ev-arrival-met: planted=wrong-temperature; verdict=issues_found; status=ok
- ev-conflict-sensors: planted=invented-repair-cause; verdict=issues_found; status=ok
- ev-normal-night: planted=report-proves-warmth; verdict=issues_found; status=ok
- ev-outage-0130: planted=wrong-time; verdict=issues_found; status=ok
- ev-outage-0340: planted=wrong-temperature; verdict=issues_found; status=ok
- ev-outage-2310: planted=invented-repair-cause; verdict=issues_found; status=ok
- ev-recovery-fails: planted=report-proves-warmth; verdict=issues_found; status=ok
- ev-report-no-warm: planted=wrong-time; verdict=issues_found; status=ok
- ev-slow-cool-ontrack: planted=wrong-temperature; verdict=issues_found; status=ok
- ev-stale-room: planted=invented-repair-cause; verdict=issues_found; status=ok
- ev-thermostat-gap-steady: planted=report-proves-warmth; verdict=issues_found; status=ok
- ev-wrong-zone: planted=wrong-time; verdict=issues_found; status=ok

## C — watcher first attempt vs revised attempt

Verified first attempt: 3/12.
Revisions corrected: 7/9 attempted.
Missed-problem proxy (empty model answer while code detections fire): 2/12.
- REJECTED ev-conflict-sensors: evidence ev11-tstat-temp-0093 is not fresh at the evaluation time (historical only); observation value does not match evidence ev11-tstat-temp-0093: 64.2 != 66.1 (tolerance 0.15); observation time does not match evidence ev11-tstat-temp-0093; observation value does not match evidence ev11-roomb-0128: 64.1 != 68.4 (tolerance 0.15); evidence source:room_sensor is not fresh at the evaluation time (historical only); observation cites contradictory readings ['ev11-room-0128', 'ev11-roomb-0128']: unresolved conflicts block the claim; observation value does not match evidence ev11-tstat-temp-0128: 'idle' != 64.2 (tolerance 0.15)
- REJECTED ev-outage-0130: evidence ev02-room-0093 is not fresh at the evaluation time (historical only); observation value does not match evidence ev02-room-0093: 64.4 != 65.9 (tolerance 0.15); observation time does not match evidence ev02-room-0093; evidence source:thermostat is not fresh at the evaluation time (historical only); evidence ev02-tstat-temp-0113 is not fresh at the evaluation time (historical only)
- REJECTED ev-outage-0340: evidence ev03-room-0119 is not fresh at the evaluation time (historical only); observation value does not match evidence ev03-room-0119: -2.3 != 65.9 (tolerance 0.15); observation time does not match evidence ev03-room-0119; observation value does not match evidence ev03-room-0154: -2.3 != 63.6 (tolerance 0.15); evidence source:thermostat is not fresh at the evaluation time (historical only); evidence ev03-tstat-temp-0139 is not fresh at the evaluation time (historical only); observation value does not match evidence ev03-room-0154: -4.4 != 63.6 (tolerance 0.15)
- REJECTED ev-outage-2310: evidence source:room_sensor is not fresh at the evaluation time (historical only)
- REJECTED ev-recovery-fails: evidence ev04-room-0141 is not fresh at the evaluation time (historical only); observation value does not match evidence ev04-room-0141: 66.5 != 68.2 (tolerance 0.15); observation time does not match evidence ev04-room-0141; observation value does not match evidence ev04-room-0176: 'idle' != 66.5 (tolerance 0.15)
- REJECTED ev-report-no-warm: evidence ev09-room-0141 is not fresh at the evaluation time (historical only); observation value does not match evidence ev09-room-0141: -0.4 != 62.3 (tolerance 0.15); observation time does not match evidence ev09-room-0141; observation value does not match evidence ev09-room-0176: -0.4 != 61.9 (tolerance 0.15); observation value does not match evidence ev09-room-0176: 'idle' != 61.9 (tolerance 0.15)
- REJECTED ev-stale-room: evidence ev07-tstat-temp-0093 is not fresh at the evaluation time (historical only); observation value does not match evidence ev07-tstat-temp-0093: 62.7 != 63.8 (tolerance 0.15); observation time does not match evidence ev07-tstat-temp-0093; observation value does not match evidence ev07-tstat-temp-0128: 'idle' != 62.7 (tolerance 0.15); evidence source:room_sensor is not fresh at the evaluation time (historical only); evidence ev07-room-0048 is outside the 3-hour as-of window; evidence ev07-room-0048 is not fresh at the evaluation time (historical only)
- REJECTED ev-thermostat-gap-steady: evidence source:room_sensor is not fresh at the evaluation time (historical only)
- REJECTED ev-wrong-zone: evidence ev08-room-0093 is not fresh at the evaluation time (historical only); observation value does not match evidence ev08-room-0093: 64.2 != 65.9 (tolerance 0.15); observation time does not match evidence ev08-room-0093
- MISSED-PROXY ev-outage-2310: model empty, code detections fired
- MISSED-PROXY ev-thermostat-gap-steady: model empty, code detections fired
Needs human scoring per variant (never guessed): observation_correct.

## Limitations

- Models interpret only; readiness and verification stay in code.
- Rubric parts needing judgement are listed above as needs-human, not scored.
- Twelve synthetic variants cannot represent real homes; results do not generalize.
- A Wonder non-flag is not proof the answer is true; a flag is bounded to the pack.

## Rescore after a validator fix found by this run (2026-10-31, no new calls)

This run exposed a bug in the watcher's validator, not in the model. Citing a
whole source (`source:room_sensor`) was always rejected as "not fresh",
because the validator read `last_observed_at` while source-status items carry
`newest_observed_at`. The fix is in `aria_home/watcher.py`, with
`tests/test_watcher_source_status_freshness.py`. It was red-proofed: with the
fix reverted, the available-source test fails. A silent thermostat source is
still rejected after the fix.

Every saved first and revised claim was re-checked offline with the fixed
validator. The raw results file above is unchanged.

| watcher measure | as recorded | after the validator fix |
|---|---|---|
| first attempt verified with observations | 0/12 (3 confirmed with no observations) | 0/12 (unchanged) |
| first attempt rejected | 9/12 | 9/12 (every rejection still has a real failed check, 2 to 9 each) |
| revisions verified | 7/9 | 9/9 |
| missed-problem proxy | 2/12 | 0/12 (both were the rejected revisions above) |

The two changed cases are `ev-outage-2310` and `ev-thermostat-gap-steady`. In
each, the only failed check on the revised claim was the false
`source:room_sensor` rejection.

What the first-attempt failures actually were: citing older readings as
current, values that do not match the cited record (for example a trend rate
written as a temperature), and timestamps that do not match the cited record.
On every variant, code caught these and the revision fixed them.

### Wonder check

On every planted copy, Wonder's issue note names the planted claim itself
(the higher temperature, the earlier time, the "report alone proves warmth"
wording, or the invented repair cause). It is not flagging something else by
chance. Every genuine review came back `no_issues`, with 0 issues listed.

Added limitations:
- The planted claims use four fixed templates ("about 6 F higher", "3 hours
  earlier", "alone proves", "proves furnace failure"). Catching these says
  little about subtler errors.
- One planted review (`ev-report-no-warm`) also raised a follow-up timing
  point (07:15 against a 07:00 arrival) that the genuine review did not raise.
  That is a possible missed issue in the genuine review, and it is not counted
  as a false alarm.
- Part A's problem and next-action scores still need a human, as listed above.

## Part A human scoring (drafted by Claude, confirmed by Brad 2026-10-31)

Each Spark answer was scored against the variant's written ground truth: did it name the real problem, and was its
next action right? C = correct, P = partly, W = wrong.

| Variant | Problem named | Next action right | Note |
|---|---|---|---|
| ev-arrival-met | P | C | target met at arrival; the earlier outage is not mentioned |
| ev-conflict-sensors | C | C | names the disagreeing sensors; asks which is authoritative |
| ev-normal-night | C | C | at target, routine check |
| ev-outage-0130 | P | P | at risk and falling, but heat stopping is not named; next is "manager may need to check on site", not HVAC now |
| ev-outage-0340 | P | P | same pattern |
| ev-outage-2310 | P | P | same pattern |
| ev-recovery-fails | C | P | cooling after earlier warming; next is manager review, not "the fix did not hold" |
| ev-report-no-warm | P | P | no rise toward target; never says the completion report proves nothing |
| ev-slow-cool-ontrack | C | C | above target, routine check |
| ev-stale-room | C | C | no usable room samples; get an authoritative reading |
| ev-thermostat-gap-steady | C | P | correctly no dispatch, but does not say to check the thermostat link |
| ev-wrong-zone | P | P | zone difference raised only as a hypothesis |

Totals: problem named 6/12 correct, 6/12 partly, 0/12 wrong; next action right 5/12 correct, 7/12 partly, 0/12
wrong. No answer claimed a cause the evidence could not support.

Limitation found by this scoring: Spark's prompt (`PROMPT_VERSION`) and the confirmation context it reads were
written for the earlier trip-home story, so its next steps say "manager review before the planned arrival" instead of
naming the caregiver or the HVAC company. That explains most of the partly scores. Fixing it needs a new prompt version
and a re-recording of every answer, which is a separate paid batch and has not been done.

Update 2026-11-01: the story change reworded the prompt to inv-v4, and on 2026-11-02 to inv-v5, which also names the responder. Every score above was measured on inv-v3. Neither newer prompt has been re-scored.
