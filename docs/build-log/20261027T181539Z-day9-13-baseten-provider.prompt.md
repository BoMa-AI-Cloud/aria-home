ARIA Home, task D9-13 (approved by Brad; a scoped exception to docs/freeze.md for evaluation): a
second Meta-model provider, used only by the evaluation harness. DO THE WORK NOW in this turn; do not
stop after a plan. No live calls, no installs, no network in tests, no git, NO helper scripts. Do not
end your turn until `cd backend && python -m pytest -q` passes.

Read: backend/aria_home/provider.py, investigator.py, evaluation.py, .env.example, README.md,
docs/evaluation.md, backend/requirements.txt (httpx is already there).

Facts (from Baseten's hackathon onboarding, relayed by Brad): base URL https://inference.baseten.co/v1,
OpenAI-compatible POST /chat/completions with header Authorization: Bearer <key>, the only allowed
model is meta-models/muse-spark-open-1026 (a Meta open-weight model); it always reasons first, so a
small max_tokens returns an empty answer; about 500+ tokens are needed for a short reply.

BUILD:
1. provider.py: a BasetenProvider (same interface and result fields as MetaProvider: ok, mode "live",
   requested/answered model, text, latency, tokens, error category, stop/finish reason). Config:
   BASETEN_API_KEY (env only), ARIA_HOME_BASETEN_MODEL_ID (default meta-models/muse-spark-open-1026),
   ARIA_HOME_BASETEN_ENABLED (must be "1"), timeout and max tokens as for the Meta provider, no
   retries. Separate reasoning content from the final answer if the response carries it; empty final
   answer is an explicit "no_text" error. Never log the key.
2. The app's runtime provider stays the Meta Model API; BasetenProvider is selectable ONLY from the
   evaluation CLI: `python -m aria_home.evaluation --live --provider baseten --max-calls N` (requires
   ARIA_HOME_BASETEN_ENABLED=1 plus --live and --max-calls, otherwise refuses). Results go to
   backend/eval/results-live-baseten.json.
3. .env.example documents the three variables; README "How Meta models are used" adds one line that
   the evaluation can also run Muse Spark Open (meta-models/muse-spark-open-1026, a Meta open-weight
   model) through Baseten's hosted API, evaluation only.
TESTS (httpx mocked; socket blocked): success parses text and tokens; reasoning-only response gives
no_text; 403 gives an auth/permission error category; timeout category; key never appears in any
error string or log; the CLI refuses without the enable flag; the app runtime never selects Baseten.
Final answer: files and the REAL final pytest line.

