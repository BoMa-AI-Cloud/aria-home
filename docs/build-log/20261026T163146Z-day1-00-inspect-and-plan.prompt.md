We are starting ARIA Home for the Meta Global AI Developer Hackathon. I am Brad Wentzel, a solo entrant in the Indie Developer track.

Your first task is to inspect this workspace and propose our implementation plan. DO NOT start implementing until I approve it.

PROJECT

Build a small, standalone home-understanding prototype that demonstrates:

1. A homeowner confirms a planned trip, return time, and desired indoor temperature.
2. ARIA Home connects four disconnected sources:
   - Calendar/trip context.
   - Thermostat readings and indoor-temperature history.
   - Circuit-level electricity readings.
   - Weather context.
3. Meta models help explain whether the home is behaving as expected, grounding explanations in identified evidence and clearly separating observations, hypotheses, missing information, and uncertainty.
4. The system prepares appropriately scoped notifications for the homeowner and an explicitly authorized property manager.
5. Subsequent measurements determine whether warming occurred and whether the homeowner's target was reached.

The central story:
"The homeowner is returning, the house is not warming as expected, and ARIA connects the evidence, coordinates attention, and checks what happens next."

IMPORTANT EVIDENCE RULES

- A thermostat's reported heating state does not prove heat is being delivered.
- Electrical activity does not prove useful heating.
- Fresh activity on other circuits weighs against a complete power outage during the observed interval. It does not rule out partial outages, earlier outages, or backup power.
- Missing readings are not zero readings.
- Do not describe a circuit as behaving normally without a defined, validated baseline.
- Keep circuit-to-equipment mappings explicit.
- Weather forecasts are not on-property measurements.
- Message creation, sending, delivery, acknowledgement, and physical resolution are different states.
- Do not invent diagnoses, savings, confidence percentages, or verified outcomes.
- Use deterministic code for calculations, freshness, permissions, and outcome checks. Use Meta models for evidence-grounded synthesis and relevant clarification.
- No equipment control or hazardous repair instructions.

HACKATHON CONSTRAINTS

- Focus exclusively on the Meta hackathon. No other competitions.
- Our submission must have a public repository and a three-minute demo.
- Clearly document what was newly built during the event.
- Do not import, copy, modify, or publish my existing ARIA code or private data.
- Treat this as a new standalone implementation. Familiarity with my existing platform is not permission to reuse it.
- Track unresolved organizer questions rather than inventing eligibility interpretations.
- Optimize for Impact 30%, Meta AI Tooling 25%, Demo 25%, and Technical Depth & Execution 20%.
- Never promise that we will win.

TECHNICAL DIRECTION

Prefer:
- Python Flask backend.
- React + TypeScript + Vite frontend.
- SQLite only where persistence is actually needed.
- pytest for backend tests.
- A small browser smoke test once the interface exists.

Start synthetic-first:
- Clearly label synthetic data.
- Use a fixed scenario clock for reproducible replay.
- Keep observed time, received time, and scenario evaluation time distinct.
- Never present mock or cached model responses as live inference.
- Do not add real calendar OAuth, thermostat connections, electrical integrations, or real message sending on Day One.

MODEL AND PROVIDER SEPARATION

- Coding: Muse Wonder for difficult design/integration/review; Muse Spark for routine implementation.
- The coding assistant's model configuration is separate from the application runtime.
- Confirm the actual coding model if the interface exposes it; otherwise say that you cannot verify it.
- Before choosing the application runtime model, verify current official documentation and my available access.
- Candidate runtime options are Meta Model API or Baseten-hosted Meta models.
- The participant guide specifies Baseten model ID meta-models/muse-spark-open-1026. Verify availability before relying on it.
- Do not invent API endpoints, SDK methods, supported parameters, prices, or account access.
- Do not silently switch models or providers.

SECURITY AND COST

- Never ask me to paste API keys into chat.
- Never print secrets, inspect secret values, or expose backend keys to the browser.
- Do not inspect unrelated folders or my existing ARIA checkout.
- Do not run paid application API calls, install dependencies, deploy, push, publish, or commit without my approval.
- Do not launch subagents or unattended loops.
- My provisional Day One application-test budget is at most $10 of approved usage, preferably covered by confirmed promotional credits.
- This is a planning budget, not a claim that a billing hard cap exists.
- Coding-assistant usage may also incur charges; do not claim that application counters cover it.
- Mock provider calls first. Propose one bounded live smoke test separately and wait for approval.

DAY ONE FINISH LINE

By the end of Day One we want:
1. A safe standalone workspace.
2. A working local backend health endpoint.
3. A working local frontend.
4. Four clearly labeled synthetic input sources.
5. Basic source cards showing timestamps and data availability.
6. Provider integration tested with mocks.
7. One approved, small live model test if account access and billing are ready; otherwise an explicit documented blocker.
8. An honest handoff listing what works, what was tested, and what comes next.

Do not build the complete agent, live integrations, notification delivery, elaborate charts, or full outcome-verification workflow today.

FIRST RESPONSE REQUIRED

A. Inspect only the current authorized workspace:
   - Confirm its path and whether it is empty.
   - Identify operating system and shell.
   - Check Python, Node, package-manager, and Git availability.
   - Report whether a repository already exists.
   - Do not read secret files or modify anything.

B. Explain the proposed architecture in plain language.

C. Give a short Day One task sequence with:
   - The coding model to use for each task.
   - Files expected to be created.
   - A clear pass/fail checkpoint.
   - Any command, installation, network access, or spending that needs my approval.

D. Identify only decisions that materially block the next step.

E. Stop and wait for my approval before creating files or installing anything.

Keep the plan small enough for one person to complete. If you cannot inspect this environment, say so and give me the exact safe commands to run instead.

(Operator note: this is a non-interactive run in plan/read-only mode, web tools disabled. Write your full response as your final answer.)

