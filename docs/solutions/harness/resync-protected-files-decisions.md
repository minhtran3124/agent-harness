---
problem_type: decision
module: harness
tags: resync-conflict, protected-files, bookkeeping-automation, versioning-contract, rule-4, targeted-list, ground-truth
severity: standard
applicable_when: Make these decisions when guarding a small enumerable set of files from a destructive sync, when finishing a branch in harness-skills, or when a restore path assumes the source ships none of some per-repo artifact class.
affects:
  - scripts/deploy-harness.sh
  - scripts/install-harness.sh
  - .gitignore
  - tests/scripts/resync-conflict.test.sh
  - specs/resync-protected-files/ESCALATIONS.md
supersedes: null
confidence: high
confirmed_at: 2026-07-10
---

## Applicable When

Guarding a small enumerable set of files from a destructive sync; finishing a branch in this repo; or writing a restore path premised on the source shipping none of some artifact class.

## Decision 1 — stop shipping `*.proposed` from the harness

### Context

`sync_protected_dir` restores a consumer's `skills/xia2/PROJECT.md.proposed` unconditionally, on the premise that the harness ships none of its own. The premise was false: `f7d2d58` had committed `skills/xia2/PROJECT.md.proposed` (7140 bytes) and `agents/PROJECT.md.proposed` as artifacts of a `bootstrap-xia2` run against this meta-repo. With those shipped, the restore freezes a consumer's copy forever and silently discards source updates — even under `--overwrite-conflicts`. Reproduced.

### Options Considered

- **(a) `git rm` both + gitignore `*.proposed`** — makes the design's premise true rather than accidentally true; minimal. Cost: deleting files from the harness source is a Rule-4 action.
- **(b) Add both `.proposed` paths to `BOOTSTRAP_OWNED_FILES`** so they flow through the conflict machinery. Cost: keeps shipping a meaningless meta-repo proposal to every consumer forever.
- **(c) Restore the local `.proposed` only when the source ships none.** Cost: leaves the original clobber gap open — a consumer's pending proposal is destroyed by the meta-repo's copy.

### Decision & Rationale

**(a)**, human-approved. A `.proposed` is by definition a per-repo human-review artifact (`skills/bootstrap-xia2/SKILL.md` step 4: "Do NOT overwrite `PROJECT.md`. Write proposals to `xia2/PROJECT.md.proposed`"). The harness has no business shipping one. Landed as `cfff07c`.

Note `git rm --cached` alone is **not** sufficient: `copy_dir` reads the working tree, not the git index, so a file left on disk is still copied by a local `deploy-harness.sh` run. The files must actually be removed.

### Applicable When

Make this decision when a restore or merge path assumes the source ships none of some per-repo artifact class — enforce that assumption as a tested invariant, do not launder the artifact through conflict machinery.

### Consequences

Deleting source files is Rule 4 ("removing existing functionality"). Guardrail: `tests/scripts/resync-conflict.test.sh` case 1 asserts `find "$T1/.claude" -name '*.proposed'` is empty, repo-wide; verified non-vacuous by the "re-add a shipped `.proposed`" mutation. The protection is an invariant enforced by `.gitignore` + CI, not a runtime guard.

## Decision 2 — never hand-edit `VERSION` / `CHANGELOG.md` when finishing a branch here

### Context

`skills/finishing-a-development-branch/SKILL.md` Step 1b instructs updating `CHANGELOG.md` + `VERSION` and committing them with the work. But `scripts/bookkeeping.sh` — invoked by `.github/workflows/post-merge-maintenance.yml` on `pull_request_target: closed` gated by `merged == true` — already bumps `VERSION` and inserts a dated `## [x.y.z]` CHANGELOG section on merge.

### Options Considered

- Hand-edit per Step 1b → the automation bumps again at merge. Double-bump.
- Let the automation own both files; leave them out of the PR diff entirely.

### Decision & Rationale

Never hand-edit them in this repo. The post-merge automation is authoritative. Both files were kept out of PR #50's diff, and the reason was recorded in the commit message.

**Correction to a claim made during this session:** it was asserted that "v0.3 Phase 1 explicitly removed the manual-append mandate." That is **false** for this skill. The removal applied to `feature-intake`'s guardrails; `finishing-a-development-branch/SKILL.md` Step 1b still mandates the manual edit. Skipping it is therefore a **deliberate deviation from a live skill instruction**, not a waiver the skill grants. The skill and the automation contradict each other, and the skill should be updated.

### Applicable When

Make this decision when finishing or PR-ing a branch in `harness-skills` — leave `VERSION` and `CHANGELOG.md` to the merge automation, and say so in the commit message.

### Consequences

Open escalation (deny-on-no-response) in `specs/resync-protected-files/ESCALATIONS.md`: `scripts/bookkeeping.sh:76` selects `bump="minor"` only when the changed-file list matches `^(hooks/|settings\.json|skills/)`. A change to `scripts/deploy-harness.sh` — the deploy engine that runs `rm -rf` inside every consuming project — is therefore auto-tagged **patch** (`0.8.1` → `0.8.2`), while `CHANGELOG.md` lines 4–6 promise **minor** for "a changed skill/hook contract". Options: (A) accept the patch bump and file a follow-up; (B) widen the regex, which touches the versioning contract and needs its own lane plus a `tests/scripts/bookkeeping.test.sh` update.

Second consequence: `finishing-a-development-branch/SKILL.md` Step 1b is stale and will keep telling agents to double-bump until it is corrected.

## Decision 3 — a targeted protected-file list, not a checksum manifest

### Context

The stated problem was narrow: stop blind re-sync from clobbering the four files `bootstrap-xia2` generates per project (`rules/architecture.md`, `rules/guidelines.md`, `agents/PROJECT.md`, `skills/xia2/PROJECT.md`). A general solution was available.

### Options Considered

- **Hardcoded `BOOTSTRAP_OWNED_FILES`** — a code comment pointing at `bootstrap-xia2/SKILL.md` is the contract. Cost: can drift silently if `bootstrap-xia2` gains new outputs.
- **Checksum manifest + 3-way diff** over all synced files — correct for arbitrary user customizations. Cost: far more code than the stated problem needs.
- **Diff-any prompt on every differing file** — too noisy on normal updates.

### Decision & Rationale

The targeted four-file list. Minimum machinery that solves the verbatim request; non-bootstrap files still overwrite exactly as before, which the intent review confirmed is what the user asked for. A machine gate against list-vs-`SKILL.md` drift was an explicit non-goal.

### Applicable When

Make this decision when a data-loss guard is requested for a known, small, enumerable set — hardcode the set rather than build a general manifest or diff engine.

### Consequences

The list can drift from `skills/bootstrap-xia2/SKILL.md` with no machine check. Conflict resolution is also **batch, not per-file** (one policy for all conflicting files) — flagged by `/intent-review` as `drift` against "let they make decision", human-approved; the escape hatch is `[b] backup+overwrite`, then merge from `.harness-backup-<ts>/`.

## Related

- `docs/solutions/harness/unverified-premise-propagates-through-plan-anchored-reviews.md` — the failure that forced Decision 1.
- `docs/solutions/harness/gap-closure-decisions.md` — the shared protected-path surface and the ground-truth-before-acting principle.
- `docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md` — why the `bookkeeping.sh` regex fix (option B) needs its own lane.
