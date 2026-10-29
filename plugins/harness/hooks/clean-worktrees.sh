#!/usr/bin/env bash
# Remove the worktree and local branch of every branch that is merged. Run by hooks (after a merge
# command, and at session start) and safe to run by hand.
# A branch counts as merged when: (1) with gh, a merged PR has a head commit equal to the local tip
# (removed with `git branch -D`: a squash merge is not in git history, the exact tip match is the
# guard, so a branch with commits after the merge is never removed); (2) without gh, its upstream is
# gone and its tip is an ancestor of <remote>/main; (3) a `worktree-*` agent branch that no worktree
# has checked out and whose tip is in a <remote>/* branch (only after a successful fetch). Every rule except (1) uses `git branch -d`.
# `git worktree remove` has no force flag: it refuses a dirty or locked worktree.
# Never touches main, master, develop, development, staging, production, release/*, release-*, CLEAN_KEEP names, the current branch, or the worktree the session runs in. A SessionStart sweep also keeps any worktree that another running process has as its working directory.
# A branch matching CLEAN_STRICT gets only rule (1). Settings (env): CLEAN_REMOTE (default origin),
# CLEAN_KEEP, CLEAN_STRICT, CLEAN_RECREATE (space separated; a CLEAN_RECREATE name must be a valid plain
# branch name, and the push is never forced, so a branch another session created in the race is not overwritten). It runs `git fetch --prune` first.
# Hook use: `clean-worktrees.sh PostToolUse` reads the tool payload on stdin. It acts only on a real
# `gh pr merge <n>` or `gh api .../pulls/<n>/merge` command (heredoc bodies and quoted strings are
# ignored, so text that merely mentions the phrase does nothing) and cleans only the branches of the PRs it merges (each merge in a chain counts),
# found with `gh pr view`. With no number it uses the PR of the current branch; if that lookup fails
# it exits silently. `clean-worktrees.sh SessionStart` takes no payload and sweeps every branch,
# answering with additionalContext. Run by hand with no argument, it sweeps and prints plain text.
set -u
only=""  # set in hook mode: clean only the branch of the PR that was just merged
if [ "${1:-}" = PostToolUse ]; then
  command -v jq >/dev/null || exit 0
  cmd=$(jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
  [ -n "$cmd" ] || exit 0
  # Braces split only as standalone tokens (a brace group), so `repos/{owner}/{repo}` stays intact.
  # Reduce the command to what the shell would run: drop heredoc bodies and quoted strings that hold
  # whitespace or shell separators, so text that only mentions the merge phrase (an issue body, a
  # commit message, an echo) never matches. A quoted single token ("12", "repos/o/r/pulls/12/merge")
  # is kept unquoted. A `<<` starts a heredoc only outside quotes, not as `<<<`, and only when a
  # terminator line follows; otherwise it is plain text and swallows nothing.
  segs=$(printf '%s\n' "$cmd" | awk '
    { L[NR] = $0 }
    END {
      q = ""; qb = ""; out = ""; hd = ""
      for (r = 1; r <= NR; r++) {
        line = L[r]
        if (hd != "") { l = line; sub(/^[ \t]+/, "", l); if (l == hd) hd = ""; continue }
        n = length(line)
        for (i = 1; i <= n; i++) { c = substr(line, i, 1)
          if (q == "") {
            if (c == "\"" || c == "\047") { q = c; qb = "" }
            else {
              if (c == "<" && substr(line, i + 1, 1) == "<" && substr(line, i + 2, 1) != "<" && (i == 1 || substr(line, i - 1, 1) != "<")) {
                rest = substr(line, i); if (match(rest, /^<<-?[ \t]*["\047]?[A-Za-z_][A-Za-z0-9_]*/)) {
                  d = substr(rest, RSTART, RLENGTH); sub(/^<<-?[ \t]*["\047]?/, "", d)
                  for (k = r + 1; k <= NR; k++) { t = L[k]; sub(/^[ \t]+/, "", t); if (t == d) { hd = d; break } } } }
              out = out c }
          } else if (q == "\"" && c == "\\") { qb = qb c substr(line, i + 1, 1); i++ }
          else if (c == q) { if (qb ~ /^[^ \t\n;|&()]*$/) out = out qb; q = "" }
          else qb = qb c }
        if (q == "") { print out; out = "" } else qb = qb "\n" }
      if (out != "") print out
    }' | sed -E 's/&&|\|\||[;|&()]/\
/g; s/(^|[[:space:]])[{}]([[:space:]]|$)/\
/g')
  # A merge counts only at command position (after optional env assignments). Take the PR number from it.
  nums=""; hit=0
  while IFS= read -r seg; do
    seg=$(printf '%s' "$seg" | sed -E 's/^[[:space:]]+//')
    while printf '%s' "$seg" | grep -qE '^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*([[:space:]]+|$)'; do
      seg=$(printf '%s' "$seg" | sed -E 's/^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]*//')
    done
    if printf '%s' "$seg" | grep -qE '^gh[[:space:]]+pr[[:space:]]+merge([[:space:]]|$)'; then
      hit=1; num=""
      for w in $seg; do case "$w" in
        [0-9]*) case "$w" in *[!0-9]*) ;; *) num=$w; break ;; esac ;;
        */pull/[0-9]*) num=${w##*/pull/}; num=${num%%[!0-9]*}; break ;;
      esac; done
      nums="$nums ${num:--}"
    elif printf '%s' "$seg" | grep -qE '^gh[[:space:]]+api[[:space:]].*pulls/[0-9]+/merge'; then
      hit=1; nums="$nums $(printf '%s' "$seg" | sed -E 's|.*pulls/([0-9]+)/merge.*|\1|')"
    fi
  done <<EOF
$segs
EOF
  [ "$hit" = 1 ] || exit 0
  command -v gh >/dev/null || exit 0
  # Every merge segment counts (`gh pr merge 7 && gh pr merge 8`). "-" means no number: current branch.
  only=" "
  for num in $nums; do
    [ "$num" = - ] && num=""
    pr=$(gh pr view ${num:+"$num"} --json state,headRefName 2>/dev/null) || continue
    [ "$(printf '%s' "$pr" | jq -r '.state // empty' 2>/dev/null)" = MERGED ] || continue
    hb=$(printf '%s' "$pr" | jq -r '.headRefName // empty' 2>/dev/null)
    [ -n "$hb" ] && only="$only$hb "
  done
  [ "$only" != " " ] || exit 0
fi
set -f  # CLEAN_STRICT globs are matched with case, never expanded against files
have_gh=1; command -v gh >/dev/null || have_gh=""
start=$(pwd -P)
session_branch=$(git symbolic-ref -q --short HEAD 2>/dev/null)
root=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || exit 0
root=${root%/.git}; cd "$root" || exit 0
remote=${CLEAN_REMOTE:-origin}
# Fetch first so a branch the remote already deleted is seen. A failed fetch (no network) is not fatal.
# Rule (3) trusts remote-tracking refs, so it runs only when the fetch succeeded (refs may be stale).
fetched=""; git fetch -q --prune "$remote" 2>/dev/null && fetched=1
keep=" main master ${CLEAN_KEEP:-} $(git symbolic-ref -q --short HEAD) $session_branch "
# bash 3.2 (macOS) has no associative arrays: look the worktree path up per branch.
wt_of() { git worktree list --porcelain | awk -v b="refs/heads/$1" '/^worktree /{p=substr($0,10)} $0=="branch " b{print p; exit}'; }
out=""
base="refs/remotes/$remote/main"
git rev-parse -q --verify "$base" >/dev/null 2>&1 || base=""
# Recreate a deleted base branch from <remote>/main, only when ls-remote says it is missing (exit 2).
if [ -n "$base" ]; then
  for name in ${CLEAN_RECREATE:-}; do
    # Guard the name: a valid short branch name only (no leading dash, no glob), never a long-lived branch.
    case "$name" in -*|*[*?[]*|develop|development|staging|production|release/*|release-*) continue ;; esac
    git check-ref-format --branch "$name" >/dev/null 2>&1 || continue
    git ls-remote --exit-code --heads "$remote" "$name" >/dev/null 2>&1; rc=$?
    [ "$rc" = 2 ] || continue
    if git push -q "$remote" "$base:refs/heads/$name" 2>/dev/null; then out+="recreated $remote/$name from $remote/main"$'\n'
    else out+="could not recreate $remote/$name"$'\n'; fi
  done
fi
# SessionStart only: the working directories of every running process, one per line, so a worktree that
# another live session (or shell) is using is kept. /proc on Linux, lsof elsewhere; with neither, nothing is known.
live_cwds=""
if [ "${1:-}" = SessionStart ]; then
  if [ -d /proc/self ]; then
    set +f; live_cwds=$(for l in /proc/[0-9]*/cwd; do readlink "$l" 2>/dev/null; done); set -f
  elif command -v lsof >/dev/null; then
    live_cwds=$(lsof -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
  fi
fi
in_use() { [ -n "$live_cwds" ] && printf '%s\n' "$live_cwds" | awk -v p="$1" '$0==p || index($0, p "/")==1 {f=1; exit} END{exit !f}'; }
is_strict() { local g; for g in ${CLEAN_STRICT:-}; do case "$1" in $g) return 0 ;; esac; done; return 1; }
# True when the tip is in a <remote>/* branch other than <remote>/HEAD.
in_remote_branch() { git for-each-ref --contains "$1" --format='%(refname)' "refs/remotes/$remote/" 2>/dev/null | grep -qvx "refs/remotes/$remote/HEAD"; }
# Delete a branch whose tip is already verified to be contained in a remote branch: `git branch -d`,
# and if git refuses only because the local HEAD lacks the commit, drop the ref guarded by its tip.
del_contained() { git branch -d "$1" >/dev/null 2>&1 || git update-ref -d "refs/heads/$1" "$2" >/dev/null 2>&1; }
for b in $(git for-each-ref --format='%(refname:short)' refs/heads); do
  [ -z "$only" ] || case "$only" in *" $b "*) ;; *) continue ;; esac
  case "$keep" in *" $b "*) continue ;; esac
  case "$b" in develop|development|staging|production|release/*|release-*) continue ;; esac  # long-lived branches
  tip=$(git rev-parse -q --verify "refs/heads/$b") || continue
  strict=""; is_strict "$b" && strict=1
  p=$(wt_of "$b")
  how=""
  if [ -n "$fetched" ] && [ -z "$strict" ] && [ -z "$p" ] && [ -z "$only" ] && case "$b" in worktree-*) true ;; *) false ;; esac && in_remote_branch "$tip"; then
    how=contained
  elif [ -n "$have_gh" ]; then
    case " $(gh pr list --head "$b" --state merged --json headRefOid --jq '.[].headRefOid' 2>/dev/null | tr '\n' ' ') " in *" $tip "*) how=pr ;; esac
  elif [ -z "$strict" ] && [ -n "$base" ] \
    && [ "$(git for-each-ref --format='%(upstream:track)' "refs/heads/$b")" = "[gone]" ] \
    && git merge-base --is-ancestor "$tip" "$base" 2>/dev/null; then
    how=gone
  fi
  [ -n "$how" ] || continue
  if [ -n "$p" ]; then
    [ "$p" = "$root" ] && continue
    case "$start/" in "$p"/*) out+="kept $b: the session runs in $p"$'\n'; continue ;; esac
    if in_use "$p"; then out+="kept $b: a running process uses $p"$'\n'; continue; fi
    git worktree remove "$p" 2>/dev/null || { out+="kept $b: worktree $p has changes or a lock"$'\n'; continue; }
  fi
  if { [ "$how" = pr ] && git branch -D "$b" >/dev/null 2>&1; } || { [ "$how" != pr ] && del_contained "$b" "$tip"; }; then
    out+="removed $b${p:+ and worktree $p}"$'\n'
  else out+="kept branch $b: merged but could not be deleted; delete by hand if wanted"$'\n'; fi
done
git worktree prune
[ -n "$out" ] || exit 0
case "${1:-}" in
  PostToolUse) jq -n --arg t "Worktree cleanup:"$'\n'"$out" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$t}}' ;;
  SessionStart) jq -n --arg t "Worktree cleanup:"$'\n'"$out" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$t}}' ;;
  *) printf '%s' "$out" ;;
esac
