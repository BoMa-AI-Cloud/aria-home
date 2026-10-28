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
