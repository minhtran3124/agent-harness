---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: claude
date: 2026-07-17
---

# 0015. Verify each research-doc gap on disk before implementing it

## Context

Gap-closure work driven by `docs/research-*.md`, which named a backlog of "missing" harness features to implement. Before building, the question was how much to trust those research docs as ground truth for what does and doesn't already exist in the repo.

## Options

- **Option A:** Trust the research docs — treat each named gap as genuinely missing and implement directly. Faster to start; no verification step.
- **Option B:** Verify each named gap on disk first (grep/read the actual repo), then build only what is genuinely absent. Adds a per-gap verification cost up front but prevents wasted re-implementation.

## Decision

Chose **Option B** — verify each gap on disk before implementing.

## Why

The deciding factor: a research doc reflects the repo state at the moment it was written, and this repo moves faster than the research captures it. Concretely, the majority of "gaps" were already shipped — `verify_summary.py`, the read-only `reviewer` agent, the SessionStart `session-knowledge` hook, the Q3 `Affects:` contract field, `ci-strict-gate.sh`, and the entire `benchmarks/review-chain` infra. Building from the doc alone would have re-implemented all of these.

## Consequences

Enables: the real remaining work was a small fraction of the documented backlog; avoided re-implementing already-shipped features across ~5 phases. Constrains: every doc-named gap now carries a mandatory on-disk verification step before it can be actioned (slower to start, cheaper overall). The cross-session memory `research-docs-predate-repo` records the underlying observation; this is the decision/protocol derived from it.

Applies when: A future engineer is about to implement a backlog item named in a research or planning doc (`docs/research-*.md`, a gap-closure plan, a stale spec) that asserts a feature is missing — verify presence on disk before writing code.

Related:
- docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness/ before #567 and is in git history.
