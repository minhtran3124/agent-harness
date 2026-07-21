# version-bump-single-owner — Summary

Lane: normal
Confidence: high
Reason: flag 8 (changes the finishing-branch workflow — removes the manual VERSION/CHANGELOG bump step); no hard gate — SKILL.md is a prompt doc, not settings.json/hooks/*/a skill engine.
Flags: existing behavior
Affects: skills/finishing-a-development-branch/SKILL.md (workflow doc); docs/solutions/ (new learning)
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane.

### Intent

> "ok, let run compound and open new PR to fix it"

referring to the friction surfaced at the end of the dynamic-rule-loading work:

> "the finishing-a-development-branch Step 1b (manual VERSION/CHANGELOG bump) conflicts with the post-merge-maintenance automation (event-sourced bump), causing double-bump ... Cách sửa gốc: bỏ Step 1b khỏi finishing-a-development-branch (để automation độc quyền lo CHANGELOG/VERSION), khớp với lời feature-intake."

## What changed

Removed the manual `VERSION` + CHANGELOG bump from `finishing-a-development-branch` Step 1b so
`bookkeeping.sh` (via `post-merge-maintenance.yml`) is the single owner of the release bump —
matching `feature-intake`'s existing "Do NOT hand-append the ledger" instruction. Recorded the
underlying learning as a `/compound` failure doc.

### Rationale

`bookkeeping.sh` unconditionally bumps VERSION from the current value and inserts a CHANGELOG
section on every merge; its idempotency guard keys on PR number, not on whether a human already
bumped — so a manual pre-bump double-counts (observed on PR #141/#142: 2.12→2.13 manual → 2.14
auto, skipped 2.13.0 section, orphaned Unreleased bullet). Single-owner removes the collision.

### Alternatives considered

- Add a CI check failing any non-bookkeeping PR that touches VERSION / `## [Unreleased]` —
  heavier; recorded as the lighter mechanical backstop in the compound doc's Guardrail, not
  built now (the doc fix removes the instruction that causes the leak in the first place).
- Make `bookkeeping.sh` detect a human pre-bump and not double-count — more complex, and it
  would legitimize two owners; rejected in favor of one owner.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Step 1b no longer instructs a manual VERSION bump | `grep -c "bump root .VERSION." skills/finishing-a-development-branch/SKILL.md` | 0 | expect 0 matches after edit |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | new solutions doc paths resolve |

### Rollback

- `git revert <sha>`

### Harness-Delta

- fix-direct — this task IS the harness fix (Step 1b removal) plus its compound record.
