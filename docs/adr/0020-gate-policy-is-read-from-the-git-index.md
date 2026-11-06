---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: claude
date: 2026-07-23
---

# 0020. Gate policy is read from the git index

> Superseded in part (2026-09-29, hook-surface simplification): the former `risk-corroboration.sh` hook and
> `commit-gate.sh` no longer exist in this tree; read mentions of them below as historical. Affects: `harness-manifest.json`,
> `scripts/check_manifest.py`, `scripts/check_gate_modes_smoke.py` (historical). Tags: gate-modes, manifest-as-authority.

## Context

Codex PR #160: hook read the manifest from the worktree while all gated signals are index-side.

## Options

- Worktree read (simpler) — an uncommitted local edit weakens the gate for a commit that doesn't contain it.
- `git show :harness-manifest.json`, fail-closed.

## Decision

Index — the policy input must come from the same tree as the signals it gates.

## Why

Loosening now requires *staging* the manifest edit, auditable in the same commit. - Always: commit-time gates read policy files from the index (`git show :<path>`). - Never: let an unstaged worktree edit change the enforcement outcome for a staged commit.

## Consequences

A manifest staged for deletion or unreadable from the index blocks rather than allows. Full story:
[gate-config-must-read-index](../solutions/harness/gate-config-must-read-index.md).

Related:
- docs/solutions/harness/gate-config-must-read-index.md
- docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness/ before #567 and is in git history.
