---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: claude
date: 2026-10-15
---

# 0025. Pilot three files, then gate the STE rewrite rollout

## Context

The user asked to apply the asd-ste100 skill to the whole harness: rewrite existing prose (A),
use the skill for new prose (B), and add the linter (C). An earlier record,
`docs/research/ste-terminology-evidence/DECISION.md`, measured three STE ideas. Only machine-decidable
acceptance criteria had an effect.

## Options

- Rewrite all prose with no trial.
- Run a full A/B before any rewrite.
- Pilot three files, then gate the rollout on the result.

## Decision

Pilot then gate.

## Why

Three high-traffic files were rewritten and measured with comprehension probes and real `feature-intake` runs (80 trials, $2.91). All three passed. Each method passes at original − 2 correct answers, with no probe drop from 10/10 to 7/10 or fewer.

## Consequences

The rollout of the other files (Phase 3) is a separate plan. Its task briefs must ask the task
reviewer for a per-file meaning-equivalence review, because the task-reviewer prompt does not run
one on its own. The pilot review ran only because the Task 2.2 brief asked for it, and it caught
two dropped conditions that the tests missed
(`docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`).

Applies when: You plan a bulk rewrite of agent-executed prose.

Related:
- docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md
- docs/research/ste-terminology-evidence/DECISION.md
- specs/ste100-harness-prose/DECISION.md (historical)
- specs/ste100-harness-prose/design.md (historical)

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness/ before #567 and is in git history.
