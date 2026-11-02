ARIA Home: the recorded answers must use this story's words. Approved by Brad. DO THE WORK NOW in this turn. IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; keep editing and running commands until the done-condition holds. No live calls, no paid calls, no installs, no git, no network beyond 127.0.0.1. Do not weaken any test without replacing what it proved. Never edit backend/eval/ or backend/scenarios/. Do not edit docs other than what the runner writes itself. Shell starts in C:\aria-home. Use the Bash tool for every command, one per call, no pipes: `cd backend && python -m pytest -q`, `cd frontend && npm run typecheck`, `cd frontend && npm run build`, `cd frontend && npm run test:e2e`, `cd frontend && npm run test:e2e:public-demo`, `cd frontend && npm run test:e2e:alt-ports`. You cannot run other Python scripts in this session, so do not write any that you need to run.

Measured this morning on commit 8b76856 with real Muse Spark calls on care_home_v1. All numbers were correct, and the review found no issues, but the words are from another story. This story is a family caregiver and a resident's home with a warm-by time. There is no property manager and no trip.

At 23:30 the model wrote: "With homeowner notification requested and manager authorization present, manager review with homeowner notification appears to be the appropriate response path."
At 07:01 the model wrote: "Evaluation time is after the planned arrival, so the computed readiness reflects the arrival outcome". Code rendered the verified fact: "Indoor temperature at arrival 68.2 F (at 06:55)".

Causes I traced. Check them yourself:
- backend/aria_home/investigator.py, the evidence pack: `confirmation` carries raw `manager_authorized` and `notify_homeowner`, and nothing tells the model who responds. SYSTEM_PROMPT asks "who should respond?" without giving an answer.
- SYSTEM_PROMPT line for temperature_at_arrival says "planned arrival". The field and enum names contain "arrival" and "trip".
- investigator.py near line 745 renders "Indoor temperature at arrival".
- readiness.py lines 458 to 462 say "Arrival has passed" and "at arrival time". notifications.py line 37 says "at arrival". provider.py lines 261 and 262 say "planned arrival time" in the mock.

The change:
1. Add a responder to the evidence pack, derived in code from the scenario: for care_home_v1, the family caregiver, and the person living in the home is the resident. Scenarios that really have a property manager keep their own responder and their own words, so demo_recovery_v1 must still say manager. Do not change the fixtures. Keep `manager_authorized` in the data contract; only what the model is told and what is shown changes.
2. SYSTEM_PROMPT: bump to inv-v5. Tell the model to name the responder only as the pack's responder says, and to write "warm-by time" in prose. Tell it that field names containing arrival, trip or manager are internal names and never belong in prose. Keep `temperature_at_arrival`, `arrival_passed` and the JSON schema exactly as they are. Update the sentence in evaluation.py that describes the prompt versions; published scores stay marked as they are.
3. Code-rendered sentences a viewer reads say warm-by time: "Indoor temperature at the warm-by time 68.2 F (at 06:55)", and the readiness and notification sentences listed above. Search backend/aria_home and frontend/src for other viewer-facing "arrival" text shown in the care story and fix it the same way. Leave internal identifiers, rejection reasons and the existing demo_recovery_v1 labels alone.
4. A mechanical gate, in the same validation path as CERTAINTY_PHRASES: for care_home_v1 only, reject an answer whose model-written prose (interpretation, hypotheses, unknowns, clarification, follow-up observation, limitations) contains the word "manager" or the phrase "planned arrival". The other scenarios are unaffected.

Tests, in the existing test files where they fit:
- the care pack names the family caregiver, and a manager scenario's pack does not
- the rendered at-warm-by-time sentence
- the gate rejects each of the two wordings for care_home_v1, accepts the same prose for demo_recovery_v1, and accepts clean care prose
Red-proof the gate: remove it, watch its test fail with an assertion, restore it, and say so in your final message. Finish the restore with an edit, then rerun that test.

The stored input revision must not change because of the pack addition if it can be kept out of the hash the same way other non-record fields are. If it does change, say so plainly and do not work around it; the night is being re-recorded anyway.

If a test fails only because a generated doc such as docs/evaluation.md needs regenerating, do not edit the doc and do not touch the test. Name it in your final message and the operator will regenerate it.

Done means: all six commands pass, and your final message lists every file changed, the red-proof, the exact pass counts, whether input revision changed, and anything you noticed that could still read wrong to a judge.

