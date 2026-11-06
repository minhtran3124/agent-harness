---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: claude
date: 2026-07-23
---

# 0019. Enforcement mode is separate from risk classification

> Superseded in part (2026-09-29, hook-surface simplification): the former `risk-corroboration.sh` hook and
> `commit-gate.sh` no longer exist in this tree; read mentions of them below as historical. Affects: `harness-manifest.json`,
> `scripts/check_manifest.py`, `scripts/check_gate_modes_smoke.py` (historical). Tags: gate-modes, manifest-as-authority.

## Context

Flipping two gates to warn raised: should `/feature-intake` also stop classifying them
`Lane: high-risk` (65% of specs are high-risk)?

## Options

- Loosen both axes together — invalidates intake eval fixture LC-11, redefines intake semantics.
- Warn-mode changes enforcement only.

## Decision

Enforcement only.

## Why

Fixes the pain (blocked commit, no working override) without redefining intake; LC-11 stays valid; warn still prints to stderr so the signal survives. The 65% rate is a *classification* problem → separate spec. - Always: change one axis (enforcement vs classification) per spec.

## Consequences

High-risk lane rate stays inflated until the classification spec lands. Blocking-gate trip rate
expected 85% → ~15%.

Related:
- docs/solutions/harness/gate-config-must-read-index.md
- docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness/ before #567 and is in git history.
