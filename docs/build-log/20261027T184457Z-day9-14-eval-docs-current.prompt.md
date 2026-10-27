ARIA Home, docs task (approved by Brad): add the current-code live comparison to docs/evaluation.md.
Docs only. No code, no live calls, no git, NO helper scripts. DO THE WORK NOW.

Read docs/evaluation.md and backend/eval/results-live-current.json (three runs, non-secret).

Add a section "Live comparison on the current code (2026-10-27)":
- How: run by the operator, approved by Brad; 12 eval cases per run; committed snapshot 114be6a (after
  the Audit 2 repairs); 90 s timeout; no retries.
- Table computed from the file, which the operator measured as:
  muse-spark-1.3 via the Meta Model API, 12000 output tokens: 8 valid, 4 rejected, 0 no answer,
  median latency 35.9 s, median output 6695 tokens.
  meta-models/muse-spark-open-1026 (Meta open-weight Muse Spark Open, hackathon deployment) via
  Baseten, 12000 tokens: 1 valid, 10 rejected, 1 no answer (all tokens spent reasoning), 21.6 s,
  6086 tokens.
  Same model, 2000 tokens: 0 valid, 12 no answer (reasoning used the whole budget), 8.1 s.
- Rejection reasons: Muse Spark Open's were mostly prose numbers not present in the cited facts
  (185 occurrences across the 10 rejected answers), stale or superseded readings stated as current,
  and the word "confirmed" twice; muse-spark-1.3's four rejections were all after-arrival cases citing
  a stale or superseded reading as the current temperature.
- Honest reading, plainly: every valid answer agreed with the computed readiness (enforced by the
  contract). The earlier 24/24 results used the pre-repair checks and are not comparable. In
  after-arrival cases every reading is old by design while the contract still asks for a current
  temperature, so part of those rejections is a contract gap, not only a model error. Some
  number-check rejections may come from clock times (for example "09"); not investigated. One run per
  case, synthetic data, small sample. Conclusion: muse-spark-1.3 stays the runtime model.
Final answer: the section as written.

