---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: claude
date: 2026-07-23
---

# 0018. Loosening knob lives in the manifest and settings.local.json, not settings.json

> Superseded in part (2026-09-29, hook-surface simplification): the former `risk-corroboration.sh` hook and
> `commit-gate.sh` no longer exist in this tree; read mentions of them below as historical. Affects: `harness-manifest.json`,
> `scripts/check_manifest.py`, `scripts/check_gate_modes_smoke.py`. Tags: gate-modes, manifest-as-authority.

## Context

Review item said: add an `env` block to root `settings.json` with
`RISK_WARN_CATEGORIES="weakening-validation"`.

## Options

- `env` in root `settings.json` — rejected: `deploy-harness.sh` re-sync merges with the **consumer's** file as base and replaces only `.hooks`; a new top-level key ships on first install and is silently dropped on every re-sync.
- Inline `VAR=x git commit` prefix — impossible: a PreToolUse hook runs *before* the command with the **session** env; the prefix sets the var only for the `git` process. Reproduced empirically.
- Manifest `mode` for durable + `.claude/settings.local.json → env` for session-scoped.

## Decision

Split honestly: durable loosening in the manifest; session override in `settings.local.json → env` (the only place a PreToolUse hook actually inherits env from); delete the impossible advice.

## Why

- Always: check deploy-harness merge semantics before adding a top-level `settings.json` key for consumers. - Never: advise `VAR=x git commit` to influence a PreToolUse hook.

## Consequences

"Reachable knob" = machine-local gitignored config; a shared in-repo knob remains an open
follow-up (intent-review advisory).

Related:
- docs/solutions/harness/gate-config-must-read-index.md
- docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness/ before #567 and is in git history.
