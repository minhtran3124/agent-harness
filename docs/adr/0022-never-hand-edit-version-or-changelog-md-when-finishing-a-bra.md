---
ticket: legacy
stage: solutions-migration
status: superseded
superseded_by: 0031
confidence: high
decided_by: claude
date: 2026-07-10
---

# 0022. Never hand-edit VERSION or CHANGELOG.md when finishing a branch in this repo

## Context

`skills/finishing-a-development-branch/SKILL.md` Step 1b instructs updating `CHANGELOG.md` + `VERSION` and committing them with the work. But `scripts/bookkeeping.sh` — invoked by `.github/workflows/post-merge-maintenance.yml` on `pull_request_target: closed` gated by `merged == true` — already bumps `VERSION` and inserts a dated `## [x.y.z]` CHANGELOG section on merge. (historical)

## Options

- Hand-edit per Step 1b → the automation bumps again at merge. Double-bump.
- Let the automation own both files; leave them out of the PR diff entirely.

## Decision

Never hand-edit them in this repo. The post-merge automation is authoritative. Both files were kept out of PR #50's diff, and the reason was recorded in the commit message.

## Why

**Correction to a claim made during this session:** it was asserted that "v0.3 Phase 1 explicitly removed the manual-append mandate." That is **false** for this skill. The removal applied to `feature-intake`'s guardrails; `finishing-a-development-branch/SKILL.md` Step 1b still mandates the manual edit. Skipping it is therefore a **deliberate deviation from a live skill instruction**, not a waiver the skill grants. The skill and the automation contradict each other, and the skill should be updated.

## Consequences

Open escalation (deny-on-no-response) in `specs/resync-protected-files/ESCALATIONS.md`: `scripts/bookkeeping.sh:76` selects `bump="minor"` only when the changed-file list matches `^(hooks/|settings\.json|skills/)`. A change to `scripts/deploy-harness.sh` (historical) — the deploy engine that runs `rm -rf` inside every consuming project — is therefore auto-tagged **patch** (`0.8.1` → `0.8.2`), while `CHANGELOG.md` lines 4–6 promise **minor** for "a changed skill/hook contract". Options: (A) accept the patch bump and file a follow-up; (B) widen the regex, which touches the versioning contract and needs its own lane plus a `tests/scripts/bookkeeping.test.sh` update. (historical)

Second consequence: `finishing-a-development-branch/SKILL.md` Step 1b is stale and will keep telling agents to double-bump until it is corrected.

Applies when: Make this decision when finishing or PR-ing a branch in `harness-skills` — leave `VERSION` and `CHANGELOG.md` to the merge automation, and say so in the commit message.

Related:
- `docs/solutions/harness/unverified-premise-propagates-through-plan-anchored-reviews.md` — the failure that forced Decision 1.
- ADR 0015 — the shared protected-path surface and the ground-truth-before-acting principle.
- `docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md` — why the `bookkeeping.sh` regex fix (option B) needs its own lane.

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness/ before #567 and is in git history.
