Model: muse-spark-1.3
Turns: 51

Both failures are pre-existing drift from earlier tasks' in-flight working-tree changes, not from this fix. Wrapping up with the final report.

**Files changed**
- `backend/aria_home/watcher.py` — added `_messages_text()` (joins `type=="text"` blocks in order, ignores `thinking`/`redacted_thinking`) + `NO_TEXT_REASON = "no text block in reply (thinking only)"` + `_parse_watcher_text()`; `request_live_watcher` uses the helper and returns the clear reason instead of `no_text`; `run_watcher` reports the clear reason for empty/None text instead of `invalid JSON`; `_generate_text` also extracts from a raw `content`-block dict when `text` is absent.
- `backend/aria_home/review.py` — `_candidate_texts()` now skips `reasoning`/`thinking`/`redacted_thinking` items and blocks and reads only `text`/`output_text` blocks.
- `backend/aria_home/visual.py` — `extract_sam_text()` now skips `reasoning`/`thinking`/`redacted_thinking` items and blocks, joins `text`/`output_text` blocks in order.
- `backend/aria_home/provider.py` — `MetaProvider` now accepts `text`/`output_text` (was `text` only); `BasetenProvider` list-block parsing now skips `redacted_thinking` and only reads `text`/`output_text`-typed blocks (was taking any block with a `text` field).
- `backend/tests/test_thinking_blocks.py` — new, 8 tests.

**Readers fixed vs already correct**
- Fixed: `watcher.request_live_watcher` + `run_watcher`/`_generate_text`, `review._candidate_texts`, `visual.extract_sam_text`, `provider.BasetenProvider` list parsing (redacted_thinking leak), `provider.MetaProvider` (widened to text/output_text).
- Already correct: `investigator.py` (uses `provider.generate().text` only), `transcribe.py` (ASR shape, no content blocks), `scripts/record_care_watcher.py` + `scripts/record_care_answers.py` (pass through the fixed helpers, no direct block indexing).

**Tests added** (`test_thinking_blocks.py`, fakes built from the real 02:31 shape — first block `redacted_thinking`, second `text` with the observations JSON): watcher live skips redacted_thinking; thinking-only gives the clear reason via `request_live_watcher` and `run_watcher` (no `invalid JSON`); provider skips redacted_thinking; investigator end-to-end via live transport; review skips reasoning item + thinking blocks; visual skips thinking blocks; transcribe ignores extra reasoning keys; scripts `_LiveWatcherProvider` returns the text.

**REAL pytest line:** `cd backend && python -m pytest -q` → **671 passed, 2 failed**. The 2 failures are pre-existing and unrelated to this change (neither touches a file I edited): `test_committed_evaluation_docs_start_with_rendered_offline` (working-tree drift in `docs/evaluation.md` from an earlier task) and `test_build_log_tasks_have_prompts` (another task's untracked `20261030T185314Z-day11-22-record-care-watcher.prompt.md` not yet indexed in the build-log README). All watcher/provider/review/visual/transcribe/scripts tests pass, including the 8 new ones.
