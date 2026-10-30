# Operator log

Steps the operator (Claude Code running Anthropic's Claude model, directed by Brad Wentzel) took directly,
outside the Meta-model tasks in the table in [README.md](README.md). None of these steps wrote application
code. Times are local (ET). Earlier operator steps are summarised in the README's Operator section and in
[../timeline.md](../timeline.md).

## 2026-10-27

- Ran the approved live evaluation batches and recorded them through Meta-model task day9-14 (see
  [../evaluation.md](../evaluation.md)): 12 calls on muse-spark-1.3 via the Meta Model API and 12 + 12 calls on
  meta-models/muse-spark-open-1026 via Baseten, each batch approved by Brad with its count and limits.
- Assembled the demo video outside the repository with ffmpeg: real ARIA Home screen recordings (`record:demo`,
  `record:insets`, `record:keys`), AI-generated dramatization scenes, synthetic Kokoro narration and a Meta AI
  music bed. Video assembly scripts and media are not part of the repository.

## 2026-10-28

- Edited [../submission.md](../submission.md) directly (commit d883778): the write-up now quotes the
  current-code live result (8 of 12 valid on muse-spark-1.3) instead of the earlier pre-repair 24-call result,
  and the checklist quotes the then-current opening line.
- Video scenes: tried Gemini (stopped at its video limit; no clip produced) and Grok Imagine (four clips
  produced, then not used). Brad had Meta AI generate the 16 story clips; the operator downloaded them from
  meta.ai in Brad's signed-in browser with his approval. The demo video now uses only Meta AI story scenes.
- Opening card: wrote the prompt for Meta-model task day9-17, which changed the card to
  "Story scenes and music: Meta AI."; reviewed its diff and re-recorded the card into the video.
- Audit 3: ran the independent auditor's probe scripts against d883778 with fake providers and temporary
  databases (no live calls). All twelve reported defects reproduced. Read the auditor's report, the AI-generated
  submission checklists (V1, V2), master to-do list and enhancement pack, and recorded which of their statements
  were unsupported (outdated "24 calls, 0 rejected", invented timeline entries, placeholder `assert True` tests,
  unsourced product comparisons) so later tasks do not repeat them.
- Wrote the prompts for the Audit 3 repair tasks (day10-*) and queued them for the Meta-model sessions.
- Backfilled 75 missing rows in the [README.md](README.md) task table from the saved prompt/answer files.
- Started this operator log.
- Verified task day10-01 (Audit 3 group 1) independently: full backend suite 319 passed; re-ran the auditor's
  probes 1-3: the conflicting reading now gives unable_to_verify for both id orderings, idle-at-target and
  already-at-target give arrival_met, and non-finite readings are rejected at validation.
- Verified task day10-02 (Audit 3 group 2) independently: full backend suite 329 passed; re-ran the auditor's
  probes: the retried investigation is now stored as ok with its output, switching the provider mode makes a new
  identity (2 provider calls), /api/metrics and /api/investigation both report met at 22:01, and the
  68.04/67.96 cache probe is no longer deduplicated (second readiness at_risk, as computed).
- Task day10-03 (Audit 3 group 3) failed: the session ended after 33 turns of reading, with no edits (backend
  suite still 329 passed). Split it into day10-03a (backend: claims, read-only GET, acknowledgements) and
  day10-03b (frontend: pending UI, ports, recording tooling) and re-queued.
- Model availability check (read-only model listings, no inference): the Meta Model API key lists muse-wonder-1.0,
  muse-spark-1.1, -1.2, -1.2-contributor, -1.3, -1.3-contributor, sam-3.1, muse-image-1.0 and
  muse-voice-transcribe-1.0. The Baseten key lists two Meta models (meta-models/muse-spark-open and
  meta-models/muse-spark-open-1026) among 20; no SAM or image model there.
- Verified task day10-03a independently: backend suite 336 passed; two GETs make 0 provider calls; malformed acks
  return 400/403 (2000-dated and numeric timestamps 400, list body 400, unknown actor 403). The auditor's
  abandoned-claim probe no longer applies as written: the identity now includes the provider, so the probe's
  hand-made claim has a different key; abandoned-claim recovery is covered by the task's own tests instead.
- Task day10-03b failed: 22 turns, ended on a plan sentence with no edits (e2e still has 11 hard-coded
  127.0.0.1:5173 URLs). Re-queued as day10-03b2 on muse-spark-1.3 with an explicit instruction not to end on a
  status sentence.
- Brad created the Meta developer app "ARIA Home Notifications" (WhatsApp use case, his business portfolio,
  WhatsApp test sender number) with the operator driving the browser; Brad accepted the Meta terms, verified his
  own phone as the only recipient, generated the token and entered all credentials himself through a hidden-input
  script. The operator never saw the token or passwords.
- Task day10-04 (Audit 3 group 4) made its changes but its saved answer is only a status line. Checked directly:
  backend suite 344 passed, no placeholder tests, MIT LICENSE (Bradley Allen Wentzel), Brad's hook at the top of
  the README, no absolute safety or invented-statistic claims found. Two doc errors found and queued for fixing:
  the 10-27 run labelled readiness-policy-v2, and the demo script still describing a log cabin.
- Installed pyemvue (Brad approved the integrations) for the read-only Emporia panel; queued day10-05.
- Ecobee check: ecobee's developer page says "Sorry, we are not currently accepting new developer registrations at
  this time" (read 2026-10-28), so a new ecobee API key cannot be created today.
- Brad sent a WhatsApp message from his phone to the test number (reported 2026-10-28T19:19Z), opening WhatsApp's 24-hour free-form window. The ecobee account Brad signed in with has no devices, no developer menu and no apps; ecobee integration not started.
- HomeKit check (read-only mDNS browse from the laptop, installed aiohomekit): no HomeKit accessory was visible; the only mDNS service seen at all was this laptop's own Spotify, so the laptop either is not on the thermostat's network or local discovery is blocked.
- Verified task day10-03b2 (muse-spark-1.3): backend 348 passed, e2e 32 passed, alternate-port smoke passed, all
  recording clips pass, no hard-coded 5173 URLs left. Review finding: its test-only POST parameters (test_delay_s,
  test_fail, lease_s) are honoured in the default mock mode; queued day10-06 to gate them behind an explicit
  ARIA_HOME_E2E_HOOKS=1 that only the Playwright configs set.
- Verified task day10-05 (WhatsApp test delivery + Emporia read-only panel; its saved answer ends on a status
  line before the frontend checks) and day10-06 (e2e hook gate): backend 365 passed; frontend typecheck clean,
  build ok, e2e 32 passed. Code review: WhatsApp live only with all credentials plus ARIA_HOME_WHATSAPP_LIVE=1,
  text built by the existing HVAC allowlist function, any other recipient refused, attempt persisted before the
  API call; Emporia module reads only. Credential check: none of the seven real credential values appears in any
  of the 77 changed or new files (compared in memory, values never printed).
- Committed the Audit 3 repair and integrations as c3acce9, 8605c1e, cfdc74a, 916783f and pushed with Brad's approval; the first CI run on GitHub (run 40761110029) passed.
- One approved real WhatsApp send attempt (demo_video_v1 16:52 HVAC notice, temporary database): Meta refused it
  with error 131030 "Recipient phone number not in allowed list"; nothing was delivered; the app recorded
  failed:api_error_400 and kept the notice simulated. Cause: the stored WHATSAPP_TEST_RECIPIENT differs from the
  single number on the app's allowed list (compared without printing either). Review finding: the real send is
  triggered from GET /api/follow-ups/<id>, a read endpoint; to be moved to an explicit POST.
- Committed and pushed day10-07 (fa39f93): the WhatsApp send now runs only from POST /api/notifications/<id>/whatsapp;
  backend 372 passed, e2e 32 passed. After Brad corrected the stored recipient (confirmed matching the allowed number
  without printing it), the second approved real send through the new POST returned Meta error 131005
  "(#131005) Access denied"; nothing was delivered, notice stays simulated. Likely cause: the access token lacks
  WhatsApp messaging permission or has expired.
- Brad generated a new access token (operator clicked Generate token without viewing the page; Brad copied and stored it). Third approved send through POST /api/notifications/<id>/whatsapp: Meta accepted it, state delivered_to_test_number, a WhatsApp message id was returned.
- Brad confirmed the WhatsApp message looks right and approved the visual work (4 muse-image-1.0 + 4 sam-3.1 calls) 2026-10-28.
- Visual probe (approved: 4 muse-image-1.0 + 4 sam-3.1 calls, Meta Model API, 90 s, no retries): all 8 returned 200.
  SAM results: water puddle 1 object; frost on copper pipe 0 objects (a false negative: the frost is obvious);
  dry floor 0; frost on window 4. Committed the images and raw responses as fixtures (backend/fixtures/visual) and
  queued day10-08 to build the visual evidence source on them.
- Verified task day10-08 (visual evidence on sam-3.1 recordings): backend 390 passed, e2e 34 passed (re-run by the
  operator); GET /api/visual/image ignores caller-supplied paths (four traversal attempts all returned the
  scenario's own fixture); no credential value in the 92 changed text files; no banned claims.
- Live evaluation (approved: 17 calls, muse-spark-1.3, Meta Model API, snapshot 77cafc9, 90 s, 12000 tokens, no retries): 11 of 17 valid, 6 rejected (all six are after-arrival cases citing an old reading as current), 11 of 11 valid answers agreed with the computed readiness, median 24.5 s. Raw records copied to backend/eval/results-live-77cafc9.json; queued day10-09 to record it.
- Live rerun of the six after-arrival cases (approved: 6 calls, muse-spark-1.3, Meta Model API, snapshot efdff57 with the inv-v3 contract, 90 s, 12000 tokens, no retries): 5 of 6 valid, all 5 agreeing with arrival_passed; 1 rejected (demo_no_followup_v1@20:31: the answer said 'below target', contradicting the resolved target_gap fact). Two script errors were fixed before any call was made. Raw records: backend/eval/results-live-arrival-efdff57.json.
- Re-recorded all app screens after day10-12 (8 main + 13 close-up/key clips), regenerated the key-line stills and title cards from them, and rebuilt the demo video as A6 outside the repository: 5400 frames, 180.0 s.
- Fresh-clone check (2026-10-29) of github.com/BoMa-AI-Cloud/aria-home at a94915a, following the README only: new
  venv from backend/requirements.lock + requirements-dev.txt, 400 passed with no model key; backend started with
  the README command in mock mode on 127.0.0.1 (health, provider, metrics, whatsapp/status, live-power all 200;
  WhatsApp and live power report not configured); frontend npm ci, typecheck and build passed.
- Re-ran the auditor's probes against HEAD: conflicts give unable_to_verify for both id orders; idle and
  already-at-target give arrival_met; retry persisted as ok with output; provider mode change makes a new identity;
  metrics and investigation agree (met); repeated GETs make 0 provider calls; malformed acks 400/403; non-finite
  values rejected; 67.96/68.04 get different identities. Probe 4 (abandoned claim) is covered by tests because the
  identity now includes the provider.
- 2026-10-29: drafted the final write-up and X demo post from the repository docs (private draft for Brad);
  Brad approved the write-up, and task day10-14 put it into docs/submission.md verbatim after checking every
  number and model id. That check found the audit claim had no in-repo source, so task day10-15 added
  docs/audit-3.md (12-row finding matrix; the operator confirmed every test file it names exists). Brad chose the
  Meta AI music cue, so A6 stays the final video. The X post is drafted, not posted.
- Updated the build-log task table with the 17 tasks run since the 2026-10-28 backfill (rows use the first line of
  each saved answer).
- 2026-10-29: received Audit 4 (merged independent findings on baseline af94e2b; HEAD 077e849 differs only by the
  build-log index). Recorded the ten findings and the group C/D scope in docs/audit-4.md as a work list, all
  "pending". Under this audit's rules commits stay local until Brad approves a push.
- Checkpoint A reproduction (temporary DB, fakes, no external calls): findings 1, 5, 8, 9 reproduced by running them; 6, 7, 10 reproduced by inspecting the code and the installed PyEmVue 0.18.9 signature; 2, 3, 4 need constructed scenarios and are reproduced inside the group A task's tests. Statuses recorded in docs/audit-4.md.
- Verified task day11-01 (Audit 4 group A): backend 418 passed; the finding-1 probe now gives unable_to_verify for both insertion orders; the 'or True' assertion is gone. Noted for Brad: finding 4 keeps a zone-scoped thermostat liveness gate on recovery rather than separating temperature success from thermostat restoration; the task documents it as a limitation.
- 2026-10-29: received the public-demo and model-coverage plan from Brad; recorded it with the baseline in docs/public-demo-plan.md as a 10-step work list (Audit 4 finishes first).
- Verified task day11-02 (Audit 4 group B): backend 449 passed; re-probed: empty, whitespace and null ack timestamps 400; WhatsApp 200 {} and malformed elements recorded as unconfirmed, not success; exact returned image URLs load (200) at Z, +05:00 and -05:00; the Emporia 0.001 kWh/1 s -> 3600 W case is tested. Made a synthetic technician voice note with the Kokoro voice (14 s, mono 16-bit 24 kHz) as a labelled fixture in backend/fixtures/voice for the approved transcription call.
- Verified task day11-03 (Audit 4 groups C-D): test:e2e:alt-ports passes with the PLAYWRIGHT_* port variables unset (re-run by the operator) and is in CI; runtime, optional (PyEmVue) and dev locks exist; deadline listed as needing confirmation and a freeze/recording schedule proposed (not agreed); recording checklist added.
- Ledger correction: public-demo-plan.md step 1 marked done (uncommitted), steps 5-6 marked approved, and a section added listing Brad's own open items.
- Published a live ledger page for Brad (claude.ai artifact 'ARIA Home Build Ledger', private) mirroring this log, docs/public-demo-plan.md and docs/audit-4.md; it is updated alongside these files.
- 2026-10-29: Brad approved the items waiting on him. Recorded as: freeze end of day Nov 2 and recording Nov 3 agreed; push approved (to run after the queued Muse jobs finish). Not covered by a general approval: the official deadline still needs the organizers' current rules; a specific host and deploy step need his yes once the handoff is written; watching A6 and submitting remain his actions.
- 2026-10-29: Brad changed the story: an older-adult care story replaces the trip-home story, motivated by his in-laws getting older (his words, used verbatim). Queued day11-07 to build the care_home_v1 scenario with a family caregiver audience, consent, and a warm-by time, and to update every judge-facing text.
- 2026-10-29: Brad asked for the model to notice anomalies unprompted, with wrong claims corrected and verified, and verified corrections kept as Laws it cannot break. Queued day11-08: code-enforced Laws registry (design laws seeded, new laws proposed and activated only by a person), anomaly watcher on muse-spark-1.3 with a one-revision correction loop and correction records, documented as prompt-level learning, not retraining.
- 2026-10-29: adopted Brad's 15-stage release process as docs/release-process.md; added the three missing stages (red-proof of each safeguard, a running-version check via /api/health, an overnight post-deploy check) and queued day11-09 for the version stamp. Red-proofs for the Audit 4 safeguards will be run at the release-batch step before committing.
- 2026-10-29: Brad asked to add the release process to the laws; appended a 'process laws' category to day11-08 (CI-enforced checks for regression-test files, red-proof records, build-log completeness, placeholder-only env example, no live flags in CI, the version stamp; review-checked approval rules).
- 2026-10-29: Brad: Muse does the testing and fixing; the operator only prompts and retests. Updated docs/release-process.md stages 5 and 7, pointed the red-proof process law at docs/red-proofs.md, and queued day11-10 for Muse to red-proof every Audit 4 safeguard.
- Retested day11-04 (public-demo backend) and day11-05 (guided story): Muse reports e2e 34 and public-demo 22 passed. day11-06 (Wonder review, transcription) stopped mid-task at 'Now wiring app.py'; the backend suite shows 3 failures (assert 5 == 4 on the evidence-source count). Queued day11-06b for Muse to finish it ahead of the care story.
- Care-story camera fixtures (approved: "You make them one at a time", then "Do whatever you recommend" for a camera-style
  redo): 9 muse-image-1.0 + 9 sam-3.1 calls, Meta Model API, all 200. The first three images were cinematic and were
  regenerated as fixed home-camera frames (kept privately, not used). Final six: sam-3.1 found the blank thermostat
  display (1) and correctly found nothing on the dry floor and the warm morning; it MISSED frost on the window and on the
  pipe (0 each) and found no indicator light (0). Copied to backend/fixtures/visual/care. A real Nest camera
  integration is deferred until after the freeze (Device Access registration, WebRTC-only stills).
- Retested day11-07 (care story) and day11-06b: backend 497 passed. day11-07 ended mid-task; day11-06b explained the 5-source count (the transcribed report is listed as an inventory source with 0 records for demo_v1 and is excluded from measurement, eligibility, verification and notifications). Browser coverage dropped (normal 34 -> 18 passed, public-demo 22 -> 2). Queued day11-07c for Muse to finish the care story and restore every dropped test without weakening any.
- Ran the approved muse-voice-transcribe-1.0 call (1 call, Meta Model API, 90 s, no retries) on the synthetic technician note through backend/aria_home/transcribe.py: validation passed; the transcript matches the script word for word except punctuation ('seven forty' -> '7 40'); recorded in backend/eval/transcripts-20261029.json. The 16 approved muse-wonder-1.0 review calls were NOT run: the recorded live results store each answer's status and readiness but not the answer text, so there is nothing to review; reviewing needs the answers regenerated first.
- Brad approved 20 calls (2026-10-29): 10 muse-spark-1.3 investigation answers on the care_home_v1 checkpoints with full answer text saved, then 10 muse-wonder-1.0 reviews of those answers; Meta Model API, 90 s, no retries. Replaces the 16 earlier approved review calls (not run). To be run on a snapshot after day11-07c lands so the recorded input revisions match the code.
- 2026-10-29: Brad lifted the no-faces rule for the dramatization ('it takes away all of the caring feeling'). New rules: fictional faces allowed and consistent across clips, labelled AI-generated dramatization (Meta AI), not resembling any real or famous person (not Brad's in-laws). Operator sent the care-story 17-clip series prompt to Meta AI in Brad's Chrome, then the faces update; Meta AI is generating.
- Downloaded the Meta AI care-story clips from Brad's Chrome (one pack, with his earlier download permission): 34 videos on the page were 17 unique clips (each listed twice), kept as care34/c01-c17. All show the fictional characters with faces. Continuity issues found: c15 (dawn exterior) shows a cabin-style house, not the modern house; c17 (mother and daughter by the fire) shows a brick fireplace with photos, not the linear stone fireplace.
- Meta AI regenerated the two off-continuity clips on request: c15 is now the same modern flat-roofed glass house at dawn, c17 the same living room with the linear stone fireplace, mother and daughter together. Originals kept in care34/replaced. The 17-clip care-story set is complete.
- 2026-10-29: Brad wants the video to show how ARIA works, with some dramatization. Plan: real 'ARIA's view' (a live map drawn from a read-only decision trace; queued day11-12 after the watcher/Laws job) plus Meta AI light-stream dramatization clips that follow the same beat order, labelled AI-generated dramatization; hard cuts from each dramatized beat to the real screen.
- 2026-10-29: Brad wants ARIA to ask the daughter for permission on WhatsApp before contacting HVAC. Queued day11-13 (step 1): permission request built from the caregiver allowlist, optional real WhatsApp send to the test number via explicit POST, Approve/Decline in the app, HVAC request only after approval. Step 2 (real WhatsApp reply via a webhook and a temporary tunnel during recording) left for Brad to decide on recording day.
- Downloaded the 5 Meta AI light-stream dramatization clips (plus one extra) into care34/light. The extra morning clip shows readable text ('Morning Threads') on a wall panel, which breaks the no-text rule; moved to care34/replaced and not used.
- Retested day11-11 (care camera frames) and day11-07c (finish care story, restore tests): both ended mid-task on a status line. Backend 505 passed; operator browser run: e2e 7 failed / 29 passed, public-demo 6 failed / 16 passed. Queued day11-07d for Muse to fix every failure without weakening tests and to finish day11-11's open investigation (late-start replay giving unable_to_verify). The watcher/Laws job (day11-08) was already running when this was found.
- Retested day11-07d (browser fixes) and day11-08 (watcher, Laws): both ended mid-task. Backend 537 passed, 1 failed (process law: build-log index missing a task); updated the index (operator task), process-law tests now 5 passed, 2 expected-to-fail (red-proofs, version stamp). Queued day11-07e to finish the browser fixes with day11-07d's findings (stale 'Arrival' label, recording expectation, two timing-sensitive tests).
- 2026-10-29: Nest setup. Created Google Cloud project 'ARIA Home Nest' (not ARIA's 'ARIA EMAIL' project), enabled the Smart Device Management API, OAuth consent in testing mode, web OAuth client (redirects http://127.0.0.1:8765/callback and https://www.google.com); Brad entered the client secret himself. Brad paid the Device Access fee on his business Google account; created the Device Access project 'ARIA Home' with the OAuth client ID and saved its Project ID; test users: Brad's two Google accounts. Queued day11-14 (Nest Cam Indoor gen 1 snapshot via RTSP + ffmpeg, auth script, opt-in POST). Wrote and rendered the care-story narration (vo/care.json, Kokoro af_bella, 13 segments, 180 s).
- Wrote docs/hosting-handoff.md (proposal only): Render paid Starter recommended for judging, Render free as the $0 fallback, Hugging Face Spaces as an alternative; exact approval wording included; nothing deployed.
- 2026-10-29 ~20:20Z on: every Muse worker job (day11-07e, 13, 14, 09, 10) failed at once with Meta Model API 402 "Billing verification failed". ARIA's view (day11-12) had finished before that: retested, backend passes and both browser suites green (42 / 24), so day11-07e is no longer needed. The five unrun prompts are indexed in the build log as not completed. Brad: "use meta ai if the api key is donzo", so code work now goes through the Meta AI web chat (meta.ai, account saf_integration); the operator applies, integrates and retests.
- Version stamp (day11-09b, Meta AI web): /api/health reports version.commit and source (env ARIA_HOME_RELEASE_COMMIT, else backend/RELEASE_COMMIT, else "unknown"/"not stamped"; hex-only, never git); the footer and landing show "Version <short>". Red-proofed (format check removed -> invalid-value test failed with AssertionError). Two exact-health tests updated to pop the new field; landed xfail removed.
- Caregiver permission (day11-13b, Meta AI web, partly used): Approve/Decline on a permission card in the care story; HVAC request only after approval, decline blocks it; once-only decision, replay-visible, never changes readiness or verification (tested); the permission request goes through the same opt-in, once-only WhatsApp POST; caregiver "HVAC contacted" / "goal verified" updates; a teal permission step in ARIA's view; guided story text updated. Meta AI's whatsapp.py rewrite was rejected (wrong table columns, API v20.0, safety logic dropped), and the operator refactored by hand. Class fix: the e2e reset now empties every table in the schema (it had missed the new one), with a test. Red-proofed (decline rule removed -> 2 AssertionErrors). Backend 576+ passed, browser 48 / 26 passed.
- Nest snapshot (day11-14b, Meta AI web): backend/aria_home/nest.py (SDM token refresh, camera pick, GenerateRtspStream, one ffmpeg frame, StopRtspStream always in a finally, every failure a status, secrets scrubbed); backend/scripts/nest_auth.py (one-time consent on 127.0.0.1:8765, stores only NEST_REFRESH_TOKEN as a Windows user variable, prints camera names). Fixed Meta AI's device list being sent as a POST. Routes are live-only (absent in public demo; public demo refuses to start with ARIA_HOME_NEST_LIVE). The sam-3.1 upload happens only on an explicit button press and is disclosed. Red-proofed. Backend 588 passed, browser 50 / 26 passed. Not run against the real camera: needs Brad's one-time sign-in, and sam-3.1 needs the 402 billing fix.
- Pushed 3891f63 (the batch) and c4eb322 (CI fix: an unquoted ': ' in the install step name made ci.yml invalid YAML; the first run failed in 0 s). CI green on c4eb322 (run 40987974396). Still open: red-proofs (day11-10), the 20 approved paid calls and the watcher recording batch (all need the Model API billing fixed), Brad's Nest sign-in, hosting approval, re-recording screens, final cut.
- 2026-10-30: billing fixed. Muse red-proofed all ten Audit 4 safeguards (docs/red-proofs.md; #5's TypeError is the original 500 defect itself, confirmed from the audit row) and wrote backend/scripts/record_care_answers.py (dry run by default, hard cap, no internal retries; rejected answers recorded but never served). Retested: backend 599 passed; browser 50 / 26 / alt-ports 1 passed; real dry run plans 20 calls.
- 2026-10-30: first live recording run (commit 564c527, cap 20): 11 calls made. 1 accepted answer (07:01); 9 answers rejected with 'provider error: timeout' (20 s provider default); the one review failed with bad_response (status hidden by review.py). Nothing rejected is served. Queued day11-15b for Muse: 180 s recording timeout, review failures report status and a scrubbed detail, --only-missing re-runs. Re-run needs 19 calls (9 answers + 10 reviews); 9 remain of the 20 approved.
- 2026-10-30: Brad completed the Nest sign-in. First real snapshot via aria_home.nest.capture_snapshot (no upload): status ok, device 'Living Room' (its Google Home name), stream_stop stopped, one night-vision frame of the furnace saved to the git-ignored backend/instance/nest-snapshots/.
- 2026-10-30: recording run 2 (24c152e, --only-missing, cap 19): 19 calls; all 9 missing answers accepted, so all 10 care checkpoints now have recorded muse-spark-1.3 answers, served by the public demo with provenance (verified). All 10 muse-wonder-1.0 reviews refused: 400 'unknown parameter max_tokens' (the Responses API takes max_output_tokens). Queued day11-15c. 30 of the 30 approved calls are used. Render job (day11-16) retested: NODE_VERSION quoted, production start command verified locally with waitress (health reports public_demo and version, index served, WhatsApp and camera routes 404).
- 2026-10-30: review fix (798ff77) retested; 4 diagnostic muse-wonder-1.0 calls on the 07:01 answer: at 512 max_output_tokens the reply is status incomplete (510 of 512 tokens spent on reasoning, effort max); at 16000 it completes in 16 s with {"verdict": "no_issues", "issues": []}, validated. Queued day11-15d (review budget 16000, incomplete/failed replies named).
- 2026-10-30: deployed 798ff77 to Render Starter (Blueprint aria-home-demo, GitHub access to aria-home only). Verified from outside: /api/health 200 with public_demo true and version 798ff77 (source file); index 200; WhatsApp, camera, live-power and e2e-reset routes 404; recorded muse-spark-1.3 answer served at 02:31; two cookie sessions isolated (B gets 404 reading or deciding on A's investigation); an off-checkpoint time is refused with 400. Clean built-in browser: the guided story runs all 10 steps to 'Warm-by expectation met'; the only host contacted is aria-home-demo.onrender.com; no horizontal overflow at phone width. 11 console errors from expected 400/404 requests (owner-only status probes, a pre-checkpoint default time, follow-ups before they exist): queued day11-17. Overnight check still to do.
- 2026-10-30: recorded 10 muse-wonder-1.0 reviews on b8b948f (10 calls): all no_issues; served by the public demo. Control call (1): the 07:31Z answer with its current temperature falsified to 71 F got issues_found / contradiction citing room-care-1630 (52.0 F), so the reviewer does check. Calls used today for the care batch: 30 answers/reviews + 14 review diagnostics/control (Brad: 'make as many calls as necessary').
- 2026-10-30: video script v2 (C:\aria-home-private\video\vo\care-v2.json): Meta AI in the web chat drafted an app-first structure, then merged it with the original narration's voice; the operator fixed a stray entity tag, a repeated 'noticed the room falling' line and 'furnace' vs 'HVAC'. Brad approved it. Rendered with Kokoro af_bella (care2_01..13.wav, every segment within its slot; model names spoken as words) plus a 3:00 preview track. Also: Meta AI drafted the new judge one-pager (docs/judge-one-pager.md), cleaned by the operator.
- 2026-10-30: Meta AI web chat drafted the submission write-up update and three X posts in parallel tabs. The write-up draft was unusable (it renamed every Muse model to 'llama-*' and compressed sentences to fragments), so the operator wrote the update from Brad's approved text and the same facts (docs/submission.md section 2, 542 words; hosted-demo row now Shown). The X posts were saved to the private draft for Brad to choose from.
- 2026-10-30: re-recorded the 10 muse-wonder-1.0 reviews bound to their exact answers (10 calls, all no_issues; served as bound). Watcher batch (approved 16): 11 calls; 19:20 corrected-and-verified, 04:21-07:01 confirmed, 02:31 and 02:45 rejected with 'invalid JSON at char 0'. One diagnostic call: the reply's first content block is redacted_thinking with no text, the answer is in the second block (a correct 52 F temperature_drop observation). Queued day11-22b to read text blocks only, swept across every reader. 12 of 16 watcher calls used; 4 left for the two checkpoints. Dependencies: Werkzeug 3.1.9, AnyIO 4.14.2 (4.15.1 conflicts with the pinned typing_extensions), certifi 2026.10.23, idna 3.20; clean venv: pip check OK, pip-audit 'No known vulnerabilities found'. Decision-map red-proof on HEAD: 7 failed with assertions (unable_to_verify vs reporting_restored at 04:21; approved vs declined), 9 passed on the new tree.
- 2026-10-30: watcher re-record for 02:31/02:45 (4 + 4 calls, the second set approved by Brad with a 16000-token budget): both recorded as 'no text block in reply (thinking only)'. The direct diagnostic call had returned text, so the recorder is masking the provider's real error (_LiveWatcherProvider drops live['error']). Queued day11-22d. 02:31 and 02:45 ship with 'No recorded watcher run'; the other 6 checkpoints are recorded. Watcher calls used: 20 (16 + 4).
- 2026-10-30: final pre-deploy check caught a real crash: with the recorded watcher and correction files present, the Reasoning tab throws React error #31 (a correction's original_claim is a list of observation objects rendered as a child); 9 main-suite tests fail, and pass with the two files moved aside. Not deployed. Queued day11-23 (safe rendering + per-section error boundary + real-data tests, plus the watcher error-masking fix that day11-22d could not run). Backend 681 passed in a clean venv. Title cards for the video rendered (C:\aria-home-private\video\cards).
- 2026-10-30: deployed fbc9094 to Render Starter after green CI (run 41124883196, 13m35s). Hosted checks: /api/health 200, public_demo true, version fbc9094 (file); WhatsApp, camera, camera-status, live-power and e2e-reset routes 404; the permission text reads 52 F and quiet since 01:30; a visitor's decline shows in their own trace at 06:21 (basis 'visitor investigation'); a second visitor gets 404 on the first visitor's investigation; a malformed decision body gets 400; a forged session cookie gets a fresh session (200). Clean built-in browser: the guided story runs to 'The house was warm by 7:00 — the expectation was met.'; the Reasoning tab renders all 8 sections; zero console errors; zero failed requests; the only host contacted is aria-home-demo.onrender.com; footer reads 'Version fbc9094'. Overnight check still to do.
- 2026-10-30: watcher re-record for 02:31 and 02:45 (Brad approved 5 calls; 3 used) on fbc9094 with a 16000-token budget: 02:31 corrected and verified (the first answer cited stale thermostat evidence as current, rejected by the stale-is-not-current check, and the one revision passed: 'Room temp 52.0F at 02:30, 16.0F below 68F target with falling trend'); 02:45 confirmed. Both are served in public-demo mode with provenance. All 8 care checkpoints now have recorded watcher runs. Watcher calls in total: 23.
