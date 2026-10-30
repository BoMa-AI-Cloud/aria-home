ARIA Home: the public-demo session disk bound is too low for judging day (approved by Brad, 2026-10-30). DO THE WORK NOW in this turn. IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; keep editing and running commands until the done-condition holds. No live calls, no installs, no git, no network beyond 127.0.0.1. Do not weaken any test. Keep all working-tree changes; never edit backend/eval/. Shell starts in C:\aria-home. Run `cd backend && python -m pytest -q` exactly (one per call, no pipes); do not end your turn until it passes.

Real measurement from the operator (Gate A probe on 247cdb5): each public session that runs one investigation stores about 0.73 MB, and admission stopped at the 64 MiB disk bound (MAX_SESSION_BYTES in backend/aria_home/public_demo.py) after 93 sessions: 93 x 200, then 409 x 503. So about 90 visitors in any 2-hour window would fill it, far below the 500-session cap, and a burst of judges would see 503.

Change:
1. MAX_SESSION_BYTES default 512 MiB (so the 500-session cap is the binding limit at about 0.73 MB each), overridable with ARIA_HOME_PUBLIC_DEMO_MAX_BYTES (a positive integer of bytes; invalid or empty values fall back to the default, never to unlimited). Document it in .env.example and the README public-demo section, and mention it in docs/audit-5.md row 3 (the bound and why).
2. Keep everything else about admission unchanged (server-issued ids, expiry before touch, no eviction, 503 with nothing allocated when full).
3. Tests: the default is 512 MiB; the env override works; invalid values fall back to the default; the existing admission tests still pass (they may set a small bound through the env to stay fast).
Final answer: files changed, tests added, and the REAL pytest line.

