# Model-Value Evaluation Report

Status: NOT RUN. No live model call has been made under
`docs/model-value-eval-plan.md`. This file is a placeholder; the live runner
(`backend/scripts/run_model_value_eval.py --live --max-calls 60
--code-snapshot <SHA>`) overwrites it with scored results.

Planned denominators: 12 variants, 12 Spark explanations, 24 Wonder reviews
(12 genuine + 12 planted), up to 24 watcher calls (12 first + up to 12
revisions); at most 60 calls.

Failures so far: none recorded (no run yet).

Limitations: see `docs/model-value-eval-plan.md`.
