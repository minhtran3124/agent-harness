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
#   It denies `--auto`, the GraphQL merge mutations, a merge inside bash -c / eval / xargs or another wrapper
#   on a list (also behind an assignment, keyword, zsh prefix or redirection, or with a path, backslash or =
#   on the name; #677), a merge that is not at command position, and `gh alias set|import` next to the word
#   merge. #680: merge-like text (quoted or not, in a heredoc, a here-string or a backslash-continued line) is
#   allowed only in commands on an allow list of commands that never run their arguments (echo, printf,
#   grep, rg, jq, git commit/log/..., gh pr create|comment|edit, gh issue ...; see inert()). Any other command
#   with such text is denied (python3 -c, perl -e, awk, sed with a script, find -exec, git -c alias, ...), and
#   so is every command that is not on the list in the same Bash call as such text, a write of such text to a
#   git hook or config file, and an expansion that evaluates a value ($(( )), ${s:x}, ${!x}, zsh ${(e)x}).
# Does not verify: your own `!` or terminal commands (the hook never sees them), a local `git merge`, a
#   merge through the web UI or another client, a merge built at run time with no merge-like text (#675:
#   `gh pr m{e..e}rge`, $'...', base64, string slicing in an interpreter), a file written in one Bash call
#   or with the Write tool and run later, or whether the PR is ready (the workflow gate checks that).
# No env-var bypass. No helper file and no path derived from this file's location: the hook is
# self-contained so it can be copied alone.
set -u
payload=$(cat)
# Pre-filter on a folded copy (lowercase; newlines, quotes and backslashes removed, and a backslash-newline
# in its JSON form removed first) so "g""h", GH-case, me\rge or a word continued on the next line do not
# skip the guard.
fold() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -d '\n' | sed 's/\\\\\\n//g' | tr -d "\"'\\\\"; }
is_merge_like() {
  local f; f=$(fold "$1")
  # "pr merge" with gh after it or in a variable (echo 'pr merge 7' | xargs gh; set -- pr merge 7; gh "$@")
  if printf '%s' "$f" | grep -qE '(^|[^a-z0-9])pr[^a-z0-9]+merge'; then return 0; fi
  case "$f" in
    *gh*merge*|*pulls/*merge*|*mergepullrequest*|*enablepullrequestautomerge*|*enqueuepullrequest*|*repos/*/merges*|*gh*pr*[\$\`]*|*[\$\`]*merge*) return 0 ;;
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

# Reduce the command to what the shell would run. One awk pass walks the text the way the shell reads it
# and prints one line per command segment: "<flags><TAB><segment>". (clean-worktrees.sh has an older,
# simpler splitter; this one is no longer a copy of it.)
# - Segments end at ; | & ( ) a newline and a standalone { or }. A backslash escapes the next character.
# - A backslash-newline joins two lines in code, in double quotes and in an unquoted heredoc (not in single
#   quotes, not after an escaped backslash). A join in the middle of a word leaves one backslash in the
#   segment, so a gh word split that way reads as "spelled with a backslash".
# - A quoted string that holds whitespace or a separator becomes the word QUOTED (a value option such as
#   --body keeps its value); any other quoted string is put in as its text. A heredoc body is dropped.
# - $( ... ) inside double quotes is code: its commands become segments of their own. A backtick span is
#   never parsed: it becomes the segment `BT with the span as its text.
# - Flags: q = the quoted text, heredoc body or here-string of the segment holds merge-like text;
#   w = the whole text of the segment does (quoted or not); g = as w, but without the first gh word;
#   a = a quoted string that became QUOTED holds a pulls/<n>/merge or /merges path;
#   o = the text holds the start of an option that makes an otherwise harmless command run a program
#       (rg --pre, sort --compress-program, git push --exec / --receive-pack, and their short forms).
# - A line "\001<REASON>" means the text cannot be parsed safely: deny.
# Redirections that hold & or | (2>&1, >&f, <&3, >|f) would be cut at that character and leave their
# target as a command word; turn them into a plain > or < first.
segs=$(printf '%s\n' "$cmd" | sed -E 's/[0-9]*([<>])&[0-9-]+/ \1 \/dev\/null /g; s/([<>])&/\1 /g; s/>\|/> /g' | awk '
    # fold: lowercase, quotes and backslashes removed. Words that only start with "merge" (mergeable, mergedAt,
    # mergeStateStatus, mergeCommit, merge-base, merge_method, merge-guard) are not a merge and become "mrg".
    function fold(s) { s = tolower(s); gsub(/["\047\\]/, "", s); gsub(/[\n\t]/, " ", s)
      gsub(/merge(able|d|state|commit|base|_base|-base|-guard|_state|_commit|_method)/, "mrg", s); return s }
    function loose(s) { return fold(s) ~ /gh.*merge|(^|[^a-z0-9])pr[^a-z0-9]+merge|pulls\/.*merge|mergepullrequest|enablepullrequestautomerge|mergebranch|enqueuepullrequest|repos\/.*\/merges/ }
    function wordy(s) { return s ~ /(^|[^a-z0-9_-])gh([^a-z0-9_.-]|$).*merge|(^|[^a-z0-9])pr[^a-z0-9]+merge|pulls\/.*merge|mergepullrequest|enablepullrequestautomerge|mergebranch|enqueuepullrequest|repos\/.*\/merges/ }
    function tc() { return (KIND[sp] == "C") ? sp : sp - 1 }
    function seg(f) { if (!CUR[f]) { n++; CUR[f] = n; OUT[n] = ""; RAW[n] = ""; EX[n] = ""; QD[n] = ""; QH[n] = "" } return CUR[f] }
    function out(s,   i) { i = seg(tc()); OUT[i] = OUT[i] s }
    # RAW: all text of the segment; EX: the part the shell expands (not single quotes, $\047 \047, quoted heredocs)
    function raw(s,   f) { for (f = 0; f <= sp; f++) if (KIND[f] == "C" && CUR[f]) { RAW[CUR[f]] = RAW[CUR[f]] s; if (!NOEX) EX[CUR[f]] = EX[CUR[f]] s } }
    function qd(s,   i) { i = seg(tc()); QD[i] = QD[i] s " " }
    function bad(why) { if (BAD == "") BAD = why }
    function flush(f) {
      if (CUR[f] && f > 0 && OUT[CUR[f]] ~ /^[ \t]*(case|esac)([ \t]|$)/) bad("NESTEDCASE")
      CUR[f] = 0 }
    function quoted(body,   i) {  # a closed quoted string: record it and put it into the segment
      qd(body); raw(body)
      if (body ~ /^[^ \t\n;|&()]*$/) out(body); else { out("QUOTED"); i = seg(tc()); QH[i] = QH[i] body " " } }
    # plainexp <text>: 1 when every expansion in the text is $NAME, ${NAME}, a special or positional parameter,
    # $( or a $-quote (dollar-single or dollar-double). Any other form ($(( )), $[ ], ${s:x}, ${a[x]}, ${!x}, zsh ${(e)x} or $~x)
    # can evaluate a value as code or arithmetic, and an array subscript in that value runs $( ).
    function plainexp(t) {
      gsub(/\\./, "", t)
      gsub(/\$\{([A-Za-z_][A-Za-z0-9_]*|[0-9#?@*$!-])\}/, "", t)
      gsub(/\$\(\(/, "$[", t)
      gsub(/\$([A-Za-z_(\047"#?@*$!0-9-]|$)/, "", t)
      return t !~ /\$/ }
    function pseudo(name, body) { n++; OUT[n] = name; RAW[n] = body; EX[n] = body; QD[n] = body; QH[n] = "" }
    function endbody(   f, o) {  # the body HB of heredoc hcur is complete
      o = HO[hcur]; RAW[o] = RAW[o] " " HB; QD[o] = QD[o] HB " "; if (!HQ[hcur]) EX[o] = EX[o] " " HB
      for (f = 0; f <= sp; f++) if (KIND[f] == "C" && CUR[f] && CUR[f] != o) { RAW[CUR[f]] = RAW[CUR[f]] " " HB; if (!HQ[hcur]) EX[CUR[f]] = EX[CUR[f]] " " HB }
      if (!HQ[hcur] && HB ~ /\$\(|`|\$\[|\$\{/ && !spans(HB)) pseudo("HEREDOC-SUBST", HB)
      hcur++; HB = ""; HJ = "" }
    # spans <body>: an unquoted heredoc body is data except its substitutions. Each simple $( ... ) is put
    # after the input as a command line of its own, so it is split and judged like any other command. A body
    # with a backtick, $(( )), $[ ], ${ } with a subscript or an offset, or a $( ) that holds a quote, a
    # comment, a case, a heredoc or unbalanced parentheses is not read: return 0 (one opaque command).
    function spans(b,   i, m, c, d, st, k, a, parts, ln) {
      if (b ~ /`/ || !plainexp(b)) return 0
      m = length(b); k = 0
      for (i = 1; i <= m; i++) {
        c = substr(b, i, 1)
        if (c == "\\") { i++; continue }
        if (c != "$" || substr(b, i + 1, 1) != "(") continue
        d = 1; st = i + 2
        for (i = st; i <= m && d > 0; i++) {
          c = substr(b, i, 1)
          if (c ~ /["\047`#\\<]/) return 0
          if (c == "(") d++; else if (c == ")") d-- }
        if (d > 0) return 0
        a = substr(b, st, i - 1 - st); i--
        if (a ~ /(^|[^A-Za-z0-9_])case([^A-Za-z0-9_]|$)|\$[^A-Za-z_]|\$$/) return 0
        k++; parts[k] = a }
      for (i = 1; i <= k; i++) { m = split(parts[i], ln, "\n"); for (c = 1; c <= m; c++) L[++NL] = ln[c] }
      return 1 }
    { L[NR] = $0 }
    END {
      sp = 0; KIND[0] = "C"; CUR[0] = 0; PC[0] = 0; n = 0; sq = 0; bt = 0; nh = 0; hcur = 1; HB = ""; HJ = ""; cont = 0; BAD = ""
      NL = NR
      for (r = 1; r <= NL; r++) {
        line = L[r]
        # lines after NR are substitutions taken from heredoc bodies; the input must be fully read by then
        if (r == NR + 1 && (sq || bt || sp > 0 || hcur <= nh || cont)) bad("OPENQUOTE")
        if (hcur <= nh && !cont) {  # a heredoc body line; the end line is matched exactly as the shell does
          l = line
          if (!HQ[hcur]) {  # an unquoted heredoc joins backslash-newline first; only the joined line can be the end word
            j = HJ line
            if (j ~ /(^|[^\\])(\\\\)*\\$/) { if (HD[hcur]) bad("HEREDOCWORD"); HJ = substr(j, 1, length(j) - 1); HB = HB line "\n"; continue }
            HJ = ""; l = j }
          if (HD[hcur]) sub(/^\t+/, "", l)
          if (l == HW[hcur]) { endbody(); continue }
          # bash ends a heredoc inside $( ) at "EOF)" too; this reader does not, so it cannot judge the rest
          if (index(l, HW[hcur]) == 1 && substr(l, length(HW[hcur]) + 1) ~ /^[ \t]*\)/) bad("HEREDOCWORD")
          HB = HB line "\n"; continue }
        cont = 0; incomment = 0; qic = 0
        len = length(line)
        for (i = 1; i <= len; i++) { c = substr(line, i, 1); nx = substr(line, i + 1, 1)
          if (sq) {
            if (sq == 2 && c == "\\") { sqb = sqb c nx; i++ }
            else if (c == "\047") { sq = 0; NOEX = 1; quoted(sqb); NOEX = 0 }
            else sqb = sqb c
          } else if (bt) {
            if (c == "\\") { btb = btb c nx; i++ }
            else if (c == "`") { bt = 0; raw("`" btb "`"); pseudo("`BT", btb)
              if (KIND[sp] == "C") out("`BT`"); else { QB[sp] = QB[sp] "`BT`"; SUB[sp] = 1 } }
            else btb = btb c
          } else if (KIND[sp] == "D") {
            if (c == "\\") { if (i == len) cont = 1; else { QB[sp] = QB[sp] c nx; i++ } }
            else if (c == "\"") {
              body = QB[sp]; sub_ = SUB[sp]; sp--
              if (sub_) { qd(body); raw(body); out("QUOTED"); if (loose(body)) bad("SUBSTTEXT") }
              else quoted(body) }
            else if (c == "$" && nx == "(") { SUB[sp] = 1; raw("$("); sp++; KIND[sp] = "C"; CUR[sp] = 0; PC[sp] = 0; i++ }
            else if (c == "`") { bt = 1; btb = ""; if (incomment) qic = 1 }
            else QB[sp] = QB[sp] c
          } else {  # code
            prev = (i == 1) ? " " : substr(line, i - 1, 1)
            if (c == "\\") {
              if (i == len) { cont = 1
                if (prev !~ /[ \t;|&()]/ && r < NL && L[r + 1] !~ /^([ \t]|$)/) out("\\") }
              else { out(c nx); raw(c nx); i++ }
            } else if (c == "\047") { seg(sp); sq = (prev == "$") ? 2 : 1; sqb = ""; if (incomment) qic = 1 }
            else if (c == "\"") { seg(sp); sp++; KIND[sp] = "D"; QB[sp] = ""; SUB[sp] = 0; if (incomment) qic = 1 }
            else if (c == "`") { seg(sp); bt = 1; btb = ""; if (incomment) qic = 1 }
            else if (c == ";" || c == "|" || c == "&") { flush(sp); raw(c) }
            else if (c == "(") { if (sp > 0) PC[sp]++; flush(sp); raw(c) }
            else if (c == ")") {
              if (sp > 0 && PC[sp] == 0) { flush(sp); sp--; raw(")") }
              else { if (sp > 0) PC[sp]--; flush(sp); raw(c) } }
            else if ((c == "{" || c == "}") && prev ~ /[ \t;|&()]/ && (nx == "" || nx ~ /[ \t;|&()]/)) { flush(sp); raw(c) }
            else if (c == " " || c == "\t") { if (CUR[sp]) { out(c); raw(c) } }
            else {
              if (c == "#" && prev ~ /[ \t;|&()]/) { if (sp > 0) bad("NESTEDCOMMENT"); incomment = 1 }
              if (c == "$" && nx == "{" && sp > 0) {  # ${ ... } inside a nested substitution: keep it only when it is simple
                rest = substr(line, i); k = index(rest, "}")
                if (k == 0 || substr(rest, 1, k) ~ /[()"\047`\\]/) bad("NESTEDBRACE")
                else { out(substr(rest, 1, k)); raw(substr(rest, 1, k)); i += k - 1; continue } }
              if (c == "<" && nx == "<" && substr(line, i + 2, 1) != "<" && prev != "<") {
                # A heredoc. Only the plain end words NAME, \047NAME\047 and "NAME" are read; any other form is not judged.
                rest = substr(line, i + 2); dash = 0
                if (substr(rest, 1, 1) == "-") { dash = 1; rest = substr(rest, 2) }
                sub(/^[ \t]+/, "", rest); w = rest; if (match(w, /[ \t;|&()<>]/)) w = substr(w, 1, RSTART - 1)
                hq_ = -1
                if (w ~ /^[A-Za-z_][A-Za-z0-9_]*$/) hq_ = 0
                else if (w ~ /^\047[A-Za-z_][A-Za-z0-9_]*\047$/ || w ~ /^"[A-Za-z_][A-Za-z0-9_]*"$/) { hq_ = 1; w = substr(w, 2, length(w) - 2) }
                if (hq_ < 0 || incomment) bad("HEREDOCWORD")
                else { nh++; HW[nh] = w; HQ[nh] = hq_; HD[nh] = dash; HO[nh] = seg(sp); HS[nh] = sp } }
              out(c); raw(c) }
          }
        }
        if (incomment && qic && (sq || bt || sp > 0)) bad("COMMENTQUOTE")
        if (hcur <= nh && !cont && (sq || bt || sp != HS[hcur])) bad("HEREDOCQUOTE")
        if (cont) continue
        if (sq) sqb = sqb "\n"; else if (bt) btb = btb "\n"; else if (KIND[sp] == "D") QB[sp] = QB[sp] "\n"
        else { flush(sp); raw("\n") }
      }
      if (sq || bt || sp > 0 || hcur <= nh) bad("OPENQUOTE")
      if (BAD != "") print "\001" BAD
      for (i = 1; i <= n; i++) {
        f = ""; s = fold(RAW[i])
        if (loose(QD[i])) f = f "q"
        if (wordy(s)) f = f "w"
        s2 = s; sub(/(^|[^a-z0-9_-])gh([^a-z0-9_.-]|$)/, " ", s2); if (wordy(s2)) f = f "g"
        if (fold(QH[i]) ~ /pulls\/[^ ]*merge|repos\/[^ ]*\/merges/) f = f "a"
        if (!plainexp(EX[i])) f = f "x"
        if (f == "") f = "-"
        print f "\t" OUT[i] }
    }')

# The text could not be parsed the way the shell reads it, so what runs cannot be judged: deny.
case "$segs" in
  *$'\001'OPENQUOTE*) deny "an unclosed quote in the command hides what follows it, so a merge cannot be judged." ;;
  *$'\001'COMMENTQUOTE*) deny "a quote inside a # comment hides what follows it, so a merge cannot be judged." ;;
  *$'\001'SUBSTTEXT*) deny "merge-like text next to a \$( ) or backtick substitution inside double quotes cannot be judged." ;;
  *$'\001'HEREDOC*) deny "a heredoc with an end word that is not a plain name, in a # comment, or next to an open quote cannot be judged next to the word merge." ;;
  *$'\001'*) deny "a case statement, a comment or a \${ } expansion inside a quoted substitution cannot be judged next to the word merge." ;;
esac

# inert <segment> <flags> <T>: the allow list of #680. It returns 0 for a command that never runs its
# arguments, its stdin or a named file as code, and sets LEVEL: 1 = a shell builtin or a text tool that reads
# no configuration; 2 = git, gh or rg, which read configuration files that can name a program to run.
# T is 1 when the segment itself holds merge-like text. A command that is not on the list, and that holds
# merge-like text, is denied.
# Never on the list: a segment with an expansion other than $NAME, ${NAME}, a special parameter or $( )
# (flag x: $(( )), $[ ], ${s:x}, ${a[x]}, ${!x}, zsh ${(e)x} and $~x): the shell evaluates a variable's value
# there as code or arithmetic, and an array subscript in that value runs $( ). jq is listed: it has no way
# to run a program. Left out on purpose:
# test / [ / [[ with a numeric operator or -v, and printf -v (same arithmetic reason), exit, read, export,
# awk, find, xargs, cp, mv, sed with any script but a line-range print (GNU sed runs a program with e),
# git -c and every git global option but -C and --no-pager, git pull (-s runs git-merge-<name> from PATH),
# git grep -O, git log --output, and every interpreter.
inert() {
  local s=$1 fl=$2 t=$3 w sub
  LEVEL=1
  case "$fl" in *x*) return 1 ;; esac
  w=${s%%[[:space:]]*}
  case "$w" in
    '#'*|echo|:|true|false|cd|pwd|'for'|'case'|'esac'|'done'|'fi'|sleep|seq|jq|wc|ls|mkdir|touch|rm|date|basename|dirname|realpath|readlink|which|type|stat|du|df) return 0 ;;
    cat|head|tail|grep|egrep|fgrep|tee|uniq|cut|tr|nl|comm|paste|column|rev|diff|cmp|sha256sum|shasum|md5sum|md5|base64|xxd|od) return 0 ;;
    printf) printf '%s' "$s" | grep -qE '[[:space:]]-[^[:space:]]*v' && return 1; return 0 ;;
    test|'['|'[[')
      case "$s" in *\\*) return 1 ;; esac
      printf '%s' "$s" | grep -qE '[[:space:]]-(eq|ne|lt|le|gt|ge|v)([[:space:]]|$)' && return 1; return 0 ;;
    sort) printf '%s' "$s" | grep -qE '[[:space:]]--co' && return 1; return 0 ;;
    sed)  # only `sed [-n] [-E] 'N[,M]p' [file...]`: a line-range print runs nothing
      printf '%s' "$s" | grep -qE '^sed([[:space:]]+-[nEr]+)*[[:space:]]+[0-9]+(,([0-9]+|\$))?p([[:space:]]+[^-[:space:]][^[:space:]]*)*[[:space:]]*$' && return 0; return 1 ;;
    rg) LEVEL=2; printf '%s' "$s" | grep -qE '[[:space:]]--(pr|hostname-bin)' && return 1; return 0 ;;
    git)
      LEVEL=2
      # the subcommand after -C <dir> and --no-pager; any other global option (-c, --exec-path, ...) is not listed
      sub=${s#git}
      while :; do
        sub=$(printf '%s' "$sub" | sed -E 's/^[[:space:]]+//')
        case "$sub" in
          -C[[:space:]]*) sub=${sub#-C}; sub=$(printf '%s' "$sub" | sed -E 's/^[[:space:]]+[^[:space:]]+//') ;;
          --no-pager[[:space:]]*|-P[[:space:]]*) sub=${sub#*[[:space:]]} ;;
          *) break ;;
        esac
      done
      if printf '%s' "$sub" | grep -qE '^(commit|log|show|diff|status|add|tag|branch|rev-parse|merge-base|stash|switch|checkout|restore|rev-list|show-ref|for-each-ref|describe|blame|ls-files|ls-tree|cat-file|reflog|shortlog|worktree[[:space:]]+list|grep)([[:space:]]|$)'; then
        printf '%s' "$sub" | grep -qE '[[:space:]](--output|--open|-O|-[A-Za-z]*O)' && return 1
        return 0
      fi
      # these talk to a remote: only without merge-like text and without a program option
      if printf '%s' "$sub" | grep -qE '^(fetch|ls-remote|push)([[:space:]]|$)'; then
        [ "$t" -eq 0 ] || return 1
        printf '%s' "$sub" | grep -qE '[[:space:]]--(no-)?(u|e|rec)' && return 1
        printf '%s' "$sub" | grep -qE '^ls-remote[[:space:]](.*[[:space:]])?-u' && return 1
        return 0
      fi ;;
    gh)
      LEVEL=2
      printf '%s' "$s" | grep -qE '^gh[[:space:]]+(pr[[:space:]]+(create|comment|edit|review|view|list|checks|diff|status|close|ready|reopen)|issue[[:space:]]+(create|comment|edit|view|list|close|reopen)|run[[:space:]]+(list|view|watch)|release[[:space:]]+(create|edit|view|list)|repo[[:space:]]+view|search|api|label)([[:space:]]|$)' && return 0 ;;
  esac
  return 1
}

# cfgtarget <segment>: 0 when the segment writes (a > or >> redirection, or tee) to a target that can be a
# configuration file git, gh or rg read, or a hook git runs; it sets WRITES=2 for a target that is surely
# one (a .git path, a gitconfig, a hooks/ directory, husky, lefthook, pre-commit, a gh/ directory) and
# WRITES=1 for one that may be (a hidden file or directory, a name with config or a *rc name, or a target the
# hook cannot read: a variable, a substitution, a glob, a quoted name). After a cd into such a directory,
# or a cd to a target the hook cannot read (CDCFG), every write counts as WRITES=1.
CDCFG=0
cfgsure() {
  case "$1" in
    .git|.git/*|*/.git|*/.git/*|*.gitconfig*|*hooks/*|hooks|*husky*|*lefthook*|*pre-commit*|*.config/gh*|*gh/config.yml|*gh/hosts.yml) return 0 ;;
  esac
  return 1
}
cfgmaybe() {
  local w=$1
  # A file under a variable directory ($SCRATCH/pr-body.md) whose own name is a plain data file is not a
  # configuration: git, gh and rg read no configuration with these names (hooks and config names are sure).
  case "$w" in
    '$'*)
      # shellcheck disable=SC2016  # a literal $ in the sed pattern
      w=$(printf '%s' "$w" | sed -E 's#^\$(\{[A-Za-z_][A-Za-z0-9_]*\}|[A-Za-z_][A-Za-z0-9_]*)/##')
      case "$w" in
        *'$'*|*'`'*|*'*'*|*'?'*|*'['*|.*|*/.*|*[Cc]onfig*) ;;
        *.md|*.txt|*.json|*.log|*.csv|*.html|*.out|*.diff|*.patch) return 1 ;;
      esac ;;
  esac
  case "$1" in
    .*|*/.*|*[Cc]onfig*|*rc|*'$'*|*'`'*|*'*'*|*'?'*|*'['*|QUOTED|'~'*|-) return 0 ;;
  esac
  return 1
}
cfgtarget() {
  local s=$1 tg w
  case "$s" in
    cd[[:space:]]*)
      w=$(printf '%s' "${s#cd}" | sed -E 's/^[[:space:]]+//')
      if cfgsure "$w" || cfgmaybe "$w"; then CDCFG=1; fi ;;
  esac
  tg=$(printf '%s\n' "$s" | sed -E 's#[0-9]*>>?[[:space:]]*/dev/null([[:space:]]|$)# #g' | grep -oE '>>?[[:space:]]*[^[:space:]]+' | sed -E 's/^>>?[[:space:]]*//')
  if [ "${s%%[[:space:]]*}" = tee ]; then tg="$tg $(printf '%s' "${s#tee}" | sed -E 's/(^|[[:space:]])-[^[:space:]]*//g')"; fi
  for w in $tg; do
    if cfgsure "$w"; then WRITES=2; return 0; fi
    if [ "$CDCFG" -eq 1 ] || cfgmaybe "$w"; then [ "$WRITES" -eq 2 ] || WRITES=1; fi
  done
  return 0
}

set -f
NSEGS=0
SRC=0     # segments on the allow list (and bare assignments) that hold merge-like text
OTHERS=0  # segments that are neither a judged merge nor on the allow list
CONFS=0   # allow-list segments of level 2 (git, gh, rg: they read configuration files)
WRITES=0  # 2: a write to a sure configuration or hook file, 1: to a possible one (cfgtarget)
OTHER1=""
while IFS= read -r seg; do
  case "$seg" in *$'\t'*) FL=${seg%%$'\t'*}; seg=${seg#*$'\t'} ;; *) continue ;; esac
  seg=$(printf '%s' "$seg" | sed -E 's/^[[:space:]]+//'); orig=$seg
  # #677: variable assignments, shell keywords (if then else elif do while until !), zsh prefixes (noglob,
  # nocorrect, -) and redirections (>f, 2>&1, <f, <<<w) in front of a command do not change what runs.
  # Strip them in one loop until nothing changes, so `if X=1 bash -c ...` and `>/dev/null bash -c ...`
  # reach the wrapper check below. KW records that a keyword, prefix or redirection was stripped.
  KW=0; ASG=0
  drop_word() { case "$seg" in *[[:space:]]*) seg=$(printf '%s' "${seg#*[[:space:]]}" | sed -E 's/^[[:space:]]+//') ;; *) seg="" ;; esac; }
  while :; do
    if printf '%s' "$seg" | grep -qE '^[A-Za-z_][A-Za-z0-9_]*(\[[^]]*\])?\+?=[^[:space:]]*([[:space:]]+|$)'; then
      seg=$(printf '%s' "$seg" | sed -E 's/^[A-Za-z_][A-Za-z0-9_]*(\[[^]]*\])?\+?=[^[:space:]]*[[:space:]]*//'); ASG=1; continue
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
  # A redirection to a file anywhere in the segment (2>&1 and >&2 are > /dev/null by now).
  # A write to a file that git, gh or rg can read as configuration (rule R4 below).
  cfgtarget "$orig"
  # T: the segment holds merge-like text. For a gh command the first gh word is the command itself.
  T=0
  case "$FL" in *q*) T=1 ;; esac
  if printf '%s' "$seg" | grep -qE '^gh([[:space:]]|$)'; then case "$FL" in *g*) T=1 ;; esac; else case "$FL" in *w*) T=1 ;; esac; fi
  if [ -z "$seg" ]; then
    # A keyword or redirection alone still counts as a command, so a merge next to it is not "the only command".
    [ "$KW" -eq 1 ] && NSEGS=$((NSEGS + 1))
    # A bare assignment (or a keyword line) that holds merge-like text is a source of that text.
    [ "$T" -eq 1 ] && SRC=1
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
  # A backslash inside the gh words (g\h pr merge, gh pr mer\ge, or a backslash-newline in the middle of a
  # word) does not change what runs, but it hides the words from the checks below: deny such a segment when
  # it reads as a gh merge without the backslashes.
  case "$seg" in
    *\\*)
      if printf '%s' "$(fold "${seg//\\/}")" | grep -qE '^gh[[:space:]].*(pr[[:space:]]+merge|/merge|graphql)'; then
        deny "a gh merge spelled with a backslash cannot be judged."
      fi ;;
  esac
  KIND=other
  if printf '%s' "$seg" | grep -qE '^gh[[:space:]]+pr[[:space:]]+merge([[:space:]]|$)'; then
    judge_pr_merge "$seg"; KIND=merge
  elif printf '%s' "$seg" | grep -qE '^gh[[:space:]]+api[[:space:]]'; then
    # No test for the word graphql: the endpoint can come from a variable (gh api "$E").
    case "$(fold "$cmd")" in
      *mergepullrequest*|*enablepullrequestautomerge*|*mergebranch*|*enqueuepullrequest*) deny "a GraphQL mergePullRequest, enablePullRequestAutoMerge, mergeBranch or enqueuePullRequest mutation is not allowed; a human merges." ;;
    esac
    if printf '%s' "$seg" | grep -qE 'repos/[^[:space:]]*/merges([^A-Za-z0-9_]|$)'; then
      deny "'gh api repos/.../merges' merges a branch and is not allowed; a human merges."
    fi
    case "$FL" in *a*) deny "a gh api merge path inside a quoted string cannot be judged; write the path without quotes." ;; esac
    if printf '%s' "$seg" | grep -qE 'pulls/[^[:space:]]*/merge'; then judge_api_merge "$seg"; KIND=merge; fi
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
      # This list is kept as a second net behind the allow list below (#680): it also denies a merge that a
      # listed shell or wrapper builds at run time, which holds no merge-like text for the allow list to see.
      bash|sh|zsh|dash|ksh|rbash|eval|xargs|env|exec|nohup|time|command|sudo|doas|builtin|source|.|nice|timeout|stdbuf|setsid|ionice|taskset|chronic|unbuffer|repeat|coproc|busybox|flock|script|setpriv|prlimit|chrt|strace|fakeroot|runuser|su|watch|unshare)
        deny "a merge inside a shell string or wrapper ($cw) cannot be judged." ;;
    esac
  fi
  # #680: merge-like text that is not a judged merge is allowed only where nothing can run it.
  if [ "$ASG" -eq 1 ]; then
    # The value of an assignment in front of a command reaches that command through its environment
    # (GIT_SSH_COMMAND, GH_PAGER, ...).
    if [ "$KIND" = merge ]; then case "$FL" in *q*) deny "merge-like text in a variable assignment in front of a merge cannot be judged." ;; esac
    elif [ "$T" -eq 1 ]; then deny "merge-like text next to a variable assignment in front of a command cannot be judged; run the command without the assignment."
    fi
  fi
  if [ "$KIND" != merge ]; then
    if inert "$seg" "$FL" "$T"; then
      [ "$T" -eq 1 ] && SRC=1
      [ "$LEVEL" -eq 2 ] && CONFS=$((CONFS + 1))
    else
      cw=${seg%%[[:space:]]*}
      [ "$T" -eq 0 ] || deny "merge-like text in the arguments or input of '$cw', which is not on the list of commands that never run their arguments. Run it yourself, or put the text in a file with the Write tool."
      OTHERS=$((OTHERS + 1)); [ -n "$OTHER1" ] || OTHER1=$cw
    fi
  fi
done <<SEGS
$segs
SEGS

# Merge-like text in one command (an echo, a heredoc, a variable) can reach another command of the same
# Bash call through a pipe, a variable or a file, so every other command must be on the allow list too.
if [ "$SRC" -eq 1 ] && [ "$OTHERS" -gt 0 ]; then
  deny "merge-like text in the same Bash call as '$OTHER1', which is not on the list of commands that never run their input. Run the two in separate Bash calls."
fi

# The same text written to a file can be a configuration or a hook that git, gh or rg read or run (.git/config
# core.fsmonitor, .git/hooks/pre-commit, .husky/pre-commit, a gh alias file, a ripgrep config). A sure target
# is denied even with no git, gh or rg in the call (the next call would run it); a possible one only next to
# git, gh or rg. The Write tool is not a Bash call, so this hook does not see a file written with it.
if [ "$SRC" -eq 1 ] && [ "$WRITES" -eq 2 ]; then
  deny "merge-like text is written to a git configuration or hook file, which git runs. The owner writes such a file by hand."
fi
if [ "$SRC" -eq 1 ] && [ "$WRITES" -eq 1 ] && [ "$CONFS" -gt 0 ]; then
  deny "merge-like text is written to a file in the same Bash call as git, gh or rg, which read configuration files. Write the file in a separate Bash call."
fi

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
