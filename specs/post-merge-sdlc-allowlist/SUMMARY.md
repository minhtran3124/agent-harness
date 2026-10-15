# post-merge-sdlc-allowlist — Summary

Lane: high-risk
Confidence: high
Reason: audit/security hard gate. The change widens a `pull_request_target` (write-token) trigger to one more base branch. The human gave the exact change and accepted its consequence.
Flags: audit/security, existing behavior
Affects: .github/workflows/post-merge-maintenance.yml (post-merge bookkeeping trigger)
Input-type: maintenance

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

add sdlc to that list in a small PR against main. Note that a list containing sdlc would also let the automation run on sdlc merges, by design.

### Intake notes

- Context: the `branches:` allowlist of `post-merge-maintenance.yml` on `main` is `[main, loop, simplify]`. `pull_request_target` loads the workflow from the default branch, so PRs merged into `sdlc` (#292, #293) fired nothing, and their runs stay at `ready_to_merge`. This is the silent-rot class from issue #196.
- Scope narrowed by the human to one allowlist entry, plus the guard test. The design is given, so there is no design.md, research-brief.md or PLAN.md (two files, three steps). High-risk evidence is kept: Verify rows, Rollback, and independent correctness and intent reviews.
- `simplify` stays in the list. Removing an entry is a separate decision.

## What changed

`sdlc` is added to the `pull_request_target` base-branch allowlist in `.github/workflows/post-merge-maintenance.yml` on `main`, with a dated comment line. `tests/scripts/post-merge-runstate-staging.test.sh` now requires `sdlc` in the allowlist, so the entry cannot silently disappear.

### Rationale

The workflow comment calls this allowlist the one authoritative place for the policy. It must be synced on `main`, because `pull_request_target` reads the definition from the default branch. Adding the active integration branch is the documented fix for this silent-rot class (#196, #36/#44/#45).

### Alternatives considered

- Remove the `branches:` filter. Rejected: the workflow comment and the guard test forbid an unbounded write-token trigger.
- Transition the stuck runs by hand with a bookkeeping commit on `sdlc`. Rejected as the fix, because it repairs the symptom once and leaves future `sdlc` merges broken.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Allowlist guard and staging contract | `bash tests/scripts/post-merge-runstate-staging.test.sh` | 0 | 12 passed, including the new "allowlist includes the active integration branch (sdlc)" | |

The new assertion fails against `main`'s current workflow: the `branches:` line there has 0 matches for `sdlc` (`git show github/main:.github/workflows/post-merge-maintenance.yml`). The full suite (`bash scripts/run-tests.sh`) runs before push.

### Not auto-verified

- That GitHub fires the job on the next `sdlc` merge — reached traceability only. No merge into `sdlc` has happened since this change, and `pull_request_target` runs only on GitHub.
- The stuck `ready_to_merge` runs from earlier `sdlc` merges (#292, #293) are not terminalized by this change, because the trigger does not replay past merges — reached traceability only.

### Rollback

- `git revert <sha>` of this PR's merge on `main`. That restores `branches: [main, loop, simplify]`, and the guard-test assertion goes with it.

### Harness-Delta

- none

### Intent Findings

Intent review (independent). No gap and no drift: the list is the old value `[main, loop, simplify]` plus `sdlc`, the PR is one commit based on `main`, and the "by design" consequence is stated in the workflow comment. Three excess items, all report-only:

| # | Class | Finding | Route |
| --- | --- | --- | --- |
| 1 | excess | The guard-test assertion that requires `sdlc`. Removing `sdlc` later also needs a test edit. | report-only |
| 2 | excess | The dated comment history (#292, #293, `ready_to_merge`) beyond the "by design" sentence. | report-only |
| 3 | excess | This SUMMARY.md: harness bookkeeping that roughly doubles the PR's size. | report-only |

### Correctness review

Independent reviewer, range `github/main..08288ca`. **No correctness defects.** Paths traced:

- the trigger allowlist;
- the base-only checkout (the PR head is never run);
- PR strings passed only through env;
- the run-state slug loop (`ready_to_merge` → `shipped`);
- `bookkeeping.sh`, which assumes no branch;
- the bookkeeping PR (`--base "$BASE_REF"` = `sdlc`);
- the loop guard (`chore/bookkeeping-<N>`);
- the later `sdlc` → `main` merge, where terminal slugs are skipped.

Every file the job stages exists on `sdlc`. Advisory, score 0:

- Three comments still named only `simplify`. Fixed in a follow-up commit.
- Inherited traits that now also apply to `sdlc`: a bookkeeping VERSION/CHANGELOG bump on `sdlc` can conflict or double-count when `sdlc` merges into `main`, and two `sdlc` merges close together each bump VERSION from the same value. This is not new in this diff.
