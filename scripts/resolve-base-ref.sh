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
# Resolution order — declared, then DERIVED, never guessed by name:
#   1. $VERIFY_ROWS_BASE  — explicit override (CI debugging, local runs, consumers)
#   2. $GITHUB_BASE_REF   — the PR's real target branch, set by GitHub Actions
#   3. @{upstream}        — but only when it tracks a *different* branch (see below)
#   4. nearest ancestor   — derived from history, below
#
# On guessing vs deriving. An earlier draft tried a name chain (`origin/main` →
# `github/main` → `main`). On a branch cut from `simplify` that picks `main`, which is not
# even an ancestor of HEAD — it holds 5 commits HEAD does not, and its merge-base is 268
# commits back. The resulting diff was 36 spec files instead of this branch's 1,
# un-grandfathering 7 violations in already-shipped specs. Ordering candidates by NAME
# preference is the bug; the branch's real base is a fact about history, not a preference.
#
# Tier 4 derives it: among all local and remote-tracking refs, keep those that are
# ancestors of HEAD (a base must be one — this alone disqualifies `main` here), then take
# the one fewest commits behind HEAD. Excluded: this branch and its own remote copies,
# which after a push are ancestors at distance 0 and would win with an empty diff — the
# same self-comparison that makes tier 3 refuse a self-tracking upstream.
#
# Ties (e.g. `simplify` and `github/simplify` at the same commit) resolve lexicographically,
# which prefers the remote-tracking name — the shared truth when a local branch is stale.
# If nothing qualifies, refuse loudly; a wrong-and-wide base is worse than skipping.

derive_base() {
  local branch excl rem best
  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" || return 1
  [ -n "$branch" ] && [ "$branch" != "HEAD" ] || return 1   # detached HEAD has no base to derive
  excl="^${branch}$"
  for rem in $(git remote 2>/dev/null); do excl="${excl}|^${rem}/${branch}$"; done
  best="$(
    git for-each-ref --format='%(refname:short)' refs/heads refs/remotes 2>/dev/null \
      | grep -Ev "$excl" \
      | while read -r r; do
          git merge-base --is-ancestor "$r" HEAD 2>/dev/null || continue
          printf '%06d %s\n' "$(git rev-list --count "$r"..HEAD 2>/dev/null)" "$r"
        done \
      | sort -k1,1n -k2,2 | head -1
  )"
  [ -n "$best" ] || return 1
  printf '%s' "${best#* }"
}

set -uo pipefail

ref=""
why=""

if [ -n "${VERIFY_ROWS_BASE:-}" ]; then
  ref="$VERIFY_ROWS_BASE"; why="VERIFY_ROWS_BASE"
elif [ -n "${GITHUB_BASE_REF:-}" ]; then
  ref="origin/$GITHUB_BASE_REF"; why="GITHUB_BASE_REF (CI pull request)"
fi

# Tier 3 — @{upstream}, but only when it tracks a DIFFERENT branch. The dominant flow is
# `git push -u <remote> <branch>`, which points upstream at the branch's OWN remote copy;
# diffing against that yields only unpushed edits — nothing once pushed — and the caller
# then reports "compared and found nothing". A self-tracking upstream is not a base, so it
# is SKIPPED (falling through to derivation), not treated as an error: the branch still has
# a real base, this ref just is not it.
if [ -z "$ref" ] && upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null)"; then
  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  self=0
  if [ -n "$branch" ]; then
    # Compare against `<remote>/<branch>` per remote, NOT `${upstream##*/}` — branch names
    # contain slashes (`fix/depth-policy-and-base-ref`), so suffix-stripping compares the
    # last path segment and silently fails to recognise the self-tracking case.
    [ "$upstream" = "$branch" ] && self=1
    for _rem in $(git remote 2>/dev/null); do
      [ "$upstream" = "$_rem/$branch" ] && self=1
    done
  fi
  [ "$self" -eq 1 ] || { ref="$upstream"; why="branch upstream"; }
fi

# Tier 4 — derive from history when nothing was declared.
if [ -z "$ref" ] && derived="$(derive_base)"; then
  ref="$derived"; why="nearest ancestor ref"
fi

if [ -z "$ref" ]; then
  echo "no base ref could be declared or derived — set VERIFY_ROWS_BASE explicitly" >&2
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
