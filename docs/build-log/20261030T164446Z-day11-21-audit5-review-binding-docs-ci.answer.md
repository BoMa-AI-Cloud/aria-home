Model: muse-spark-1.3
Turns: 162

Done. `cd backend && python -m pytest -q` passes: **651 passed**.

## Finding 5 — review bound to its exact answer

**Failing line before the fix:** `tests/test_audit5_review_binding.py:154: AssertionError: assert {'issues': [], 'verdict': 'no_issues'} is None` — a copied care answer with only its interpretation changed to another schema-valid sentence still showed the original `no_issues` review.

**Repair:**
- `backend/aria_home/review.py` — `answer_digest()` (sha256 of canonical JSON: sorted keys, no whitespace); `recorded_review_for()` takes `answer_output`, requires digest equality, mismatch returns no review + "review does not match this answer"; entries without a digest return flagged `answer_bound False`, never fabricated.
- `backend/aria_home/app.py` — serving resolves the displayed answer's output and passes it for the digest check.
- `backend/scripts/record_care_answers.py` — new reviews record `answer_digest` + reviewed prompt/readiness-policy versions; `--only-missing` treats unbound reviews as missing.
- `frontend/src/api.ts`, `frontend/src/App.tsx` — binding fields; RecordedReviewBlock shows "Review recorded before answer binding (legacy, not bound to this exact answer)", the mismatch line, and "a matching review is a bounded check, not proof the narrative is true"; model-matrix status updated.

**Tests added:** `backend/tests/test_audit5_review_binding.py` (7: digest contract, bound shown, tampered unit + app-level repro, legacy label, `--only-missing` dry-run, README↔`/api/scenarios` count); `backend/tests/test_secret_scan.py` (4: `git ls-files` walk, binary skip, token shapes, FAKE/MARKER-only allowlist, red-proof); `frontend/e2e/public-demo.spec.ts` +1 ("completion report arrives after verification and ack changes no outcome": absent at 06:21, present at 06:45 as "Corroboration only, does not set the outcome", Outcome headline identical across ack).

**Docs/CI:** README (8 scenarios, deduped heading + results sentence, Emporia + owner-only Nest as the two optional real-data paths, recorder binding, digest-match wording, stale Wonder text removed); `docs/evaluation.md` (legacy-review section, transcription placeholder split); SECURITY.md (synthetic public-demo exception, all three opt-ins); `docs/audit-5.md` (new finding-5 section, row 5 repaired, rows 7–8 executed); `docs/build-log/README.md` (day11-20 row, fixes the process-law failure); `.github/workflows/ci.yml` (public-demo e2e step, audits fail with why-comment). Temp debug files deleted. Committed recordings untouched.

**REAL pytest line:** `651 passed in 134.00s` (full suite); targeted `18 passed`.
