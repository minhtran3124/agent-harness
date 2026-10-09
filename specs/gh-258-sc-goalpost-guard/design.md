# gh-258-sc-goalpost-guard — Design

Issue #258 item 5. Intake: `specs/gh-258-sc-goalpost-guard/SUMMARY.md` (high-risk, medium).

## Goal

Stop a failing acceptance check from being quietly weakened until it passes. When a branch has
recorded an `SC-n` as failing and later changes that row's `Check` or `Expected` (or deletes the
row), `scripts/verify_summary.py` warns unless `### Deviations` names `SC-n`. Warn-first; an env
flag makes it block.

## Current state

- `PLAN.md` §3 holds the SC table `| ID | Behavior | Check | Expected |`.
  `scripts/verify_summary.py` `parse_sc_table` maps each `SC-n` to its expected exit only; it
  does not return `Check`.
- `SUMMARY.md` `### Verify` rows may carry a `Criterion` column naming an `SC-n`
  (`_parse_verify_rows`: `check, command, claimed_exit, notes, criterion`).
- Running `verify_summary.py <slug>` **without** `--check` re-runs every row and rewrites the
  `Exit` cells with the actual exit codes (`_rewrite_table`). A committed SUMMARY can therefore
  carry a row whose `Exit` differs from its SC's `Expected`. That committed row is the failure
  record this design reads. `--check` re-runs without writing.
- `weakening-validation` is a warn-mode, diff-based signal in `hooks/commit-gate.sh` that looks
  at removed `assert` / validator lines. It does not look at SC rows.
- `scripts/ci-strict-gate.sh` exits 0 early when no gated path is touched. The item-3 shipping
  section (`#274`) already runs before that exit. `verify_summary.py` already ships to consumers
  (`scripts/deploy-harness.sh` `CONSUMER_SCRIPTS=(`).

## Approaches considered

What counts as "recorded as failing":

1. **Branch history (chosen).** Some commit in `merge-base..HEAD` has a Verify row with
   `Criterion: SC-n` whose `Exit` differs from SC-n's `Expected` in that commit's PLAN. This is
   the issue's own wording ("the same branch where that row is recorded as failing"), it needs
   no new artifact, and it uses evidence that already exists.
2. Any change to an already-committed SC row: simpler, but it flags ordinary SC edits made
   during plan review.
3. A separate failure ledger written by `verify_summary.py`: explicit, but it adds an artifact
   and a write path, and the agent that writes it can also edit it.

Where the check runs and how it blocks:

1. **New `verify_summary.py` mode plus an env flag (chosen).** Called by `ci-strict-gate.sh`
   and the finish step; `REQUIRE_SC_STABLE=1` blocks. It matches "in `verify_summary.py`", uses
   the same switch shape as `REQUIRE_NOT_AUTO_VERIFIED`, and does not touch `hooks/`.
2. A mode read from `harness-manifest.json`, like `weakening-validation`. Rejected: it changes
   the CI-pinned 2-warn / 7-block parity and the hook defaults (high-blast).
3. A new category in `hooks/commit-gate.sh` `check_risk`. Rejected: high-blast, and it leaves
   `verify_summary.py`.

## Architecture

### 1. `verify_summary.py --sc-history <slug> --base <ref>`

The files are always `specs/<slug>/SUMMARY.md` and `specs/<slug>/PLAN.md`, read from git
objects, never from the working tree. There is no `--plan-dir`: it exists for a temp SUMMARY
copy, which does not apply to history.

**Repository seam.** Every git command runs with `cwd` = the repository root, resolved from the
current directory with `git rev-parse --show-toplevel`. The history logic is a function that
takes that root as a parameter, so tests point it at a temporary repository. The CLI passes the
resolved root. It never uses `_REPO_ROOT` (the script's own location). This also holds when the
script is deployed at `.claude/scripts/`, because both callers run from the repository root.

1. Resolve `mb = git merge-base <ref> HEAD`. Exit 2 with a usage message when `--base` is
   missing, the ref does not resolve, there is no merge base, the current directory is not
   inside a git repository, or `git` cannot be run.
2. List commits in `mb..HEAD` that touch either file, oldest first:
   `git rev-list --reverse <mb>..HEAD -- <summary> <plan>`. Merge commits are included as they
   come; no `--first-parent`.
3. For each commit `c`, read both files at `c` with `git show c:<path>`. If either is missing
   at `c`, there is nothing to record at `c`. Per D8 (DC1), Verify rows are judged only at a
   commit where `SUMMARY.md` itself changed, meaning its content differs from the previous commit
   in the walk (for the first commit in the walk, from the merge base) or it is new. A
   PLAN-only commit records nothing, so a row that a plan edit left stale is never a failure
   record. At a qualifying commit, for each Verify row whose `Criterion` is `SC-n`
   and whose `Exit` cell is an integer, compare it with SC-n's expected exit in the PLAN at
   `c`. A mismatch is a **failure record**. This includes `124`, which the rewriter writes for
   a timeout. A non-integer `Exit`, such as an empty cell, a trivial row or a placeholder, is
   ignored. An SC whose PLAN row is malformed at `c` (`parse_sc_table` returns `ERROR: …`)
   produces no record at `c`. For each SC-n, keep the **first** failure record, together with
   that commit's SC-n `Check` cell and expected exit token.
4. At `HEAD`, for each SC-n with a failure record:
   - neither file exists at HEAD (the spec directory was removed): skip the slug and print a
     note;
   - PLAN.md is missing at HEAD, or SC-n's row is gone from §3: **removed after failing**;
   - the expected exit token differs, or the `Check` cell differs after collapsing whitespace:
     **changed after failing**. Free text after `exit <n>` in `Expected` is not compared, so
     rewording the prose does not count;
   - otherwise nothing.
5. A finding is suppressed when any `Deviations` heading in the HEAD `SUMMARY.md` (every match of
   `^#{1,3}\s+Deviations\b`, not only the first) has `SC-n` as a whole token in its body, so
   `SC-1` does not match inside `SC-12`. If SUMMARY.md or its
   Deviations section is missing at HEAD, nothing is suppressed.
6. Output goes to stdout, one line per finding:
   `SC-GOALPOST [SC-n] <changed|removed> after it failed at <short-sha>; name SC-n in ### Deviations to acknowledge`.
   Exit 0 by default, or 1 when there is a finding and `REQUIRE_SC_STABLE=1`. No findings:
   exit 0 with a one-line summary. Any unexpected exception, such as a non-UTF-8 spec file,
   prints `sc-history: unexpected error: …` and exits 2, so exit 1 only ever means a finding.
7. A new helper reads each SC id's `Check` cell and expected-exit token. `parse_sc_table` keeps
   its current return shape, so existing callers do not change.

`Verifies:` no SC row that the branch recorded as failing has had its `Check` or `Expected`
changed, or been removed, without a `### Deviations` entry naming it. `Does not verify:` that a
Deviations entry justifies the change, that the SC was not weakened before its failure was
committed, or that the command's own content (a test file) was not weakened. Tier: provenance
(re-derived from git history), not truth.

### 2. Wiring

- **`scripts/ci-strict-gate.sh`.** A section next to the item-3 open-questions section, after
  the diff is computed and before `exit 0  # no gated paths touched`. For each slug whose
  `specs/<slug>/PLAN.md` or `specs/<slug>/SUMMARY.md` is in the diff, run
  `python3 scripts/verify_summary.py --sc-history <slug> --base "$BASE"` (the gate's existing,
  already validated `$BASE`). The exit codes map the same way as the item-3 section next to it:
  - rc 0: continue.
  - rc 1 with `REQUIRE_SC_STABLE=1`: a goalpost finding. The gate exits 1 with a BLOCKED line
    naming SC goalposts.
  - rc 1 without `REQUIRE_SC_STABLE=1`, or any other non-zero rc: print
    `sc-history check errored for <slug> (exit <rc>)`. This blocks only under
    `REQUIRE_SC_STABLE=1`. A crash exits 2 (step 6), so in warn mode it never blocks.

  `REQUIRE_SC_STABLE` has its surrounding whitespace stripped before the comparison, as the
  script does. If a spec directory is renamed to a different slug within `$BASE...HEAD`
  (`git diff --name-status -M`, an R entry), the section prints
  `sc-history: spec directory renamed <old> -> <new>; failure history before the rename is not followed`
  and counts it as an error, which blocks only under `REQUIRE_SC_STABLE=1`. The section never
  exits 0 on its own. It skips slugs whose spec directory no longer exists at HEAD.
- **`skills/finishing-a-development-branch/SKILL.md` step 3.** One clause: run
  `python3 scripts/verify_summary.py --sc-history <slug> --base <base>`, where `<base>` is the
  base already reported by `resolve_finish_context.py`. Relay any finding to the user and the PR
  body. In warn mode the flow continues. Under `REQUIRE_SC_STABLE=1` an exit 1 stops the flow.
  The skill stays within its 600-word ceiling (budget; 528 words measured 2026-10-09 with `wc -w`).

## Error behavior

| Situation | Output | Exit (default) | Exit (`REQUIRE_SC_STABLE=1`) |
|---|---|---|---|
| No SC row ever recorded as failing | summary line | 0 | 0 |
| SC-n failed, then `Expected` changed, not in Deviations | `SC-GOALPOST [SC-n] changed …` | 0 | 1 |
| SC-n failed, then `Check` changed, not in Deviations | same | 0 | 1 |
| SC-n failed, then its row removed, not in Deviations | `SC-GOALPOST [SC-n] removed …` | 0 | 1 |
| Any of the above, but Deviations names SC-n | none | 0 | 0 |
| SUMMARY.md or its `### Deviations` missing at HEAD | findings not suppressed | 0 | 1 if any finding |
| PLAN.md missing at HEAD, SUMMARY present | `removed` for every failed SC | 0 | 1 |
| Spec directory gone at HEAD (both files missing), whether or not a failure record exists | skip note | 0 | 0 |
| SC-n changed but never recorded as failing | none | 0 | 0 |
| Only the prose after `exit <n>` in `Expected` changed | none | 0 | 0 |
| SC-n failed and is unchanged (still failing or later passing) | none | 0 | 0 |
| SC row malformed at a commit (`ERROR: …` from `parse_sc_table`) | no record at that commit | 0 | 0 |
| `Exit` cell not an integer (empty, trivial, placeholder) | row ignored | 0 | 0 |
| `Exit` `124` (timeout written by the rewriter) | counts as a failure record | as rows above | as rows above |
| `--base` missing or unresolved, no merge base, not a git repository, or `git` unavailable | usage message | 2 | 2 |
| Any unexpected exception (for example a non-UTF-8 spec file) | `sc-history: unexpected error: …`, no traceback | 2 | 2 |
| PLAN-only commit leaves a SUMMARY row stale (D8) | no failure record | 0 | 0 |
| Slug has no SUMMARY or PLAN in any commit | summary line | 0 | 0 |

## Tests

- `scripts/test_verify_summary.py`: one test per error-behavior row. Each builds a temporary git
  repository with a base commit and then commits on top, so the history is real. The test calls
  the history function with that repository as its root, or runs the CLI with `cwd` set to it. Also covered:
  a `Exit` cell that is not an integer is ignored, `SC-1` is not matched inside `SC-12`, and the
  existing `--check` and `--lane` modes are unchanged. Tier: truth.
- `tests/scripts/ci-strict-gate.test.sh`:
  - a specs-only branch that records SC-1 failing, then changes SC-1 `Expected`, prints the finding and exits 0;
  - the same branch exits 1 under `REQUIRE_SC_STABLE=1`;
  - a branch with no failure record prints nothing;
  - an errored check (the fixture's `verify_summary.py` replaced by one that exits 2) prints
    `sc-history check errored`, exits 0 in warn mode, and exits 1 under `REQUIRE_SC_STABLE=1`.
- `tests/scripts/finishing-branch-contract.test.sh`: the skill names
  `verify_summary.py --sc-history`. Tier: traceability.

## Success criteria

- SC-1: the mode's output and exit codes match the error-behavior table (pytest).
- SC-2: in CI, a specs-only branch that moves a failed SC's goalpost prints the finding, exits 0
  by default and 1 under `REQUIRE_SC_STABLE=1`; an errored check never blocks in warn mode;
  existing ci-strict-gate cases still pass.
- SC-3: the finish skill runs the check (contract test).
- SC-4: existing `verify_summary.py` behavior is unchanged (existing pytest cases pass).
- SC-5: the finish skill stays within its 600-word ceiling (budget, `scripts/audit_skill_prompts.py`).

## Non-goals

- No change to `hooks/`, `harness-manifest.json` or the gate-mode parity.
- No new artifact (no failure ledger).
- No detection of weakening inside the command's own test content, or before the failure was
  committed.
- No blocking by default.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | A failing SC reaches git history as a committed Verify row whose `Exit` differs from the SC's `Expected` | provenance: Local, 2026-10-09, `scripts/verify_summary.py` `main` (without `--check`, `_rewrite_table` writes actual exits) | accepted risk: an agent can run only `--check` and never commit a failing row; then nothing is recorded and nothing is flagged | the guard is silent for that branch; stated in What we do not claim |
| A2 | The `Criterion` column ties a Verify row to an SC id | provenance: Local, 2026-10-09, `_parse_verify_rows` (fifth cell) and `rules/plan-format.md` "SUMMARY side" | SC-1 | rows without `Criterion` are invisible to the guard |
| A3 | The CI job has full history, so `git merge-base` and `git show <c>:<path>` work | provenance: Local, 2026-10-09, `.github/workflows/harness-ci.yml` `strict-gate` job (`fetch-depth: 0`) | SC-2 (in a local fixture repository), plus the exit-2 → check-error path in SC-1 and SC-2; the real CI checkout itself is not exercised | the mode exits 2; the gate reports a check error, not a pass |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| A failing SC can never be weakened | Only failures that reach a commit are seen (A1); a change made before the failing row is committed is invisible. |
| A Deviations entry justifies the change | The check only looks for the `SC-n` token; whether the reason is good is a reviewer's call. |
| Weakening of the tested code or test file is caught | The check compares SC `Check`/`Expected` cells, not what the command runs. |
| The check blocks by default | Warn-first; `REQUIRE_SC_STABLE=1` blocks. |
| A renamed spec directory keeps its failure history | The walk is per slug path. A rename is detected and reported as an error, which blocks under the flag, but history before the rename is not followed. A rename with a heavy rewrite, which git pairs as a delete plus an add, is not detected. |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | A failure record is a committed Verify row whose `Exit` differs from its SC's `Expected` at that commit, within `merge-base..HEAD` | no new artifact; failures never committed are not seen | superseded by DC1 |
| D2 | The check is a new `verify_summary.py --sc-history` mode, warn by default, `REQUIRE_SC_STABLE=1` blocks | no `hooks/` or manifest change | settled |
| D3 | Removing a failed SC row counts as a goalpost move | the strongest weakening is not a loophole | settled |
| D4 | A finding is acknowledged only by `SC-n` appearing as a whole token in HEAD `### Deviations` | the existing deviation record is the acknowledgement; no new field | settled |
| D5 | The CI section runs for any slug whose PLAN or SUMMARY changed, before the early exit, and never exits 0 itself; rc 1 blocks only under `REQUIRE_SC_STABLE=1`, as in the item-3 section | specs-only PRs are checked; existing tiers are never bypassed; a crash never blocks in warn mode | settled |
| D6 | `Expected` is compared by its `exit <n>` token only; `Check` by its whitespace-collapsed text | rewording the free text after the exit token is not a goalpost move | settled |
| D7 | Git runs in the repository root resolved from the current directory, passed into the history function | tests reach a temporary repository; the deployed copy works from a consumer root | settled |
| D8 | A failure record is a committed Verify row whose `Exit` differs from its SC's `Expected`, judged only at a commit where `SUMMARY.md` itself changed, against the PLAN at that commit, within `merge-base..HEAD` | a SUMMARY row left stale by a PLAN-only commit is not a failure; failures never committed are still not seen | superseded by DC2 |
| D9 | A failure record is a committed Verify row whose `Exit` differs from its SC's `Expected`, judged only at a commit where **that row** (same `Criterion`, same cells) is new or changed compared with the previous SUMMARY in the walk (the merge-base SUMMARY for the first commit), against the PLAN at that commit, within `merge-base..HEAD` | a row left stale by a PLAN-only commit stays not-a-failure even when unrelated SUMMARY text is edited later; failures never committed are still not seen | settled |

## Decision changes

- DC1 — 2026-10-09 — reopens D1 — evidence: correctness review of `51eb4e0..dcdce4d` (enclosing-function finder; scorer 50, confirmed by reading `sc_history`). Under D1, a PLAN-only commit that changes `Expected` while an older SUMMARY row still names that SC records a "failure" no one committed. A later `Check` edit then produces a false `SC-GOALPOST`, which blocks under `REQUIRE_SC_STABLE=1`. This contradicts the error-table row "SC-n changed but never recorded as failing → none". The user chose to fix it ("Sửa #1–#6"). — new decision: D8
- DC2 — 2026-10-09 — reopens D8 — evidence: a re-check of the fix round `dcdce4d..fb0657f` reproduced the same false positive with confidence 75. A scratch probe printed `SC-GOALPOST [SC-1] changed after it failed at <prose-edit sha>`. D8 compares the whole SUMMARY file, so an unrelated prose edit still makes a stale row count as a failure. The fix completes the user-approved fix for finding #1 ("Sửa #1–#6"). — new decision: D9
