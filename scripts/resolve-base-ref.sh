#!/bin/bash
# Resolve the base ref a changed-files check should diff against.
#
# Verifies:        that a named base ref exists and resolves in this repo.
# Does not verify: that it is the *right* base for the work in flight — this reports
#                  the base the environment declares, it does not infer one.
#
# Exit 0 → the resolved ref is printed on stdout.
# Exit 1 → nothing on stdout; a human-readable reason on stderr.
#
# Why this is its own file rather than inline in run-tests.sh: the bug it fixes was a
# dead scope selector, not dead logic. `run-tests.sh` hardcoded `origin/main`, which
# resolved neither locally (this repo's only remote is `github`) nor in CI (the `test`
# job checked out shallow), so the verify-row lint skipped 100% of the time from the
# day it shipped and still reported green. Inline logic inside a 100-line suite runner
# cannot be unit-tested, so nothing would stop that regressing the same silent way.
#
# Resolution order — declared bases only, never a branch-name guess:
#   1. $VERIFY_ROWS_BASE  — explicit override (CI debugging, local runs, consumers)
#   2. $GITHUB_BASE_REF   — the PR's real target branch, set by GitHub Actions
#   3. @{upstream}        — the branch's own tracking ref
#
# Guessing is deliberately absent. Falling back to `main` when a PR targets a different
# integration branch widens the diff to everything merged into that branch since main —
# measured in this repo: 36 spec files instead of the branch's own, un-grandfathering 7
# pre-existing violations in already-shipped specs. A wrong-and-wide base turns the
# suite red for work the branch never touched, which is worse than skipping.

set -uo pipefail

ref=""
why=""

if [ -n "${VERIFY_ROWS_BASE:-}" ]; then
  ref="$VERIFY_ROWS_BASE"; why="VERIFY_ROWS_BASE"
elif [ -n "${GITHUB_BASE_REF:-}" ]; then
  ref="origin/$GITHUB_BASE_REF"; why="GITHUB_BASE_REF (CI pull request)"
elif upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null)"; then
  # An upstream is only a BASE when it tracks a different branch. The dominant flow here
  # is `git push -u <remote> <branch>`, which sets upstream to the branch's OWN remote
  # copy — diffing against that yields only unpushed edits, i.e. nothing once pushed, and
  # the caller then prints "compared and found nothing". That is the same skip-looks-like-
  # pass ambiguity this whole script exists to remove, so refuse it rather than resolve it.
  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  if [ -n "$branch" ] && [ "${upstream##*/}" = "$branch" ]; then
    echo "upstream '$upstream' tracks this same branch, so it is not a base — set VERIFY_ROWS_BASE to the integration branch instead" >&2
    exit 1
  fi
  ref="$upstream"; why="branch upstream"
else
  echo "no base ref declared — set VERIFY_ROWS_BASE, or give the branch an upstream (git branch -u <remote>/<base>)" >&2
  exit 1
fi

# `^{commit}` is load-bearing: plain `--verify` accepts ANY object, so a blob or tree sha
# passes here and then makes `git diff <blob> -- <pathspec>` die with a fatal the caller
# swallows — surfacing as "compared and found nothing" instead of "bad base".
if ! git rev-parse --verify -q "${ref}^{commit}" >/dev/null 2>&1; then
  echo "base ref '$ref' (from $why) does not resolve to a commit" >&2
  exit 1
fi

echo "$ref"
