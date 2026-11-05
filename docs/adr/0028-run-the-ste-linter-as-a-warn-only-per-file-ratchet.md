---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: claude
date: 2026-10-15
---

# 0028. Run the STE linter as a warn-only per-file ratchet

## Context

The linter is a style tool. A blocking CI or commit gate on it would block builds on wording.

## Options

- A blocking lint in CI or in a hook.
- A warn-only per-file baseline ratchet in `run-tests.sh`.
- A manual command only.

## Decision

A warn-only ratchet.

## Why

The default `check_ste_baseline.py` run always exits 0. `--strict` exits 1 on a WARN, and only plan checks use it. The earlier record forbids a blocking gate built on a rule with no measured effect.

## Consequences

`--strict` exits 0 when the run is skipped (the linter or baseline is unusable). The plan required
this, and correctness review recorded it as advisory (score 50).

Update 2026-10-15 (`specs/ste100-prose-rollout/` design D7): `--strict` now exits 1 on a skipped
run, so a skip is never read as a pass. The default run still exits 0. `--against <git-ref>`
compares each file with its baseline entry at that ref.

Applies when: You change how `run-tests.sh` or CI uses the STE linter.

Related:
- docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md
- docs/research/ste-terminology-evidence/DECISION.md
- specs/ste100-harness-prose/DECISION.md
- specs/ste100-harness-prose/design.md

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness/ before #567 and is in git history.
