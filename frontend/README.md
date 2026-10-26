# ARIA Home — Frontend (Day 1, Task 3)

Vite + React + TypeScript evidence strip. It reads `GET /api/health` and
`GET /api/sources` (typed helpers in `src/api.ts`) and renders four source
cards. It contains no API keys and no provider settings.

## Run the frontend

From `frontend/`:

```
npm ci
npm run dev
```

The dev server proxies `/api` to `http://127.0.0.1:5000`, so start the
backend first (see root README "Setup and run").

Also from `frontend/`:

```
npm run build
npm run typecheck
npm run test:e2e
```
