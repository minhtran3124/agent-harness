---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: claude
date: 2026-07-10
---

# 0021. Stop shipping *.proposed files from the harness

## Context

`sync_protected_dir` restores a consumer's `skills/xia2/PROJECT.md.proposed` unconditionally, on the premise that the harness ships none of its own. The premise was false: `f7d2d58` had committed `skills/xia2/PROJECT.md.proposed` (7140 bytes) and `agents/PROJECT.md.proposed` as artifacts of a `bootstrap-xia2` run against this meta-repo. With those shipped, the restore freezes a consumer's copy forever and silently discards source updates — even under `--overwrite-conflicts`. Reproduced.

## Options

- **(a) `git rm` both + gitignore `*.proposed`** — makes the design's premise true rather than accidentally true; minimal. Cost: deleting files from the harness source is a Rule-4 action.
- **(b) Add both `.proposed` paths to `BOOTSTRAP_OWNED_FILES`** so they flow through the conflict machinery. Cost: keeps shipping a meaningless meta-repo proposal to every consumer forever.
- **(c) Restore the local `.proposed` only when the source ships none.** Cost: leaves the original clobber gap open — a consumer's pending proposal is destroyed by the meta-repo's copy.

## Decision

**(a)**, human-approved. A `.proposed` is by definition a per-repo human-review artifact (`skills/bootstrap-xia2/SKILL.md` step 4: "Do NOT overwrite `PROJECT.md`. Write proposals to `xia2/PROJECT.md.proposed`"). The harness has no business shipping one. Landed as `cfff07c`.

## Why

Note `git rm --cached` alone is **not** sufficient: `copy_dir` reads the working tree, not the git index, so a file left on disk is still copied by a local `deploy-harness.sh` run. The files must actually be removed.

## Consequences

Deleting source files is Rule 4 ("removing existing functionality"). Guardrail: `tests/scripts/resync-conflict.test.sh` case 1 asserts `find "$T1/.claude" -name '*.proposed'` is empty, repo-wide; verified non-vacuous by the "re-add a shipped `.proposed`" mutation. The protection is an invariant enforced by `.gitignore` + CI, not a runtime guard.

Applies when: Make this decision when a restore or merge path assumes the source ships none of some per-repo artifact class — enforce that assumption as a tested invariant, do not launder the artifact through conflict machinery.

Related:
- `docs/solutions/harness/unverified-premise-propagates-through-plan-anchored-reviews.md` — the failure that forced Decision 1.
- ADR 0015 — the shared protected-path surface and the ground-truth-before-acting principle.
- `docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md` — why the `bookkeeping.sh` regex fix (option B) needs its own lane.

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness/ before #567 and is in git history.
