Model: muse-spark-1.3
Turns: 45

Done. Both gates pass.

**Files changed**
- `backend/aria_home/public_demo.py` — new `admit_session()` owns admission: unknown cookie treated as absent (new id issued, nothing created under the client id), expiry checked before any touch, cap + 64 MiB `MAX_SESSION_BYTES` enforced after sweeping expired (LRU evict only sessions idle beyond `SESSION_ACTIVE_GRACE_S` = 5 min; else busy), lock-guarded for concurrent admissions
- `backend/aria_home/app.py` — `_public_guard` uses `admit_session` (503 at capacity, nothing allocated); ack endpoint validates the public checkpoint before `record_ack`; caregiver-decision lookup only for string input
- `docs/audit-5.md` — rows 3, 4, 7 filled (repro, repair, regression, limitation)
- `docs/build-log/README.md` — indexed the two unlisted day11-18/day11-19 prompt files (pre-existing `test_build_log_tasks_have_prompts` failure, unrelated to this fix)

**Tests added**: `backend/tests/test_audit5_sessions_admission.py` — 13 tests: forged-cookie cap, expired-cookie re-issue, forged-id file check, full-cap 503, concurrent admissions, off-checkpoint ack dump-compare, checkpoint ack idempotency, rejected decision/investigation/whatsapp dump-compares, private whatsapp 409 dump-compare, decision/ack typed validation (both modes)

**Failing lines before the fix**
- Finding 3: `test_audit5_sessions_admission.py:98` (`assert 520 <= 500`), `:114` (expired cookie not re-issued, via `:58`), `:126` (forged-id file created), `:141` (`assert 200 == 503`), `:166` (`assert 560 <= 500`); code at `app.py:1132-1139`, `public_demo.py:140`
- Finding 4: `test_audit5_sessions_admission.py:179` (dump diff showed stored `ack-5aa827a8a33a` on a 400); write at `app.py:1097` ran before the checkpoint check at `:1104`
- Finding 7: `test_audit5_sessions_admission.py:245` and `:269` (`assert 500 == 400`); `TypeError: unhashable type: 'list'` at `app.py:1019`

**Real command output**
- `python -m pytest tests/test_audit5_sessions_admission.py -q` (pre-fix): `8 failed, 5 passed in 15.10s`
- `python -m pytest tests/test_audit5_sessions_admission.py -q` (post-fix): `13 passed in 29.90s`
- `python -m pytest -q`: `640 passed in 114.18s (0:01:54)`
- `npm run test:e2e:public-demo`: `38 passed (1.1m)`
