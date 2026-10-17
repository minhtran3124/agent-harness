# Intent: Prove the red test is real (bug-fix lane)

Author: Minh Tran
<!-- Set Status to approved or draft. Intake proceeds only on approved. -->
Status: approved

## Problem

For a bug fix (`Input-type: bug fix`), the lane check in `scripts/verify_summary.py --lane`
accepts a `red`/`green` row pair in `### Verify`. The `red` row is
`python3 scripts/run_at_commit.py <red sha> -- <test command>` with a claimed exit 1–123, and the
`green` row runs the same test command with exit 0. The check reads only the text of the rows. It
does not check that any code changed after `<red sha>`. So a "fix" that changes nothing passes:
the SUMMARY can claim red at `<red sha>` and green at HEAD, and no gate sees that the two trees
hold the same code. `scripts/run_at_commit.py` takes one rev and one command and does not know
red from green, so it cannot catch this either.

## Proposed outcome

1. In the bug-fix branch of `verify_summary.py --lane`, after the `red`/`green` pair is found,
   require a non-empty diff between `<red sha>` and the tree under check, outside the files that
   do not count as a fix (see Open question 1).
2. An empty diff is reported like the other red/green issues: a printed advisory by default, and
   an error (exit 1) when `REQUIRE_RED_TEST=1` is set. The switch and its default do not change.
3. The new check documents its tier: `Verifies:` some non-test code changed after the red
   commit. `Does not verify:` that the change fixes the bug, or that the red exit was real
   (`--check` re-runs rows).
4. `rules/auto-correct-scope.md` (the bug-fix bullet) and the implementer prompt say what the
   check now requires, in one clause each, if they restate the rule.

## Affected users and systems

- `scripts/verify_summary.py` (lane mode) and `scripts/test_verify_summary.py`.
- `hooks/commit-gate.sh` `check_lane_evidence` calls `--lane` on the staged SUMMARY. The hook
  itself is expected not to change (assumed).
- Consumer repos get the same check through the deployed `.claude/scripts/verify_summary.py`.
- Every bug-fix SUMMARY with a red/green pair. Today the check is advisory unless
  `REQUIRE_RED_TEST=1`.

## Constraints

- Keep `REQUIRE_RED_TEST=1` as the only switch: advisory by default, blocking when set.
- The commit gate judges the staged tree, not the working copy
  (`docs/solutions/harness/gate-config-must-read-index.md`). At commit time HEAD does not yet
  hold what is being committed, so the comparison must include staged changes (assumed: diff
  `<red sha>` against the index, which equals HEAD when nothing is staged).
- No new SUMMARY field unless the user picks option (b) in Open question 1.
- Exempt SUMMARYs (`Red test exempt: <reason>`) and non-bug-fix SUMMARYs keep today's result.
- `run_at_commit.py` does not change.

## Out of scope

- Issue #313 step 2 (route `Input-type: bug fix` to `diagnosing-bugs`). It waits for #318.
- Re-running the red or green test (that is `--check` and `REQUIRE_VERIFY=1`).
- Proving that the changed code is the fix (a mutation or revert test).
- Back-filling or editing old bug-fix SUMMARYs.

## Open questions

Decided by the user on 2026-10-17 ("approve" on the draft): question 1 is option (a), and
question 2 is the proposed advisory that blocks under `REQUIRE_RED_TEST=1`.
Amended by the user on 2026-10-17 (`ESCALATIONS.md` E001 = A, after correctness review): in
option (a), "the test files" are the paths that the red commit itself changed, not the paths in
the red row's test command.

1. **Which diff counts as the fix?** The issue says "in the files that the row names", but the
   `red` row names only a test command, not the fixed files. Options:
   - (a) Any path changed in `<red sha>`..tree, except `specs/**` and the test files. A test file
     is a path that appears in the red row's test command. (chosen: no format change)
   - (b) A new field (for example `Fix-files:`) that names the fixed files, and the diff must
     touch one of them.
   - (c) Any path changed except `specs/**`, with no test-file exclusion (simplest, weakest: a
     test-only edit after red passes).
2. **`<red sha>` cannot be resolved** (shallow clone, rebased away, a SUMMARY checked outside a
   git tree). Proposed: report "cannot verify the fix diff" as the same advisory; with
   `REQUIRE_RED_TEST=1` it blocks, because an unverifiable claim is not a pass (assumed).

## What success looks like

- A canary bug-fix spec whose "fix" changes nothing after `<red sha>`: `verify_summary.py --lane`
  exits 1 with `REQUIRE_RED_TEST=1` and prints the new advisory without it. The run is recorded
  in the SUMMARY `### Verify`.
- The same canary with a real code change after `<red sha>` exits 0.
- `bash scripts/run-tests.sh` passes, and existing bug-fix and non-bug-fix lane tests keep their
  results.

## Original request

GitHub issue #313 step 1 only (prove the red): in scripts/verify_summary.py --lane bug-fix branch, require a non-empty `git diff <red sha>..HEAD` in the changed code, keep REQUIRE_RED_TEST=1 advisory-by-default switch. Step 2 (routing to diagnosing-bugs) is out of scope until #318 exists. Worktree .claude/worktrees/feat+gh-313-prove-the-red (branch feat/gh-313-prove-the-red from sdlc ece206d). PR base: sdlc. Open point for the user: which diff counts — (a) any diff after <red sha> excluding specs/ and test files, or (b) a new field naming the fixed files.

Issue #313 step 1 text: "Prove the red. `scripts/run_at_commit.py` takes one rev and one command, and it does not know red from green. So put the assertion in the bug-fix branch of `scripts/verify_summary.py --lane`, which already parses the `red` row and its `<red sha>`. Require a non-empty `git diff <red sha>..HEAD` in the files that the row names. Keep the `REQUIRE_RED_TEST=1` switch: advisory by default, blocking when set." Proof: "Create a canary spec with a no-op \"fix\". Run `verify_summary.py --lane` on it. The issue passes when the command exits with code 1. Record the run in the SUMMARY."
