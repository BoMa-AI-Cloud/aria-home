Model: muse-spark-1.3
Turns: 9

Done: created `docs/submission.md` and linked it from `README.md`.

Write-up (209 words):

An absent homeowner cannot tell whether the home will be ready for their return. An automation starting is not proof the expectation was met.

ARIA Home connects calendar, thermostat, room-sensor, electrical, and weather evidence into one readiness picture. A Meta model explains the situation, but it explains only code-checked facts: each claim cites allowed evidence, values are verified against the evidence pack, and readiness, follow-ups, and outcomes are computed in code, never decided by the model. When something looks wrong, ARIA coordinates scoped simulated notifications with permission gates — the HVAC request carries only property, access, and observations after manager authorization, and acknowledgement is recorded as acknowledged, not resolved. Recovery is verified independently from later sensor readings: reconnection alone closes nothing, warming must be observed, the goal must hold, and arrival is re-checked.

The app calls only Meta models at runtime (muse-spark-1.3), with claim binding that rejects mismatches. All code was written this week by muse-wonder-1.0 and muse-spark-1.3, with every prompt and answer in the public build log.

On 12 builder-labeled synthetic cases, combined evidence scored 12/12; thermostat-only 8/12; all other single sources 3/12. In one operator-run live pass (24 calls), 0 answers were rejected by the claim checks. Limits: small synthetic sample, no real channels or equipment control.

Word count: 209 (under 250).
