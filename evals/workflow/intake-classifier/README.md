# Intake-Classifier Eval (auto-score / manual-run v1)

Measures whether **`/feature-intake`** assigns the correct **lane · confidence · hard-gate** for
a request. Sibling of `../../skills/review-chain` — same honesty model, different oracle: this scores the
*router* the whole workflow hinges on. The scorer is automatic (`scripts/score_intake_eval.py`,
unit-tested); the classification runs are triggered manually via **blind** subagents.

## Claim discipline (read first)

This benchmark measures **only** whether `/feature-intake` classifies **these fixtures** correctly.
It is *not* evidence about other skills, the full workflow chain, or real-world classification
accuracy. A number here is a claim about *this fixture set and this skill*, nothing more — state
that scope wherever it is cited (`not_observed != absent` — a request shape we did not seed is
unmeasured, not "handled").

The single non-negotiable metric is **hard-gate respect**: a fixture whose truth declares a hard
gate (auth · authorization · data-loss/migration · audit · external provider · public contract ·
high-blast file) MUST be classified `high-risk`. A downgrade there is a safety failure, not a
scoring miss — `score_intake_eval.py --strict` exits non-zero on it.

## Fixture layout

Each fixture is `fixtures/<name>/` with:

- **`request.md`** — the user request to classify (what a blind runner sees).
- **`truth.md`** — a parseable header + prose rationale. Header keys the scorer reads:

  | Key | Meaning |
  |---|---|
  | `expected_lane` | `tiny` / `normal` / `high-risk`, or `any` (lane not asserted — e.g. an ambiguity fixture) |
  | `expected_confidence` | `high` / `medium` / `low` |
  | `expected_hard_gate` | the hard-gate class, or `none` |
  | `expected_flags_include` | flags that MUST appear (comma-sep), or `none` |
  | `expected_escalate` | `yes` / `no` |
  | `must_not_downgrade` | `true` for hard-gate fixtures |

## Running (manual, blind)

A **run** is:

1. For each fixture, dispatch a subagent given **only** `request.md` + the `feature-intake` skill —
   **never** `truth.md` (integrity: the orchestrator authored the answer key).
2. The subagent applies `/feature-intake` and writes the emitted header
   (`Lane:` / `Confidence:` / `Flags:` / `Escalate:` …) to `results/<run>/<fixture>.md`.
3. Score the run: `python3 scripts/score_intake_eval.py --run evals/workflow/intake-classifier/results/<run>`.
4. Record the scorecard in `results/<date>-<label>.md` (from `results/template.md`).

## Honesty rules

- Report misclassifications plainly. A miss is a finding about the skill (or the fixture's answer
  key), not a failure of the benchmark.
- **Do not re-run a fixture until it passes** — the first scored run is the record.
- If a fixture is found to carry an ambiguous or wrong expected label, revise `truth.md` and note
  the revision here; prior runs are not comparable across the revision.
- The baseline (`results/<date>-baseline.md`) is the regression reference for any future edit to
  `skills/feature-intake/SKILL.md` — note the measured skill commit sha in it.
