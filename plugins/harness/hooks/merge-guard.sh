#!/usr/bin/env bash
# PreToolUse(Bash) guard: a PR merge from a Claude session is allowed without a prompt when the PR base is
# not protected (feat/*, phase3-ui and any other branch that is not listed below). Protected bases are
# main, master, develop, development, staging, production, release/*, release-* and the repo default
# branch. A merge into a protected base is allowed only as ONE plain `gh pr merge <n> --repo o/r` from the main session, and only
# after the owner answers a confirmation prompt (permissionDecision "ask"); the agent cannot answer it.
# `ask` is honored in every permission mode (probed: default, auto, bypassPermissions); with no one to
# answer (`claude -p`) Claude Code turns it into a denial. The hook itself denies in a mode it does not
# know, in dontAsk, in a subagent (payload carries agent_id) and when permission_mode is missing.
# A merge into a protected base in any other form (a subagent, a chain, --admin-less variants) is denied.
# Unlike the other hooks, this one FAILS CLOSED: once it has seen a merge command, any doubt (no gh,
# no jq, no PR number, no --repo, an unreadable base, a stalled gh) blocks the command (exit 2, reason
# on stderr). A Bash call that is not a merge exits 0 at once, before any parsing.
# Verifies: the PR base read live with `gh pr view --json baseRefName` for every PR number of every merge
#   segment (`gh pr merge`, `gh api .../pulls/<n>/merge`) is not protected (see above) and is not the repo default branch.
#   It denies `--auto`, `gh api graphql ... mergePullRequest`, a merge inside bash -c / eval / xargs or another
#   wrapper on a best-effort list (also behind an assignment, keyword, zsh prefix or redirection, or with a
#   path, backslash or = on the name; #677), a merge that is not at command position, and `gh alias
#   set|import` next to the word merge. Not on the list: interpreters (python, perl, awk), find -exec, git -c.
# Does not verify: your own `!` or terminal commands (the hook never sees them), a local `git merge`, a
#   merge through the web UI or another client, a script that builds the command at run time, or whether
#   the PR is ready (the workflow gate checks that).
# No env-var bypass. No helper file and no path derived from this file's location: the hook is
# self-contained so it can be copied alone.
set -u
payload=$(cat)
# Pre-filter on a folded copy (lowercase, quotes and backslashes removed) so "g""h", GH-case or
# me\rge spellings do not skip the guard.
fold() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -d "\"'\\\\"; }
is_merge_like() {
  case "$(fold "$1")" in
    *gh*merge*|*pulls/*merge*|*mergepullrequest*|*enablepullrequestautomerge*|*repos/*/merges*|*gh*pr*[\$\`]*|*[\$\`]*merge*) return 0 ;;
  esac
  return 1
}
is_merge_like "$payload" || exit 0

TMPF=""
trap '[ -z "$TMPF" ] || rm -f "$TMPF"' EXIT
deny() {
  printf 'merge-guard: BLOCKED. %s\nA human merges this PR: run the merge yourself in a terminal (or with the ! prefix).\n' "$1" >&2
  exit 2
}

if ! command -v jq >/dev/null 2>&1; then
  if printf '%s' "$payload" | grep -qE 'gh[[:space:]]+(pr[[:space:]]+merge|api)'; then
    deny "jq is not installed, so the merge command cannot be parsed."
  fi
  exit 0
fi
cmd=$(printf '%s' "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null) || deny "the command could not be parsed."
[ -n "$cmd" ] || deny "the command is empty or could not be parsed."
is_merge_like "$cmd" || exit 0

DEADLINE=20  # seconds for the whole hook; the registered hook timeout is 30
GH_OUT=""
# ghrun <args...>: run gh in the background, kill it after 10 s (or at the hook deadline). No `timeout`
# binary is needed, so it works on macOS. Sets GH_OUT; returns 0 only on a clean exit.
ghrun() {
  local pid limit rc
  [ "$SECONDS" -lt "$DEADLINE" ] || deny "the time budget of ${DEADLINE}s ran out while reading the PR."
  command -v gh >/dev/null 2>&1 || deny "gh is not installed, so the PR base cannot be read."
  [ -n "$TMPF" ] || TMPF=$(mktemp 2>/dev/null) || deny "no temp file for the gh answer."
  : > "$TMPF"
  gh "$@" >"$TMPF" 2>/dev/null &
  pid=$!
  limit=$((SECONDS + 10)); [ "$limit" -le "$DEADLINE" ] || limit=$DEADLINE
  while kill -0 "$pid" 2>/dev/null; do
    if [ "$SECONDS" -ge "$limit" ]; then kill "$pid" 2>/dev/null; { wait "$pid"; } 2>/dev/null; return 1; fi
    sleep 0.1
  done
  { wait "$pid"; } 2>/dev/null; rc=$?
  GH_OUT=$(head -n 1 "$TMPF" 2>/dev/null | tr -d '\r')
  return "$rc"
}

DEFAULTS=" "  # "repo=branch " cache, one default-branch read per repo
MERGES=0  # merge segments seen (gh pr merge and gh api .../merge)
ASKS=0    # merges into a non-feat base that may be put to the owner
ASK_REASON=""
NOTE=""   # flags of the one plain merge that change what it does (--admin), named in the owner prompt
default_of() {  # default_of <repo>: sets def
  case "$DEFAULTS" in
    *" $1="*) def=${DEFAULTS#*" $1="}; def=${def%% *} ;;
    *) ghrun repo view "$1" --json defaultBranchRef -q .defaultBranchRef.name || deny "the default branch of $1 could not be read."
       def=$GH_OUT; [ -n "$def" ] || deny "the default branch of $1 is empty."
       DEFAULTS="$DEFAULTS$1=$def " ;;
  esac
}
# judge <pr> <repo> [plain] [match]: "plain" marks the one form that may be put to the owner (a single
# plain `gh pr merge`); every other form into a non-feat base is denied. The owner approves one head
# commit, so the ask needs --match-head-commit <that head> (match): gh then refuses to merge a later push.
judge() {
  local pr=$1 repo=$2 plain=${3:-} match=${4:-} base head def words
  MERGES=$((MERGES + 1))
  ghrun pr view "$pr" --repo "$repo" --json baseRefName,headRefOid -q '.baseRefName + " " + .headRefOid' || deny "PR #$pr of $repo: its base could not be read."
  # shellcheck disable=SC2086
  set -- $GH_OUT
  [ "$#" -eq 2 ] || deny "PR #$pr of $repo: gh returned no usable base branch and head commit."
  base=$1; head=$2
  case "$base" in *[!A-Za-z0-9._/-]*) deny "PR #$pr of $repo: unreadable base branch name." ;; esac
  case "$head" in *[!0-9a-f]*) deny "PR #$pr of $repo: unreadable head commit." ;; esac
  [ "${#head}" -eq 40 ] || deny "PR #$pr of $repo: unreadable head commit."
  words="PR #$pr of $repo targets '$base'"
  case "$base" in
    main|master|develop|development|staging|production|release/*|release-*)
      [ -n "$plain" ] || deny "$words (only a plain single 'gh pr merge' can be put to the owner)."
      [ "$match" = "$head" ] || deny "$words: add --match-head-commit $head so the owner's approval covers exactly that commit."
      ASKS=$((ASKS + 1)); ASK_REASON="Merge PR #$pr of $repo into $base at $head$NOTE?"; return ;;
    feat/?*) ;;
    *)
      # Any other base (for example phase3-ui) is not protected: it is allowed like feat/*, unless it is
      # the repo default branch, which is protected and goes to the owner.
      default_of "$repo"
      [ "$def" = "$base" ] || return 0
      [ -n "$plain" ] || deny "$words, the default branch (only a plain single 'gh pr merge' can be put to the owner)."
      [ "$match" = "$head" ] || deny "$words: add --match-head-commit $head so the owner's approval covers exactly that commit."
      ASKS=$((ASKS + 1)); ASK_REASON="Merge PR #$pr of $repo into $base at $head$NOTE?"; return ;;
  esac
  default_of "$repo"
  [ "$def" != "$base" ] || deny "$words, the default branch of the repo."
}

judge_pr_merge() {  # judge_pr_merge <segment starting with gh pr merge>
  local seg w repo="" prs="" skip="" u n r urepos="" match=""
  NOTE=""
  local adm=0 delb=0  # last occurrence wins, as in gh; the note is built once after the loop
  seg=$(printf '%s' "$1" | sed -E 's/^gh[[:space:]]+pr[[:space:]]+merge[[:space:]]*//')
  set -f
  for w in $seg; do
    if [ "$skip" = repo ]; then repo=$w; skip=""; continue; fi
    if [ "$skip" = match ]; then match=$w; skip=""; continue; fi
    if [ -n "$skip" ]; then skip=""; continue; fi
    case "$w" in
      --repo|-R) skip=repo ;;
      --repo=*) repo=${w#--repo=} ;;
      -R?*) repo=${w#-R} ;;
      --admin=false|--admin=0|--admin=f|--admin=F|--admin=False|--admin=FALSE) adm=0 ;;
      --admin|--admin=*) adm=1 ;;
      --delete-branch=false|--delete-branch=0|--delete-branch=f|--delete-branch=F|--delete-branch=False|--delete-branch=FALSE|-d=false|-d=0) delb=0 ;;
      -b?*|-t?*|-F?*|-A?*) ;;  # attached value of a value-taking short flag, not bundled flags
      --delete-branch|--delete-branch=*|-d|-[!-]*d*) delb=1 ;;
      --auto) deny "'gh pr merge --auto' is not allowed; a human merges." ;;
      --match-head-commit) skip=match ;;
      --match-head-commit=*) match=${w#--match-head-commit=} ;;
      -b|--body|-t|--subject|-F|--body-file|-A|--author-email) skip=other ;;
      -*) ;;
      *[!0-9]*)
        case "$w" in
          http*://*/*/*/pull/[0-9]*)
            u=${w#*://}; u=${u#*/}; r=${u%%/pull/*}; n=${u##*/pull/}; n=${n%%[!0-9]*}
            urepos="$urepos $r"
            prs="$prs $n" ;;
          *) deny "'$w' is not a PR number or PR URL, so the PR cannot be judged." ;;
        esac ;;
      *) prs="$prs $w" ;;
    esac
  done
  [ "$adm" = 1 ] && NOTE="$NOTE, WITH --admin (bypasses branch protection and required checks)"
  [ "$delb" = 1 ] && NOTE="$NOTE, and deletes the head branch"
  [ -n "$prs" ] || deny "'gh pr merge' without a PR number cannot be judged."
  # gh merges the repo in the URL; the PR must be judged in that same repo, so any other repo is a deny.
  for u in $urepos; do
    if [ -z "$repo" ]; then repo=$u
    elif [ "$(printf '%s' "$u" | tr '[:upper:]' '[:lower:]')" != "$(printf '%s' "$repo" | tr '[:upper:]' '[:lower:]')" ]; then
      deny "the PR URL repo '$u' and the repo '$repo' differ, so the PR cannot be judged."
    fi
  done
  [ -n "$repo" ] || deny "'gh pr merge' without --repo cannot be judged (GH_REPO does not count)."
  case "$repo" in */*/*|*/|/*|*[!A-Za-z0-9._/-]*|"") deny "unreadable --repo value '$repo'." ;; esac
  # shellcheck disable=SC2086
  set -- $prs
  if [ "$#" -eq 1 ]; then judge "$1" "$repo" plain "$match"; else for n in "$@"; do judge "$n" "$repo"; done; fi
}

judge_api_merge() {  # judge_api_merge <segment>
  local rp
  rp=$(printf '%s' "$1" | sed -nE 's|.*repos/([A-Za-z0-9._-]+/[A-Za-z0-9._-]+)/pulls/([0-9]+)/merge.*|\1 \2|p')
  [ -n "$rp" ] || deny "'gh api ... /merge' without a literal repos/<owner>/<repo>/pulls/<n>/merge path (placeholders cannot be resolved here)."
  judge "${rp#* }" "${rp%% *}"
}

# Reduce the command to what the shell would run (same splitter as clean-worktrees.sh): drop heredoc
# bodies and quoted strings that hold whitespace or separators (each leaves one QUOTED word, so a value
# option such as --body still has its value and does not swallow the PR number), so text that only
# mentions a merge never matches; then split on separators and standalone braces.
# Redirections that hold & or | (2>&1, >&f, <&3, >|f) would be cut at that character and leave their
# target as a command word; turn them into a plain > or < first.
segs=$(printf '%s\n' "$cmd" | sed -E 's/[0-9]*([<>])&[0-9-]+/ \1 \/dev\/null /g; s/([<>])&/\1 /g; s/>\|/> /g' | awk '
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
          else if (c == q) { if (qb ~ /^[^ \t\n;|&()]*$/) out = out qb; else out = out "QUOTED"; q = "" }
          else qb = qb c }
        if (q == "") { print out; out = "" } else qb = qb "\n" }
      if (q != "") print "\001OPENQUOTE"
      if (out != "") print out
    }' | sed -E 's/&&|\|\||[;|&()]/\
/g; s/(^|[[:space:]])[{}]([[:space:]]|$)/\
/g')

# A quote still open at end of input (an apostrophe in a # comment, an escaped or stray quote) would
# swallow a later merge, so the splitter cannot be trusted: deny.
case "$segs" in *$'\001'OPENQUOTE*) deny "an unclosed quote in the command hides what follows it, so a merge cannot be judged." ;; esac

set -f
NSEGS=0
while IFS= read -r seg; do
  seg=$(printf '%s' "$seg" | sed -E 's/^[[:space:]]+//'); orig=$seg
  # #677: variable assignments, shell keywords (if then else elif do while until !), zsh prefixes (noglob,
  # nocorrect, -) and redirections (>f, 2>&1, <f, <<<w) in front of a command do not change what runs.
  # Strip them in one loop until nothing changes, so `if X=1 bash -c ...` and `>/dev/null bash -c ...`
  # reach the wrapper check below. KW records that a keyword, prefix or redirection was stripped.
  KW=0
  drop_word() { case "$seg" in *[[:space:]]*) seg=$(printf '%s' "${seg#*[[:space:]]}" | sed -E 's/^[[:space:]]+//') ;; *) seg="" ;; esac; }
  while :; do
    if printf '%s' "$seg" | grep -qE '^[A-Za-z_][A-Za-z0-9_]*(\[[^]]*\])?\+?=[^[:space:]]*([[:space:]]+|$)'; then
      seg=$(printf '%s' "$seg" | sed -E 's/^[A-Za-z_][A-Za-z0-9_]*(\[[^]]*\])?\+?=[^[:space:]]*[[:space:]]*//'); continue
    fi
    w0=${seg%%[[:space:]]*}
    case "$w0" in
      if|then|else|elif|do|while|until|'!'|noglob|nocorrect|-) KW=1; drop_word ;;
      [0-9]*'<'*|[0-9]*'>'*|'<'*|'>'*)
        KW=1; drop_word
        # an operator with its target in the next word (`> f`, `2> f`, `<<< w`): drop that word too
        case "$w0" in *'<'|*'>'|*'>&'|*'<&') drop_word ;; esac ;;  # *'<' also covers <<<
      *) break ;;
    esac
  done
  if [ -z "$seg" ]; then
    # A keyword or redirection alone still counts as a command, so a merge next to it is not "the only command".
    [ "$KW" -eq 1 ] && NSEGS=$((NSEGS + 1))
    continue
  fi
  # A shell or wrapper name with a path, a backslash anywhere, or zsh's =cmd runs the same program. A glob
  # (/bin/bas?) or a brace word ({bash,-c,...}) in the command name cannot be judged.
  w0=${seg%%[[:space:]]*}
  case "$w0" in
    '['|'[['|'{'|'}') ;;
    *'*'*|*'?'*|*'['*) deny "a command name with glob characters next to the word merge cannot be judged." ;;
    '{'*,*|'{'*..*) deny "a command name built by brace expansion next to the word merge cannot be judged." ;;
  esac
  b=${w0//\\/}; b=${b#=}; b=${b##*/}  # drop every backslash, zsh's leading =, and any path
  case "$b" in
    bash|sh|zsh|dash|ksh|rbash|eval|xargs|env|exec|nohup|time|command|sudo|doas|builtin|source|nice|timeout|stdbuf|setsid|ionice|taskset|chronic|unbuffer|repeat|coproc|busybox|flock|script|setpriv|prlimit|chrt|strace|fakeroot|runuser|su|watch|unshare)
      seg="$b${seg#"$w0"}" ;;
  esac
  NSEGS=$((NSEGS + 1))
  # A gh merge behind a keyword, prefix or redirection is not a plain merge to put to the owner.
  if [ "$KW" -eq 1 ] && printf '%s' "$seg" | grep -qE '^gh[[:space:]]'; then
    if printf '%s' "$(fold "$seg")" | grep -qE 'pr[[:space:]]+merge|/merge|graphql'; then
      deny "a gh merge behind a shell keyword, prefix or redirection cannot be put to the owner; run the merge alone."
    fi
  fi
  # A backslash inside the gh words (g\h pr merge, gh pr mer\ge) does not change what runs, but it hides
  # the words from the checks below: deny such a segment when it reads as a gh merge without the backslashes.
  case "$seg" in
    *\\*)
      if printf '%s' "$(fold "${seg//\\/}")" | grep -qE '^gh[[:space:]].*(pr[[:space:]]+merge|/merge|graphql)'; then
        deny "a gh merge spelled with a backslash cannot be judged."
      fi ;;
  esac
  if printf '%s' "$seg" | grep -qE '^gh[[:space:]]+pr[[:space:]]+merge([[:space:]]|$)'; then
    judge_pr_merge "$seg"
  elif printf '%s' "$seg" | grep -qE '^gh[[:space:]]+api[[:space:]]'; then
    if printf '%s' "$seg" | grep -qE '(^|[[:space:]])graphql([[:space:]]|$)'; then
      case "$(fold "$cmd")" in
        *mergepullrequest*|*enablepullrequestautomerge*) deny "a GraphQL mergePullRequest or enablePullRequestAutoMerge mutation is not allowed; a human merges." ;;
      esac
    fi
    if printf '%s' "$seg" | grep -qE 'repos/[^[:space:]]*/merges([^A-Za-z0-9_]|$)'; then
      deny "'gh api repos/.../merges' merges a branch and is not allowed; a human merges."
    fi
    if printf '%s' "$seg" | grep -qE 'pulls/[^[:space:]]*/merge'; then judge_api_merge "$seg"; fi
  elif case "${seg%%[[:space:]]*}" in *[\$\`]*) printf '%s' "$(fold "$cmd")" | grep -q 'merge' ;; *) false ;; esac; then
    deny "a command name built from a variable or substitution next to the word merge cannot be judged."
  elif printf '%s' "$seg" | grep -qE '^gh[[:space:]]+(pr[[:space:]]+)?[^[:space:]]*[$`]'; then
    deny "a gh pr subcommand built from a variable or substitution cannot be judged."
  elif printf '%s' "$seg" | grep -qE '^gh[[:space:]]+alias[[:space:]]+(set|import)([[:space:]]|$)'; then
    case "$cmd" in *merge*) deny "'gh alias set|import' next to the word merge could hide a merge command." ;; esac
  elif printf '%s' "$seg" | grep -qE '^gh[[:space:]].*[[:space:]]pr[[:space:]]+merge([[:space:]]|$)'; then
    deny "a gh merge command in an unusual form cannot be judged."
  elif printf '%s' "$orig" | grep -qE '(^|[^[:alnum:]_-])gh[[:space:]]+(pr[[:space:]]+merge|api[[:space:]].*(pulls/[^[:space:]]*/merge|graphql))|pulls/[^[:space:]]*/merge'; then
    deny "a gh merge command that is not at command position (wrapper, path, backtick) cannot be judged."
  else
    cw=${seg%%[[:space:]]*}
    case "$cw" in
      # No exemption for a shell that runs a script file (#671): four security reviews of such an exemption
      # each found a way to run a merge built at run time. A harmless command that trips this (a $ before a
      # file name like post-merge-hooks.test.sh) is a known false positive: put the command in a script file
      # with the Write tool and run that file by a path without the word.
      # This is a best-effort list of common shells and wrappers, not a complete one (interpreters such as
      # python or awk, find -exec and git -c alias are not on it; see the follow-up issue).
      bash|sh|zsh|dash|ksh|rbash|eval|xargs|env|exec|nohup|time|command|sudo|doas|builtin|source|.|nice|timeout|stdbuf|setsid|ionice|taskset|chronic|unbuffer|repeat|coproc|busybox|flock|script|setpriv|prlimit|chrt|strace|fakeroot|runuser|su|watch|unshare)
        deny "a merge inside a shell string or wrapper ($cw) cannot be judged." ;;
    esac
  fi
done <<SEGS
$segs
SEGS

[ "$ASKS" -gt 0 ] || exit 0
# Something targets a non-feat base. It may be put to the owner only when it is the one and only merge.
if [ "$ASKS" -ne 1 ] || [ "$MERGES" -ne 1 ]; then
  deny "a command with more than one merge cannot be put to the owner; one PR at a time."
fi
# The owner's yes approves the whole Bash command, but the prompt names only the merge: any other
# segment (&&, ;, |, a second line) would run on that yes, so the merge must be the only command.
[ "$NSEGS" -eq 1 ] || deny "a merge into a non-feat base must be the only command; other commands in the same line would run on the owner's yes. Run the merge alone."
agent=$(printf '%s' "$payload" | jq -r '.agent_id // empty' 2>/dev/null) || deny "the hook input could not be parsed."
[ -z "$agent" ] || deny "a subagent or workflow agent cannot merge into a non-feat base; the owner answers in the main session."
mode=$(printf '%s' "$payload" | jq -r '.permission_mode // empty' 2>/dev/null) || deny "the hook input could not be parsed."
case "$mode" in
  default|acceptEdits|auto|bypassPermissions) ;;
  *) deny "permission mode '${mode:-missing}' cannot show the owner a confirmation prompt." ;;
esac
jq -n --arg r "$ASK_REASON" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"ask",permissionDecisionReason:$r}}' \
  || deny "the confirmation prompt could not be built."
exit 0
