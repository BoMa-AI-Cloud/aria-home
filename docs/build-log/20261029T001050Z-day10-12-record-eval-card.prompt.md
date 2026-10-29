ARIA Home, small recording-tooling fix (approved by Brad). DO THE WORK NOW in this turn. IMPORTANT: a message
without a tool call ends your turn, so never write a status or plan sentence on its own; keep editing and running
commands until the done-condition holds. No live calls, no installs, no git, NO helper scripts. Shell starts in
C:\aria-home; prefix frontend commands with `cd frontend && `. Do not end your turn until
`cd frontend && npm run record:demo` exits 0 with every clip passing, and `cd frontend && npm run test:e2e` passes.

`npm run record:demo` fails at `[chrome] recording/demo.record.ts c2-evaluation`: it asserts getByText('12/12'),
but the offline evaluation now has 17 cases (combined 17/17), so the evaluation card correctly shows the new
totals. Update the recording's assertions to the totals the card renders from the current offline results (read
them from backend/eval/results-offline.json or the card's own data, never hard-code a number that is not in that
file). Check frontend/cards.html and src/cards.ts render the current totals and wording (17 cases, 9 scenarios,
both live runs cited as in docs/evaluation.md); fix any stale text there too. Then run record:demo to the end so
the insets and keys projects also record.
Final answer: files changed and the REAL output lines.

