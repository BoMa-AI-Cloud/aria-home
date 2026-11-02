ARIA Home, third set of edits. This is a synthetic replay of one winter night. The attached file is the caregiver decision endpoint from backend/aria_home/app.py. Answer in the same FILE / FIND / REPLACE format, with exact text, keeping the file's indentation.

Measured on the working tree: the recorded story answers the caregiver's permission request at 02:45 (scenario event kind "caregiver_hvac_authorized", available_at 02:45). If the visitor has made no decision by then, the story is approved at 02:45 and a technician visits at 03:30. But the endpoint still accepts a decline posted after that:
- POST decline with at=06:21 returns 201, recorded true.
- The follow-up for 04:51 then shows approved and 54.5 F, and 06:21 suddenly shows declined and 51.5 F. A repair that already happened is erased, and the room drops 16 F in the replay.

The rule: the permission request can be answered only until the recorded answer takes effect. A decision is accepted when `at` is at or before that event's available_at. If `at` is later and this investigation has no decision recorded yet, refuse it, and record nothing:
    return jsonify({"error": "the recorded story already answered this request at 02:45", "reason": "already_answered", "data_mode": "synthetic"}), 409
Build the time in the message from the event, not a literal. If the investigation already has a decision, keep today's behaviour exactly: repeating or changing it returns 200, recorded false, as of the request time. Scenarios with no such event are unaffected.

EDIT 1: in caregiver_decision_endpoint, add this check right after the "not_yet_visible" check. Read the scenario's events from dec_scn using the same access the rest of app.py uses for scenario events: `events_as_of` is imported in trace.py, and if app.py does not have it, add the import from where trace.py gets it. Use `store.get_caregiver_decision(existing["investigation_id"])` with no `at` to see whether any decision exists. Tell me if that signature is wrong.

EDIT 2: FILE backend/tests/test_p1_4_asof_decisions.py. Add these tests, using the file's existing `_client`, `_start`, and T0231 and T0245 helpers:
- test_decision_after_recorded_answer_is_refused: post decline at "2026-01-17T06:21:00-05:00" gives 409 with reason "already_answered"; the follow-up at 06:21 has caregiver permission status "approved" and verification stage "goal_verified"; and the follow-up at 07:01 is unchanged by the attempt.
- test_decision_at_the_recorded_answer_time_is_accepted: post decline at T0245 gives 201, and the follow-up at 06:21 has permission status "declined" and a stage that is not "goal_verified".
- test_repeat_after_recorded_answer_keeps_first_decision: decline at T0231 gives 201; then approve at 06:21 gives 200 with recorded false; permission status at 06:21 stays "declined".

Also tell me about any path in this endpoint where a false or contradictory story state could still be recorded. If you are unsure of any exact text, say so instead of guessing.
