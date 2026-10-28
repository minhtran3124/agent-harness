#!/usr/bin/env bash
# Remove the worktree and local branch of every branch whose PR is merged on GitHub (the PR head
# commit equals the local tip). Run by hooks after a merge command, and safe to run by hand.
# Only reports and removes: no force flags. `git worktree remove` refuses a dirty or locked worktree,
# and `git branch -d` refuses an unmerged branch (a squash-merged branch is reported, not forced).
# Never touches the default branch, the current branch, or the worktree the session runs in.
# Hook use: `clean-worktrees.sh PostToolUse` reads the tool payload on stdin. It acts only on a real
# `gh pr merge <n>` or `gh api .../pulls/<n>/merge` command (heredoc bodies and quoted strings are
# ignored, so text that merely mentions the phrase does nothing) and cleans only the branch of PR <n>,
# found with `gh pr view`. With no number it uses the PR of the current branch; if that lookup fails
# it exits silently. Run by hand with no argument, it sweeps every merged branch.
set -u
only=""  # set in hook mode: clean only the branch of the PR that was just merged
if [ "${1:-}" = PostToolUse ]; then
  command -v jq >/dev/null || exit 0
  cmd=$(jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
  [ -n "$cmd" ] || exit 0
  # Braces split only as standalone tokens (a brace group), so `repos/{owner}/{repo}` stays intact.
  # Reduce the command to what the shell would run: drop heredoc bodies and quoted strings, so text
  # that only mentions the merge phrase (an issue body, a commit message, an echo) never matches.
  segs=$(printf '%s\n' "$cmd" | awk '
    hd != "" { l = $0; sub(/^[ \t]+/, "", l); if (l == hd) hd = ""; next }
    { print; if (match($0, /<<-?[ \t]*["\047]?[A-Za-z_][A-Za-z0-9_]*/)) {
        d = substr($0, RSTART, RLENGTH); sub(/^<<-?[ \t]*["\047]?/, "", d); hd = d } }' |
    awk 'BEGIN { q = "" }
    { out = ""; n = length($0)
      for (i = 1; i <= n; i++) { c = substr($0, i, 1)
        if (q == "") { if (c == "\"" || c == "\047") q = c; else out = out c }
        else if (q == "\"" && c == "\\") i++
        else if (c == q) q = "" }
      print out }' | sed -E 's/&&|\|\||[;|&()]/\
/g; s/(^|[[:space:]])[{}]([[:space:]]|$)/\
/g')
  # A merge counts only at command position (after optional env assignments). Take the PR number from it.
  num=""; hit=0
  while IFS= read -r seg; do
    seg=$(printf '%s' "$seg" | sed -E 's/^[[:space:]]+//')
    while printf '%s' "$seg" | grep -qE '^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*([[:space:]]+|$)'; do
      seg=$(printf '%s' "$seg" | sed -E 's/^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]*//')
    done
    if printf '%s' "$seg" | grep -qE '^gh[[:space:]]+pr[[:space:]]+merge([[:space:]]|$)'; then
      hit=1
      for w in $seg; do case "$w" in
        [0-9]*) case "$w" in *[!0-9]*) ;; *) num=$w; break ;; esac ;;
        */pull/[0-9]*) num=${w##*/pull/}; num=${num%%[!0-9]*}; break ;;
      esac; done
      break
    elif printf '%s' "$seg" | grep -qE '^gh[[:space:]]+api[[:space:]].*pulls/[0-9]+/merge'; then
      hit=1; num=$(printf '%s' "$seg" | sed -E 's|.*pulls/([0-9]+)/merge.*|\1|'); break
    fi
  done <<EOF
$segs
EOF
  [ "$hit" = 1 ] || exit 0
  command -v gh >/dev/null || exit 0
  pr=$(gh pr view $num --json state,headRefName 2>/dev/null) || exit 0
  [ "$(printf '%s' "$pr" | jq -r '.state // empty' 2>/dev/null)" = MERGED ] || exit 0
  only=$(printf '%s' "$pr" | jq -r '.headRefName // empty' 2>/dev/null)
  [ -n "$only" ] || exit 0
fi
command -v gh >/dev/null || exit 0
start=$(pwd -P)
root=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || exit 0
root=${root%/.git}; cd "$root" || exit 0
keep=" main master $(git symbolic-ref -q --short HEAD) "
# bash 3.2 (macOS) has no associative arrays: look the worktree path up per branch.
wt_of() { git worktree list --porcelain | awk -v b="refs/heads/$1" '/^worktree /{p=substr($0,10)} $0=="branch " b{print p; exit}'; }
out=""
for b in $(git for-each-ref --format='%(refname:short)' refs/heads); do
  [ -z "$only" ] || [ "$b" = "$only" ] || continue
  case "$keep" in *" $b "*) continue ;; esac
  tip=$(git rev-parse -q --verify "refs/heads/$b") || continue
  case " $(gh pr list --head "$b" --state merged --json headRefOid --jq '.[].headRefOid' 2>/dev/null | tr '\n' ' ') " in *" $tip "*) ;; *) continue ;; esac
  p=$(wt_of "$b")
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
