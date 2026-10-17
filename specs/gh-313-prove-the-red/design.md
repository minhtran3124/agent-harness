# gh-313-prove-the-red — Design

Written 2026-10-17. Pins: repo 11ac08f
Revised 2026-10-17. Pins: repo 8b05a26

## Goal

For a bug-fix SUMMARY, make `scripts/verify_summary.py --lane` prove that code changed after the
red commit, outside `specs/` and outside the paths that the red commit itself changed (D10). A "fix" that
changes nothing then no longer passes the red/green check.

## Current state

- `_red_green_issue(text)` (`scripts/verify_summary.py`, around line 405) reads only the SUMMARY
  text. For `Input-type: bug fix` it accepts a `red` row
  (`[python3] scripts/run_at_commit.py <sha> -- <test>`, claimed exit 1–123) plus a `green` row
  with the same test command and claimed exit 0, or a `Red test exempt: <reason>` line.
- Two callers use it: `check_lane_warnings` (advisory, when `REQUIRE_RED_TEST` is unset) and
  `check_lane_evidence` (error, when `REQUIRE_RED_TEST=1`).
- `_git(root, *args)` (around line 793) already runs git for `--sc-history`.
- `hooks/commit-gate.sh` `check_lane_evidence` copies the staged SUMMARY into a `mktemp`
  directory and runs `--lane` on that copy from the repo root. It relays lines that start with
  `!` on the passing path too.
- One committed SUMMARY has a red row: `specs/gh-302-red-green-input-type/SUMMARY.md`
  (red sha `ee6da93`, test file `scripts/test_verify_summary.py`).
- `rules/auto-correct-scope.md:44` and `skills/subagent-driven-development/implementer-prompt.md:63`
  restate the red/green rule.

## Approaches considered

- **A. Separate the text parse from the git check (chosen).** Keep `_red_green_issue` pure text.
  Add `_red_pairs` (text only) and `_red_fix_diff_issue` (the only git caller), and call the
  second one from the two existing callers. The switch and the hook relay do not change. Cost:
  `--lane` runs git, but only for a bug-fix SUMMARY with a matched pair.
- **B. An `--expect-red` mode in `run_at_commit.py`.** Rejected: issue #313 states that this
  helper does not know red from green, and a test run does not prove that code changed.
- **C. A bash check in `commit-gate.sh`.** Rejected: it edits a high-blast hook, and a manual
  `--lane` run would not get the check. `verify_summary.py` is the evidence authority.

## Architecture

All code changes are in `scripts/verify_summary.py`.

- `_red_pairs(text) -> list[tuple[str, str]]`: the `(red_sha, test_command)` of each red row that
  has a matching green row. It returns `[]` for a non-bug-fix SUMMARY and when a
  `Red test exempt:` line has a non-empty reason.
- `_red_fix_diff_issue(text) -> str | None`: for each pair, list the paths that differ between
  the red commit and the index, drop the paths that do not count as a fix, and report when none
  remain. It returns `None` when `_red_pairs` is empty.
- `check_lane_warnings` and `check_lane_evidence` call `_red_fix_diff_issue` beside
  `_red_green_issue`, under the same `REQUIRE_RED_TEST` split.
- `rules/auto-correct-scope.md` (bug-fix bullet) and `implementer-prompt.md` (red/green step)
  each get one clause: after the red commit, a change must exist outside `specs/` and the red
  test files.

## Worked trace

A bug-fix SUMMARY has `| red | python3 scripts/run_at_commit.py abc1234 -- python3 -m pytest
scripts/test_x.py::test_y | 1 |` and a matching green row.

1. `_red_pairs` returns `[("abc1234", "python3 -m pytest scripts/test_x.py::test_y")]`.
2. `_red_fix_diff_issue` runs `git rev-parse --show-toplevel` in the process cwd, then
   `git diff --cached --name-only abc1234` in that root.
3. The test tokens are split on whitespace. Each token loses any `::…` suffix and a leading `./`:
   `{python3, -m, pytest, scripts/test_x.py}`.
4. From the diff paths, drop each path under `specs/` and each path equal to a token.
5. `scripts/x.py` remains, so the result is `None`. If only `scripts/test_x.py` and
   `specs/foo/SUMMARY.md` changed, the result is the empty-diff message.

## Error behavior

- **Empty fix diff:** `bug fix: no code change after red commit <sha> outside specs/ and the red
  test files`.
- **Cannot check:** `bug fix: cannot check the fix diff for red commit <sha> -- <cause>`, where
  `<cause>` is one of `git is not available`, `the current directory is not in a git repository`,
  or `the commit does not resolve here`.
- Both are `!` advisories when `REQUIRE_RED_TEST` is unset and errors (exit 1) when it is set.
  An unverifiable claim is not a pass (intent Q2).
- The docstring states the tier. `Verifies:` (provenance) a path outside `specs/` and the red test
  files differs between the red commit and the index. `Does not verify:` that the change fixes the
  bug, or that the red exit was real (`--check` re-runs rows).

## Tests

- The seam is `_red_fix_diff_issue` and the `main(["--lane", ...])` exit code, run in a real git
  repository built in `tmp_path` with the cwd set to it. Cases:
  - no-op fix: exit 1 with `REQUIRE_RED_TEST=1`, a `!` advisory without it (the canary);
  - a real code change after red: exit 0;
  - only the red test file changed: reported;
  - only `specs/` changed: reported;
  - a directory token (`pytest scripts/`) does not drop the fix file;
  - a staged, uncommitted fix counts;
  - an unknown sha: the cannot-check message with the `does not resolve` cause;
  - the commit-gate shape: the SUMMARY is a copy outside the repo and the cwd is in the repo
    (proves A1);
  - an exempt SUMMARY and a non-bug-fix SUMMARY: no git call.
- The existing `TestRedGreen` cases use the fake sha `abc1234`. A case that expects a pass under
  `REQUIRE_RED_TEST=1`, or that asserts "no warning" without the switch, moves to a temp repo with a
  real fix. The check is not relaxed, and no assertion passes only because of its wording.
- A regression case: `specs/gh-302-red-green-input-type/SUMMARY.md` passes `--lane` in this repo.
  It skips when `ee6da93` does not resolve (a shallow clone or a tarball); CI checks out with
  `fetch-depth: 0`.
- Evidence tier: truth for the temp-repo cases (the CLI is re-run and its exit compared).

## Success criteria

- SC-a: the no-op canary exits 1 under `REQUIRE_RED_TEST=1` (pytest case, exit 0). The canary
  pytest run has its own row in the SUMMARY `### Verify` (the intent's recording requirement).
- SC-b: a real fix exits 0, and the advisory is absent.
- SC-c: the existing red/green, exempt and non-bug-fix tests keep their results.
- SC-d: `bash scripts/run-tests.sh` exits 0.
- SC-e: the two prose files carry the new clause (grep, exit 0).

## Non-goals

- Issue #313 step 2 (route bug fixes to `diagnosing-bugs`); it waits for #318.
- Re-running the red or green test.
- Proving that the changed code is the fix (mutation or revert test).
- Back-filling or editing old bug-fix SUMMARYs.
- Changes to `hooks/commit-gate.sh`, `run_at_commit.py`, or the SUMMARY format.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | The commit gate runs `--lane` with its cwd inside the repo being committed. | provenance: Local, 2026-10-17, `hooks/commit-gate.sh:149-157` (`cd` to `CLAUDE_PROJECT_DIR` or the git toplevel before any check; `check_lane_evidence` passes a temp copy of the SUMMARY) | a temp-repo test that runs `--lane` on a SUMMARY copy outside the repo with cwd in the repo | Every gated bug-fix commit gets the cannot-check message; fallback: pass the repo root as a flag from the hook (a hook change, Rule 4) |
| A2 | `git diff --cached --name-only <sha>` lists the paths that differ between `<sha>` and the index, including staged-only changes. | none yet: Inference, git documentation recall | the staged-fix test case | A staged fix is reported as empty; fallback: union of `git diff --name-only <sha> HEAD` and `git diff --cached --name-only` |
| A3 | The gh-302 SUMMARY's red sha `ee6da93` resolves here and has a non-test diff. | provenance: Local, 2026-10-17, `git cat-file -t ee6da93` → `commit`; filtered diff is non-empty | the gh-302 regression case | That SUMMARY gets an advisory; fallback: none needed, it stays advisory unless the switch is set |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| The changed code fixes the bug. | The check is provenance-tier: it proves that something changed, not what the change does. |
| An old bug-fix SUMMARY is checked at its own fix time. | The diff runs to today's index. Later commits make an old SUMMARY pass. The check is meaningful at the commit that records the fix. |
| Every test file is excluded. | Only paths that the red commit changed are excluded (D10). A test file added after the red commit counts as a fix. |
| A merge commit works as the red commit. | `git diff-tree -r` prints no paths for a merge commit without `-m`, so nothing is excluded. Red commits are single-parent by the implementer prompt's step order. |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | A fix is any path in the red-to-index diff outside `specs/` and outside the red row's test-file tokens (intent Q1 = a). | No SUMMARY format change. | superseded by DC1 |
| D2 | An unresolvable sha, no git, or no repo gives the cannot-check message, advisory by default and an error under `REQUIRE_RED_TEST=1` (intent Q2). | A shallow clone with the switch set blocks bug-fix commits. | settled |
| D3 | Compare the red commit with the index (`git diff --cached`). | The gate judges the staged tree, per `docs/solutions/harness/gate-config-must-read-index.md`. | settled |
| D4 | Only exact file-path tokens are excluded; a directory token excludes nothing (round 1, Q1). | `pytest scripts/` does not hide a fix in `scripts/`. | superseded by DC1 |
| D5 | Each matched red/green pair needs its own non-empty diff (round 1, Q2). | One no-op pair is reported even if another pair has a fix. | settled |
| D6 | The repo is the one that holds the process cwd (`git rev-parse --show-toplevel`) (round 1, Q3). | Works with the hook's temp copy; a manual run must start inside the repo. | settled |
| D7 | Add one clause each to `rules/auto-correct-scope.md` and `implementer-prompt.md` (round 1, Q4). | A context-propagation audit runs. | settled |
| D8 | The canary is a pytest case on a temp git repo that calls the real CLI; no canary spec is committed (round 1, Q5). | The proof re-runs in CI. | settled |
| D9 | Approach A: `_red_pairs` (text) and `_red_fix_diff_issue` (git), wired into both existing callers. | `_red_green_issue` keeps its signature and tests; hook unchanged. | settled |
| D10 | The red test files are the paths that the red commit itself changed (`git diff-tree --root --no-commit-id --name-only -r -z --no-renames <red sha>`). A fix is any path in the red-to-index diff outside `specs/` and outside those paths. The red command's tokens are not used. | No SUMMARY format change. A directory, absolute, quoted or relative test path no longer matters, and a command that runs the file under repair no longer hides the fix. If the red commit also edits source, a fix that touches only that source is reported as no code change. | settled |

## Decision changes

- DC1 — 2026-10-17 — reopens D1 and D4 — evidence: correctness review location `scripts/verify_summary.py:528-538` scored 75: exact token equality lets a test-only edit pass when the red command names a directory or an absolute, quoted or relative path, and excludes the real fix when the red command runs the file under repair; user decision `ESCALATIONS.md` E001 = A — new decision: D10
