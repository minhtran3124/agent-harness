#!/usr/bin/env bash
# Refuse to start a release while another release PR or release branch is open.
#
# Two releases at once are dangerous: merging the wrong release PR tags the wrong version, and a
# tag cannot be fixed afterwards. The release workflow runs this guard before it changes anything.
#
# Checks:
#   1. `gh pr list --state open` shows a PR whose head branch starts with `release/`
#   2. `git ls-remote --heads origin 'release/*'` shows a branch
#
# Exit codes: 0 = no release PR and no release branch; 1 = at least one found (all are named);
#             2 = the check could not run (gh failed, no origin, bad argument). The guard fails
#             closed: a failed query is never read as "nothing is open".
#
# Usage: scripts/release-guard.sh [--root DIR]
# Env:   GH_BIN overrides the gh binary (tests stub it). GH_TOKEN is read by gh itself.
set -uo pipefail

ROOT="."
while [ $# -gt 0 ]; do
  case "$1" in
    --root) [ $# -ge 2 ] || { echo "release-guard: --root needs a dir" >&2; exit 2; }; ROOT="$2"; shift 2 ;;
    *) echo "release-guard: unknown argument: $1" >&2; exit 2 ;;
  esac
done
GH="${GH_BIN:-gh}"

cd "$ROOT" || { echo "release-guard: cannot enter $ROOT" >&2; exit 2; }

# gh applies the filter itself (-q), so this script needs no jq.
prs=$("$GH" pr list --state open --json number,headRefName \
  -q '.[] | select(.headRefName | startswith("release/")) | "#\(.number) \(.headRefName)"') || {
  echo "release-guard: 'gh pr list' failed; cannot tell whether a release PR is open. Stopping." >&2
  exit 2
}

branches=$(git ls-remote --heads origin 'release/*') || {
  echo "release-guard: 'git ls-remote origin' failed; cannot tell whether a release branch exists. Stopping." >&2
  exit 2
}
# Keep only the branch names: "<sha><TAB>refs/heads/release/vX.Y.Z" -> "release/vX.Y.Z".
branches=$(printf '%s\n' "$branches" | sed -n 's|^.*[[:space:]]refs/heads/||p')

[ -z "$prs" ] && [ -z "$branches" ] && exit 0

{
  echo "release-guard: another release is in progress. Not starting a second one."
  if [ -n "$prs" ]; then
    echo "Open release PRs:"
    printf '%s\n' "$prs" | sed 's/^/  /'
  fi
  if [ -n "$branches" ]; then
    echo "Release branches on origin:"
    printf '%s\n' "$branches" | sed 's/^/  /'
  fi
  echo "To recover: merge or close each PR, then delete its branch"
  echo "  (git push origin --delete release/vX.Y.Z, or \"Delete branch\" on GitHub)."
  echo "Then run the workflow again."
} >&2
exit 1
