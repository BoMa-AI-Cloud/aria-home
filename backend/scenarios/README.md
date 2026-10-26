# Synthetic scenarios

All scenarios here are synthetic. Scenario timestamps (January 2026) are
fictional replay times, not when the data was created.

Trip availability timestamps were added on 2026-10-26: every trip entry
carries an explicit `known_at` (when that created/revised/cancelled state
became known) and a `revision_id`, and every homeowner confirmation carries
the `revision_id`/`trip_revision` it was confirmed against. Existing reading
timestamps (`observed_at`/`received_at` on evidence records) were not changed
when these fields were added.

Visibility is as-of the evaluation time (see `context_as_of` in
`backend/aria_home/scenario.py`): a trip revision is only used once its
`known_at` is reached, a cancellation only once known, and a confirmation
only once `confirmed_at` is reached and it still matches the property, trip
and current revision. A materially changed revision (arrival or target
changed) makes an earlier confirmation outdated.

Variants:
- `demo_v1`: base scenario.
- `demo_recovery_v1`, `demo_no_followup_v1`: outcome variants.
- `demo_revised_v1`: synthetic variant where the arrival is revised at
  17:00, after the 14:30 confirmation, so that confirmation becomes outdated.
- `demo_cancelled_v1`: synthetic variant where the trip is cancelled at
  17:00, after the 14:30 confirmation.
- `demo_video_v1`: synthetic video scenario with a thermostat outage
  (15:30-18:20), a continuing `room_sensor.json` stream, and
  `thermostat.json`/`electrical.json` streams generated deterministically by
  `demo_video_v1/generate_streams.py`.
