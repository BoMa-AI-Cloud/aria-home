# Gate A evidence: Audit 5 findings reproduced, repaired, retested

Audit 5 reviewed commit `a2995fd` and reported seven findings. This page shows each one failing on `a2995fd` and fixed on `247cdb5`, with the raw logs in [`docs/evidence/gate-a/`](evidence/gate-a/). Everything here was run offline on synthetic data (Flask test client, temporary databases and session folders, no live calls), except the hosted checks, which ran against the public demo.

How to reproduce: check out each commit and run `python -I docs/evidence/gate-a/gate_a_probe.py <checkout>/backend` (probe output), and copy `backend/tests/test_audit5_*.py` from `247cdb5` into the old checkout before running pytest (regression tests).

| # | Finding (Audit 5) | On `a2995fd` (audited) | On `247cdb5` (fixed) | Regression tests |
|---|---|---|---|---|
| 1 | The decision map built its own follow-up, so it disagreed with the real one | follow-up `goal_verified`, map `unable_to_verify` at 06:21 | both `goal_verified` | `test_audit5_trace_parity.py`: 7 failed on the old code (e.g. `assert 'unable_to_verify' == 'reporting_restored'`), 9 passed on the new |
| 2 | The decision map ignored the visitor's caregiver decline | follow-up `declined`, map `approved`, map HVAC allowed `True` | map `declined`, HVAC allowed `False` | same file: `assert 'approved' == 'declined'` on the old code |
| 3 | Client-chosen cookies bypassed the 500-session cap | 502 forged cookies: 502 × HTTP 200, **502 session databases**, 366 MB | sessions are server-issued; admission stops at the disk bound (64 MiB): 93 × 200, then **409 × 503**, nothing allocated for refused visitors; no eviction of active visitors | `test_audit5_sessions_admission.py`: 9 failed on the old code, 14 passed on the new |
| 4 | A rejected off-checkpoint acknowledgement was still written | HTTP 400, **1 acknowledgement stored** | HTTP 400, **0 stored** (validated before any write) | same file (full table dump compared before and after) |
| 5 | A recorded review was not tied to the exact answer it reviewed | a copied answer with only its interpretation changed still got the old `no_issues` review (`assert {'issues': [], 'verdict': 'no_issues'} is None`) | the review carries an `answer_digest` of the whole answer; a changed answer gets no review and the note "review does not match this answer" | `test_audit5_review_binding.py`: 7 failed on the old code, 7 passed on the new |
| 6 | Pinned Python packages had known advisories | `pip-audit`: **7 known vulnerabilities in 4 packages** (Werkzeug 3.1.8, AnyIO 4.13.0, certifi 2026.2.25, idna 3.11) | **No known vulnerabilities found** (Werkzeug 3.1.9, AnyIO 4.14.2, certifi 2026.10.23, idna 3.20); CI now fails on advisories | [`pip-audit-old-vs-new.txt`](evidence/gate-a/pip-audit-old-vs-new.txt) |
| 7 | A malformed caregiver decision returned HTTP 500 | `[]` → 500, `{}` → 500 | `[]`, `{}`, `null`, `5`, `true` → 400 | `test_audit5_sessions_admission.py` (typed bodies) |

Note on finding 3: on `247cdb5` the probe hit the 64 MiB disk bound after 93 sessions (each probe session runs a full investigation, about 0.73 MB). That would have turned away a burst of judges, so the bound was raised to 512 MiB (overridable with `ARIA_HOME_PUBLIC_DEMO_MAX_BYTES`) and the 500-session cap now binds first. Either limit refuses new visitors with 503 and allocates nothing.

## Full checks on `247cdb5`

- Backend: 701 passed (clean virtual environment, the pinned locks); `pip check` clean; `pip-audit` clean.
- Frontend: typecheck clean, build passes; browser suites 50 passed (main, two timezones), 46 passed (public demo, two timezones), 1 passed (alternate ports). One public-demo test failed once while another heavy job ran on the same machine and passed on the rerun alone; noted, not hidden.
- CI: run 41127405907 on `247cdb5`, success (now includes the public-demo suite and blocking dependency audits).
- Recordings, as served by the public demo ([`recordings-inventory.txt`](evidence/gate-a/recordings-inventory.txt)): all 10 care checkpoints have a recorded muse-spark-1.3 answer and a muse-wonder-1.0 review bound to it; watcher observations are recorded from 19:20 to 04:51 (02:31 was corrected and verified after the stale-evidence check rejected its first answer), and the watcher found nothing to flag from 06:21 on, after recovery.

## Hosted demo

See the section below, added after the deploy of the commit that carries this page's fixes.
