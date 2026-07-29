---
name: correctness-review
description: Run an adversarial runtime-correctness review over a diff. Independently find, score, route, and close concrete bugs before a PR; use standalone or as SDD’s final pre-ship gate.
---

# Adversarial Correctness Review

Review runtime behavior, not style or plan compliance. Determine the intended `BASE..HEAD` range
(merge-base for a branch, working-tree diff for uncommitted work, explicit range when supplied).
In SDD, use the commit before task 1 through current HEAD.

When SDD supplies `REVIEW_PACKAGE_PATH`, read that explicit package first for the exact SHAs,
commit list, stat, and mechanical diff instead of reconstructing a duplicate diff. It is not an
oracle: use it only as runtime evidence, retain this skill's plan-blindness, and perform a named
focused read outside it only for a concrete runtime risk. Standalone calls without a package keep
the existing range-construction behavior.

## Pipeline

1. Read `review-config.json`, then render six independent FIND prompts from `correctness-reviewer-prompt.md`: enclosing-function,
   removed-behavior, call-site-impact, stack-defects, guard-completeness, and prior-art. Each
   candidate names a concrete trigger and wrong result.
2. Deduplicate by `(file, line)`. Angles are provenance only—never evidence and never scorer input.
3. Dispatch one independent SCORE prompt per remaining location using
   `correctness-scorer-prompt.md`. The scorer reads the code/diff, not finder reasoning.
4. Route scores at the configured threshold to classification; record lower scores as advisory in
   `SUMMARY.md` (or inline standalone). Never lower the threshold below its configured floor.
5. Before classifying, **read `.claude/rules/auto-correct-scope.md`**. Rule 1–3 findings may be
   fixed; Rule 4 is STOP and goes to `ESCALATIONS.md` (or directly to the user standalone).
6. Re-review each Rule 1–3 fix. Cap each finding at three rounds; if open blocking findings do not
   decrease and the reviewed diff hash is unchanged, escalate immediately.

The scorer owns anchor scores, unreadable-code caps, JSON schema, and threshold rationale. The
finder owns the six-angle methods and output shape. Compose isolated child prompts with
`scripts/render_skill_prompt.py`; never assume they inherited controller context.

## Completion gate

Before reporting success or handing to `finishing-a-development-branch`, every finding is either
fixed with a commit SHA or durably recorded: advisory/carry-over in `SUMMARY.md`, or a STOP/capped
blocker in `ESCALATIONS.md`. Anything else blocks completion.

`/code-review` is a sibling cleanup review, not a replacement for this runtime-bug oracle.
