ARIA Home, second set of edits. The attached file is the current `step_activity` function from backend/aria_home/trace.py. Answer in the same FILE / FIND / REPLACE format, with exact text. Do not change anything else.

Measured activity lines after a decline, today, for every step from 02:45 to 07:01:
"Thermostat telemetry missing; independent room sensor 52.0 F" (source computed:telemetry), with only the temperature changing. Readiness and verification are correct. The line never says she declined, or that the warm-by time was missed.

EDIT 1, in step_activity. When a decline is visible at this replay time (`caregiver_decision` is the decision as of `at`, with decision == "declined"):
- At the first checkpoint at or after decided_at, the text is: "Caregiver declined HVAC contact at HH:MM; nobody was contacted. Independent room sensor X F". Source: "computed:caregiver_declined". HH:MM is the decision time, formatted like the existing approved line, which reads "approved HVAC contact at 02:31".
- At later checkpoints before the warm-by time: "No contact made; independent room sensor X F, below the 68 F goal", using the confirmed target value already read in this function. Source: "computed:telemetry".
- Once the warm-by time has passed: "Warm-by time checked: expectation missed; room X F". Source: "computed:arrival_checked".
Keep the room value and the target coming from the values this function already computes. Add no constants. The checkpoint list is already available in this function.

EDIT 2, FILE backend/tests/test_step_activity_branches.py. In `test_activity_decline_branch`, replace these lines:
```
    assert lines[CARE_TIMES[4]]["source"] == "computed:telemetry"
    assert AUTH_LINE not in lines[CARE_TIMES[4]]["text"]
    assert lines[CARE_TIMES[5]]["source"] == "computed:reporting_restored"
    assert "visit" not in lines[CARE_TIMES[5]]["text"].lower()
```
and also these two lines further down:
```
    assert lines[CARE_TIMES[9]] == {"text": "Warm-by time checked", "source": "computed:arrival_checked"}
    follow = client.get(f"/api/follow-ups/{investigation_id}", query_string={"at": CARE_TIMES[7]}).get_json()
    assert follow["verification"]["stage"] == "goal_verified"
```
with assertions that prove the new rule. In this test she declines at 02:31 (CARE_TIMES[3]).
- CARE_TIMES[3]: source "computed:caregiver_declined", text contains "Caregiver declined HVAC contact at 02:31" and "nobody was contacted".
- CARE_TIMES[4]: AUTH_LINE not in the text.
- CARE_TIMES[5]: source "computed:telemetry", and "visit" and "restored" not in the lowercased text.
- CARE_TIMES[9]: source "computed:arrival_checked", text starts with "Warm-by time checked: expectation missed".
- At CARE_TIMES[7], verification stage is NOT "goal_verified" and NOT "warming_observed".
The rule changed on purpose: after a decline the thermostat stays silent, the room never warms, and the goal is never verified. Do not weaken anything else in the test.

EDIT 3, FILE backend/tests/test_trace.py. In `test_permission_step_follows_the_caregiver_and_never_shows_the_future`, the expected label ends "until she answers". The product text is now "until the caregiver answers". Update only that expected string.

Then list anything else in these files that the decline rule makes false. If you are unsure about any exact text, say so instead of guessing.
