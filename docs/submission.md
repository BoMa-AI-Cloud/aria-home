# ARIA Home submission (Day 9 D9-4, updated Audit 3 Group 4, 2026-10-28)

## 1. Requirements checklist

Status words mean what is actually shown: **Shown** = evidence in this repo points at it; **Disclosed** = a statement by the author, not proof; **Pending** = Brad must do/confirm it.

| Requirement | Status / where shown |
|---|---|
| Public repo containing only event work | **Disclosed, not proven.** https://github.com/BoMa-AI-Cloud/aria-home — [Existing vs new](existing-vs-new.md) and the README declaration list what is said to be new and what pre-existed (name "ARIA", private planning notes, no code). A README declaration is a disclosure, not proof of authorship. A public repo is also not an open-source licence by itself; the licence is the separate MIT [LICENSE](../LICENSE) added 2026-10-28. |
| Demo must only highlight what was built during the Hackathon, and judges must clearly identify it (Participant Guide; failure risks disqualification) | **Script opens with this statement, including who wrote the code; video Pending.** Three-minute video, judged with the code and live product. |
| Video link accessible | **Pending** (Brad) |
| Every team member listed (solo) | **Pending** (Brad, submission form) |
| Uses Meta's models (Stage One, pass/fail) | **Shown in code.** Runtime calls go through the Meta Model API behind a gated live provider (`backend/aria_home/provider.py`); mock is the default. Using only Meta models at runtime is this project's own design choice, not a guide rule. |
| No code, data or assets without rights (Participant Guide) | **Disclosed.** The public demo uses invented fixtures labelled synthetic; that is this project's own design choice, not a guide rule. The video's one labelled real-equipment segment shows the owner's own furnace and panel. `.env` files are git-ignored and `.env.example` holds placeholders only. |
| Live product or run instructions | **Shown.** Hosted demo at https://aria-home-demo.onrender.com (Render, public demo mode, synthetic data; deployed commit shown in the footer and in `/api/health`); run instructions in README. Verified from outside on 2026-10-30; the overnight check is still to do. |
| Deadline Nov 4 | **9:00 PM EST** via the CV platform (Participant Guide); late submissions are not considered. Internal target 5 PM ET. |
| Optional: Most Viral Project post on X, with its link submitted | **Pending** (Brad) |
| Licence | **Shown.** MIT [LICENSE](../LICENSE), Copyright (c) 2026 Bradley Allen Wentzel. Public visibility alone would not grant these rights; the licence file does. |
| Security posture | **Scoped, not "secure".** See [SECURITY.md](../SECURITY.md): local loopback, synthetic data, simulated delivery, no equipment control. It lists what is checked vs not checked and prerequisites for any shared/real-data deployment. No compliance claim is made. |

## 2. Write-up (updated 2026-10-30, approved by Brad; story passages updated 2026-11-01; story and code-authorship passages updated 2026-11-02, CONFIRM Brad's approval of this version)

I live in Petoskey, Michigan, where the winters are long and cold. As my in-laws get older, I've started wondering
what happens when they can't fix something, or can't tell that something is wrong, and nobody is around to help. As
an electrician, I've worked on houses with major damage from a fault that nobody caught in time. ARIA Home is built
to notice sooner and get the right person moving. It does not repair or control anything, and it is not a medical
or emergency service.

ARIA Home answers one question for an older adult's household: will the home be warm by the warm-by time, and if
something looks wrong overnight, who should respond? Try it at https://aria-home-demo.onrender.com (synthetic data,
no sign-in). On a synthetic winter night the evening starts warm and on track, and at 9:00 PM the room is slowly falling but
still on track. At 9:41 PM it is 66 F, 2 F below the target: code flags it as at risk, and ARIA records a notice and
asks nobody. At 10:46 PM it is 62 F, 6 F below, and ARIA asks the family caregiver: "May I contact the HVAC company?"
The 2 F and 6 F are configured settings, not safety limits, and a backstop still asks when the house is at risk within
2 hours of the warm-by time. The demo checks at set story times. She approves right away, and only then is the HVAC
request created, with allowed fields only. A technician is on site by 11:30 PM and finishes the repair at 4:15. Until
then the room keeps falling: the thermostat goes silent at 1:30 and the room reaches 52 F. If she declines, no contact is made
— no request, visit, report or voice note — and the room readings are still checked at each later step: the room
holds 52 F, verification never leaves missing thermostat telemetry, and 07:01 states the miss against the 68 F goal.
On the approved path, reconnection alone proves nothing: the goal is verified at 6:21 from independent readings held for 30 minutes, and
the technician's 6:45 voice note counts only as a human report.

Code decides readiness, verification and who is told; Meta models explain and review, never decide. The app has
three pages: House (the verdict and who knows), Reasoning (ARIA's view, a live map of how each decision is made,
with the recorded model answers) and Integrations. Messages are simulated in the hosted demo. As an opt-in test,
the permission request and the HVAC notice can go to my own phone through the WhatsApp Cloud API. Two other
owner-only integrations are off in the demo: a read-only Emporia energy panel and a Nest camera snapshot of my
mechanical room. The video shows them in one labelled segment on my own furnace and panel, apart from the synthetic
story; sam-3.1 missed a visible red indicator light there, which is why finding nothing is never an all-clear.

Meta models: muse-spark-1.3 explains the code-checked facts at each step under a contract that rejects mismatched
claims, and at each story step looks for anomalies that code then confirms. muse-wonder-1.0 gives a recorded second
review of each explanation; in a control test it flagged a deliberately falsified reading. sam-3.1 reads the
synthetic camera frames (recorded); it missed frost, and the miss is shown, which is why "no detection" never lowers
risk. muse-voice-transcribe-1.0 turns the technician's voice note into text, and muse-image-1.0 made the synthetic
frames. Meta's Muse models (muse-spark-1.3 and muse-wonder-1.0, through Claude Code as operator) wrote most of the
application code; while the Model API was unavailable for a few hours, Meta AI in the web chat drafted some code that
the operator applied and retested. Claude (Anthropic) wrote the 2 F and 6 F alert rule and the final wording pass under
my direction, recorded in docs/build-log/operator-log.md. Every Muse prompt and answer is in the public build log.

Outside audits reported 12, 10 and 7 defects; each was reproduced and repaired with a regression test, and the
Audit 4 repairs were red-proofed. Recorded-model coverage is per-step (a muse-spark-1.3 answer that passed the
contract checks, each with a muse-wonder-1.0 review). The main story has recordings at all 11 steps, on prompt inv-v5
[CONFIRM after the 11-step re-recording]; a step without a matching recording shows the labelled "No recorded model
response for this snapshot" fallback, and the derived decline branch shows that fallback at its later changed
checkpoints. Model-value scores were measured on the earlier prompt inv-v3, not re-scored on the current inv-v5. Offline: 22 synthetic cases across 10 scenarios, combined
evidence 22/22. Live (muse-spark-1.3, older trip-home scenarios): 11 of 17 valid on the full run, then 5 of 6 on the
after-arrival rerun; kept verbatim, not re-scored. Limits: small synthetic sample, simulated delivery, no equipment
control. Explanation quality from the current prompt has not been measured, and real-world effectiveness has not been
established.

## 3. Do not claim (from [Demo video plan](demo-script.md))

- That anyone boarded, that a flight, traffic, or baggage state is known, or that ARIA Home is a travel platform (the older trip-home fixtures only).
- That ARIA Home knows where the resident is, or that it senses falls, activity, or health in any way.
- That command acknowledgement, a caregiver acknowledgement, or a technician report proves physical success or caused the recovery.
- That electrical activity proves useful heat, a fault, equipment power, or "no outage".
- That recovery was "instantaneous", that the equipment is fault-free, or that the goal is guaranteed beyond the observed readings.
- That any email, call, message, location, or scene control in the video is real, except the one labelled real-equipment segment, which shows the owner's own furnace and panel.
- Only "verified recovery of the monitored temperature goal" — never a proven repair cause. Reconnection alone proves nothing; say "on the next sensor update". Missing location is "unavailable", never evidence about her schedule.
- That ARIA monitors continuously (the demo checks at set story times), or that 2 F and 6 F are safety limits (they are configured settings).
- That inv-v3 scores validate the current inv-v5 prompt, that every branch has recorded model answers, or that real-world effectiveness is established.
- That Muse wrote all the code. Meta's Muse models wrote most of it; Claude (Anthropic) wrote the 2 F and 6 F alert rule and the final wording pass.
- No dollar-loss figures, no "0 hallucinations", no "secure" or "guaranteed" claims.

## 4. Proposed final freeze and recording schedule (proposed, not assumed — needs Brad's approval)

- Final code freeze: proposed end of day November 2, so November 3 is reserved for a clean re-run of the full check (`python -m pytest -q`, typecheck, build, both e2e suites, `record:demo`) with no further edits except wording fixes.
- Recording: proposed November 3 from the frozen tree in default mock/replay mode on a fresh temporary database, following [Recording checklist](recording-checklist.md); a live-inference take only if Brad separately approves that call before filming.
- Submission: official cutoff November 4, 9:00 PM EST (Participant Guide); internal target 5 PM ET.
