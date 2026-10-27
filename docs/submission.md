# ARIA Home submission (Day 9 D9-4)

## 1. Requirements checklist

| Requirement | Status / where satisfied |
|---|---|
| Public repo containing only event work | Satisfied: https://github.com/BoMa-AI-Cloud/aria-home — every file listed as new during the event in [Existing vs new](existing-vs-new.md); pre-existing input is the name "ARIA" and private planning notes only, no code |
| 3-minute video opens stating what was pre-existing vs built this week, and shows only event-built features | Satisfied in script: opening line in [Demo video plan](demo-script.md) section A — "ARIA is my existing personal-assistant project. Its name, planning notes, and ARIA Home designs predate this event. All ARIA Home code shown was written this week with Meta's Muse models." Functional claims use real interface footage; simulated actor cards are labeled simulations, per section F |
| Video link accessible | Brad, pending |
| Every team member listed (solo) | Brad, pending (submission form) |
| Meta models only at runtime | Satisfied: runtime calls only muse-spark-1.3 through the Meta Model API behind a gated live provider; see README "How Meta models are used" and `backend/aria_home/provider.py` |
| Synthetic data only | Satisfied: every thermostat, electrical, weather, calendar and contact record is invented and labeled synthetic; banner "SYNTHETIC DATA - demo scenario, not a real home"; see README "Safety and honesty rules" |
| Live product or run instructions | Brad, pending (the office-hours answer). Run instructions exist in README "Try it in 5 minutes"; no hosted URL exists (see [Day 9 handoff](day9-handoff.md)) |
| Deadline Nov 4, 5 PM ET | Brad, pending (submit before the deadline) |
| Optional: Most Viral Project post on X, with its link submitted | Brad, pending |

## 2. Write-up draft (222 words)

An absent homeowner cannot tell whether the home will be ready for their return. An automation starting is not proof the expectation was met.

ARIA Home connects calendar, thermostat, room-sensor, electrical, and weather evidence into one readiness picture. A Meta model explains the situation, but it explains only code-checked facts: each claim cites allowed evidence, values are verified against the evidence pack, and readiness, follow-ups, and outcomes are computed in code, never decided by the model. When something looks wrong, ARIA coordinates scoped simulated notifications with permission gates — the HVAC request carries only property, access, and observations after manager authorization, and acknowledgement is recorded as acknowledged, not resolved. Recovery is verified independently from later sensor readings: reconnection alone closes nothing, warming must be observed, the goal must hold, and arrival is re-checked.

The app calls only Meta models at runtime (muse-spark-1.3), with claim binding that rejects mismatches. All application code in the repository was written this week by muse-wonder-1.0 and muse-spark-1.3 through Claude Code, which reviewed, tested and pushed it; every prompt and answer is in the public build log.

On 12 builder-labeled synthetic cases, combined evidence scored 12/12; thermostat-only 8/12; all other single sources 3/12. In one operator-run live pass (24 calls), 0 answers were rejected by the claim checks. Limits: small synthetic sample, no real channels or equipment control.

## 3. Do not claim (from [Demo video plan](demo-script.md))

- That she boarded, that a flight, traffic, or baggage state is known, or that ARIA Home is a travel platform.
- That command acknowledgement, a manager acknowledgement, or a technician report proves physical success or caused the recovery.
- That electrical activity proves useful heat, a fault, equipment power, or "no outage".
- That recovery was "instantaneous", that the equipment is fault-free, or that the goal is guaranteed beyond the observed readings.
- That any email, call, message, location, or scene control in the video is real.
- Only "verified recovery of the monitored temperature goal" — never a proven repair cause. Reconnection alone proves nothing; say "on the next sensor update". Missing location is "unavailable", never evidence about her schedule.
