You are writing code for ARIA Home, my Meta hackathon project (React + TypeScript frontend, Flask backend). The Muse API sessions that were writing the code stopped on a billing error, so you are finishing the work. The attached file is frontend/src/App.tsx from the integration branch, with merge conflict markers in it. I cannot run anything through you, so my operator will apply your edits and run the tests.

THE PRODUCT RULES
- After the caregiver DECLINES, nobody is contacted: no HVAC request, no technician, no completion report. The furnace stays out, the room stays cold, the goal is never verified, and at 07:00 the warm-by expectation is MISSED. A decline never stops independent checking; the readings alone decide.
- With no answer, the recorded story authorizes HVAC contact at the 02:45 step.
- A decision recorded later than the replay time must not change earlier steps.
- Plain English for a family caregiver. Never imply a background process: no "keeps monitoring", "continues to check", "continuously". The page is a synthetic replay.

TASK 1: resolve both conflicts in App.tsx.
The story has ten steps, index 0 to 9: 19:20, 21:00, 23:30, 02:31, 02:45, 04:21, 04:51, 06:21, 06:45, 07:01.
Conflict near line 1585. "ours" has storyStepTitle(index, choice) and storyStepGuidance(index, choice), which also give a waiting message at index 4 when she has neither approved nor declined. But "ours" contains false declined wording, for example "Verification continues from independent room and thermostat" readings that imply recovery. "theirs" has the correct declined tables DECLINED_STORY_STEP_TITLES and DECLINED_STORY_STEP_GUIDANCE.
Conflict near line 3635. "theirs" computes declinedAtThisStep correctly from decided_at and the replay time, and builds the 07:01 missed sentence from the real room reading. "ours" has only the two simple calls.
Combine them so that: declinedAtThisStep decides the declined text, using the correct tables and the computed 07:01 sentence; otherwise index 4 with no decision visible still shows "Waiting on the caregiver — no HVAC contact yet" and its guidance; otherwise the normal tables. Remove any function or constant left unused, because the typecheck fails on unused imports only if they are imports, but keep the code clean. Reword anything that implies a background process. "theirs" guidance at index 4 says "Readings keep being evaluated on their own." and index 7 says "Checking continues from readings." Replace these with plain statements of what the readings show at that step.

TASK 2: make the watcher "Corrections" list readable. Find the corrections list near the text `Original:{" "}` and `Failed checks:`. Today each record is one dense paragraph with raw evidence ids and a UTC time. Render each record as short labelled lines:
- When: the time in ET, using the app's existing ET time formatter (find it in this file)
- What the watcher first said: the original claim
- What code rejected: the failed checks
- What it revised to: the revision
- Final status: the final result
Keep the full raw text available inside the existing <details> pattern, labelled "Raw record". Keep the sentence saying the ledger is shown to the model as in-context examples and the model is not retrained, but show it once under the list, not once per record. Do not change what is stored or what the API returns.

HOW TO ANSWER
Give only exact edits, as a list, in this format, with no other prose between them:

FILE: frontend/src/App.tsx
FIND (exact text, copied character for character, long enough to be unique):
```
...
```
REPLACE WITH:
```
...
```

For the conflicts, FIND must run from the <<<<<<< line through the >>>>>>> line. Do not rewrite anything else in the file. If anything is unclear or you cannot read the whole file, say so first. At the end, list any existing test you expect these edits to affect.
