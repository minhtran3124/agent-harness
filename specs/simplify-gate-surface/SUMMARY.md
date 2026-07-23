# simplify-gate-surface — Summary

Lane: high-risk
Confidence: high
Reason: touches hooks/risk-corroboration.sh and the hard-gate list itself (high-blast + workflow-engine); it changes how the commit gate decides to block, so it is gate-defining work.
Flags: high-blast, workflow-engine
Affects: risk-corroboration gate contract (harness-manifest.json ↔ hooks/risk-corroboration.sh ↔ scripts/check_manifest.py)
Input-type: harness improvement
Route: high-risk chain — design.md + PLAN.md written; next `/using-git-worktrees` → `/subagent-driven-development` → `/correctness-review` → `/intent-review`
Escalate: no — the hard gates were narrowed by the human at request time ("muc 1 -> 3"), which scopes the work to review items 1→3 and leaves items 4→7 on the backlog

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> make the deep review code. now I feel we have a lot of scripts and gates. They are making block auto-process sometimes.
>
> I want to review all scripts and related gate/block. Thinking to make it simple and ez maintain.
>
> viet design + plan cho muc 1 -> 3

Items 1→3 of the review's cut list, verbatim as delivered:

1. **Invert the manifest coupling.** Hook reads `harness-manifest.json`; delete `category_mode()` and the source-regex checks in `check_manifest.py`. Unblocks everything else.
2. **Add an `env` block to `settings.json`** so the knobs are reachable — and set `RISK_WARN_CATEGORIES="weakening-validation"` there, which fixes your screenshot incident permanently and correctly.
3. **Make `workflow-engine` warn-mode, not block.** At 85% firing it's noise.

## What changed

<!-- filled at ship time -->

Not yet implemented — this spec carries the design + plan only.

### Rationale

The commit gate has lost discriminating power: `workflow-engine` fires on 34 of the last
40 commits (85%) and 41 of 63 specs declare `Lane: high-risk` (65%), so "high-risk" is the
default state and `/feature-intake`'s classification is nullified. The cheapest fix is not
to delete gates but to make their **mode** data (in `harness-manifest.json`) instead of code
(a `case` statement that `check_manifest.py` regex-parses back out of the hook source).
Once mode is data, loosening a noisy gate is a one-line JSON edit instead of a coordinated
4-file change plus CI.

### Alternatives considered

- **Delete `category_mode()` outright** (the 2026-07-16 over-engineering review's proposal) —
  rejected then and now for the same reason recorded in `phase-2-deep-review-2026-07-16.md:17`:
  `check_manifest.py` regex-parses those branches, so deleting them fails CI on 8 slugs.
  This spec removes the *reason* that objection existed rather than fighting it.
- **Add `env` to the root `settings.json`** (review item 2 as originally written) — rejected:
  `scripts/deploy-harness.sh:335-351` merges with `$cur` as the base and only replaces
  `.hooks`, so a new top-level key reaches a consumer on first install but is silently dropped
  on every re-sync. See `design.md` §3.
- **Delete the `weakening-validation` detector** — deferred to review item 6; setting its mode
  to `warn` is reversible and preserves the signal in the log.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Hook contract tests (27 cases, incl. 5 manifest-mode) | `bash tests/hooks/risk-corroboration.test.sh` | 0 | 27 passed — wave 1 | SC-1 |
| Mode source-regex gone from checker | `grep -q category_mode scripts/check_manifest.py` | 1 | 0 occurrences — wave 1 | SC-2 |
| Manifest inventory invariant holds | `python3 scripts/check_manifest.py` | 0 | consistent — wave 1 | SC-3 |
| Checker unit tests | `python3 -m pytest scripts/test_check_manifest.py -q --no-header -p no:cacheprovider` | 0 | 11 passed — wave 1 | SC-2 |

### Rollback

- `git revert <sha>` — the change is source-only (hook + manifest + checker + docs); no
  migration, no deployed state. To roll back only the loosening without reverting the
  refactor, set the two `mode` fields in `harness-manifest.json` back to `"block"`.

### Harness-Delta

- fix-direct — the harness's own escape hatch was documented in a way that produced unusable
  advice (`RISK_WARN_CATEGORIES=… git commit` as an inline prefix never reaches a PreToolUse
  hook). Task 1.1 corrects the hook's comment and block message. Candidate for `/compound`.
