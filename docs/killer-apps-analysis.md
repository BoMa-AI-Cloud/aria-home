# Killer-apps analysis (hypothetical designs only)

This page is analysis, not a product comparison. Every design below is a clearly hypothetical design invented for this exercise. It names no real company's product and asserts nothing about any real product's behaviour, pricing, or capabilities.

## The pattern worth copying (and the failure it avoids)

ARIA Home's bet: an automation starting is not an expectation met, so a helpful home agent should (1) connect evidence, (2) coordinate authorized help with scoped fields, and (3) independently verify the result from later measurements before reporting an outcome. The hypothetical designs below explore where that same verify-don't-trust pattern could matter. None of them is built.

## Hypothetical designs

1. **Hypothetical "Empty-house winter watch"** — for a vacant or seasonal property, a system watches independent temperature and power evidence during a cold snap, alerts a designated local contact with only property/access/observation fields after an authorization gate, and reports "warming observed / goal verified" only from later readings. Acknowledge ≠ resolved. (ARIA Home already prototypes the synthetic version of this; a real version is future work, see `docs/architecture-future.md`.)
2. **Hypothetical "Rental turn readiness"** — before a new occupant arrives, a system checks that a unit reached and held a target temperature, and shows the evidence timeline to a property manager. It would not certify that any repair caused recovery, only that the monitored goal was met and held.
3. **Hypothetical "Small-building close-out check"** — after any service visit to a small building, a system refuses to close the ticket on a technician's note alone and waits for independent readings to hold for a defined window. The human report is corroboration, timestamped, and can arrive before or after — it never sets the outcome.
4. **Hypothetical "Scoped contractor dispatch"** — a dispatch message that structurally cannot contain itinerary, personal email, live location or calendar fields because the payload is built from an allowlist, with refusals logged. The interesting property is what the message cannot say, not what it can.

## What would not be a differentiator

- A chatbot that narrates sensor data without claim binding (it could state a stale reading as current — the failure recorded in `backend/eval/results-live-current.json`).
- A dashboard that shows watts and calls it heating.
- Any design that treats acknowledgement, arrival of a report, or reconnection as resolution.

No market size, dollar-loss, adoption, or competitor figures are stated here, because none were measured.
