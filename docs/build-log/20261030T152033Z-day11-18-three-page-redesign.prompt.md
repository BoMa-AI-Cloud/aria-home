ARIA Home: redesign the app as three pages in the style of a calm home product (approved by Brad, 2026-10-30: "make it similar to the home industry pack ... relevant information on the first page, the reasoning behind it on the second, and the integrated apps on the third"). DO THE WORK NOW in this turn. IMPORTANT: a message without a tool call ends your turn, so never write a status or plan sentence on its own; keep editing and running commands until the done-condition holds. No live calls, no installs, no git, no network beyond 127.0.0.1. Write all new code yourself in this repo; do not copy any outside code. Keep every behaviour, route, safeguard and disclosure; this is layout and style only. Do not weaken any test: where a test finds an element by text or role that moves, update the locator, never the assertion. Keep all working-tree changes. Shell starts in C:\aria-home; prefix frontend commands with `cd frontend && `. Do not end your turn until `cd backend && python -m pytest -q`, `cd frontend && npm run typecheck`, `cd frontend && npm run build`, `cd frontend && npm run test:e2e` and `cd frontend && npm run test:e2e:public-demo` pass.

THE LOOK (write it as CSS variables in frontend/src/index.css, light and dark):
- Page background warm off-white #F7F3EC; panels white #FFFFFF; text #1A1A1A, body #3D3D3D, muted #6B6B6B; one accent, plum #4A2B6B (hover rgba(74,43,107,0.08), soft tint rgba(74,43,107,0.10)); hairlines rgba(26,26,26,0.08). Dark mode: background #0E0C13, panels #17131F, text #F7F3EC, accent #C9A6E8, following prefers-color-scheme plus a manual toggle in the header that is remembered in localStorage (wrapped in try/catch).
- Type: headlines in a serif (font stack: "Cormorant Garamond", Georgia, "Times New Roman", serif); everything else in a clean sans (Inter, system-ui, -apple-system, "Segoe UI", sans-serif). Load no web fonts from other hosts: the hosted demo must contact only its own host. Numbers in tiles use tabular figures.
- Rules: no boxed cards around lists. List rows are divided by hairlines. Status colour (green ok, amber watch, red at risk, grey unknown) appears only as a small dot or icon, never as a row background. At most three shadow levels, never on a list row. Transitions animate colour and background only, 0.2 s. Every control has a visible focus ring. Generous spacing (24-32 px section gaps, 64 px header). Text never smaller than 13 px. Works at 375 px wide with no horizontal scroll.

THE FRAME (every page):
- A 64 px white header with a hairline under it. Left: the wordmark "ARIA Home" in the serif, then three tabs: House, Reasoning, Integrations (the current tab marked with aria-current and a plum underline). Right: a status pill with a dot ("Synthetic demo · demo-house, Petoskey"), the replay time selector (the existing checkpoint buttons, made compact: a stepper with Back, the current time, and Next), and the light/dark toggle.
- A thin plum-tinted strip under the header carrying the existing disclosure line ("Interactive demo · Synthetic home data · Simulated notifications · Recorded model responses where indicated · No equipment control"). Always visible.
- The version line stays at the foot of every page.

PAGE 1, HOUSE (the default; "what is true right now"), laid out like a letter:
1. Eyebrow: the replay time in words ("Saturday 17 January, 2:31 AM, ET").
2. Verdict headline in the large serif, built only from the existing readiness/verification result, e.g. at risk: "The house is cooling. It may not be warm by 7:00." On track / verified / met: the matching plain sentence. Unknown: "ARIA can't tell yet." Never a sentence the code result does not support.
3. Lead: one or two sentences from the same result and the room sensor reading ("Living room 52 F and falling 0.2 F an hour; the thermostat has been silent since 1:30.").
4. A "gap" callout (icon + one line) only when a source is missing or stale ("Thermostat not reporting since 1:30"), from the existing freshness checks.
5. "The house right now": four glance tiles in one row (two by two on phones): Inside (room temperature + trend), Warm-by (target 68 F by 7:00 + on track / at risk dot), Furnace and thermostat (reporting / silent), Camera (latest synthetic frame caption, "no detection is not an all-clear" when nothing found).
6. "Who knows": hairline rows for the caregiver permission (the existing CaregiverPermissionCard content: the question text, waiting/approved/declined, Approve and Decline buttons, keep data-testid="caregiver-permission"), the HVAC request (fields sent), and the resident/homeowner update. Each row: icon dot, title, one meta line, action on the right.
7. The guided story caption (step title + guidance) sits under the verdict in public mode, with the Next button repeated at the bottom of the page.

PAGE 2, REASONING ("why ARIA thinks so"):
- Top: ARIA's view (the existing TraceView map), full width.
- Then, as hairline-separated sections with small uppercase labels: "Code checks" (freshness, conflicts, units, Laws, pass/fail with reasons), "What the model said" (the recorded muse-spark-1.3 answer with its provenance line and the muse-wonder-1.0 review when present; clearly "recorded, not live" in public mode), "Evidence timeline" (observed vs first-known times), "Human reports" (marked "a report, not a measurement"), "ARIA's Laws" (the existing Laws content, or a link to it).
- Every number cites the evidence id it came from, as today.

PAGE 3, INTEGRATIONS ("what ARIA is connected to"):
- Hairline rows, one per integration, each with a status dot and a plain status word: WhatsApp (caregiver permission and HVAC notice; "simulated in this demo; real only on the owner's test number when opted in"), Emporia energy (live read-only panel when opted in; "off in this demo"), Nest camera (owner's mechanical room; "off in this demo"), Synthetic camera frames with recorded sam-3.1 segmentation, Room sensor, Thermostat, Weather, Calendar.
- Then "Meta models": muse-spark-1.3 (investigation answers and the watcher), muse-wonder-1.0 (second review), sam-3.1 (segmentation), muse-voice-transcribe-1.0 (technician note), muse-image-1.0 (synthetic frames, offline only), each with role, "decides nothing / code decides" where true, and whether it is recorded or live here. Reuse the existing model-role data; do not invent new claims.
- In normal (non-public) mode the owner-only live panels (Emporia, Nest) render here when configured, exactly as they work today.

THE LANDING (public mode): same frame without tabs. A centred letter: eyebrow "A demo for the Meta AI hackathon", the serif question headline, Brad's paragraph (BRAD_HOOK) set as a quote, a household card ("demo-house · Petoskey, Michigan · synthetic · warm-by 68 F at 7:00 · caregiver: her daughter"), one primary plum button "Start the warm-by story", a secondary text link "Explore freely", and "Reset my session" small at the bottom. The disclosure strip stays.

KEEP: all data-testid values, aria labels used by tests (update a test locator only when the element really moved), the explore-evidence drawer contents (they can move into page 2), keyboard flow, reduced motion, the public-demo restrictions.

TESTS: add to frontend/e2e/public-demo.spec.ts: the three tabs exist and each shows its main heading; the House verdict at 02:31 says the house may not be warm by 7:00 and at 07:01 says the expectation was met; the page has no horizontal scroll at 375 px; no request leaves the page's own origin. Keep every existing test passing.

Final answer: files changed, a one-paragraph description of each page, and the REAL output lines of every command.

