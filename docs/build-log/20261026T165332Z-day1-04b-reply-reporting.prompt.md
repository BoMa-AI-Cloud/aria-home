ARIA Home, small fix (approved by Brad). Work only inside C:\aria-home. No installs, no network,
no git. Read backend/aria_home/provider.py and backend/tests/test_provider.py first.

PROBLEM: a live call to muse-spark-1.3 with max_tokens=16 returned HTTP 2xx with model
"muse-spark-1.3" but no "text" content block, so MetaProvider returned error "bad_response" and
threw the reply's shape away. We could not see why.

CHANGE (keep everything else as is):
1. Add to ProviderResult: `content_block_types: list[str] | None` (the "type" of each content
   block in the reply, in order, e.g. ["thinking", "text"]) and `stop_reason: str | None`.
   Fill them on every live reply that parsed as JSON, success or failure. Never store block
   contents other than final text, and never the key or headers.
2. When the reply has no text block, use a NEW error category "no_text" (not "bad_response");
   keep "bad_response" for unparseable or malformed bodies. Add "no_text" to the ErrorCategory.
3. Read input/output token usage on failures too when the body has a usage object.
4. Tests (mocked with httpx.MockTransport, no network): (a) reply with only a thinking block and
   stop_reason "max_tokens" -> ok False, error "no_text", content_block_types ["thinking"],
   stop_reason "max_tokens", usage filled; (b) reply with thinking + text -> ok True, text is only
   the text block, content_block_types ["thinking","text"]; (c) existing tests still pass.

Run from C:\aria-home\backend: python -m pytest -q
Final answer: what changed and the REAL test output.

