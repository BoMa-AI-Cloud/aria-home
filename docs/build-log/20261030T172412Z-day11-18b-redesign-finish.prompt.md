ARIA Home: finish the three-page redesign (approved by Brad, 2026-10-30). The first pass (day11-18) built the new frame, the landing page, the House verdict, the four glance tiles, "Who knows" and the Integrations page well. It left the old page underneath, so the House page is still a long stack of old boxed cards and Reasoning is an 11,600 px dump. DO THE WORK NOW in this turn. IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; keep editing and running commands until the done-condition holds. No live calls, no installs, no git, no network beyond 127.0.0.1. Keep every behaviour, route, safeguard and disclosure. Do not weaken any test: update a locator only when an element really moved, never an assertion. Keep all working-tree changes. Shell starts in C:\aria-home; prefix frontend commands with `cd frontend && `. Do not end your turn until `cd backend && python -m pytest -q`, `cd frontend && npm run typecheck`, `cd frontend && npm run build`, `cd frontend && npm run test:e2e` and `cd frontend && npm run test:e2e:public-demo` pass.

What the operator saw on a 1280 px full-page screenshot of the guided story at 02:31 (public mode):

HOUSE, remove the duplicates and old chrome:
1. The old grey banner "SYNTHETIC DATA - demo scenario, not a real home (data mode: synthetic)" sits under the disclosure strip. Remove it; the strip already says this. Keep the data-mode signal as a small part of the status pill.
2. The old bold sans H1 question ("Will an older adult's home be warm by morning...") repeats above the verdict. Remove it from House; the question belongs on the landing page only. The verdict is the page's h1.
3. "Demo controls (synthetic replay)", with its scenario select and the 19:03...07:01 pill row, duplicates the header's Back / time / Next stepper. In public mode remove it from House. In normal mode move the scenario select and the full time row into a compact "Replay" control in the header (a dropdown or popover), not a separate box.
4. "The warm-by story" box sits between the verdict and the tiles and uses the old tiny buttons. Make it a slim caption under the lead: "Step 4 of 10" eyebrow, the step title, the guidance in one paragraph, and the new-style buttons (Back, Next, "See ARIA's view of this step") on one row. Drop its duplicated "Now showing", "Readiness" and "What was observed" lines; the verdict and tiles already show them.
5. After "Who knows", the page repeats everything as old boxed cards: "Confirmed plan and permissions", "Outcome" (with History), "Notifications (simulated delivery)" (three side-by-side cards), an empty "Homeowner update" heading, and "Simulated timeline". Fold them into the new style:
   - "Who knows" becomes the single place for notices: each row (caregiver, HVAC company, homeowner) opens on click to show its full simulated message (fields sent, refused fields, simulated-delivery line, Acknowledge for the caregiver). Delete the separate Notifications cards. Keep every data-testid and aria-label tests use, moved onto the rows.
   - "Outcome" becomes a hairline section "Recovery so far": the four stages as a short checklist (reporting restored, warming observed, goal verified, warm-by met) with reached/not yet, the latest reading line, and "History" collapsed by default.
   - "Confirmed plan and permissions" becomes a collapsed "The plan" row (property, warm-by time, target, notifications allowed, caregiver coordination, revision) at the bottom of House.
   - "Simulated timeline" moves to Reasoning.
   - Never render an empty heading (the empty "Homeowner update" heading appears now).
6. Bug, fix it: on the caregiver permission the request text says "(54 F, furnace quiet since 19:15)" at 02:31, while the lead correctly says 52 F and silent since 1:30. The text is built at the alert's created_at (7:20 PM on the 16th), not at the moment shown. Build the displayed text and the WhatsApp text from the replay time being shown, i.e. the moment ARIA asks. Add a backend test for 02:31 -> "52 F, furnace quiet since 01:30", and keep the text using evidence visible at that time only.

REASONING: make it readable:
7. ARIA's view map stays first, full width. Its long "Steps in order" list collapses by default behind "Show all N steps".
8. "Freshness, conflicts, units and Laws": show a one-line summary first ("27 checks: 24 passed, 2 failed, 1 not run"), the failed ones expanded, and the passed ones collapsed.
9. "Investigation": the model's answer reads as a short article (verified facts, readiness, interpretation clearly labelled "model-written, not verified", what we don't know), with "Possible explanations", "One question", "Next check" and "Power context" collapsed. The second review sits beside the answer as a compact verdict line (e.g. "Second review (muse-wonder-1.0, recorded): no issues found").
10. "Evidence sources": a compact table (source, status dot, latest reading, freshness), not one tall box per source.
11. Visual evidence: a smaller image (max 480 px wide) with its caption, not full width.
12. ARIA's Laws: a compact list, with the detail collapsed.
13. Section labels like the House page (small uppercase label + serif heading), hairlines between sections, no boxed cards around lists. Target: Reasoning at 1280 px under about 3,500 px tall with everything collapsed by default.

BOTH:
14. One button style across the app (the new plum primary, outlined secondary). Remove the old small grey buttons everywhere.
15. Tests: add a public-demo test that the House page at 02:31 has no element with the old banner text, exactly one h1, and no empty headings; that the permission text at 02:31 says "52 F" and "01:30"; that the Reasoning page height at 1280 px is under 4,000 px with sections collapsed; and keep the 375 px no-scroll and same-origin tests.
Final answer: files changed, and the REAL output lines of every command.

