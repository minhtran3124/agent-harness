# review-policy — Runtime eval of the rewritten review prompts

Written 2026-10-12. Pins: repo f23e4ac (head arm), 33d6ed4 (base arm)

This eval runs the **real** reviewer prompts before and after the rewrite on the repository's existing
planted-defect fixtures. It exists because neither earlier runner does that: `scripts/run_review_chain_eval.py`
sends its own hardcoded `INSTRUCTIONS`, `scripts/run_task_review_eval.py` builds its own two-line prompts, and
the `prompt-refactor` behavior corpus holds one-line cases graded by hand. So the design's D6 ("no behavioral
eval; per-file meaning-equivalence review instead") left runtime behavior unmeasured. The user asked for it to be
measured after the PR was opened.

## Method

- **Arms.** Base is `33d6ed4` (before any change); head is `f23e4ac` (the PR). Each arm's `rules/`, `skills/` and
  `agents/` were extracted with `git archive`, and each arm's own fragments were composed with
  `render_skill_prompt.py` run from that arm's tree. (`--root` does not select fragments; running it from the
  worktree would have fed the head text to both arms, which a first check caught.)
- **Prompts under test (the real ones).**
  - Correctness finders: `prompts/shared.md` plus each of the six `prompts/angles/*.md`, with the Inputs filled in.
  - Intent reviewer: the dispatched block of `intent-reviewer-prompt.md`, with the Inputs filled in.
  - Context-propagation audit: the body of `context-propagation-audit/SKILL.md` (two audit fixtures only).
  - Task reviewer: the dispatched block of `task-reviewer-prompt.md`, with brief, report and package files.
- **Fixtures.** The 7 `evals/skills/review-chain/fixtures` (diff + intent + answer key) and the 7
  `evals/skills/task-review/fixtures` (prose + answer key). Nothing from an answer key was shown to a reviewer.
- **Identical conditions.** `claude -p`, model `claude-opus-5-5`, effort `medium` (the review bindings),
  `--safe-mode`, tools `Read` only (`--tools Read --allowedTools Read`), a fresh empty working directory per call
  holding only that arm's `rules/` and the fixture's `package.md`, `--max-budget-usd 1.5` per call, a $60 cap in
  total. For the review-chain oracles the same machine-readable output block was appended to both arms (it replaces
  each prompt's own report format); the task reviewer kept its real YAML reply.
- **Size.** 116 calls (58 per arm): 42 finder, 7 intent, 2 audit, 7 task per arm. Interleaved base/head, 4 at a
  time. Every call is first-run only; none was rerun to change a result.
- **Scoring.** The existing deterministic scorers: `score_review_chain_eval.py --score` (answer-key matching) and
  `score_task_review_eval.py --compare ... --quality-gate`, plus counts taken from the recorded tool calls.
- **Cost.** $5.02 (base) and $5.89 (head), about $10.9 including a 4-call pilot. Per-call results:
  `runtime-eval-results.json`.

## Results against the criteria written before the full run

| ID | Criterion | Base | Head | Verdict |
|---|---|---|---|---|
| C1 | Core catches (5 fixtures), head ≥ base | 5/5 (oracle match 4/5) | 5/5 (oracle match 4/5) | pass |
| C2 | Bonus catches (2 audit fixtures), head ≥ base | 2/2 | 2/2 | pass |
| C3 | False positives, head ≤ base + 2 | 13 (1 at confidence ≥ 75) | 12 (1 at confidence ≥ 75) | pass |
| C4 | Parseable JSON block ≥ 95% in each arm | 51/51 | 51/51 | pass |
| C5 | Head reviewers Read `rules/review-policy.md` ≥ 95% | 0 (file absent at base) | finders 42/42, intent 7/7, task 7/7 | pass |
| C6 | Task review: head fixtures passing ≥ base; `checked_against` on ≥ 95% of replies with findings | 6/7; field 0/7 | 7/7; field 7/7 | pass |
| C7 | Cost (recorded, no gate) | $5.02, 109k output tokens, 1,221 s | $5.89, 121k output tokens, 1,321 s | +17% cost |

Notes on the numbers:

- **C5 is the strongest result.** It turns design assumption A1 ("a fresh reviewer follows an explicit Read of a
  path-scoped rule") from a traceability-tier check (the context matrix) into an observed one: all 56 head-arm
  calls that were told to Read the policy did. No call had a permission denial. Finders also Read
  `rules/auto-correct-scope.md` in 32/42 head calls against 22/42 base calls.
- **C1.** `soft-delete-filter` was caught only by the intent reviewer in both arms; no correctness angle reported
  it as a confirmed finding in either (at most as an `unknown` at low confidence, which the scorer does not count
  as a catch). That is identical across arms, so it is not a regression, but it shows the limit of the setup: the
  finders saw only a diff, with no repository to explore.
- **C6.** In `minor-only` the base reply raised the forbidden `spec_fail`; the head reply did not. One run per
  cell, so this is an observation, not evidence of improvement.
- **C7.** The head arm costs more although its prompts are shorter (64,006 against 68,994 prompt words across all
  calls): each head call makes one extra Read turn for the policy, and replies were about 11% longer. The policy is
  not free at runtime.

## What this does and does not show

Shows: with identical conditions, the rewritten prompts catch the same planted defects, add no false positives
beyond noise, keep producing parseable and well-formed output, and the new explicit Read is followed in fresh
reviewer contexts.

Does not show:

- **Variance.** One first run per cell. A difference of one finding, or of one fixture, is within what a rerun
  could change; the eval has no significance test.
- **Breadth.** 7 + 7 fixtures, each with one planted defect class. A defect class that is not seeded is unmeasured.
- **The real subagent environment.** Calls ran in a minimal safe-mode with only a diff, not as the `reviewer` /
  `task-reviewer` agents with their runtime binding and a repository to read.
- **Other stages.** The scorer stage, the controllers' routing (fix rounds, escalation, recording) and Codex
  contexts were not exercised.
- **The policy's own effect.** No fixture tests that style or generated-file findings are actually suppressed, so
  "the do-not-report list works" remains unmeasured.
- **Report-format adherence.** The appended JSON block replaced each finder's and intent reviewer's own report
  format, so adherence to `Angle / Severity / Rule class` was not tested. Task review used its real format.

## Correction to earlier statements

The design's "What we do not claim" table says the task reviewer "has no behavioral fixture". That is wrong:
`evals/skills/task-review` has seven fixtures and a scorer. What is true is that its runner does not use the real
`task-reviewer-prompt.md`. This eval did. The design is approved and is not edited; this note stands as the
correction.

## Follow-ups (not in this PR)

1. Promote the driver into a tested `scripts/` tool, so the A/B can be re-run on any later prompt change. Today it
   lives in the session scratchpad.
2. Add a style-and-generated-file bait fixture so the do-not-report list is measured.
3. A second attempt on the discordant cells (`minor-only`) if variance matters for a decision.
