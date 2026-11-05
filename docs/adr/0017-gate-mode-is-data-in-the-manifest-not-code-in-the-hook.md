---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: claude
date: 2026-07-23
---

# 0017. Gate mode is data in the manifest, not code in the hook

## Context

Gate modes lived in a `case` statement that `scripts/check_manifest.py` regex-parsed back out of
the hook source — the manifest was *declared* the authority while being validated against the
hook. Loosening one gate = 4-file coordinated edit + CI.

## Options

- Delete `category_mode()` outright — rejected 2026-07-16: the checker regex-parses the branches, deletion fails CI on 8 slugs.
- Status quo (hand-mirrored case).
- Make `mode` load-bearing data in the manifest; hook reads it at runtime; drop the source-regex.

## Decision

Data. Removes the *reason* the deletion objection existed instead of fighting the checker. Fail-safe (per-field, when a manifest IS resolved): slug absent / mode missing ⇒ `block`. Cost of a future loosening: one JSON field.

## Why

> **Revised by B3 (2026-08-06, `hook-surface-slim`, see ADR 0030):** the
> *absent-index-manifest* fallback is no longer block-all. `risk-corroboration.sh` now resolves modes
> from the git index (`git show :harness-manifest.json`) else **embedded defaults**
> (`hooks/lib/gate-modes.default.sh`, 2-warn/7-block parity, CI-drift-guarded). A consumer without a
> tracked manifest gets that parity, not deny-everything — and the hook never reads `.claude/`/worktree
> policy. The per-field fail-safe above still holds for a present-but-incomplete manifest.
- Always: when a checker regex-parses source to validate config, invert it — config becomes the runtime input, regex dies.
- Never: hand-mirror the same policy in code and data with a regex bridging them.

## Consequences

`RISK_WARN_CATEGORIES` only loosens (block→warn), never re-tightens — accepted; the manifest edit
is the durable path. `check_gate_modes_smoke.py` pins 2-warn/7-block in CI.

Related:
- docs/solutions/harness/gate-config-must-read-index.md
- docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md
- ADR 0021

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness/ before #567 and is in git history.
