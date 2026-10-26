ARIA Home, Day 7 task D7-3 (approved by Brad): the user-test kit and the feature freeze. Docs
only: create docs/usability.md and docs/freeze.md, and add one line each to README.md and
docs/timeline.md. No code changes, no live calls, no installs, no network, no git, NO helper
scripts. DO THE WORK NOW in this turn.

Read: README.md, docs/demo-script.md, docs/day6-handoff.md, frontend/src/App.tsx (labels only).

docs/usability.md, a kit Brad runs himself with 3 to 5 people (homeowners, renters or property
managers; no minors; no personal data recorded):
- Consent script (one paragraph): synthetic demo, no recording unless they agree, they can stop.
- Setup: run backend and frontend per README with ARIA_HOME_MODEL_ENABLED=0 and a fresh database
  (delete backend/instance/aria_home.db first).
- Five tasks, each with what the participant is asked, what success looks like, and what to note:
  1) "Will this home be ready when you arrive?" on No recovery at 18:00;
  2) "Who was told, and what were they told?" on the video scenario at 16:52;
  3) "Did the manager's acknowledgement fix it?" after acknowledging;
  4) "Is the home warm? How do you know?" at 20:21, and why 19:51 is not yet verified;
  5) "What did the repair report change?" at 20:46.
- Questions after: one 1-5 trust rating with a why, what was confusing, what they would act on.
- A results table to fill in (participant id P1..P5, role, task 1-5 pass/partial/fail, rating,
  quotes), with a note: "Leave blank until sessions happen. Do not fill with predicted results."
docs/freeze.md: feature freeze from 2026-10-26 (local). Allowed after the freeze: bug fixes,
accessibility and wording fixes found in user tests, docs, the video, setup and submission.
Not allowed: new features, sources, providers or integrations. List what is in scope as of commit
<the latest commit in the build log, D7-2>, and the known limits from the day handoffs.
Final answer: the files changed.

