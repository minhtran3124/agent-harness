#!/usr/bin/env bash
# PreToolUse(Bash) guard: a PR merge from a Claude session is allowed only when the PR base is a
# feat/* branch. Every merge into main, master, the default branch or any other branch is a human merge.
# Unlike the other hooks, this one FAILS CLOSED: once it has seen a merge command, any doubt (no gh,
# no jq, no PR number, no --repo, an unreadable base, a stalled gh) blocks the command (exit 2, reason
# on stderr). A Bash call that is not a merge exits 0 at once, before any parsing.
# Verifies: the PR base read live with `gh pr view --json baseRefName` for every PR number of every merge
#   segment (`gh pr merge`, `gh api .../pulls/<n>/merge`) is feat/* and is not the repo default branch.
#   It denies `--auto`, `gh api graphql ... mergePullRequest`, a merge inside bash -c / eval / xargs, a merge
#   that is not at command position, `gh alias set|import` next to the word merge, a substitution, backtick or
#   variable expansion next to a merge-like word, and a backslash-newline that splits a word.
# Does not verify: your own `!` or terminal commands (the hook never sees them), a local `git merge`, a
#   merge through the web UI or another client, a script that builds the command at run time, a command name
#   built in a variable or substitution that holds a gh word without a literal `pr merge` (or gh and merge)
#   in the same command, the full shell grammar, or whether the PR is ready (the workflow gate checks that).
# No env-var bypass. No helper file and no path derived from this file's location: the hook is
# self-contained so it can be copied alone.
set -u
payload=$(cat)
# Pre-filter on a folded copy (lowercase, quotes and backslashes removed) so "g""h", GH-case or
# me\rge spellings do not skip the guard.
fold() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -d "\"'\\\\"; }
# Also tests a copy with every backslash-newline joined (raw, or JSON-escaped in the payload), so a
# continuation inside a word cannot hide it.
is_merge_like() {
  local j=${1//$'\\\n'/}
  j=${j//'\\\n'/}
  case "$(fold "$1")$(printf '\n')$(fold "$j")" in
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
# A backslash-newline inside a word (g\<newline>h) is joined by the shell but not by the line splitter below.
# Deny it next to a merge-like command; a continuation between words is joined and judged as usual.
cont=${cmd//$'\\\n'/}
if [ "$cont" != "$cmd" ]; then
  re=$'[^[:space:]]\\\\\n[^[:space:]]'
  if [[ $cmd =~ $re ]] && is_merge_like "$cont"; then
    deny "a line continuation (backslash-newline) splits a word of a merge-like command, so it cannot be judged."
  fi
  cmd=$cont
fi
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
judge() {  # judge <pr> <repo>
  local pr=$1 repo=$2 base def
  ghrun pr view "$pr" --repo "$repo" --json baseRefName -q .baseRefName || deny "PR #$pr of $repo: its base could not be read."
  base=$GH_OUT
  [ -n "$base" ] || deny "PR #$pr of $repo: gh returned no base branch."
  case "$base" in *[!A-Za-z0-9._/-]*) deny "PR #$pr of $repo: unreadable base branch name." ;; esac
  case "$base" in
    main|master|develop|development|staging|production|release/*|release-*) deny "PR #$pr of $repo targets '$base' (rule: only feat/* may be merged by the workflow)." ;;
    feat/?*) ;;
    *) deny "PR #$pr of $repo targets '$base' (rule: only feat/* may be merged by the workflow)." ;;
  esac
  case "$DEFAULTS" in
    *" $repo="*) def=${DEFAULTS#*" $repo="}; def=${def%% *} ;;
    *) ghrun repo view "$repo" --json defaultBranchRef -q .defaultBranchRef.name || deny "the default branch of $repo could not be read."
       def=$GH_OUT; [ -n "$def" ] || deny "the default branch of $repo is empty."
       DEFAULTS="$DEFAULTS$repo=$def " ;;
  esac
  [ "$def" != "$base" ] || deny "PR #$pr of $repo targets '$base', the default branch of the repo."
}

judge_pr_merge() {  # judge_pr_merge <segment starting with gh pr merge>
  local seg w repo="" prs="" skip="" u n r urepos=""
  seg=$(printf '%s' "$1" | sed -E 's/^gh[[:space:]]+pr[[:space:]]+merge[[:space:]]*//')
  set -f
  for w in $seg; do
    if [ "$skip" = repo ]; then repo=$w; skip=""; continue; fi
    if [ -n "$skip" ]; then skip=""; continue; fi
    case "$w" in
      --repo|-R) skip=repo ;;
      --repo=*) repo=${w#--repo=} ;;
      -R?*) repo=${w#-R} ;;
      --auto) deny "'gh pr merge --auto' is not allowed; a human merges." ;;
      -b|--body|-t|--subject|-F|--body-file|--match-head-commit|-A|--author-email) skip=other ;;
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
  for n in $prs; do judge "$n" "$repo"; done
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
reduced=$(printf '%s\n' "$cmd" | awk '
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
    }')
segs=$(printf '%s\n' "$reduced" | sed -E 's/&&|\|\||[;|&()]/\
/g; s/(^|[[:space:]])[{}]([[:space:]]|$)/\
/g')

# A quote still open at end of input (an apostrophe in a # comment, an escaped or stray quote) would
# swallow a later merge, so the splitter cannot be trusted: deny.
case "$segs" in *$'\001'OPENQUOTE*) deny "an unclosed quote in the command hides what follows it, so a merge cannot be judged." ;; esac

# A command substitution, backtick or variable expansion can build the gh, pr or merge word at run time
# (g$(true)h, $(echo gh)). Quoted text was reduced away above, so a mention inside a message does not match.
# With a substitution and a merge-like word anywhere, the command cannot be judged: deny.
fr=$(fold "$reduced"); dollar='$'
case "$fr" in
  *"$dollar("*|*'`'*|*"$dollar"[a-z0-9_\{@*]*)
    case "$fr" in
      *pr*merge*|*gh*merge*|*pulls/*merge*|*mergepullrequest*|*enablepullrequestautomerge*|*repos/*/merges*)
        deny "a command substitution or variable expansion next to a merge command could build the gh command at run time, so it cannot be judged." ;;
    esac ;;
esac

set -f
while IFS= read -r seg; do
  seg=$(printf '%s' "$seg" | sed -E 's/^[[:space:]]+//'); orig=$seg
  while printf '%s' "$seg" | grep -qE '^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*([[:space:]]+|$)'; do
    seg=$(printf '%s' "$seg" | sed -E 's/^[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]*//')
  done
  [ -n "$seg" ] || continue
  case "$seg" in
    QUOTED*) if printf '%s' "$seg" | grep -qE '(^|[[:space:]])pr[[:space:]]+merge([[:space:]]|$)'; then deny "a quoted command name before 'pr merge' cannot be judged."; fi ;;
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
      bash|sh|zsh|dash|ksh|eval|xargs|env|exec|nohup|time|command|sudo|builtin|source|.)
        deny "a merge inside a shell string or wrapper ($cw) cannot be judged." ;;
    esac
  fi
done <<SEGS
$segs
SEGS
exit 0
