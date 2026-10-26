ARIA Home: finish the browser test (approved by Brad). Do not expand scope. Work only inside
C:\aria-home. No installs, no network, no git. @playwright/test 1.64.1 is now installed in
frontend/ (the earlier stray install at the repo root was removed).

PROBLEM: `npm run test:e2e` from frontend/ fails with "Timed out waiting 60000ms from
config.webServer". The backend web server starts and /api/health returns 200; the frontend dev
server never answers at http://127.0.0.1:5173 (Vite listens on localhost by default, which may
resolve to ::1).

FIX in frontend/playwright.config.ts only: make the frontend webServer command bind explicitly,
`npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`, keep its url
http://127.0.0.1:5173, and set use.baseURL to the same. Keep everything else.

Your shell starts in C:\aria-home, so prefix commands with `cd frontend && `.
RUN: `cd frontend && npm run test:e2e` until green, then `cd frontend && npm run build`.
Final answer: the change and the REAL test output.

