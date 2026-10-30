# ARIA Home submission (Day 9 D9-4, updated Audit 3 Group 4, 2026-10-28)

## 1. Requirements checklist

Status words mean what is actually shown: **Shown** = evidence in this repo points at it; **Disclosed** = a statement by the author, not proof; **Pending** = Brad must do/confirm it.

| Requirement | Status / where shown |
|---|---|
| Public repo containing only event work | **Disclosed, not proven.** https://github.com/BoMa-AI-Cloud/aria-home — [Existing vs new](existing-vs-new.md) and the README declaration list what is said to be new and what pre-existed (name "ARIA", private planning notes, no code). A README declaration is a disclosure, not proof of authorship. A public repo is also not an open-source licence by itself; the licence is the separate MIT [LICENSE](../LICENSE) added 2026-10-28. |
| 3-minute video opens stating what was pre-existing vs built this week, and shows only event-built features | **Shown in script only; video Pending.** Opening line in [Demo video plan](demo-script.md). That the finished video does this is not shown until Brad records/checks it. |
| Video link accessible | **Pending** (Brad) |
| Every team member listed (solo) | **Pending** (Brad, submission form) |
| Meta models only at runtime | **Shown in code for the gated live path.** Runtime calls only muse-spark-1.3 through the Meta Model API behind a gated live provider (`backend/aria_home/provider.py`); mock is the default. This is different evidence from a recorded live run, and different again from a current live call: no current live call is claimed here. Recorded live runs are in [Evaluation](evaluation.md). Baseten Muse Spark Open is evaluation-only, not runtime. |
| Synthetic data only | **Shown for the shipped fixtures; not a certification.** The shipped thermostat, electrical, weather, calendar and contact records are invented and labelled synthetic, and the UI banner reads "SYNTHETIC DATA - demo scenario, not a real home". Synthetic fixtures do not by themselves certify "no PII / no secrets" in every possible file or environment; `.env` files are git-ignored and `.env.example` holds placeholders only. |
| Live product or run instructions | **Shown.** Hosted demo at https://aria-home-demo.onrender.com (Render, public demo mode, synthetic data; deployed commit shown in the footer and in `/api/health`); run instructions in README. Verified from outside on 2026-10-30; the overnight check is still to do. |
| Deadline Nov 4 | **Needs confirmation** (Brad): earlier organizer material said 9 PM ET on November 4; 5 PM ET is Brad's internal target. Submit before the earlier of the two until confirmed. |
| Optional: Most Viral Project post on X, with its link submitted | **Pending** (Brad) |
| Licence | **Shown.** MIT [LICENSE](../LICENSE), Copyright (c) 2026 Bradley Allen Wentzel. Public visibility alone would not grant these rights; the licence file does. |
| Security posture | **Scoped, not "secure".** See [SECURITY.md](../SECURITY.md): local loopback, synthetic data, simulated delivery, no equipment control. It lists what is checked vs not checked and prerequisites for any shared/real-data deployment. No compliance claim is made. |

## 2. Write-up (final text; updated 2026-10-30, approved by Brad)

I live in Petoskey, Michigan, where the winters are long and cold. As my in-laws get older, I've started wondering
what happens when they can't fix something, or can't tell that something is wrong, and nobody is around to help. As
an electrician, I've worked on houses with major damage from a fault that nobody caught in time. ARIA Home is built
to notice sooner and get the right person moving. It does not repair or control anything, and it is not a medical
or emergency service.

ARIA Home answers one question for an older adult's household: will the home be warm by the warm-by time, and if
something looks wrong overnight, who should respond? Try it at https://aria-home-demo.onrender.com (synthetic data,
no sign-in). On a synthetic winter night the furnace stops and the thermostat goes silent at 1:30; an independent
room sensor shows the living area falling toward 52 F. At 2:31 code flags it as at risk before the 07:00 warm-by
time, and ARIA asks the family caregiver: "May I contact the HVAC company?" Only after she approves is the HVAC
request created, with allowed fields only; if she declines, there is no request and ARIA keeps monitoring.
Reconnection alone proves nothing: the goal is verified at 6:21 from independent readings held for 30 minutes, and
the technician's 6:45 voice note counts only as a human report.

Code decides readiness, verification and who is told; Meta models explain and review, never decide. The app has
three pages: House (the verdict and who knows), Reasoning (ARIA's view, a live map of how each decision is made,
with the recorded model answers) and Integrations. Messages are simulated in the hosted demo. As an opt-in test,
the permission request and the HVAC notice can go to my own phone through the WhatsApp Cloud API. Two other
owner-only integrations are off in the demo: a read-only Emporia energy panel and a Nest camera snapshot of my
mechanical room.

Meta models: muse-spark-1.3 explains the code-checked facts at each step under a contract that rejects mismatched
claims, and watches overnight for anomalies that code then confirms. muse-wonder-1.0 gives a recorded second
review of each explanation; in a control test it flagged a deliberately falsified reading. sam-3.1 reads the
synthetic camera frames (recorded); it missed frost, and the miss is shown, which is why "no detection" never lowers
risk. muse-voice-transcribe-1.0 turns the technician's voice note into text, and muse-image-1.0 made the synthetic
frames. The application code was written by muse-spark-1.3 and muse-wonder-1.0 through Claude Code as operator;
while the Model API was unavailable for a few hours, Meta AI in the web chat drafted some code that the operator
applied and retested. Every prompt and answer is in the public build log.

Outside audits reported 12, 10 and 7 defects; each was reproduced and repaired with a regression test, and the
Audit 4 repairs were red-proofed. All ten care-story steps have recorded muse-spark-1.3 answers that passed the
contract checks, each with a muse-wonder-1.0 review. Offline: 22 synthetic cases across 10 scenarios, combined
evidence 22/22. Live (muse-spark-1.3, older trip-home scenarios): 11 of 17 valid on the full run, then 5 of 6 on the
after-arrival rerun; kept verbatim, not re-scored. Limits: small synthetic sample, simulated delivery, no equipment
control.

## 3. Do not claim (from [Demo video plan](demo-script.md))

- That anyone boarded, that a flight, traffic, or baggage state is known, or that ARIA Home is a travel platform (the older trip-home fixtures only).
- That ARIA Home knows where the resident is, or that it senses falls, activity, or health in any way.
- That command acknowledgement, a caregiver acknowledgement, or a technician report proves physical success or caused the recovery.
- That electrical activity proves useful heat, a fault, equipment power, or "no outage".
- That recovery was "instantaneous", that the equipment is fault-free, or that the goal is guaranteed beyond the observed readings.
- That any email, call, message, location, or scene control in the video is real.
- Only "verified recovery of the monitored temperature goal" — never a proven repair cause. Reconnection alone proves nothing; say "on the next sensor update". Missing location is "unavailable", never evidence about her schedule.
- No dollar-loss figures, no "0 hallucinations", no "secure" or "guaranteed" claims.

## 4. Proposed final freeze and recording schedule (proposed, not assumed — needs Brad's approval)

- Final code freeze: proposed end of day November 2, so November 3 is reserved for a clean re-run of the full check (`python -m pytest -q`, typecheck, build, both e2e suites, `record:demo`) with no further edits except wording fixes.
- Recording: proposed November 3 from the frozen tree in default mock/replay mode on a fresh temporary database, following [Recording checklist](recording-checklist.md); a live-inference take only if Brad separately approves that call before filming.
- Submission: before the earlier deadline interpretation (9 PM ET November 4 unconfirmed vs 5 PM ET internal target) until the official time is confirmed.
