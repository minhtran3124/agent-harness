---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: claude
date: 2026-10-15
---

# 0026. Vendor the asd-ste100 skill into skills/asd-ste100

## Context

`npx skills add` installed the skill into `.agents/skills/` with a lock file and a symlink in
`.claude/skills/`. `deploy-harness.sh` syncs only root `skills/`, so consumers did not get it.
`.agents/skills/` is also the Codex adapter's output location.

## Options

- Commit the `npx skills` install.
- Vendor into `skills/asd-ste100/`.
- Vendor only the linter under `scripts/`.

## Decision

Vendor into `skills/asd-ste100/` from upstream `3944283c18`, with three recorded deltas in `UPSTREAM.md`: an `allowed-tools` line, no upstream `README.md` or invalid-example fixture, and a linter path form that the doc-truth lint accepts.

## Why

Vendor into `skills/asd-ste100/` from upstream `3944283c18`, with three recorded deltas in `UPSTREAM.md`: an `allowed-tools` line, no upstream `README.md` or invalid-example fixture, and a linter path form that the doc-truth lint accepts.

## Consequences

Updates are a manual re-vendor. The skill is 2,659 words, over the 600-word ceiling, so
`audit_skill_prompts.py` exempts a skill directory that has `UPSTREAM.md`. The user chose this
over splitting the vendored file, which would make each re-vendor a manual merge. The exemption is
self-declared: any skill can add the marker (correctness review scored this 50, advisory).

Applies when: You add a third-party skill to the harness.

Related:
- docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md
- docs/research/ste-terminology-evidence/DECISION.md
- specs/ste100-harness-prose/DECISION.md
- specs/ste100-harness-prose/design.md

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness/ before #567 and is in git history.
