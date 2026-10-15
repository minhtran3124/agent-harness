# failing-test-first — Design

Written 2026-10-15. Pins: repo c88ce16

## Goal

A bug-fix run must prove that its test failed before the fix and passes after it. The proof is a
`red` and a `green` row in the `SUMMARY.md` `### Verify` table. `scripts/verify_summary.py` checks
that the pair is present and well-formed, advisory by default.

## Current state

- Intake has no bug-fix input type. The allowed values are new spec, spec slice, change request,
  new initiative, maintenance and harness improvement (`templates/SUMMARY.template.md`,
  `skills/feature-intake/SKILL.md` step 2). `scripts/verify_summary.py` does not read `Input-type`.
  Existing SUMMARYs also use free values (`harness fix`, `docs correction`, `plan execution (…)`)
  and mixed case (`Harness improvement`).
- Every `### Verify` row is re-run later. `verify_summary.py --check` (run by
  `finishing-a-development-branch`, `scripts/ci-strict-gate.sh:294`, and `hooks/commit-gate.sh:638`
  when `REQUIRE_VERIFY=1`) re-executes each row through `run_checks` with `shell=True`
  (`scripts/verify_summary.py:570`). It fails when the actual exit differs from the claimed one
  (`:993`). Without `--check`, the script rewrites each Exit cell with the actual exit (`:1011`).
- So a plain red row (the test at HEAD, Exit 1) breaks after the fix: `--check` reports a
  mismatch, and a plain run overwrites the red evidence with 0.
- Advisories already have a pattern: `REQUIRE_NOT_AUTO_VERIFIED` (`:65`). `check_lane_warnings`
  returns them (`:387`), but it returns `[]` at once when that variable is set (`:393`), and
  `_check_lane_targets` prints every warning with a fixed suffix naming that variable (`:547`).
  `hooks/commit-gate.sh:289` relays lines that start with `!` from a passing `--lane` run.
- Consumer repos receive only the scripts in `CONSUMER_SCRIPTS` (`scripts/deploy-harness.sh:45`),
  all Python, deployed under `.claude/scripts/`. `tests/scripts/consumer-subset.test.sh` pins
  that deployed set.

## Approaches considered

- **A. The red row runs the test at the pre-fix commit (chosen).** A new helper runs the test in
  a temporary worktree at a given sha. The red row records the helper's non-zero exit, and the
  green row runs the same test at HEAD with exit 0. Both rows reproduce their claimed exit on
  every re-run, so they fit `--check` unchanged. Cost: one new consumer script.
  **Scope note:** the intent puts a re-run of the red row out of scope. This approach adds no new
  re-run code, but the existing `--check` will re-run the red row, which raises the red evidence
  to truth tier where `--check` runs. The user approved A with this stated (2026-10-15).
- **B. A separate `### Red test` section outside `### Verify`.** Nothing re-runs or rewrites it.
  Simpler, but the red evidence is an unchecked claim, and it departs from E5's wording, which
  puts the red row in the `### Verify` table. Rejected by the user.
- **C. Keep a plain red row in `### Verify` (sha in Notes), and make `--check` and the rewrite
  skip rows whose `Check` is `red`.** No new script, and it stays at traceability tier. Rejected:
  it makes one class of Verify row exempt from the re-run that every other row gets, so the red
  evidence is a claim nothing checks, the same weakness as B. It also changes the shared re-run
  path that every gate depends on, instead of adding a new path. (Raised by the design reviewer
  after A was approved; recorded here for the user's final review.)

## Architecture

1. **`scripts/run_at_commit.py <sha> -- <arg…>`.** Creates a detached worktree at `<sha>` in a new
   temporary directory outside the repo (`git worktree add --detach`), runs the arguments after
   `--` as an argument list without a shell, with that worktree as the working directory, and
   returns the command's exit code. A command killed by signal `n` (a negative `returncode` in
   Python) returns 128+n, as a shell does, so a crash keeps a distinct code that the red-row rule
   rejects. It always removes the worktree (`git worktree remove --force`) in a `finally` block.
   Any failure of its own exits 125 (budget) with a message on stderr:
   no `--` or no command, an unknown sha, a `git worktree` error, or a command that cannot start
   (`OSError`, for example an unknown binary or an env-prefix form such as `FOO=1 pytest`). The
   test command must therefore be a plain argument list. Added to `CONSUMER_SCRIPTS`.
2. **`scripts/verify_summary.py` red/green check.** Applies only when the `Input-type:` header,
   trimmed and lower-cased, is exactly `bug fix`. It is satisfied by either:
   - a `red` row and a `green` row. `Check` cells are compared trimmed and lower-cased.
     - Red row: the command invokes `run_at_commit.py` (path `scripts/` or `.claude/scripts/`)
       with a 7–40 (budget) character hex sha, then `--`, then a non-empty test command. Its
       claimed Exit is an integer from 1 to 123 (budget). That rejects 0, 124 (the `run_checks`
       timeout code), 125 (the helper's own failure), 126 and 127 (the shell's cannot-execute and
       not-found codes), and 128 and above (a process killed by a signal).
     - Green row: its command equals the red row's test command after whitespace is normalized,
       and its claimed Exit is 0.
   - a line `Red test exempt: <reason>` in the `### Verify` section, with a non-empty reason.

   Otherwise it reports one issue that names what is missing.
   - Without `REQUIRE_RED_TEST=1`, the issue is a warning. It is returned by `check_lane_warnings`
     whatever `REQUIRE_NOT_AUTO_VERIFIED` is set to. Warnings carry the variable that enforces
     them, so this one prints with the suffix `(warn-only; set REQUIRE_RED_TEST=1 to enforce)`,
     and the Not-auto-verified warning keeps its own suffix. The printed line still starts with
     `!`, so `hooks/commit-gate.sh` relays it without a hook change.
   - With `REQUIRE_RED_TEST=1`, `check_lane_evidence` returns the issue as an error (exit 1), and
     `check_lane_warnings` does not return it, so it is not printed twice.
   - The function carries `Verifies:` / `Does not verify:` docstring lines at traceability tier.
3. **`templates/SUMMARY.template.md`.** Add `bug fix` to the `Input-type:` option list.
4. **`skills/feature-intake/SKILL.md`.** Add `bug fix` to the step 2 input types, used for any
   fix of wrong behavior, harness bugs included.
5. **`skills/subagent-driven-development`.** For a bug-fix run, the implementer commits the failing
   test before the fix, then records the `red` row (helper at that commit) and the `green` row, or
   the exemption line with its reason. The test command is a plain argument list (no `&&`, pipes,
   globs or env prefixes), because the red row runs it without a shell and the green row with one.
6. **`rules/auto-correct-scope.md`.** One line in the lane-evidence box: a bug-fix SUMMARY also
   needs the red/green pair or an exemption, advisory unless `REQUIRE_RED_TEST=1`.

## Error behavior

- A SUMMARY whose `Input-type` is not `bug fix` gets no new message and the same exit as today.
- A bug-fix SUMMARY with a missing or malformed pair prints one warning naming what is missing,
  and exits 0. Under `REQUIRE_RED_TEST=1` it exits 1 with the same message.
- A red row that claims 0 or anything from 124 up is rejected, so a timeout, a helper failure, a
  command that cannot start or a crashed process cannot pass as a failing test.
- `--check` re-runs the red row through the helper. It passes while the pre-fix commit returns
  the same exit, and reports a mismatch if it stops doing so.
- If the red sha becomes unreachable (a squash merge followed by branch deletion and garbage
  collection), a later `--check` on that SUMMARY gets 125 and reports a mismatch. The fix is to
  replace the pair with `Red test exempt: red commit <sha> no longer reachable`. See A5.
- Under `REQUIRE_VERIFY=1`, the commit-time re-run (`hooks/commit-gate.sh:638`) also runs the red
  row, so it creates and removes a worktree inside the PreToolUse hook, within the same 60-second
  (budget) row limit.

## Tests

- `scripts/test_verify_summary.py`, traceability tier, new cases:
  - a valid pair → no warning, exit 0;
  - no red row → one warning with the `REQUIRE_RED_TEST` suffix, exit 0;
  - the same SUMMARY under `REQUIRE_RED_TEST=1` → exit 1, and the warning is not also printed;
  - the warning still appears when `REQUIRE_NOT_AUTO_VERIFIED=1` is set;
  - `Red test exempt: <reason>` → accepted; an empty reason → rejected;
  - a green command that differs from the red test command → rejected;
  - a red row claiming 0, 124, 125, 126, 127, 128 or 139 → rejected; a red row claiming 1 → accepted;
  - `Input-type: Bug Fix` (mixed case) → the check applies;
  - a SUMMARY with another `Input-type` → no new message;
  - every `specs/*/SUMMARY.md` whose `Input-type` is not `bug fix` → `check_lane_warnings` and
    `check_lane_evidence` contain no red/green message. Bug-fix SUMMARYs are excluded: a warning is
    their designed result, so a later bug-fix run must not turn this advisory into a test failure.
- `scripts/test_run_at_commit.py`, truth tier, on a throwaway git repo:
  - a test that fails at the sha → its exit code is returned;
  - an unknown sha → 125; an unknown binary → 125;
  - a command killed by a signal → 128 plus the signal number;
  - after each run, `git worktree list` shows no extra worktree.
- `tests/scripts/consumer-subset.test.sh`: a deployed consumer tree contains
  `.claude/scripts/run_at_commit.py`.
- `bash scripts/run-tests.sh` before the PR.

## Success criteria

- A bug-fix SUMMARY with a valid pair: `verify_summary.py --lane` exits 0 with no red/green
  warning. Check: the valid-pair case in `scripts/test_verify_summary.py`.
- A bug-fix SUMMARY without a pair: exit 0 with the warning; exit 1 under `REQUIRE_RED_TEST=1`.
  Check: the missing-pair and opt-in cases in `scripts/test_verify_summary.py`.
- Every `specs/*/SUMMARY.md` whose `Input-type` is not `bug fix` gets no red/green message.
  Check: the non-bug-fix SUMMARYs case in `scripts/test_verify_summary.py`.
- `run_at_commit.py` returns the test's exit, returns 125 on an unknown sha or binary, and leaves
  no worktree behind. Check: `scripts/test_run_at_commit.py`.
- A deployed consumer tree contains `.claude/scripts/run_at_commit.py`. Check:
  `tests/scripts/consumer-subset.test.sh`.

## Non-goals

- A hook that blocks test edits during a fix (M2).
- Making the check blocking by default.
- New code that re-runs the red row. The existing `--check` re-runs every row anyway.
- Any change to `hooks/`.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | No existing `specs/*/SUMMARY.md` has `Input-type: bug fix`, so the new check changes no existing result | provenance: Local, 2026-10-15, `grep -rhi '^Input-type:' specs/*/SUMMARY.md` lists no `bug fix` value | accepted risk: a legacy SUMMARY mislabelled `bug fix` would only warn under the advisory default; the non-bug-fix SUMMARYs case in `scripts/test_verify_summary.py` covers every other SUMMARY | A legacy SUMMARY starts warning; fix its header or accept the warning |
| A2 | A detached worktree at the red sha, created and removed inside one row, fits the 60-second (budget, existing `run_checks` timeout) row limit for a small test | none yet: Inference, 2026-10-15, worktree creation is local and file-count bound | accepted risk: a throwaway-repo test cannot show large-repo timing | Large repos time out; the exemption line or a narrower test is the fallback |
| A3 | The red test command runs from a fresh worktree root, with no untracked setup (such as a venv inside the repo) | none yet: Inference, 2026-10-15 | accepted risk: the SDD instruction says to use an absolute interpreter path for such commands | The red row fails for a setup reason; the implementer adjusts the command |
| A4 | A red/green warning reaches the agent at commit time | provenance: Local, 2026-10-15, `hooks/commit-gate.sh:289` relays `!` lines from a passing `--lane` run | the warning-suffix case in `scripts/test_verify_summary.py` (the line starts with `!`) | The advisory is silent at commit; the opt-in still blocks |
| A5 | The red sha stays reachable wherever `--check` later runs on that SUMMARY | provenance: Local, 2026-10-15, this repo merges PRs with merge commits (`git log --first-parent github/sdlc`) | accepted risk: consumer repos may squash; the documented fallback is the exemption line | A later `--check` on that slug fails until the pair is replaced by `Red test exempt: red commit <sha> no longer reachable` |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| The `red` row proves the test failed on the bug | The new check is format-only. Where `--check` runs (finishing, CI, `REQUIRE_VERIFY=1`), the re-run proves only that the pre-fix commit returns the same non-zero exit. A test-runner usage or collection error (pytest exit 2, a test file missing at the sha) gives that too |
| The `green` test exercises the bug | No check can decide that; it stays with the task reviewer and correctness review |
| Bug fixes are always labelled `Input-type: bug fix` | Intake classifies by judgment; a mislabelled fix skips the check |
| An exemption reason is genuine | The check only requires a non-empty reason |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | The red row runs the test at the pre-fix commit through `run_at_commit.py` (approach A) | One new consumer script; red evidence is re-runnable by `--check` | settled |
| D2 | The helper is Python, not shell, and runs the test without a shell | Matches the other consumer scripts; the test command must be a plain argument list | settled |
| D3 | A run is a bug fix when `Input-type`, trimmed and lower-cased, is `bug fix` | New template and intake value; the check reads one header | settled |
| D4 | An untestable bug uses `Red test exempt: <reason>` in `### Verify` | No new section; an empty reason is rejected | settled |
| D5 | Rows are marked by `Check` = `red` / `green`; no new column | The table shape is unchanged | settled |
| D6 | Advisory by default; `REQUIRE_RED_TEST=1` blocks | Same opt-in shape as `REQUIRE_NOT_AUTO_VERIFIED` | settled |
| D7 | Every failure of the helper itself exits 125 (budget); a signal kill returns 128+n; a red row must claim an exit from 1 to 123 (budget) | A timeout, a broken setup, a command that cannot start or a crash cannot pass as a failing test | settled |
| D8 | Each warning carries its own enforcing variable, and the red/green warning does not depend on `REQUIRE_NOT_AUTO_VERIFIED` | `check_lane_warnings` and `_check_lane_targets` change shape; no hook change | settled |
