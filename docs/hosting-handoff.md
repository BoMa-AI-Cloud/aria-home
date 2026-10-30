# Hosting handoff (proposal, not deployed)

Written 2026-10-29 by the operator for Brad's approval. Nothing here has been deployed. The README's hosted link stays
"Pending deployment" until a deployment is approved, done, and tested in a clean browser (release process stages
11-15).

## What runs

One process: the Flask app in public-demo mode (`ARIA_HOME_PUBLIC_DEMO=1`) serving the built frontend and the
restricted API. It refuses to start if any live flag is set. Per-visitor state lives in temporary SQLite files that are
deleted after two hours idle, so the host needs no database and no persistent disk. No model, WhatsApp, Emporia or Nest
credentials are given to the host.

## Options

Facts below are from the providers' public documentation as read on 2026-10-29; check them again before choosing.

| Option | Cost | Behaviour during judging | Account work for Brad |
|---|---|---|---|
| Render, free web service | $0 | Spins down after 15 minutes without traffic; the next visit waits for a cold start (third-party reports say roughly 30-60 s; Render does not publish a figure); 750 free instance hours a month; may restart at any time | Render account, connect the GitHub repo |
| Render, paid Starter instance | paid monthly (check Render's current price) | Stays running; no cold start | Render account with a card, connect the repo |
| Hugging Face Spaces, Docker, free CPU | $0 | Free hardware sleeps after a period without use (a library reference says 48 hours); community reports of occasional slow or stuck restarts | Hugging Face account, a Space, a Dockerfile |

## Recommendation

Render's paid Starter instance for the judging period only, then downgrade or delete. A judge who waits 30-60 s on a
cold start may leave; the paid tier removes that, and one service avoids a split frontend/backend. If Brad prefers $0,
Render free is the fallback, with the README noting that the first load can take up to a minute.

## Exposure and data

- Public: the synthetic demo only. No real household data, no credentials, no real messages or sensors.
- Retained: per-visitor temporary state for at most two hours idle; host request logs as the provider keeps them.
- Not built for real deployments: authentication, authorization, tenant isolation, quotas and retention controls (see
  SECURITY.md).

## Steps after approval

1. Brad creates the account and approves connecting the GitHub repository.
2. Build command `cd frontend && npm ci && npm run build`; start command runs the backend in public-demo mode with debug
   off and ARIA_HOME_RELEASE_COMMIT set to the deployed commit.
3. Verify: /api/health returns 200 and the deployed commit; a clean browser outside this laptop completes the guided
   story; two browsers stay isolated; no request leaves for Meta, WhatsApp, Emporia or Google.
4. Overnight check (health plus one guided story) before marking it verified; then put the URL in the README.
5. Rollback: redeploy the previous commit from the provider's dashboard, or suspend the service.

## Exact approval needed

"Approve deploying commit <sha> to <provider and tier>, public, synthetic demo only."
