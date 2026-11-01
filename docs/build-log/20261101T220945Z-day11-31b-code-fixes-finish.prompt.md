ARIA Home: finish job day11-31. Read <private-notes> for the items; its rules all still apply. DO THE WORK NOW in this turn. IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own. That is what ended your last run. Keep editing and running commands until the done-condition holds. Shell starts in C:\aria-home. Use the Bash tool for every command, one per call, no pipes, exactly as written in that prompt. Your own red-proof runs may use `cd frontend && npx playwright test ...`.

Your last run stopped straight after this message: "3b red-proof confirmed. Restoring." It did not restore.

1. Restore first. In `frontend/e2e/public-demo.spec.ts`, the `completion report arrives...` test still has your deliberate break, `.toBe(checkpoints[0])`, in its `.outcome-time` wait. Put back the correct checkpoint. Check that no other deliberate break remains in the spec, `frontend/src/App.tsx` or `frontend/src/api.ts`.

2. Regression to check in your fix. You removed the code that cleared `storyBusyRef` and `storyWaiting` on the stale-token path of `handleReplayTime`, in both `.then` and `.catch`. A non-story `handleReplayTime` (a time that is not a story checkpoint) or a scenario change can replace the token while a story step is loading. Nothing would then clear busy, so Next and Back could stay disabled for good. Write a browser test that does exactly this: hold a story step's request, trigger the replacing action through the UI, release, and assert that Next works again. If that UI action cannot be reached while a story step loads, say which control you checked and why, and still make busy impossible to leave set: busy is cleared whenever the step that set it ends, unless a newer story step now owns it. Red-proof if you change code.

3. Item 3 decisions. You changed tests to wait for `.outcome-time`, but you never stated the decision the prompt asks for. For `rapid step changes...` and `completion report...`: can a visitor see `Status: Unable to verify` as a settled-looking state while the step is still loading? Check what the page shows during that time. If yes, fix the app so it shows a loading state, and assert that. For `ARIA's view shows failed checks...`: you ran it and it passed, so state what `Loading ARIA's view…` was waiting on and whether a real condition can leave it stuck, and fix it if so.

4. `window.__ariaStepTimeoutMs` is accepted in every build. It only changes the visitor's own browser, so leave it, but state in your final answer that it exists and why it is harmless.

Done-condition: all six commands pass, and then `cd frontend && npm run test:e2e:public-demo` and `cd frontend && npm run test:e2e` each pass a second full time in a row. Any failure in those runs means the item is not done.

Final answer: per item from both prompts, the cause, the fix (files), the red-proof's failing line, your decisions for item 3, and the REAL output line of every command, including every failed run.

