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

## 2. Write-up draft

An absent homeowner cannot tell whether the home will be ready for their return. An automation starting is not proof the expectation was met.

ARIA Home connects calendar, thermostat, room-sensor, electrical, and weather evidence into one readiness picture. A Meta model explains the situation, but it explains only code-checked facts: each claim cites allowed evidence, values are verified against the evidence pack, and readiness, follow-ups, and outcomes are computed in code, never decided by the model. When something looks wrong, ARIA coordinates scoped simulated notifications with permission gates — the HVAC request carries only property, access, and observations after manager authorization, and acknowledgement is recorded as acknowledged, not resolved. Recovery is verified independently from later sensor readings: reconnection alone closes nothing, warming must be observed, the goal must hold, and arrival is re-checked. This is temperature-goal verification, not proof of a repair cause.

The app calls only Meta models at runtime (muse-spark-1.3), with claim binding that rejects mismatches. All application code in the repository was written this week by muse-wonder-1.0 and muse-spark-1.3 through Claude Code, which reviewed, tested and pushed it; every prompt and answer is in the public build log. That paragraph is the author's disclosure; the build log shows the prompts and answers that were recorded.

On 12 builder-labeled synthetic cases across 6 scenarios, combined evidence scored 12/12 fully correct; thermostat-only 7/12; room-sensor-only 3/12; electrical-only and calendar-only 2/12 each. Recovery verification was scored for 5 of the 12 cases (the `demo_video_v1` cases). In the latest recorded live run (snapshot 77cafc9, 2026-10-28, exactly 17 calls on muse-spark-1.3 via the Meta Model API), 11 of 17 answers were valid and all 11 agreed with the code-computed readiness, which the contract enforces, so that agreement shows contract-following, not independent readiness judgment; the claim checks rejected 6, all six after-arrival cases citing a stale or superseded reading (or old electrical activity) as current. Earlier recorded runs are kept in [Evaluation](evaluation.md) with their model ids, provider routes, dates, snapshots and policy versions, and are superseded, not current. Limits: small synthetic sample, no real channels or equipment control, simulated delivery only.

## 3. Do not claim (from [Demo video plan](demo-script.md))

- That she boarded, that a flight, traffic, or baggage state is known, or that ARIA Home is a travel platform.
- That command acknowledgement, a manager acknowledgement, or a technician report proves physical success or caused the recovery.
- That electrical activity proves useful heat, a fault, equipment power, or "no outage".
- That recovery was "instantaneous", that the equipment is fault-free, or that the goal is guaranteed beyond the observed readings.
- That any email, call, message, location, or scene control in the video is real.
- Only "verified recovery of the monitored temperature goal" — never a proven repair cause. Reconnection alone proves nothing; say "on the next sensor update". Missing location is "unavailable", never evidence about her schedule.
- No dollar-loss figures, no "0 hallucinations", no "secure" or "guaranteed" claims.
