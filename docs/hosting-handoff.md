# Hosting handoff (decision recorded, not yet deployed)

Written 2026-10-29 by the operator for Brad's approval. Decision 2026-10-30: Brad approved the Render paid Starter
("we will do the render paid starter"). Nothing here has been deployed yet. The README's hosted link stays
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

Decision 2026-10-30: Brad approved the paid Starter ("we will do the render paid starter").

## Exposure and data

- Public: the synthetic demo only. No real household data, no credentials, no real messages or sensors.
- Retained: per-visitor temporary state for at most two hours idle; host request logs as the provider keeps them.
- Not built for real deployments: authentication, authorization, tenant isolation, quotas and retention controls (see
  SECURITY.md).

## Deploy (Render paid Starter, approved 2026-10-30)

1. Brad creates the Render account (with a card) and approves connecting the GitHub repository.
2. Create the web service from the `render.yaml` blueprint at the repo root (service `aria-home-demo`, Python runtime,
   Starter plan, Ohio region, branch `main`, `autoDeploy: false`). The blueprint's build command installs
   `backend/requirements.lock` (which pins `waitress`, the production WSGI server), builds the frontend, and writes
   `$RENDER_GIT_COMMIT` to `backend/RELEASE_COMMIT`; the start command serves the created app with waitress on `$PORT`.
   Deploy by triggering the approved commit from the Render dashboard — never by pushing to `main` alone.
3. Verify: `GET /api/health` at the public URL returns 200 with `version.commit` equal to the deployed commit
   (source `file`); a clean browser outside this laptop completes the guided story; two browsers stay isolated;
   no request leaves for Meta, WhatsApp, Emporia or Google.
4. Overnight check (health plus one guided story) before marking it verified; then put the URL in the README.
5. Rollback: redeploy the previous commit from the Render dashboard (deploys list), or suspend the service. Because
   `autoDeploy` is off, rolling back is one dashboard action and no push can re-deploy by accident.

## Exact approval needed

"Approve deploying commit <sha> to <provider and tier>, public, synthetic demo only."
