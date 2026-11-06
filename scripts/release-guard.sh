#!/usr/bin/env bash
# Refuse to start a release while another release PR or unfinished release branch exists.
#
# Two releases at once are dangerous: merging the wrong release PR tags the wrong version, and a
# tag cannot be fixed afterwards. The release workflow runs this guard before it changes anything.
#
# Checks:
#   1. `gh pr list --state open` shows a PR whose head branch starts with `release/`
#   2. origin has a branch `release/vX.Y.Z` whose tag `vX.Y.Z` does not exist on origin.
#      A release is finished when its tag exists. That does not depend on how the release PR was
#      closed (merge commit, squash or rebase), and it does not need the branch to be in main. GitHub
#      keeps the head branch after the PR is closed here (delete_branch_on_merge is false), so the
#      branch of a finished release must not block the next release. A `release/` branch that is not
#      named `release/vX.Y.Z` cannot be shown finished, so it blocks too.
#
# Exit codes: 0 = no open release PR and no unfinished release branch; 1 = at least one found (all
#             are named); 2 = the check could not run (gh failed, git ls-remote failed, bad
#             argument). The guard fails closed: a failed query is never read as "nothing is open".
#
# Usage: scripts/release-guard.sh [--root DIR]
# Env:   GH_BIN overrides the gh binary (tests stub it). GH_TOKEN and GH_REPO are read by gh itself.
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

# Full ref patterns: `ls-remote` matches the tail of a ref, so 'release/*' alone would also match
# refs/heads/docs/release/notes.
remote_branches=$(git ls-remote --heads origin 'refs/heads/release/*') || {
  echo "release-guard: 'git ls-remote origin' failed; cannot tell whether a release branch exists. Stopping." >&2
  exit 2
}
remote_tags=$(git ls-remote --tags origin 'refs/tags/v*') || {
  echo "release-guard: 'git ls-remote --tags origin' failed; cannot tell whether a release is finished. Stopping." >&2
  exit 2
}

# A branch release/vX.Y.Z is finished when refs/tags/vX.Y.Z exists on origin.
version_re='^v[0-9]+\.[0-9]+\.[0-9]+$'
branches=""
while IFS= read -r line; do
  [ -n "$line" ] || continue
  ref=${line##*[[:space:]]}                       # refs/heads/release/vX.Y.Z
  case "$ref" in refs/heads/release/*) ;; *) continue ;; esac
  name=${ref#refs/heads/}                         # release/vX.Y.Z
  tag=${name#release/}                            # vX.Y.Z
  # $tag is checked against version_re first, so it holds only digits, dots and a leading v:
  # safe to pass to awk.
  if [[ $tag =~ $version_re ]] && printf '%s\n' "$remote_tags" | awk -v t="refs/tags/$tag" '$2 == t { f = 1 } END { exit !f }'; then
    continue                                      # finished: its tag exists
  fi
  branches="${branches}${name}"$'\n'
done <<EOF
$remote_branches
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
    echo "Release branches on origin with no tag yet (an unfinished release):"
    printf '%s\n' "$branches" | sed 's/^/  /'
  fi
  echo "To recover: merge or close each PR, then delete its branch"
  echo "  (git push origin --delete release/vX.Y.Z, or \"Delete branch\" on GitHub)."
  echo "Then run the workflow again."
} >&2
exit 1
