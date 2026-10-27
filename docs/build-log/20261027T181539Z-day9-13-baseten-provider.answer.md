Model: muse-wonder-1.0
Turns: 30

Files:
- `backend/aria_home/provider.py` — `BasetenProvider`/`BasetenConfig` (Baseten `https://inference.baseten.co/v1/chat/completions`, `BASETEN_API_KEY`, `ARIA_HOME_BASETEN_MODEL_ID` default `meta-models/muse-spark-open-1026`, `ARIA_HOME_BASETEN_ENABLED=1`, reasoning separated, `no_text` on empty final answer, `auth` on 403, `timeout`, no key in errors/logs)
- `backend/aria_home/evaluation.py` — `--live --provider baseten --max-calls N` gated on `ARIA_HOME_BASETEN_ENABLED=1`, writes `backend/eval/results-live-baseten.json`; runtime `get_provider` unchanged (Meta/Mock only)
- `backend/tests/test_baseten_provider.py` — mocked-httpx, socket-blocked tests: success/tokens, reasoning-only `no_text`, 403 `auth`, timeout, key secrecy, CLI refusal, runtime never selects Baseten
- `.env.example` — documents `BASETEN_API_KEY`, `ARIA_HOME_BASETEN_MODEL_ID`, `ARIA_HOME_BASETEN_ENABLED`
- `README.md` — one line in "How Meta models are used" on Muse Spark Open via Baseten, evaluation only

Real final pytest line:
```
289 passed in 18.14s
```
