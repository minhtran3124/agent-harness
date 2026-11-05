---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: claude
date: 2026-10-15
---

# 0027. Exclude synonym-rotation from the STE review count and baseline

## Context

The linter runs as a per-file ratchet, and the task reviewer reads per-file BASE and HEAD hard
counts in the review package. The hard count includes `synonym-rotation`, the
one-concept-one-word rule. The earlier record measured that rule with no effect (H3).

## Options

- Keep the blocking review check with every hard rule.
- Make the review check advisory.
- Keep the blocking check, but exclude `synonym-rotation`.

## Decision

Exclude `synonym-rotation` from both the review-package count and the baseline.

## Why

The approved intent says not to turn an unmeasured rule into a blocking gate. Intent review caught the conflict after correctness review passed. The structural rules (semicolon, long sentence, phrasal verb, nominalization, marketing adjective) still count.

## Consequences

A manual `ste-lint.py` run (as the vendored `SKILL.md` documents it) still counts
`synonym-rotation`, so an agent that self-checks by hand sees higher counts than the gates do.
Keep the two `DISABLED_RULES` constants equal.

Applies when: You change `DISABLED_RULES` in `scripts/check_ste_baseline.py` or in `skills/subagent-driven-development/scripts/review_package.py`, or you add a lint rule to a check that can block.

Related:
- docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md
- docs/research/ste-terminology-evidence/DECISION.md
- specs/ste100-harness-prose/DECISION.md
- specs/ste100-harness-prose/design.md

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness/ before #567 and is in git history.
