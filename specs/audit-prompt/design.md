# audit-prompt — Design

## Purpose

Apply the prompt-audit findings that came with a concrete proposed diff, so the instruction text
in skills, rules, agents and `CLAUDE.md` matches the repository and current models. Source:
`research-brief.md` (the audit, approved by the user's request to fix "following research above").

## Decision

No design fork exists: each in-scope finding already names its exact replacement text in
`research-brief.md`. The approach is to apply those hunks as written, grouped by directory so the
three tasks touch disjoint files.

| Finding | File(s) | Change |
| --- | --- | --- |
| S2 | `skills/subagent-driven-development/implementer-prompt.md` | Replace the trait claim with "Keep files focused so edits stay reliable:" |
| S3 | `skills/intent-review/intent-reviewer-prompt.md` | Replace "BY DEFAULT, not just when convenient" with "Report every finding of this class." |
| C1 | `agents/PROJECT.md`, `agents/PROJECT.template.md` | Point xia2 risk signals at `rules/research-depth.md` and `skills/xia2/references/depth-classifier.md` |
| C2 | `skills/README.md` | Reword check 1.8 so the deploy rewrite cannot turn it into `.claude/harness-manifest.json` |
| C3 | `agents/PROJECT.md` | Add the pytest targeted-run form and the `PYTESTS` list |
| C4 | `agents/PROJECT.md` | Point code-style conventions at `AGENTS.md` |
| C5 | `skills/subagent-driven-development/implementer-prompt.md` | Add `lane` and `harness_delta` to the implementer report format |
| C7 | `rules/auto-correct-scope.md`, `rules/plan-format.md`, `skills/README.md` | `python` → `python3` |
| C8 | `rules/orchestration.md`, `rules/wave-parallelism.md`, `rules/auto-correct-scope.md`, `CLAUDE.md`, implementer prompt | Legacy `<verify>` / `<action>` / `<files>` → `Verify` / `Action` / `Files` |
| C9 | `rules/behavior.md` | Drop the pinned "Claude Opus 5.x guidance" reference |
| C10 | `agents/test-runner.md` | Replace the example-laden description with one sentence |
| C11 | `CLAUDE.md` | Make the code-review-graph instruction conditional on the server being connected |

## Non-goals

Findings the audit marked `flag` (S1, S4–S9, C6, C12–C18). Each needs a decision first.

## Error behavior and tests

Text-only edits. Proof is grep checks per finding plus the doc-truth lint and the repository suite
(`bash scripts/run-tests.sh`) at branch finish.
