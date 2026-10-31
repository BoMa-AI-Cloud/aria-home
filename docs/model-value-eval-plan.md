# Model-Value Evaluation Plan

Pre-registered before any model call (2026-10-30). Dry runs only so far; no
live call has been made under this plan.

## Question

Do muse-spark-1.3 explanations, muse-wonder-1.0 reviews, and the watcher
correction loop add value over code alone? Readiness and verification stay in
code; the models only interpret and review.

## Material

12 synthetic variants of the care night in `backend/scenarios/eval_variants/`,
generated deterministically by `backend/scripts/make_eval_variants.py`
(seed 20261030) from `care_home_v1` and never used in any prompt, test
fixture, or recording. Each variant carries a `variant.json` with the
code-computed expected readiness/verification labels and a human-written
ground-truth note (real problem + right next action).

Two labels read oddly and were checked against `aria_home/verification.py`
before any run (2026-10-31). Both are correct, and neither was changed:

- `ev-normal-night` is `goal_verified` at 02:45 because the follow-up opens at
  00:30, fresh room readings hold 68 F for the 30-minute hold, and the
  thermostat is reporting. That is what the stage means. It does not mean a
  repair happened.
- `ev-thermostat-gap-steady` is `telemetry_missing` because recovery
  verification starts only once thermostat reporting resumes. The steady room
  is carried by readiness (`on_track`) and by the ground truth (check the
  thermostat link; do not dispatch HVAC). An answer that dispatches HVAC
  fails the next-action criterion.

## Comparison A — Spark vs deterministic summary

For each variant, run the genuine muse-spark-1.3 explanation
(`investigator.investigate`) and score it against the ground-truth note:

- problem named (needs human scoring)
- cited evidence correct (deterministic: every cited id in pack, values match)
- next action right (needs human scoring)
- no unsupported claim (deterministic: `investigator.validate` reasons)
- contract rejections counted separately (status rejected/unavailable with reasons)

Metric: share of variants with all deterministic checks passing, over n=12;
human-scored parts listed per variant, never guessed.

## Comparison B — Spark vs Spark+Wonder

For each variant, review the genuine Spark answer and a copy with one planted
unsupported claim from the fixed list below, using muse-wonder-1.0
(`review.request_live_review`) against the same evidence pack:

- `wrong-temperature`: states an indoor temperature ~6 F above any reading
- `invented-repair-cause`: claims the blower circuit proves the furnace failed
- `report-proves-warmth`: claims the technician report alone proves warmth
- `wrong-time`: claims the key reading was observed 3 hours off

Metrics: catch rate = planted copies flagged `issues_found` over n=12;
false-alarm rate = genuine answers flagged `issues_found` over n=12.
Which claim was planted is recorded per variant.

## Comparison C — watcher first attempt vs revised attempt

For each variant, run the watcher (`watcher.run_watcher`: one revision loop)
at the variant eval time:

- correct observations (needs human scoring against the ground-truth note)
- missed problems, proxied deterministically: first attempt empty while code
  detections are non-empty
- rejected claims: failed checks on the first attempt
- correction success rate: revised-and-verified over revisions attempted

## Call budget

12 Spark + 24 Wonder (12 genuine + 12 planted) + up to 24 watcher
(12 first + up to 12 revisions) = at most 60 calls. The runner refuses live
execution when the plan exceeds `--max-calls`.

## Reporting

Raw results go to `backend/eval/model-value/`; the scored report
`docs/model-value-eval.md` shows every denominator, lists every failure, and
carries a limitations section. Deterministic checks are scored in code;
judgement parts are marked "needs human scoring" and listed per variant.
