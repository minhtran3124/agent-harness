---
problem_type: failure
module: harness
tags: review-oracle, task-review, adversarial-review, corpus-testing, fixture-fitted-tests, plan-blind, correctness-review, green-is-not-correct
severity: critical
applicable_when: A multi-task plan finished with every per-task review green (spec + quality) and the full suite passing, and you are about to treat that as sufficient correctness evidence — before the plan-blind adversarial correctness pass has run.
affects:
  - runtime/resume_decision.py
  - runtime/test_resume_decision.py
  - skills/correctness-review/SKILL.md
supersedes: null
confidence: high
confirmed_at: 2026-08-10
---
## Applicable When

A `subagent-driven-development` plan finished: each task passed its `task-reviewer` (spec + quality
verdicts), its `Verify` command was green, and the full suite passed. You are about to hand to
`finishing-a-development-branch`, treating the green per-task reviews as the correctness gate.

## Symptom

On gh-175 every per-task review passed and 145 tests were green — yet the mandatory plan-blind
`correctness-review` (six independent finder angles over `BASE..HEAD`) then found ~11 **real,
reproduced** bugs, several severe: a markdown `PLAN.md` that merely mentions the string `<task`
parsed to an empty cursor → `execute-plan` with `next_task: null` → a resuming session would skip
every task (reproduced against the live `specs/gh-121-.../PLAN.md`: renderer 7 tasks, resume 0);
a non-dict `RUN.json` crashed the decision (`exit 3`, no JSON) instead of a structured stop; the
new `SKILL.md` fallback silently re-answered from a stale deployed helper; multi-id Status-Log
entries under- and over-claimed completion across ~31 of ~49 real plans.

## Wrong Approach

Trusting the per-task reviews + the implementer's own `Verify`/unit tests as the correctness
oracle. The task tests were written by the same subagent that wrote the code, from the same
idealized assumptions, using **synthetic fixtures** (`_ACTIVE_MD_PLAN`, one clean `<task id="1.1">`
block). Passing tests written against fixtures that share the implementation's blind spot prove
consistency, not correctness.

## Why It Failed

The per-task review is **plan-anchored** — it checks the diff against the task's Action/Done, so it
inherits the plan's framing of what "correct" means. And the tests were fitted to fixtures that
never exercised the real corpus. The bugs lived precisely where real `specs/*/PLAN.md` files
diverge from the tidy fixture: prose that mentions `<task`, multi-id Status-Log entries, a stale
`.claude/` deployed copy. Nothing in the plan-anchored, fixture-fitted loop had a reason to look
there. `not_observed != absent`: green meant "the fixtures I chose pass", not "the behavior is
correct on real input."

## Correct Approach

Keep the plan-blind adversarial `correctness-review` as a **hard, non-skippable gate** after the
per-task reviews — it is a different oracle, not a redundant one (plan-anchored review answers
"does it match the task?"; the adversarial finders answer "what breaks at runtime, ignoring the
plan?"). Two concrete practices that closed the gap:

- **Corpus tests, not just fixtures.** Add a regression test that runs the parser over **every**
  real `specs/*/PLAN.md` and asserts a property (ordered-id parity with the renderer; a no-over-claim
  subset bound), so a fixture-shaped blind spot cannot hide (`runtime/test_resume_decision.py`
  `test_corpus_parity_parse_tasks_matches_render_plan` / `test_corpus_completion_never_over_claims_vs_render`).
- **Re-verify findings at truth-tier yourself**; the finders reproduced each bug with a concrete
  trigger + CLI output against a real file, which is what distinguished them from hypotheses.

## Guardrail

`existing:` `hooks/risk-corroboration.sh` + `scripts/check_review_receipt.py --require correctness,intent`
already make the plan-blind correctness + intent reviews mandatory for a workflow-engine change and
block a push whose receipt omits them. The additional, un-mechanized half — "assert the parser over
the real corpus, not a synthetic fixture" — is a review-time discipline; treat a diff that parses/
routes over `specs/*` while its tests only use inline fixtures as unproven until a corpus property
test exists.

## Related

- docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md
- docs/solutions/harness/unverified-premise-propagates-through-plan-anchored-reviews.md
- docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md
