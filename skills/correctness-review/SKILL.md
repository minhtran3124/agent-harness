---
name: correctness-review
description: "Hunt for bugs in a finished change before anyone else sees it. Use when the user asks whether a change is correct, wants a review before opening a PR, or says something feels wrong but the tests pass. Reads the diff adversarially, scores each finding, and closes or routes it."
allowed-tools: Read, Grep, Glob, Agent, Task, Bash(git diff *), Bash(git show *), Bash(git log *), Bash(python3 scripts/render_skill_prompt.py *)
---

# Adversarial Correctness Review

Review runtime behavior, not style or plan compliance. Set `BASE..HEAD` to one of these:

- the merge-base, for a branch
- the working-tree diff, for uncommitted work
- the supplied range

In SDD, use the commit before task 1 through HEAD.

When SDD supplies `REVIEW_PACKAGE_PATH`, pass it to the FIND prompts. Those prompts say how to
read it. The package is runtime evidence, not an oracle. Stay plan-blind. Do a named, focused
read outside the package only for a concrete runtime risk. When SDD does not supply
`REVIEW_PACKAGE_PATH`, build the range as above.

## Pipeline

1. Read `review-config.json`. Then render six independent FIND prompts from
   `correctness-reviewer-prompt.md`: enclosing-function, removed-behavior, call-site-impact,
   stack-defects, guard-completeness, and prior-art. Each candidate names a concrete trigger and
   wrong result.
2. Deduplicate by `(file, line)`. Angles are provenance only, never evidence or scorer input.
3. Dispatch one independent SCORE prompt per remaining location from
   `correctness-scorer-prompt.md`. The scorer reads the code and diff, not the finder's reasoning.
4. Send scores at or above the configured threshold to classification. Record lower scores as
   advisory in `SUMMARY.md` (inline when standalone). Never lower the threshold below its
   configured floor.
5. Before classifying, **read `rules/auto-correct-scope.md`**. Rule 1–3 findings may be fixed.
   Rule 4 is STOP and goes to `ESCALATIONS.md` (to the user when standalone).
6. Re-review each Rule 1–3 fix, at most three rounds per finding. If open blocking findings do
   not decrease and the reviewed diff hash is unchanged, escalate immediately.

The scorer owns anchor scores, unreadable-code caps, the JSON schema, and threshold
rationale. The finder owns the six angle methods and output shape. Compose isolated child
prompts with `scripts/render_skill_prompt.py`. The child prompts do not inherit this skill's
context.

## Completion gate

Before you report success or hand the work to `finishing-a-development-branch`, do one of these
for each finding:

- Fix it, with a commit SHA.
- Record an advisory or carry-over finding durably in `SUMMARY.md`.
- Record a STOP or capped blocker durably in `ESCALATIONS.md`.

Anything else blocks completion.

`/code-review` is a sibling cleanup review, not a replacement for this runtime-bug oracle.
