# Who wrote the code

Measured with `python backend/scripts/measure_code_authorship.py <ref>`, which uses `git blame` to trace each line of code to the commit that wrote it. Commits after 8a94f53 that do not say a Muse model wrote them count as Claude's. Everything else counts as Meta's models (Muse models and the Meta AI web chat).

Measured on commit d8344eb:

| Code | Lines | Meta's models | Claude |
|---|---:|---:|---:|
| Application (`backend/aria_home`, `frontend/src`) | 20,823 | 95.8% | 4.2% |
| Tests (`backend/tests`, `frontend/e2e`) | 18,185 | 91.6% | 8.4% |
| Scripts (`backend/scripts`) | 1,851 | 97.1% | 2.9% |
| All code | 40,859 | 94.0% | 6.0% |

Limits:

- Claude's figure is a minimum. Small operator edits inside earlier commits, listed in `docs/build-log/operator-log.md`, count as Meta's models because blame cannot separate them.
- This counts lines that survive, not effort. Claude also wrote the prompts, reviewed, ran tests and committed, as the operator log records.
- Synthetic fixtures, recordings and docs are not code and are not counted. Claude generated the final night's fixtures with a script.
