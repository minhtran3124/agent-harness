# REVIEW.md

Review-only rules for the `code-review` stages of `ship.js`. The review agent reads this file from the base branch (`git show <base>:REVIEW.md`), never from the PR's worktree, so a PR cannot edit the rules that judge it.

## What Important means here

A finding is Important when it breaks a gate, a hook, a script run on both ubuntu and macOS, or lets a check pass while the property it names is false. Style, naming and wording are not Important.

## Cap the nits

Report at most 3 Nits per review. Keep the 3 most useful and drop the rest.

## Do not report

- Wording or formatting of prose in `docs/` or `SKILL.md` files, unless it changes what an agent does.
- Anything under `specs/` (local scratch, gitignored).
- Lint-only findings that `bash scripts/check-shellcheck.sh` already covers.

## Always check

| Trigger in the diff | Check | Source |
| --- | --- | --- |
| A bash array iterated under `set -u`, or an "advisory, never blocks" block | Empty-array expansion is guarded for bash 3.2; the block is bounded with a command-level fallback, not an exception allowlist | docs/solutions/scripts/bash-empty-array-and-jsonl-parsing-gotchas.md |
| A script decides whether it may prompt the user (`[ -r /dev/tty ]`, `[ -t 0 ]`) | It opens `/dev/tty` instead of testing mode bits | docs/solutions/scripts/test-r-dev-tty-does-not-detect-missing-controlling-terminal.md |
| A spec, plan or test asserts that something does not exist or is never shipped | The claim was checked against the tree with `ls` or `git ls-files` | docs/solutions/harness/unverified-premise-propagates-through-plan-anchored-reviews.md |
| A hook or script derives the project root from its own file location | It asks the runtime (`CLAUDE_PROJECT_DIR`) and does not infer the repo from `SCRIPT_DIR` | docs/solutions/harness/hook-root-must-not-come-from-install-location.md |
| A new ratchet or checker added by the same change that fixes a defect | It matches the defect's shape, not one spelling, and was run against the pre-fix tree | docs/solutions/harness/ratchet-matches-spelling-not-property.md |
