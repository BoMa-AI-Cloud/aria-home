ARIA Home, Day 9 task D9-3 (approved by Brad; allowed under docs/freeze.md as accessibility fixes):
an accessibility pass on the app page. No new features. DO THE WORK NOW in this turn. No live calls,
no installs (no axe or other new packages), no network, no git, NO helper scripts. Shell starts in
C:\aria-home: prefix frontend commands with `cd frontend && `. Do not end your turn until
`cd frontend && npm run typecheck`, `npm run build`, `npm run test:e2e` and `npm run record:demo` pass.

Read: frontend/src/App.tsx, frontend/src/index.css, frontend/index.html, frontend/e2e/app.spec.ts.

CHECK AND FIX (by reading the code; report each item as fixed / already fine / not fixed):
1. One <h1>, then a logical h2/h3 order; landmarks (<main>, the demo controls as a labelled region
   distinct from the product).
2. Every button and select has an accessible name; replay buttons say what they do (aria-label like
   "Replay to 18:21") while keeping the visible time text.
3. Status changes (Outcome headline, notifications) are announced: aria-live="polite" on the outcome
   headline and on the notification list.
4. Colour is never the only signal (statuses already have words; check the progression list and
   refused cards).
5. Text contrast at least 4.5:1 for body text and 3:1 for large text and UI borders: compute the
   ratios for the CSS colour pairs actually used and fix any that fail; list the pairs and ratios.
6. Visible keyboard focus on every interactive element (:focus-visible outline); tab order follows
   the page.
7. html lang="en"; page <title> stays "ARIA Home — Evidence".
E2E: add one keyboard test: Tab to the scenario select, choose the video scenario with the keyboard,
Tab to the "Replay to 21:01" button and press Enter, and see "Arrival expectation met". Keep all
existing assertions. Final answer: the checklist with outcomes, the contrast table, REAL output lines.

