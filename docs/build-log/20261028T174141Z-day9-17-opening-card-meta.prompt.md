ARIA Home, video text fix (approved by Brad). Tooling and docs only, no product behaviour change. DO THE
WORK NOW in this turn. No live calls, no installs, no network beyond 127.0.0.1, no git, NO helper
scripts. Shell starts in C:\aria-home: prefix frontend commands with `cd frontend && `. Do not end
your turn until `cd frontend && npm run record:demo` and `cd frontend && npm run test:e2e` pass.

The story scenes and the music in the demo video now come only from Meta AI. Replace the sentence
"Story scenes: Grok Imagine and Meta AI." with exactly "Story scenes and music: Meta AI." in every place
it appears: frontend/cards.html (the #opening card), frontend/recording/demo.record.ts (its text
assertion), docs/demo-script.md (A3.2 line 0, and update its word count in the "(33 w)" prefix), and the
docs/demo-script.md layer-1 note that names the dramatization tools. Keep every other word of the
opening sentence and "Synthetic demo data" unchanged. Do not edit docs/build-log/.
Final answer: files changed and REAL output lines.

