# ARIA Home finishing plan

Received from Brad 2026-10-31; this is now the authoritative plan for the remaining work. It supersedes the remaining
items in [public-demo-plan.md](public-demo-plan.md), which stays as the history of what already landed. Nothing in this
file is a result: every status names its evidence, and an item without evidence is open. AI-generated suggestions,
including the audit items below, are proposals to verify, not requirements.

## 1. Goal and scope

A reliable, memorable, one-click judge experience around one person, one winter night and a clear problem; meaningful
Meta model contributions; permission-controlled follow-through; and an outcome established by later measurements.
Repairs, clarity and completion come before features or model count. No new integrations, no other hackathons, no
speculative production-platform work.

Non-negotiable principles: code computes readiness and verification under explicit rules (deterministic is not
infallible); model output is bounded by evidence and labelled; watts never establish useful heat; thermostat reconnection
never establishes recovery; acknowledgement, authorization, technician attendance and completion reports are not
measurements; no detection is not an all-clear; replay respects observed, received and available times; original
requests and notification contents are immutable history; synthetic, recorded, mock, simulated and live stay distinct;
the public demo needs no account, install, key or paid model; no equipment control; no credentials or real household
data in the repo or demo; every paid-call batch needs Brad's approval.

**Consent correction.** A caregiver decline blocks HVAC contact and must not change temperature verification: declined
contact with enough independent evidence can still be `goal_verified`, and approved contact with too little evidence
stays unverified. Never weaken measurements, suppress a supported verification, or imply approval caused recovery.
Current state: the hosted check on 6a74105 shows the decline branch at 06:21 as `goal_verified` with HVAC refused
([hosted-checks-6a74105.txt](evidence/hosted-checks-6a74105.txt)); this is already the behaviour and is kept.

## 2. Current verified state (2026-10-31)

| Item | State | Evidence |
|---|---|---|
| Audited baseline | `2364970` = GitHub `main` HEAD | `git rev-parse HEAD` |
| Deployed | `6a74105`; the only difference from `2364970` is one evidence file (docs only, no application source) | `/api/health` version.commit; `git diff --stat 6a74105 2364970` |
| CI on 6a74105 | green | GitHub Actions run 41230207234 |
| Story consistency (trend from replay time, frozen request, per-checkpoint answer, distinct decision states) | live in 6a74105 | acceptance test `frontend/e2e/public-demo.spec.ts` (10 checkpoints x 3 branches, red-proofed on 3 audit bugs); hosted checks file |
| Model-value evaluation | done, 60 approved calls | [model-value-eval.md](model-value-eval.md); Spark problem/next-action scoring still needs a human |
| User sessions | kit ready, **no user testing done yet** | [user-sessions.md](user-sessions.md) |
| Uncommitted, tested only in part | caregiver request wording built from visible evidence only (red-proofed); cream default theme; `pyemvue` removed from `requirements.txt`; README transcription and GET known-limit text; technician voice note re-recorded (1 approved call, now "about 4 15") with the old recording moved to `backend/eval/superseded/` | working tree; full six-command gate run in progress |

Audit report and probe files for the 2364970 audit were **not available** on disk (only the auditor's copy of the
repository). The Phase 1 probes below were reconstructed from the descriptions and run on both that copy and the
working tree (`phase1_probe.py`, operator scratchpad; to be committed with the repairs as `docs/evidence/phase1/`).

## 3. Prioritized work packages

### Phase 1: close the reproduced defects (required)

| # | Defect | Status | Evidence | Repair direction | Required regressions |
|---|---|---|---|---|---|
| P1-1 | Advancing before the 19:20 create finishes makes a replacement 02:31 investigation, changing the original request (54 F / asked 19:20 to 52 F / asked 02:31) | **reproduced** at the API level; the frontend path is plausible from code and still needs browser confirmation | probe: request created at 19:20 vs at 02:31 differs in time and text, baseline and now; `frontend/src/App.tsx:3216` creates fresh when no investigation id is ready | a stable story lifecycle: an explicit pending state, Next disabled (or the step queued) until the 19:20 create resolves, the existing stale-response tokens kept; never rewrite notifications | delayed 19:20 completion; rapid progression; progression awaiting checkpoint completion; early snapshots with no follow-up; rewind; original request unchanged while current room evidence updates; visitor isolation |
| P1-2 | A currently rejected watcher observation is labelled "corrected and verified" because any correction exists for the same scenario and time | **reproduced** (code) | `backend/aria_home/trace.py:288-295` overrides `status` from any correction matching scenario + time only, ignoring input revision, policy and the current validation | bind a correction to input revision, laws/prompt version and the exact revised output; show historical correction status separately from current validation | valid kind citing a nonexistent evidence id; invalid output; different input revision; unrelated same-time correction; genuinely matched corrected output |
| P1-3 | Investigation/scenario mismatch mixes evidence with another investigation's anchor or consent | **not reproduced** on `/api/trace` | probe: `scenario=demo_video_v1` with a care id gives 400; unknown id gives 404 (baseline and now) | check the remaining routes that accept both (`/api/follow-ups`, notifications, decisions) and add tests | both mismatch directions; unknown ids; valid context; separate visitors |
| P1-4 | After approval at 02:45, rewinding to 02:31 and deciding again returns the 02:45 decision | **reproduced** | probe: the rewind POST reply has `decision.decided_at = 2026-01-17T02:45:00-05:00` (baseline and now); its `caregiver_permission` block is correctly as-of | make the mutation reply as-of the request time (no future decision, actor or time), keep immutable history and once-only semantics | approve 02:45 then rewind 02:31 and decide; repeat decision idempotency; decline-then-approve |
| P1-5 | A reset between reads makes `/api/follow-ups` return 500 | **fixed for that endpoint** in 6a74105 | `backend/tests/test_followup_replay.py::test_followups_row_removed_mid_request_is_not_found_not_500` (red: 200/500 before, 404 after) | extend the same handling to the other read boundaries (trace, notifications, caregiver decision) without resurrecting state | concurrent reset at each boundary |

Earlier repairs to preserve (all have tests): trace/follow-up verification parity; decline refusing HVAC; rejected
acknowledgements storing nothing; malformed decisions returning 400; the session admission cap and isolation;
exact-answer review binding; dependency advisory fixes. Do not redesign answer hashing or strip decision-relevant
timestamps without a demonstrated need.

Also found and fixed during this cycle (uncommitted until the gate run passes): the watcher validator treated every
`source:<kind>` citation as stale (red-proofed test); the caregiver request said "furnace quiet since <latest report>"
and always "cooling" (red-proofed); the technician transcript said "about seven forty", contradicting the story.

### Phase 2: reliable judge path (required)

Run the validation commands in section 6 sequentially. The auditor saw timing failures in concurrent runs and some trace
failures in sequential reruns; the operator's sequential runs on 2026-10-31 were green (backend 727, e2e 50,
public-demo 54, alt-ports 1). Reconcile by reproducing the auditor's failing trace tests from the descriptions; measure
API and render time per step and look for redundant computation before touching any timeout. No blanket timeout
increases, no removed assertions. If concurrency needs testing, a bounded local synthetic run (a handful of simulated
judges against Waitress); never load-test the public deployment without approval. A controlled 503 at capacity is
acceptable.

Checkpoint: a fresh visitor completes the story with no unexplained stall, no context replacement, no contradictory
history and no stale UI update, in both timezones.

### Phase 3: make the value clear (required)

One truthful story: a Michigan winter night, an older adult's home that may not be warm by morning, and a family
caregiver who needs understandable evidence and permission-controlled follow-through. Fictional and synthetic details
are labelled; no invented pipe burst, loss, distance, family event or prevention claim. The first 60 seconds establish:
who benefits; what ARIA notices across sources; what the Meta models add; what code decides and what stays uncertain;
who may be contacted and what is shared; how later measurements establish follow-through.

### Story restructure proposal (prepared 2026-10-31; plan and proposal only)

Brad's direction: judges should see ARIA following the situation all night, not only reacting when something breaks.
Approved so far: updating this plan and preparing this proposal. **Not approved:** paid calls, deploy, push, or a broad
rewrite. The proposal starts only after every Phase 1 repair has landed, especially stable investigation identity and
immutable original requests.

Constraints (Brad, 2026-10-31):
1. Two separate lines on every step: **Home condition / verified outcome** (code-computed readiness and verification)
   and **ARIA's latest activity** (what actually happened in the replay at that step). The condition is not forced
   to differ at every step; the activity line carries the follow-through.
2. Every activity label describes implemented behaviour or an actual replay event. No "checking more often",
   "continuously monitoring" or any implied background process. The page keeps saying it is a synthetic replay.
3. Progression: normal, small decline noticed, readiness risk, caregiver decision, scoped contact or refusal,
   telemetry restored, warming, sustained goal verified, human report received, warm-by expectation evaluated.
   Times and labels below are proposals to confirm against code and fixtures, not predetermined results.
4. `SMALL_GAP_F` (2.0 F) is a configured readiness threshold, not a safety boundary. Readiness is computed from all
   required evidence, freshness, coverage and policy conditions; nothing is hard-coded to `on_track` because a
   reading is within 2 F.
5. A human report adds an activity/timeline update and never changes the verified outcome. Decline blocks HVAC
   contact and never blocks independent temperature verification.

**Smallest proposed change set.**
- Fixture values only: in `backend/scenarios/care_home_v1/`, change the **values** of room, thermostat and (if needed)
  circuit records observed before 23:31 on 2026-01-16 so the evening starts warm and declines. Keep every record id,
  timestamp, received time, cadence and the record count identical, and keep `manifest.version` unchanged. Why: the
  input revision hashes `scenario_fixture_version` and every source's status, including record counts since the
  start of the night (`backend/aria_home/investigator.py:295-323`), so adding or removing a record, or bumping the
  version, would rebind every later checkpoint.
- Checkpoints: replace 19:03 / 19:15 / 19:20 with three evening steps (proposed 19:20, 21:00, 23:30) in
  `backend/aria_home/public_demo.py` and `frontend/src/App.tsx` (`CARE_REPLAY_TIMES`, `CARE_START_AT`).
- Story investigation: created at the first step whose computed readiness creates a follow-up (proposed 23:30),
  the same way the pre-investigation snapshots work today (19:03 and 19:15 have no follow-up). Steps before it show
  snapshots with no request.
- One new activity line on House, derived from replay events and computed transitions only (plan confirmed;
  readiness unchanged with a falling trend; readiness changed to at risk and the request was created; decision
  recorded; contact sent or refused; thermostat reporting resumed; warming observed; goal verified; report received;
  warm-by expectation evaluated). No new constants.
- Docs, tests and the video script follow.

**Proposed checkpoint table** (every cell to be confirmed by the impact check before data is written):

| # | Time | Home condition (computed) | ARIA's latest activity (event or computed transition) |
|---|---|---|---|
| 1 | 19:20 | readiness on track for 68 F by 7:00 | plan confirmed with the caregiver contact allowed |
| 2 | 21:00 | readiness still on track; trend falling | a decline was noticed in the room readings; readiness unchanged |
| 3 | 23:30 | readiness at risk (projection misses 7:00) | readiness changed to at risk; permission request created and sent (simulated) |
| 4 | 02:31 | at risk; thermostat telemetry missing | waiting for the caregiver's answer, or her decision just recorded |
| 5 | 02:45 | unchanged by the decision | HVAC contacted with the allowed fields (approved) or contact refused (declined) |
| 6 | 04:21 | thermostat reporting restored; not verified | thermostat reporting resumed; reconnection does not close the issue |
| 7 | 04:51 | warming observed | independent room sensor shows warming |
| 8 | 06:21 | goal verified (held 30 minutes) | goal verified from independent readings |
| 9 | 06:45 | unchanged (goal verified) | technician report received, counted as a report only |
| 10 | 07:01 | warm-by expectation met | warm-by expectation evaluated at 7:00 |

**Impact inventory (run before any fixture change; nothing is assumed reusable).** A script compares, at every care
checkpoint, the identity each artifact is bound to before and after the change, and writes the result into the
evidence folder.

| Artifact | Bound by | Expected outcome under the smallest change | Checked by |
|---|---|---|---|
| Recorded muse-spark-1.3 answers | scenario, time, input revision, prompt and readiness policy versions | 02:31-07:01 reusable only if their input revisions are byte-identical; evening steps replaced | recomputing each checkpoint's input revision |
| muse-wonder-1.0 reviews | scenario, time, input revision, answer digest | follow their answers | re-matching each review to its answer digest |
| Watcher runs and correction records | scenario, time, input revision, laws and watcher prompt versions | 02:31-07:01 reusable only if revisions match; evening steps replaced | recomputing the watcher identity |
| Technician transcript | scenario and model only | reusable (re-recorded 2026-10-31, says about 4:15) | the transcript loader |
| Visual (sam-3.1) recordings | scenario and synthetic images | expected reusable | the visual loader at each checkpoint |
| Investigation identity and consent timing | creation time and evidence | changes: the request moves from 19:20 to the step-3 time, with new text | the frozen-request tests in all three branches |
| Verification after 23:31 | records after the follow-up's creation | must be re-checked, because the follow-up's creation time moves | verification at every later checkpoint |
| `backend/eval/expected.json` care cases | hand-written expected labels | care times updated by the operator | the offline evaluation |
| Tests | literal times, request text, checkpoint lists | updated, never weakened | the six-command gate |
| Video footage | none recorded yet for script v4 | the v4 opening is rewritten | n/a |

**Acceptance tests.**
- Readiness at each step equals the code's computation from all evidence; no test asserts a status from the 2 F
  threshold alone.
- No permission request before the step-3 time; from then on the request text and time are identical at every step in
  all three branches.
- The activity line at every step names a replay event or computed transition; a test fails if a label has no source.
- Decline at 02:31: contact refused, and verification at 06:21 is still `goal_verified`. Approve with too little
  evidence (synthetic variant): contact sent, verification stays unverified.
- The technician report changes the activity line only, never the outcome.
- Every recording shown at a checkpoint matches its exact identity; anything else shows the labelled fallback.
- The inventory lists a 02:31-07:01 artifact as reusable only when its identity matches byte for byte.

**Revised recording-call estimate (paid; each batch needs its own approval).**

| Case | Calls |
|---|---|
| Minimum: the three new evening steps show the labelled "no recorded model response" fallback | 0 |
| Recommended: an answer, a review and a watcher run at each of the three evening steps | 9 |
| Plus at most one watcher revision per step if a first attempt fails checks | up to 12 |
| If the inventory shows the 02:31-07:01 identities changed (for example because the follow-up's creation moved) | up to 21 more (7 checkpoints x answer, review, watcher) |


Model-contribution table (to replace the README's long paragraph; verify each row against code before publishing):

| Model id | Job | Mode | Evidence | Limitation |
|---|---|---|---|---|
| muse-spark-1.3 | explains the code's readiness and verification in plain words, citing evidence ids | recorded (live is operator-only) | `backend/eval/recorded/`, claim checks in code | readiness agreement is enforced, so it is not independent accuracy |
| muse-spark-1.3 (watcher) | notices anomalies with cited evidence; one revision after a failed check | recorded | watcher recordings; model-value eval C | first attempts failed checks in 9 of 12 unseen variants |
| muse-wonder-1.0 | second review of each recorded answer for unsupported claims | recorded, bound to the exact answer | reviews files; model-value eval B (12/12 planted claims, 0/12 false alarms) | planted claims used four fixed templates |
| muse-voice-transcribe-1.0 | transcribes the technician's voice note into a human report | recorded once | `backend/eval/transcripts-20261031.json` | a report, never a measurement |
| sam-3.1 | segments the mechanical-room camera frames | recorded over synthetic images | visual recordings | missed the frost; no detection is not an all-clear |
| muse-image-1.0 | generated the synthetic camera images | asset generation only | fixtures | never called at runtime |

### Phase 4: visible trust without clutter (optional polish)

Reuse the existing UI. A compact agreement line ("Same investigation · Same replay time · Recovery panel: <stage> ·
Decision map: <stage>") only when investigation, scenario, replay instant and policy context match; show the
disagreement otherwise, never substituted labels. Make findable: current measurement vs original request;
code result vs model interpretation; fields in each notification; permission refusals; recorded provenance; outcome
evidence with its availability time. Not a prerequisite if the current screens already show this.

### Phase 5: three-minute video (required)

Script v4 (`C:\aria-home-private\video\vo\care-v4.json`, approved by Brad 2026-10-31) follows problem, 52 F with a
silent thermostat, risk, caregiver choice, the real 02:31 correction, the evaluation card and the 30-minute hold. To
align it with this plan: add a short decline demonstration (contact refused while sensor verification stays independent,
using the hosted decline branch), and confirm every stage against the repaired build before recording. Record only from
the deployed repaired version; label dramatization; music under speech; keep three minutes.

### Phase 6: release and submission handoff (required)

Hosted link at the top of the README; synthetic/recorded/simulated disclosures; footer and `/api/health` matching the
deployed commit; a final evidence bundle tied to the repaired commit (not hard-coded 2364970); judge one-pager updated
with the model table; public repo, accessible video and submission links; Brad's end-to-end watch and click-through.
Compare the actual source diff when HEAD and the deployment differ; a docs-only difference is not an application
mismatch.

Deadline: the auditor read November 4, 2026, 9 PM ET on the public event page on 2026-10-30; Brad's earlier internal
target was 5 PM ET. **Brad to confirm the current official deadline** on the event page before setting the freeze.

## 4. Owners and dependencies

| Package | Owner | Depends on |
|---|---|---|
| P1-1, P1-2, P1-4, P1-5 extension, P1-3 route sweep | Muse (code + tests + red-proofs); operator retests | current uncommitted batch landing first |
| Phase 2 reconciliation | operator, Muse for fixes | Phase 1 |
| Model table, README/one-pager | operator with Meta AI drafting | Phase 1 (claims must match code) |
| Phase 4 | Muse, only if time remains | Phases 1-3 |
| Video | operator records and edits; Brad reviews | the repaired build deployed |
| User sessions | Brad runs them | none (kit ready) |
| Spark human scoring | Brad, or the operator drafts for Brad to check | none |
| Release and submission | operator prepares; Brad approves and submits | everything above |

## 5. Acceptance criteria

- P1: every row reaches "fixed" with its listed regressions, each red-proofed (break the fix, watch an assertion fail,
  restore), or stays visible as unresolved with the reason.
- Phase 2: section 6 all green twice in a row on unchanged code, and the fresh-visitor checkpoint passes on the deployed
  build in both timezones.
- Phase 3: the README opening and one-pager state the six first-60-second points; every model row cites evidence.
- Phase 5: the finished video is three minutes, every functional claim visible in the deployed UI, dramatization
  labelled.
- Phase 6: `/api/health` commit equals the released commit; README link works signed out; Brad has watched and clicked
  through.

## 6. Validation commands (run sequentially, never two browser suites at once)

```
cd backend && python -m pytest -q
cd frontend && npm run typecheck
cd frontend && npm run build
cd frontend && npm run test:e2e                # UTC and America/Los_Angeles projects
cd frontend && npm run test:e2e:public-demo    # both timezones
cd frontend && npm run test:e2e:alt-ports
pip-audit -r backend/requirements.lock -r backend/requirements-optional.lock -r backend/requirements-dev.lock
cd frontend && npm audit --omit=dev
cd backend && python -m aria_home.evaluation --offline   # existing deterministic evaluation
```

Plus a built-frontend Waitress run with public-demo settings (`ARIA_HOME_PUBLIC_DEMO=1`) clicked through once, and the
hosted checks script after each deploy.

## 7. Actions that need Brad's approval

Deploying; pushing a release; tagging; publishing the video; submitting; any paid model call batch; load testing the
public deployment; setting the final freeze date; any change to the official story facts.

## 8. Risks and fallback

- P1-1 needs frontend lifecycle changes close to the deadline. Fallback: disable Next until the 19:20 create resolves
  (smallest safe change), and leave the queued-step design for later.
- P1-2 label binding could hide the real 02:31 correction if bound too strictly. Fallback: show "historical correction"
  as its own line and never upgrade the current status.
- Local and CI results can differ (the auditor's trace failures). Fallback: record the exact failing test and keep it
  visible here; never claim the suite is green when it was not.
- No user testing may happen before the deadline. Fallback: the submission says so plainly.
- Hosting: the Starter plan can cold-start or hit the session cap; a controlled 503 is the designed behaviour.

## 9. Final demo and submission checklist

- [ ] Phase 1 rows fixed or visibly unresolved
- [ ] Section 6 green twice; fresh-visitor click-through in both timezones
- [ ] Repaired build deployed with Brad's approval; `/api/health` commit verified; hosted checks rerun
- [ ] README opening, model table and one-pager match the code
- [ ] Video recorded from the deployed build, three minutes, decline shown, dramatization labelled
- [ ] User-session results or the plain "No user testing has been done yet"
- [ ] Spark problem/next-action scores filled by a human, or left marked as needing one
- [ ] Final evidence bundle tied to the released commit
- [ ] Official deadline confirmed by Brad; freeze date set with Brad
- [ ] Brad's watch, listen and click-through; Brad submits
