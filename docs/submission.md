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
| Live product or run instructions | **Run instructions Shown; hosted live product Pending.** Run instructions are in README "What judges should click" / "Try it in 5 minutes"; no hosted URL exists (see [Day 9 handoff](day9-handoff.md)). Live-provider support (code), recorded live runs (files), and a current live call (not made for Audit 3) are three different kinds of evidence and are not interchangeable. |
| Deadline Nov 4, 5 PM ET | **Pending** (Brad, submit before the deadline) |
| Optional: Most Viral Project post on X, with its link submitted | **Pending** (Brad) |
| Licence | **Shown.** MIT [LICENSE](../LICENSE), Copyright (c) 2026 Bradley Allen Wentzel. Public visibility alone would not grant these rights; the licence file does. |
| Security posture | **Scoped, not "secure".** See [SECURITY.md](../SECURITY.md): local loopback, synthetic data, simulated delivery, no equipment control. It lists what is checked vs not checked and prerequisites for any shared/real-data deployment. No compliance claim is made. |

## 2. Write-up (final text)

I live in Petoskey, Michigan, where the winters are long and cold. As an electrician, I've worked on houses with
major damage from a fault that nobody caught in time. ARIA Home is built to help notice sooner and get the right
person moving. It does not repair or control anything.

ARIA Home answers one question for someone travelling home: will my property be ready when I arrive, and if
something looks wrong, who should respond? It combines trip, thermostat, room-sensor, electrical, weather and
visual evidence (all synthetic) into one readiness picture. Code decides readiness, follow-ups and outcomes;
muse-spark-1.3 explains only code-checked facts, and claim checks reject any answer that cites the wrong evidence
or presents an old reading as current. Electrical activity is never treated as heat, a visual "nothing detected"
is never treated as all-clear, an acknowledgement is not a resolution, and recovery is verified only from later
independent temperature readings. This is temperature-goal verification, not proof of a repair.

Notifications are scoped per audience with recorded refusals and stay simulated by default. As an opt-in test,
the HVAC request was delivered to my own phone through the WhatsApp Cloud API with only its allowed fields.

Meta models: muse-spark-1.3 at runtime; sam-3.1 segments synthetic images (recorded replay by default, live
opt-in); muse-image-1.0 made the synthetic test images. All application code was written by muse-wonder-1.0 and
muse-spark-1.3 through Claude Code, which acted as operator; every prompt and answer, including failed runs, is in
the public build log. That is my disclosure; the log shows what was recorded.

An independent audit reported 12 defects; all 12 were reproduced, fixed and covered by regression tests.
Offline: 17 synthetic cases across 9 scenarios, combined evidence 17/17. Live (muse-spark-1.3): 11 of 17 valid on
the full run; after a contract fix, the six after-arrival cases were rerun and 5 of 6 were valid. In the visual
probe sam-3.1 missed obvious frost on a pipe, which is why "no detection" never lowers risk.
Limits: small synthetic sample, simulated delivery, no equipment control.

## 3. Do not claim (from [Demo video plan](demo-script.md))

- That she boarded, that a flight, traffic, or baggage state is known, or that ARIA Home is a travel platform.
- That command acknowledgement, a manager acknowledgement, or a technician report proves physical success or caused the recovery.
- That electrical activity proves useful heat, a fault, equipment power, or "no outage".
- That recovery was "instantaneous", that the equipment is fault-free, or that the goal is guaranteed beyond the observed readings.
- That any email, call, message, location, or scene control in the video is real.
- Only "verified recovery of the monitored temperature goal" — never a proven repair cause. Reconnection alone proves nothing; say "on the next sensor update". Missing location is "unavailable", never evidence about her schedule.
- No dollar-loss figures, no "0 hallucinations", no "secure" or "guaranteed" claims.
