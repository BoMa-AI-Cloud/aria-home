Model: muse-wonder-1.0
Turns: 42

Files changed:
- Created `docs/demo-script.md`
- `README.md` — one link line under Planned
- `docs/timeline.md` — one line

Section G verbatim:

## G. The smallest build sequence to film it, decisions that need Brad, and claims to avoid

Smallest build sequence:

1. Freeze the C timeline, the maintained-period rule, and the sharing scope (decisions below).
2. Add the `demo_video_v1` fixture: offline thermostat, independent room stream, blower-mapped electrical channel, recovery ramp reaching and holding 68 °F before a 21:00 arrival, report available only after verification.
3. Add deterministic checks reusing `outcomes.py` / `readiness.py` patterns: reconnection ("reporting restored"), cross-source agreement, maintained-for-30-minutes verification, still-met-at-arrival.
4. Add labeled simulated actor cards (email, location, scene acknowledgement, manager/HVAC messages, visit, report) gated by the existing as-of visibility — no real integrations.
5. Frontend: video scenario in the selector, replay times through 21:01, the four progression labels, event/received/evaluation timestamps.
6. Run the E acceptance checks as replay tests, then film the real UI; use mock only with its label in frame, or one disclosed live call.
7. Record the A voiceover (431 words), add synthetic/simulated/replay-jump labels and the inference-wait disclosure, and cut to exactly 180 s.

Decisions that need Brad:

- The 30-minute maintained period (and no-dips rule) — new assumption, not today's last-2-readings rule.
- The proposed 21:00 arrival with labeled 45-minute airport-exit/baggage and 30-minute driving allowances, replacing the fixtures' 18:00 arrival for the video scenario.
- The exact property/contact/access fields the simulated HVAC request may carry, and that the report becomes available to ARIA only after verification (20:45 in C).
- Independent room sensor definition (source, placement/zone) and the blower channel's fixture mapping strength.
- Mock-with-label versus a fresh live call for the filmed investigation, given inv-v2 live behaviour is unverified and Day 3 latencies were ~23 s.

Claims to avoid:

- That she boarded, that a flight/traffic/baggage state is known, or that ARIA Home is a travel platform.
- That command acknowledgement, a manager acknowledgement, or a technician report proves physical success or caused the recovery.
- That electrical activity proves useful heat, a fault, equipment power, or "no outage".
- That recovery was "instantaneous", that the equipment is fault-free, or that the goal is guaranteed beyond the observed readings.
- That any email, call, message, location, or scene control in the video is real.
