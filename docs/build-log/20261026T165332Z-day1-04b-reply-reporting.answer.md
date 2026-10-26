Model: muse-spark-1.3
Turns: 9

Changed `backend/aria_home/provider.py`:

- `ProviderResult` gains `content_block_types: list[str] | None` and `stop_reason: str | None`; populated on every 2xx reply that parses as a JSON dict (success, `no_text`, `bad_response`, `model_mismatch`). Only block `type` strings are stored, never block contents, key, or headers.
- New `ErrorCategory` `"no_text"` for a well-formed non-empty `content` list with zero text blocks. Empty/missing/non-list `content` stays `"bad_response"`, so `test_malformed_shape` still passes.
- `input_tokens`/`output_tokens` now read from `usage` on failure paths too.

Added to `backend/tests/test_provider.py`: `test_no_text_thinking_only` (thinking-only + `stop_reason: max_tokens` → `no_text`, types `["thinking"]`, usage filled) and `test_thinking_plus_text_returns_text_only` (types `["thinking","text"]`, text is only the text block).

Test output (`python -m pytest -q` from `C:\aria-home\backend`):

```
...................................................                      [100%]
51 passed in 0.95s
```

