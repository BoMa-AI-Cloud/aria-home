Model: muse-spark-1.3
Turns: 13

Changes in `backend/aria_home/investigator.py`:
- `INVESTIGATION_MAX_TOKENS_DEFAULT` 8000 → 12000 (bounds unchanged)
- New `_round_2sig` / `_round_float` / `_round_pack`; `build_evidence_pack` returns `_round_pack(pack)` — every float to 1 decimal, except `*rate*`/`*coverage*` keys that would round to 0.0 while non-zero go to 2 significant figures (0.03428… → 0.034)
- `validate` number check is now exact (`val == a`) against the rounded pack, so `-15.9` passes and `-15.899999999999999` is rejected

`.env.example`: max-tokens comment default 8000 → 12000.

Updated expectations in `backend/tests/test_investigator.py` (8000 → 12000):
- `test_valid_output_passes`, `test_investigation_max_tokens_default_and_recorded`, `test_investigation_max_tokens_invalid_falls_back_with_note`, `test_no_text_max_tokens_explicit_reason`

New tests: `test_pack_floats_rounded_for_display` (gap −15.9, rate 0.034, ≥0.05 floats are 1-decimal), `test_rounded_numbers_validate` (accepts −15.9, rejects −15.899999999999999).

Final pytest line:
`105 passed in 1.19s`

