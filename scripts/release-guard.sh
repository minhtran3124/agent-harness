#!/usr/bin/env bash
# Refuse to start a release while another release PR or release branch is open.
#
# Two releases at once are dangerous: merging the wrong release PR tags the wrong version, and a
# tag cannot be fixed afterwards. The release workflow runs this guard before it changes anything.
#
# Checks:
#   1. `gh pr list --state open` shows a PR whose head branch starts with `release/`
#   2. `git ls-remote --heads origin 'release/*'` shows a branch that origin/main does not contain.
#      A release branch that main already contains is a finished release: GitHub keeps the head
#      branch after the PR is merged (this repo does not delete head branches on merge), so it must
#      not block the next release.
#
# Exit codes: 0 = no open release PR and no unfinished release branch; 1 = at least one found (all
#             are named); 2 = the check could not run (gh failed, no origin, a branch commit this
#             checkout does not have, bad argument). The guard fails closed: a failed query is never
#             read as "nothing is open".
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
# --limit: gh lists 30 PRs by default, so a release PR could hide behind 30 others.
prs=$("$GH" pr list --state open --limit 200 --json number,headRefName \
  -q '.[] | select(.headRefName | startswith("release/")) | "#\(.number) \(.headRefName)"') || {
  echo "release-guard: 'gh pr list' failed; cannot tell whether a release PR is open. Stopping." >&2
  exit 2
}

remote=$(git ls-remote --heads origin 'release/*') || {
  echo "release-guard: 'git ls-remote origin' failed; cannot tell whether a release branch exists. Stopping." >&2
  exit 2
}
# Keep the branches that origin/main does not contain. Each line is "<sha><TAB>refs/heads/<name>".
branches=""
while IFS= read -r line; do
  [ -n "$line" ] || continue
  sha=${line%%[[:space:]]*}
  name=${line##*[[:space:]]refs/heads/}
  git merge-base --is-ancestor "$sha" origin/main 2>/dev/null
  case $? in
    0) ;;                                   # already in main: a finished release
    1) branches="${branches}${name}"$'\n' ;; # not in main: unfinished or abandoned
    *) echo "release-guard: cannot tell whether origin/${name} is in origin/main (the commit or origin/main is missing in this checkout). Stopping." >&2
       exit 2 ;;
  esac
done <<EOF
$remote
EOF
branches=${branches%$'\n'}

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
