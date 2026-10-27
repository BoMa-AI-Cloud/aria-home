ARIA Home, video tooling (approved by Brad): "key line" close-ups. No product behaviour change. DO THE
WORK NOW in this turn. No live calls, no installs, no network beyond 127.0.0.1, no git, NO helper
scripts. Shell starts in C:\aria-home: prefix frontend commands with `cd frontend && `. Do not end
your turn until `cd frontend && npm run record:keys` and `cd frontend && npm run test:e2e` pass.

Read: frontend/src/App.tsx (the test-only ?inset view and insetClass), frontend/src/index.css,
frontend/recording/insets.record.ts, frontend/playwright.record.config.ts, frontend/package.json.

BUILD a test-only ?key=<name> view (no effect without the parameter) that renders ONE real element
from the live page, unchanged in content, large (about 40-56 px text), centred on a plain light
background in a 1280x360 viewport (deviceScaleFactor 2), with a small grey caption line under it
naming the replay time in ET. Keys and the real element each shows (from the video scenario):
k-plan (09:20): the confirmed plan rows "Target temperature 68 F", "Manager coordination allowed",
  "Confirmed 9:20 AM ET";
k-trip (09:20): the "Flight confirmation email" card title with its SIMULATED tag and available time;
k-location (14:06): "Location unavailable" card title with SIMULATED tag;
k-at-risk (16:31): the readiness line "Readiness: At risk. Indoor 52 F, target 68 F." and the
  reason "thermostat telemetry missing; room sensor used";
k-help (16:52): the HVAC company card title, its state "Simulated delivery" and its "fields sent:" line;
k-ack (16:52): the manager card's "Acknowledged, not resolved" line (after the simulated ack);
k-restored (18:21), k-warming (18:51), k-not-yet (19:51), k-verified (20:21), k-arrival (21:01): the
  Outcome "Status: ..." line plus the "Latest reading used" line;
k-report (20:46): the HVAC completion report card title and "Corroboration only, does not set the outcome";
k-home (21:01): "Your home reached and held 68 F before you arrived".
Add frontend/recording/keys.record.ts and npm script "record:keys" (output frontend/recordings-keys,
git-ignored), one 6 s clip per key, each asserting its text. Add one e2e test that without ?key the
page renders normally. Final answer: files, clip names, REAL output lines.

