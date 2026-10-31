# ARIA Home
Will an older adult's home be warm by morning, and if something looks wrong overnight, who should respond?

**Demo:** https://aria-home-demo.onrender.com (synthetic data, no sign-in)
**Video:** <video link>

I live in Petoskey, Michigan, where the winters are long and cold. As my in-laws get older, I've started wondering what happens when they can't fix something, or can't tell that something is wrong, and nobody is around to help. As an electrician, I've worked on houses with major damage from a fault that nobody caught in time. ARIA Home is built to notice sooner and get the right person moving. It does not repair or control anything, and it is not a medical or emergency service.

It is a solo entry in the Meta Global AI Developer Hackathon (Indie Developer track, theme "Build for Your World").

## What judges should click
1. Open the demo and press Start the warm-by story.
2. Step through the 10 steps with Next. The House tab shows the verdict, the house right now, and who knows.
3. At 2:31, press Approve or Decline on the caregiver permission request. Decline means no HVAC request and ARIA keeps monitoring.
4. Open Reasoning to see ARIA's view: sources, code checks, where the model contributes, the recorded muse-spark-1.3 answer and its muse-wonder-1.0 second review.
5. Open Integrations for what ARIA connects to and which Meta model does what: muse-spark-1.3, muse-wonder-1.0, sam-3.1, muse-voice-transcribe-1.0, muse-image-1.0.
6. Reset my session clears only your own session.

To run it locally, see Try it in 5 minutes below.

**What it is.** ARIA Home answers whether the home will be warm by the warm-by time and who should respond if something looks wrong overnight. Code decides readiness, verification, and who is told; muse-spark-1.3 explains under a contract and muse-wonder-1.0 reviews, sam-3.1 segments synthetic frames, muse-voice-transcribe-1.0 transcribes the synthetic voice note, muse-image-1.0 generated frames offline — models never decide. Notifications are scoped and simulated with allowed fields only, and verification uses later independent readings for temperature-goal verification, not proof of a repair. It does not repair or control anything and is not a medical or emergency service.

## Built during the hackathon vs pre-existing

As the demo video opens: "ARIA is my existing assistant project. Everything you'll see in ARIA Home was built this week with Meta's models, on synthetic data." The on-screen card adds: "Pre-existing: the name ARIA and planning notes. Built this week: all ARIA Home code, with Meta's Muse models."

In short:

- **Built during the hackathon:** all code in this repository — backend, frontend, tests, synthetic scenarios and fixtures, and these docs. No code, data, fixtures or assets from any earlier project are in this repository. The full file-by-file list is in [Existing vs new](docs/existing-vs-new.md).
- **Pre-existing:** the name "ARIA" and private pre-event planning notes and ARIA Home designs (designs, no code). This repository itself contains no code from any earlier project.

## How Meta models are used

At runtime the app normally calls one Meta model, **muse-spark-1.3**, through the Meta Model API, behind a gated live provider. Mock mode is the default and needs no key. Two further Meta models have defined, narrow, non-deciding roles: **muse-wonder-1.0** performs an offline second review of the recorded narrative (flagging unsupported claims, contradictions, missing context, overstated certainty; never changing the readiness status, follow-up schedule, outcomes, verification, or any measurement) — recorded for the ten care checkpoints, each review bound to its exact answer by digest, with pre-binding reviews labelled legacy — and **muse-voice-transcribe-1.0** transcribes the technician's spoken completion report into a `human_report` record (a corroborating human statement only, never a sensor measurement and never admitted to the measurement source list, eligibility, verification, or notifications; the technician's voice note was transcribed once by the operator on 2026-10-31, recorded in `backend/eval/transcripts-20261031.json` (an earlier recording that gave the wrong restart time is kept in `backend/eval/superseded/`), and the public demo replays that recording). A further narrow role, the anomaly watcher (**muse-spark-1.3**), watches the same evidence for overnight anomalies and returns observations with cited evidence ids; every observation is confirmed by an evidence check in code, a failed first attempt gets exactly one revision, and verified corrections are kept as a ledger that is shown to the model as in-context examples only (the model itself is not retrained). The live watcher call is operator-only and never runs from a route; the public demo replays recorded watcher answers only, and an empty or failed watcher never lowers risk. Visual evidence is replay-only: the app always replays recorded sam-3.1 responses over synthetic images and never calls sam-3.1 at runtime for the synthetic story (`SamLiveProvider` in `backend/aria_home/visual.py` is used only by the optional, owner-only Nest snapshot, and only when the owner presses "send it to sam-3.1"). The synthetic images themselves are fixtures only, generated by **muse-image-1.0** and never by a runtime call. Every model the app calls at runtime is a Meta model.
The evaluation can also run Muse Spark Open (meta-models/muse-spark-open-1026, a Meta open-weight model) through Baseten's hosted API, evaluation only.

The investigation uses the **inv-v3** contract, which binds the model's claims to the evidence. The model returns structured `facts[]`; each claim type may cite only its allowed evidence fields, values are checked against the evidence pack, and the facts shown as "Verified facts (checked against the evidence)" are rendered by code, not by the model. The model's own wording stays separate under "Interpretation (model-written, not verified)".

Recorded answers for the public demo are made with `backend/scripts/record_care_answers.py`: dry run by default (prints the 10 `care_home_v1` checkpoints, the planned call count and the output paths, makes no call); live only with `--live --max-calls N --code-snapshot HEAD`, refusing to start when the planned calls exceed N. Each checkpoint gets one muse-spark-1.3 call through the same investigation path the app uses, validated the same way (a rejected answer is written but marked rejected and never served), and each accepted answer gets one muse-wonder-1.0 second review, recorded with the answer's digest plus the prompt and readiness-policy versions so the app shows it only beside that exact answer. The key comes only from environment variables and never appears in output or files.

Watcher recordings for the public demo are made with `backend/scripts/record_care_watcher.py`: dry run by default (prints the 8 `care_home_v1` watcher checkpoints — 19:20 as a quiet control, then 02:31, 02:45, 04:21, 04:51, 06:21, 06:45, 07:01 — the planned call count of up to 16 first-plus-revision calls, and the output path, makes no call); live only with `--live --max-calls N --code-snapshot HEAD`, refusing to start when the planned 16 calls exceed N. Each checkpoint runs through `run_watcher` exactly as the app does (one revision on a failed first attempt, code verification with the Law named on rejection), each entry keeps that verification result, each verified correction is saved through `save_correction_record`, and an empty or failed run is recorded as such and never lowers risk. Recording uses a 180 s timeout (`--timeout-s`) and a 4096-token budget (`--max-tokens`); the app's own watcher defaults are unchanged.

The model may explain a computed status, describe supporting and conflicting evidence, and suggest what observation to make at a follow-up. It may not decide:

- **Readiness** — computed in code in `backend/aria_home/readiness.py` (`on_track`, `at_risk`, `cannot_tell`, `arrival_passed`). The prompt states the computed status and any answer that disagrees is rejected. If no valid answer is produced, the app shows a deterministic summary computed by code.
- **Follow-up scheduling** — computed in code; any time the model supplies is checked and replaced if it falls outside the allowed window.
- **Outcomes and recovery verification** — computed in code from later measurements only (`backend/aria_home/outcomes.py`, `backend/aria_home/verification.py`). Human statements and events never set an outcome or advance a verification stage.

The full rules and thresholds are in [Readiness rules](docs/readiness-rules.md).

## Code vs model: who decides what

| Question | Decided by | Why |
|---|---|---|
| Readiness (`on_track`, `at_risk`, `cannot_tell`, `arrival_passed`, incl. target-at-arrival) | Code (`backend/aria_home/readiness.py`, `readiness-policy-v4`) | The status must follow the same thresholds every time; the model is told the computed status and a disagreeing answer is rejected, so agreement is contract-following, not independent accuracy. |
| Follow-up scheduling | Code (`scheduling.py`, `outcomes.py`) | A model-supplied time outside the allowed window is checked and replaced. |
| Outcome and recovery verification (`telemetry_missing` → `arrival_met`) | Code from later measurements only (`outcomes.py`, `verification.py`) | Human statements, acknowledgements, service visits and the HVAC completion report never set an outcome or advance a stage; only later readings do. |
| Explanation, verified facts vs interpretation | Model explains; code renders the verified facts (inv-v3) | Each model fact may cite only its allowed evidence and values are checked against the evidence pack; the model's own wording stays separate and unverified. |
| Is the home warming / is heat useful? | Code, from temperature evidence only | Watts are not heat: circuit activity can show a circuit is drawing power, but only temperature readings can show warming, so electrical-only evidence never yields `on_track` or a warming stage. |

## ARIA's Laws

The registry is `backend/laws/laws.json` (version `laws-v1`), enforced by `backend/aria_home/laws.py`. Every model output — investigation, watcher observation, second review — is checked by code against each active law; a violation rejects the output and names the law (`law <id>: <reason>`). There are 8 active design laws: `no-heat-from-watts`, `ack-is-not-resolution`, `reconnect-proves-nothing`, `human-report-is-not-measurement`, `no-detection-is-not-safe`, `stale-is-not-current`, `conflicts-block-success`, `no-images-or-personal-in-hvac`, each with a named check function and a regression test proving both rejection and acceptance. One proposed law, `weather-never-decides`, is listed for people to read and never enforces — there is no route that activates a law. Seven process laws record the release-process rules; six name an automated pytest check and one (`process-release-needs-approval`) is checked at review. The "ARIA's Laws" view in the app shows the registry, the recorded watcher observations with their provenance, and the correction ledger.

Possible uses (not measured): vacant rentals, seasonal homes, small buildings.

The application code itself was written by **muse-wonder-1.0** and **muse-spark-1.3** through Claude Code. Every prompt and answer, failed runs included, is in [docs/build-log/](docs/build-log/README.md). The operator (Claude, directed by Brad Wentzel) wrote the prompts, reviewed and tested each change, ran the approved installs and live smoke tests, and pushed the commits.

## Results

These are builder-labeled cases on synthetic data — a small sample, not a benchmark of real homes. Full details: [Evaluation](docs/evaluation.md).

**Offline (deterministic, no model):** 22 cases across 10 synthetic scenarios, each run with all sources combined and with only one source kind at a time. Verification is scored for the 10 `demo_video_v1` and `care_home_v1` cases (the scenarios with room-sensor records); target-at-arrival is scored for the 7 `arrival_passed` cases.

| Condition | Readiness correct (of 22) | Target at arrival (scored) | Verification (scored) | Fully correct (of 22) |
|---|---|---|---|---|
| Combined (all sources) | 22 | 7 (7) | 10 (10) | 22 |
| Thermostat only | 16 | 7 (7) | 2 (10) | 12 |
| Room sensor only | 17 | 2 (7) | 2 (10) | 4 |
| Electrical only | 9 | 0 (7) | 2 (10) | 2 |
| Calendar only | 9 | 0 (7) | 2 (10) | 2 |

Combined evidence matches every expected readiness label and every scored verification stage. Single-source conditions mostly fall back to unsupported answers (`cannot_tell`, `telemetry_missing`, `unable_to_verify`) rather than asserting the opposite. Three findings stand out: during the overnight outage, thermostat-only evidence cannot support even a current-temperature claim, while independent room readings still show no warming; electrical activity alone never supports a useful-heat claim — only temperature evidence can show warming; and the three `visual_*` scenarios add recorded sam-3.1 segmentation over synthetic images — a water detection supporting `at_risk` alongside low indoor temperature, and two zero-object cases (including the recorded frost-pipe false negative) reported as no detection, never as an all-clear — while visual evidence never yields `on_track`, a warming stage, or a verification success. The `care_home_v1` night frames carry the same recorded treatment: the two frost misses stay `at_risk` and are shown as "missed by the model".

**Live (operator-run, approved by Brad):** the recorded runs are registered in [Evaluation](docs/evaluation.md) with model ids, provider routes, dates, code snapshots and policy versions — the full run (snapshot 77cafc9, 2026-10-28, inv-v2) was exactly 17 calls, the 17 eval cases on muse-spark-1.3 via the Meta Model API: 11 valid answers with 11/11 readiness agreement, 6 rejected, all six rejections after-arrival cases citing a stale or superseded reading as current; the after-arrival rerun (snapshot efdff57, inv-v3) was exactly 6 calls, only the six after-arrival cases: 5 valid with 5/5 readiness agreement, 1 rejected on a genuine claim-check catch (the answer said "below target" against the resolved target_gap fact). The rerun is not a full re-run, so the two runs are cited separately, never merged into one number. Both recorded live runs predate the care story and used the trip-home scenarios; they are kept verbatim as historical runs and are not re-scored against `care_home_v1`. Earlier recorded runs (the pre-Audit-2 run on snapshot 53a06bd, 2026-10-26: 24 calls, 0 rejected; the current-code comparison on snapshot 114be6a, 2026-10-27) are kept in [Evaluation](docs/evaluation.md) and are superseded, not current. Readiness agreement is enforced (the model is told the computed status and a mismatch is rejected), so agreement shows the models followed the contract, not that they judged readiness independently. No recorded live run is a current live call, and no cost figure is recorded, so none is stated.

## Try it in 5 minutes

Supported versions: Python 3.12 and Node 22 (CI, `.github/workflows/ci.yml`); developed locally on Python 3.12.7 / Node 25.9.0. Backend pins are exact locks in `backend/requirements.lock` (runtime), `backend/requirements-optional.lock` (optional PyEmVue graph) and `backend/requirements-dev.lock` (dev/test pytest); CI installs and audits exactly those locks. Mock mode is the default: no environment variables and no API key are needed, and the investigation is labeled "MOCK - example answer, not live inference".

Terminal 1 — backend, from the repo root:

```
# Windows PowerShell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.lock
pip install -r requirements-optional.lock
pip install -r requirements-dev.lock
```

```
# macOS / Linux shells
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
pip install -r requirements-optional.lock
pip install -r requirements-dev.lock
```

```
python -m flask --app aria_home.app:create_app run --port 5000
```

Terminal 2 — frontend, from the repo root:

```
cd frontend
npm ci
npm run dev
```

Open the page it serves on port 5173 (it proxies `/api` to port 5000). Stop each server with Ctrl+C.

**The care story:** in "Demo controls (synthetic replay)", set "Scenario" to "Winter night, older adult at home (guided story)" — selecting it runs the investigation at 19:03. Then click the replay buttons in order: **19:20, 02:31, 02:45, 04:21, 04:51, 06:21, 06:45, 07:01**. Watch the Outcome headline move from "Thermostat telemetry missing" (02:31 — the room sensor reads 52 F and is not warming) to "Thermostat reporting restored" (04:21 — reconnection alone closes nothing), "Warming observed" (04:51), "Temperature goal verified" (06:21 — the 68 F goal held 30 minutes), and "Warm-by expectation met" (07:01, evaluated from readings received by the 07:00 warm-by time). At 02:45, check the delivered HVAC company card under "Notifications (simulated delivery)" and its "fields sent:" line; click "Acknowledge (simulated)" on the family caregiver card and confirm the Outcome headline does not change. At 06:45, find the "HVAC completion report" card on the simulated timeline — it appears only after the 06:21 verification, as corroboration only. The older trip-home scenarios stay available in the scenario list as secondary fixtures. The full shot list is in [Demo video plan](docs/demo-script.md).

**Tests:** with the backend environment active, `python -m pytest -q` runs the backend tests. In a third terminal from `frontend/`:

```
npm run build
npm run typecheck
npm run test:e2e
```

`npm run test:e2e` starts its own backend and frontend servers on ports 5000 and 5173, so stop the dev servers first. It starts the backend with plain `python -m flask ...`, so the backend virtual environment must be active in that terminal (or Flask must be installed for that python). Activate it first: PowerShell `..\backend\.venv\Scripts\Activate.ps1`, macOS/Linux `source ../backend/.venv/bin/activate`. It runs the Playwright end-to-end test in the installed Google Chrome (no browser download).

**Recording footage:** `cd frontend && npm run record:demo` drives the real running frontend and backend at 1280x720 in mock mode on a fresh database, and writes one `.webm` clip per storyboard segment to `frontend/recordings/` (ignored by git). It starts the backend with plain `python -m flask ...`, so the backend virtual environment must be active in that terminal (or Flask must be installed for that python): PowerShell `..\backend\.venv\Scripts\Activate.ps1`, macOS/Linux `source ../backend/.venv/bin/activate`.

**Live mode (optional):** set `ARIA_HOME_MODEL_ENABLED=1` to enable live model calls (anything else stays in mock mode), `ARIA_HOME_PROVIDER_URL` to the model API base host, `ARIA_HOME_MODEL_ID` to the model to call, and `MODEL_API_KEY` to the API key (sent as `Authorization: Bearer <key>`). Keys live only in local environment variables; `.env` files are ignored.

**WhatsApp test delivery (optional, off by default):** set `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TEST_RECIPIENT` (the owner's own verified test number, which stands in for the HVAC company) plus `ARIA_HOME_WHATSAPP_LIVE=1`. Only then does the delivered HVAC-company card offer "Send to my test phone (WhatsApp)", an explicit `POST /api/notifications/<notification_id>/whatsapp` that sends the allowed notice once via the WhatsApp Cloud API (`POST https://graph.facebook.com/v25.0/{phone_number_id}/messages`, plain-text message starting "ARIA Home test (synthetic scenario)", rendered from the exact allowlisted payload fields); a 200/201 response carrying a message id makes the card read "Accepted by the WhatsApp API (message id …); delivery to the handset is not confirmed" — an HTTP success alone is not confirmed delivery, and a response without a usable id is recorded as "unknown", never as success. If the card reads "unknown", check the test phone manually and do not POST again: unknown and failed attempts are terminal and the app never resends (a repeat returns already_attempted). `GET /api/follow-ups/<investigation_id>` never sends — replay, refresh and repeated GETs make zero HTTP calls. With anything missing, the notice stays exactly as today ("Simulated, no message was sent") and the button is hidden (`GET /api/whatsapp/status` reports only whether live delivery is configured, never any value). Never sent to any other number; at most one real send per notification id ever, so a second POST never re-sends. Field audit: [WhatsApp audit](docs/whatsapp-audit.json), generated from the code. In the care story the same opt-in also lets the permission card send ARIA's question to the family caregiver ("May I contact the HVAC company?") once to that test number, which then stands in for the caregiver; she answers with Approve or Decline in the app, and the HVAC request is created only after approval.

**Emporia live panel (optional, off by default):** set `EMPORIA_EMAIL`, `EMPORIA_PASSWORD` plus `ARIA_HOME_EMPORIA_LIVE=1`. Only then does `GET /api/live-power` return the owner's real per-circuit watts (read-only via pyemvue, which reports interval energy in KilowattHours at 1 s scale, converted to average watts; cached 60 s, `source: "live-read-only (owner's home)"`) and the frontend shows a small separate panel, "Your real home, right now (live, read-only, Emporia Vue)". The panel is hidden otherwise, so the judge demo is unchanged. Live watts are display only: never evidence for readiness, warming or verification, never in the evidence pack (watts are not heat).

**Nest camera snapshot (optional, off by default, owner only):** for a Google Nest Cam Indoor in the mechanical room. Set `NEST_PROJECT_ID`, `NEST_CLIENT_ID`, `NEST_CLIENT_SECRET` (a Device Access project and its Google OAuth client), run `python backend/scripts/nest_auth.py` once (it opens Google's consent page, stores only the refresh token as the Windows user variable `NEST_REFRESH_TOKEN`, and prints the camera names it can see), optionally set `NEST_DEVICE_NAME`, then set `ARIA_HOME_NEST_LIVE=1`. Only then does a separate panel, "Live camera (owner's mechanical room)", appear. Each button press is one explicit `POST /api/camera/snapshot`: ARIA starts the camera's stream through the Smart Device Management API, grabs exactly one frame with ffmpeg, and always stops the stream again, even when ffmpeg fails. The frame stays in the git-ignored `backend/instance/nest-snapshots/`. Only the second button (`{"segment": true}`) uploads that one real image to Meta's sam-3.1 to look for frost, a water puddle and an indicator light, and the panel says so. The live frame is never evidence for the synthetic story's readiness or verification. The routes do not exist in public-demo mode, and the app refuses to start in public-demo mode with `ARIA_HOME_NEST_LIVE` set. Tokens and the stream URL (which carries a token) never appear in responses, logs or the database.

**Visual evidence (synthetic images, recorded segmentation):** the four images under `backend/fixtures/visual/` are synthetic, generated by muse-image-1.0; each `*.sam.txt` is the recorded raw sam-3.1 response for that image and phrase. The six home-camera frames under `backend/fixtures/visual/care/` are attached to `care_home_v1` the same way (night frames during the cooling, morning frames after recovery), labelled "Synthetic camera frame (muse-image-1.0) - segmentation by sam-3.1 (recorded)". `GET /api/visual` serves the recorded observation (boxes, counts, caption) and `GET /api/visual/image` serves the image bytes; both are gated by `received_at <= at` like every other record. The synthetic story is replay-only: setting `ARIA_HOME_VISUAL_LIVE=1` changes nothing, and no synthetic image is ever sent anywhere (the one exception is the owner's own Nest frame, uploaded only on that explicit button press) — HVAC payloads may carry only the observation line "visual observation: water detected (synthetic image)" (the unintegrated adapter would POST image bytes if anyone ever wired it in). Visual evidence never yields `on_track`, `warming_observed`, `goal_verified` or `arrival_met`, and zero detected objects is reported as no detection, never as an all-clear. Full policy: [Readiness rules](docs/readiness-rules.md).

## Public demo mode (for hosting)

One process serves the built React app and a restricted API — a judge opens one URL with no install, account, key or terminal. Build the frontend once (`cd frontend && npm ci && npm run build`), then from `backend/` with the virtual environment active:

```
# Windows PowerShell
$env:ARIA_HOME_PUBLIC_DEMO = "1"
python -m flask --app aria_home.app:create_app run --port 5000 --no-debug
```

```
# macOS / Linux shells
ARIA_HOME_PUBLIC_DEMO=1 python -m flask --app aria_home.app:create_app run --port 5000 --no-debug
```

If waitress is installed on the host, serve the created app object with it instead of the Flask dev server; otherwise the Flask command above, debug off, is the supported start. Set ARIA_HOME_RELEASE_COMMIT to the deployed commit (or write it to backend/RELEASE_COMMIT at build time); /api/health then reports it under `version`, and the footer shows "Version <short commit>". Without either, it reports "unknown" rather than guessing. Hosted link: Pending deployment.

**Render:** the repo-root `render.yaml` blueprint defines one web service (`aria-home-demo`, Python runtime, Starter plan, Ohio region, branch `main`, `autoDeploy: false` so a deploy happens only when the operator triggers a specific commit). The build installs `backend/requirements.lock`, builds the frontend, and writes `$RENDER_GIT_COMMIT` to `backend/RELEASE_COMMIT`, so the version in the footer equals the deployed commit. The start command is `cd backend && waitress-serve --listen=0.0.0.0:$PORT --threads=8 --call aria_home.app:create_app` with health check `/api/health`, and the only demo env vars are `ARIA_HOME_PUBLIC_DEMO=1` and `ARIA_HOME_PUBLIC_DEMO_DIR=/tmp/aria-home-sessions` — no keys, tokens, or live flags. What is public is the synthetic demo only. The recorded care answers are committed under `backend/eval/recorded/`, so the hosted app serves the recorded muse-spark-1.3 answers for the ten care checkpoints and the labeled fallback ("No recorded model response for this snapshot") anywhere else.

Boundaries, enforced in code (`backend/aria_home/public_demo.py`, `backend/aria_home/recorded.py`, `backend/tests/test_public_demo.py`):

- No live, delivery, sensor or paid paths are reachable: the provider, power-context, live-power, WhatsApp and test-hook routes are not registered (404), live paths run mock/recorded only, and the app refuses to start when any live flag is set alongside the demo flag (fail closed).
- Only the 8 demo scenarios at their replay checkpoints answer; anything else is rejected (unknown scenario 404, off-checkpoint time 400). Request bodies are capped at 4 KB and must be JSON; errors are JSON with no stack traces; debug is off.
- Each visitor gets an isolated SQLite session (random opaque id in an HttpOnly SameSite=Lax cookie, server-side file name). Sessions idle over 2 h are deleted, at most 500 are kept, total session disk defaults to 512 MiB (`ARIA_HOME_PUBLIC_DEMO_MAX_BYTES`, bytes; empty or invalid falls back to the default, never unlimited) so the 500-session cap binds first at ~0.73 MB per investigated session, and `POST /api/session/reset` clears only the caller. Acknowledgements never change readiness, outcome or verification.
- A model answer is shown only for an exact recorded match (scenario, replay time, evidence revision, model id, contract/policy versions) with per-answer provenance (model, route, recorded timestamp, input revision, code snapshot, validation result); otherwise the deterministic summary with the label "No recorded model response for this snapshot". A recorded review is shown only beside the answer whose digest matches the digest recorded with the review; a mismatch shows no review and says the review does not match the answer. A matching review is a bounded check, not proof the narrative is true.

## Safety and honesty rules

- **Synthetic data only.** Every thermostat, electrical, weather, calendar and contact record is invented for the demo and labeled synthetic, as are the four trip visual-evidence images (muse-image-1.0 fixtures), the six care home-camera frames and their recorded sam-3.1 responses. No credentials, real travel details or personal contacts appear anywhere. The only real data the app can ever touch are the two optional real-data paths, both off by default and both absent in the public demo: the Emporia live-watts panel and the owner-only Nest camera snapshot. Both are display only and never stored in the repo.
- **Simulated delivery and control.** Notifications are simulated only by default — every card reads "Simulated, no message was sent", and there is no real email, SMS or push channel. The one exception is the optional WhatsApp test delivery above: only the allowed HVAC-company notice, only to the owner's own test number, at most once per notice. The app reads and explains; it never operates equipment, and scene/command acknowledgements are simulated timeline events that change no physical state.
- **Scoped notifications.** Each audience (resident/homeowner, family caregiver, HVAC company) has an allowlist of fields it may receive, enforced in code with refusals recorded. The resident consented to what each audience may be told (resident: everything; caregiver: home status and observations; HVAC: property, access note, observations only). The HVAC request carries only property, access, caregiver contact and relevant observations — never itinerary, email or location — and is sent only after a caregiver authorization event. The older property-manager role survives only in the secondary trip-home fixtures.
- **Acknowledgement is not resolution.** A simulated acknowledgement is recorded as its own event and never changes readiness, outcome or verification. The same applies to service visits and the HVAC completion report, which is corroboration only and never sets an outcome.
- **No future data in replay.** Records, trip revisions, confirmations, events and notifications are visible only at or after their received/available times, so a replay at any moment shows only what ARIA could have known then.
- **Bounded claims.** Circuit watts never prove useful heat, a fault or equipment power. Verified recovery means recovery of the monitored temperature goal, never a proven repair cause or fault-free equipment. A mock answer is never presented as a fresh live response.

## Known limits

From the day handoffs and the [feature freeze](docs/freeze.md) (initial freeze 2026-10-26 at 4d3bacb, lifted 2026-10-28 for the Audit 3 repair and the integrations that follow; a final freeze date will be set later):

- All data is synthetic and every message, scene, visit and report is simulated; there are no real channels except the optional WhatsApp test delivery to the owner's own test number, and ARIA Home controls no equipment. Email, location, scene, confirmation and service-visit moments have no dedicated UI and appear as labeled simulated timeline cards.
- Room-sensor and blower mappings are synthetic assumptions, not measured physical behaviour. Readiness thresholds are fixed constants, not fitted to a home, and projection is a linear extrapolation that ignores weather, equipment cycling and occupancy.
- The notification allowlists are reviewed by hand, not by an external privacy review; the HVAC request is gated only by a synthetic caregiver authorization event.
- The evaluation sample is small and builder-labeled: 22 offline cases, one live run per case on the older trip-home scenarios. The live agreement rate shows the models followed the readiness contract, not independent readiness judgment, and input-token counts are unreliable.
- The committed live results used the pre-Day-7 readiness labels; Day 7 added `arrival_passed` with target-at-arrival, which the live run did not exercise.
- The older follow-up rule and the verification stage can disagree; the UI headlines the verification stage.
- `GET /api/follow-ups` is not read-only: moving the replay forward records that checkpoint's outcome and any HVAC or caregiver notification now due. It skips writes when rewinding and never duplicates a record, but a strict REST design would move this into an explicit evaluation step.
- The claim check is bounded — structured facts plus a phrase/number filter — not a semantic verifier of arbitrary prose.
- The Audit 3 repair and the integrations that follow are in scope after the freeze lift on 2026-10-28. Two optional live integrations are implemented, both off by default: WhatsApp test delivery of the allowed HVAC notice to the owner's own test number, and the read-only Emporia live-watts panel. Visual segmentation is replay-only recorded responses (no live call). No real email, SMS (other than that test number), location, travel or equipment-control integration is implemented — those stay synthetic/simulated (future directions, no code: [Architecture — future](docs/architecture-future.md)).

Day-by-day record: [Day 1 handoff](docs/day1-handoff.md) · [Day 2 handoff](docs/day2-handoff.md) · [Day 3 handoff](docs/day3-handoff.md) · [Day 4 handoff](docs/day4-handoff.md) · [Day 5 handoff](docs/day5-handoff.md) · [Day 6 handoff](docs/day6-handoff.md) · [Timeline](docs/timeline.md) · [User-test kit](docs/usability.md) · [Feature freeze](docs/freeze.md)

Submission: [Submission checklist and write-up](docs/submission.md)

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Bradley Allen Wentzel. Security scope and reporting: [SECURITY.md](SECURITY.md).

Further reading: [Judge one-pager](docs/judge-one-pager.md) · [Architecture diagram](docs/architecture.svg) · [Audit 3 defect matrix](docs/audit-3.md) · [Red-team notes](docs/red-team.md) · [Architecture — future](docs/architecture-future.md) · [Killer-apps analysis (hypothetical)](docs/killer-apps-analysis.md) · [HVAC field audit](docs/fields-audit.json) · [WhatsApp audit](docs/whatsapp-audit.json)
