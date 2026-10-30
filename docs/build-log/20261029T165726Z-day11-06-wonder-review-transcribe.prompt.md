ARIA Home: two more distinct Meta-model roles, built offline (approved by Brad, 2026-10-29). DO THE WORK NOW in this
turn. IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own;
keep editing and running commands until the done-condition holds. No live calls, no installs, no network beyond
127.0.0.1, no git, NO helper scripts outside tests. Fakes only in tests. Do not weaken any test. Keep all working-tree
changes. Shell starts in C:\aria-home; prefix frontend commands with `cd frontend && `. Do not end your turn until
`cd backend && python -m pytest -q`, `cd frontend && npm run typecheck` and `cd frontend && npm run test:e2e` pass.

The operator will later run Brad's approved batch through the code you write (16 muse-wonder-1.0 reviews, 1
muse-voice-transcribe-1.0 call) and commit the recordings; you only build and test the code paths now.

A. muse-wonder-1.0 structured second review (backend/aria_home/review.py).
   - Input: a recorded muse-spark-1.3 answer that passed validation plus its evidence pack. Output contract (JSON):
     {"verdict": "no_issues" | "issues_found", "issues": [{"kind": "unsupported_claim" | "contradiction" |
     "missing_context" | "overstated_certainty", "evidence_ids": [...], "note": "<= 200 chars"}]} — evidence
     references and concise conclusions only, never private reasoning.
   - Request: POST https://api.meta.ai/v1/responses, model "muse-wonder-1.0", Bearer MODEL_API_KEY, same timeout and
     no-retry handling as the existing provider; a live helper callable only by an explicit operator function, never by
     any route, GET or the public-demo mode; add muse-wonder-1.0 to the review allowlist only.
   - Validate the output strictly (unknown verdict/kind, ids not in the pack, overlong notes -> invalid review, kept
     and shown as invalid). A review never changes readiness, verification, permissions or the answer's validity;
     "no_issues" is not sensor verification.
   - Recorded reviews live in backend/eval/reviews-*.json with provenance (model, provider route, recorded timestamp
     from the file, the reviewed answer's case id and input revision). Show them in the UI and the public-demo
     "Model contributions" panel next to the answer they review, only when the reviewed answer is the one displayed.
B. muse-voice-transcribe-1.0 for a synthetic technician voice note (backend/aria_home/transcribe.py).
   - Fixture: backend/fixtures/voice/technician-note-synthetic.wav (synthetic, Kokoro voice, mono 16-bit 24 kHz) and
     its script technician-note-script.txt. Request (dev.meta.ai/docs/speech-to-text): POST
     https://api.meta.ai/v1/asr/transcribe, Bearer key, multipart parts `request` (application/json:
     {"model":"muse-voice-transcribe-1.0","audioEncoding":"WAV","mode":"PUSH_TO_TALK"}) and `audio` (the WAV);
     response JSON fields sessionId, transcript, audioDurationMs, turns. Live helper callable only by an explicit
     operator function; validate the response shape.
   - A recorded transcript becomes a human-report record (source kind human_report, synthetic, "transcribed by
     muse-voice-transcribe-1.0 from a synthetic voice note") attached to demo_video_v1 at the existing completion-report
     time; it is corroboration only and never a measurement, never sets an outcome or verification, and its text never
     enters HVAC/WhatsApp payloads beyond what the existing allowlist already permits (it permits none of it).
   - Show the transcript, its provenance and "human report, not a sensor measurement" in the UI.
C. Tests: review parser/validator (valid, invalid verdict, foreign evidence ids, overlong note); review never changes
   readiness/verification; review shown only beside the matching answer; transcription response parser (valid,
   missing transcript, wrong types); human report from transcript never advances verification and never appears in
   notification payloads; no route or GET can call either live helper (spy); public-demo mode never constructs them.
D. Docs: README model table and docs/public-demo-plan.md steps 5-6 (built offline; recordings pending the operator's
   approved run), docs/architecture.svg roles, docs/evaluation.md a placeholder section that says no review or
   transcription has been recorded yet (the operator fills in real results).
Final answer: files changed, tests added, and the REAL output lines of every command.

