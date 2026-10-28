#!/usr/bin/env bash
# Remove the worktree and local branch of every branch whose PR is merged on GitHub (the PR head
# commit equals the local tip). Run by hooks after a merge command, and safe to run by hand.
# Only reports and removes: no force flags. `git worktree remove` refuses a dirty or locked worktree,
# and `git branch -d` refuses an unmerged branch (a squash-merged branch is reported, not forced).
# Never touches the default branch, the current branch, or the worktree the session runs in.
# Hook use: `clean-worktrees.sh PostToolUse` reads the tool payload on stdin and acts only after a merge.
set -u
if [ "${1:-}" = PostToolUse ]; then
  command -v jq >/dev/null || exit 0
  jq -r '.tool_input.command // empty' 2>/dev/null | grep -qE '\bgh[[:space:]]+(pr[[:space:]]+merge|api\b.*pulls/[0-9]+/merge)' || exit 0
fi
command -v gh >/dev/null || exit 0
start=$(pwd -P)
root=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || exit 0
root=${root%/.git}; cd "$root" || exit 0
keep=" main master $(git symbolic-ref -q --short HEAD) "
declare -A wt
while read -r key val; do
  case $key in worktree) path=$val ;; branch) wt[${val#refs/heads/}]=$path ;; esac
done < <(git worktree list --porcelain)
out=""
for b in $(git for-each-ref --format='%(refname:short)' refs/heads); do
  case "$keep" in *" $b "*) continue ;; esac
  tip=$(git rev-parse -q --verify "refs/heads/$b") || continue
  case " $(gh pr list --head "$b" --state merged --json headRefOid --jq '.[].headRefOid' 2>/dev/null | tr '\n' ' ') " in *" $tip "*) ;; *) continue ;; esac
  p=${wt[$b]:-}
  if [ -n "$p" ]; then
    [ "$p" = "$root" ] && continue
    case "$start/" in "$p"/*) out+="kept $b: the session runs in $p"$'\n'; continue ;; esac
    git worktree remove "$p" 2>/dev/null || { out+="kept $b: worktree $p has changes or a lock"$'\n'; continue; }
  fi
  if git branch -d "$b" >/dev/null 2>&1; then out+="removed $b${p:+ and worktree $p}"$'\n'
  else out+="kept branch $b: merged on GitHub but git does not see it as merged (squash); delete by hand if wanted"$'\n'; fi
done
git worktree prune
[ -n "$out" ] || exit 0
if [ "${1:-}" = PostToolUse ]; then
  jq -n --arg t "Worktree cleanup:"$'\n'"$out" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$t}}'
else printf '%s' "$out"; fi
