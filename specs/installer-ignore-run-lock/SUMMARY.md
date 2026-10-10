# installer-ignore-run-lock — Summary

Lane: normal
Confidence: high
Reason: no manifest hard gate (scripts/install-harness.sh is not high-blast); flags existing behavior (consumer .gitignore gains a line) and cross-platform (bash/grep on macOS and Linux)
Flags: existing behavior, cross-platform
Affects: scripts/install-harness.sh (consumer .gitignore append)
Input-type: harness improvement
Route: using-git-worktrees → direct patch with test-first regression + one independent review (two files, no PLAN per artifact policy)
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

ok, update installer đi, ignore file này luôn

(Context, preceding turn: "theo bạn có nên commit file này events.jsonl.lock luôn ko ?" — the file is `specs/<slug>/events.jsonl.lock`, untracked in a consumer repo after a real install.)

## What changed

`scripts/install-harness.sh` now also appends `specs/**/events.jsonl.lock` to the consumer's
`.gitignore` (append-only, after the existing `.claude/` block, independent of it). It asks git
which rule decides a probe path (`check-ignore --no-index -v -n`) and skips, with an `info` line,
only when that rule lives in a `.gitignore` — a positive rule (e.g. `*.lock`) or a deliberate
negation. A narrow single-spec rule, an unrelated negation, a comment, or a rule only in
`.git/info/exclude` does not suppress the append. Ten regression cases added to
`tests/scripts/install-gitignore.test.sh`.

### Rationale

The lock is a machine-local fcntl file (`runtime/run_state.py:77`); this repo already ignores it
(`.gitignore:42-43`), but consumers showed it as untracked (found in the PR #284 real-install
trial). Asking git instead of grepping text is what removes the false-skip class the review found
twice.

### Alternatives considered

- Text probe on `.gitignore` (first two versions) — rejected after review: a narrow rule, an
  unrelated negation, or `info/exclude` caused false skips.
- Commit the lock file — rejected: it carries no data and an fcntl lock is per machine.

### Deviations

- none

### Review

One independent reviewer, three rounds: round 1 found a narrow-rule false skip and a silent skip;
round 2 found an any-path negation false skip and an `info/exclude` false skip; round 3 clean. All
fixed with a regression case each.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| installer gitignore regressions | `bash tests/scripts/install-gitignore.test.sh` | 0 | 25 passed (10 new) | |
| script syntax | `bash -n scripts/install-harness.sh` | 0 | | |

### Not auto-verified

- Full suite `bash scripts/run-tests.sh` ended ALL GREEN on the final code — re-run, cited in
  prose because whole-suite rows are not allowed in `### Verify`.
- macOS bash 3.2 / BSD tools — not run here (Linux); reviewer read the code for portability —
  traceability. CI runs the suite on macOS.

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
