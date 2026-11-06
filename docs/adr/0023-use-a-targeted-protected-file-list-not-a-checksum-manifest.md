---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: claude
date: 2026-07-10
---

# 0023. Use a targeted protected-file list, not a checksum manifest

## Context

The stated problem was narrow: stop blind re-sync from clobbering the four files `bootstrap-xia2` generates per project (`rules/architecture.md`, `rules/guidelines.md`, `agents/PROJECT.md`, `skills/xia2/PROJECT.md` (historical)). A general solution was available.

## Options

- **Hardcoded `BOOTSTRAP_OWNED_FILES`** — a code comment pointing at `bootstrap-xia2/SKILL.md` is the contract. Cost: can drift silently if `bootstrap-xia2` gains new outputs.
- **Checksum manifest + 3-way diff** over all synced files — correct for arbitrary user customizations. Cost: far more code than the stated problem needs.
- **Diff-any prompt on every differing file** — too noisy on normal updates.

## Decision

The targeted four-file list.

## Why

Minimum machinery that solves the verbatim request; non-bootstrap files still overwrite exactly as before, which the intent review confirmed is what the user asked for. A machine gate against list-vs-`SKILL.md` drift was an explicit non-goal.

## Consequences

The list can drift from `skills/bootstrap-xia2/SKILL.md` (historical) with no machine check. Conflict resolution is also **batch, not per-file** (one policy for all conflicting files) — flagged by `/intent-review` as `drift` against "let they make decision", human-approved; the escape hatch is `[b] backup+overwrite`, then merge from `.harness-backup-<ts>/`.

Applies when: Make this decision when a data-loss guard is requested for a known, small, enumerable set — hardcode the set rather than build a general manifest or diff engine.

Related:
- `docs/solutions/harness/unverified-premise-propagates-through-plan-anchored-reviews.md` — the failure that forced Decision 1.
- ADR 0015 — the shared protected-path surface and the ground-truth-before-acting principle.
- `docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md` — why the `bookkeeping.sh` regex fix (option B) needs its own lane.

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness/ before #567 and is in git history.
