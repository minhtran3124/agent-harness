#!/bin/bash
# Contract tests for hooks/merge-guard.sh (PreToolUse Bash; fails closed). A stub `gh` first on PATH
# answers `pr view` / `repo view` from files and logs every call, so a test can assert gh was not called.
source "$(dirname "$0")/../lib.sh"

R=$(new_repo merge-guard.sh)
D=$(mktemp -d); _CLEANUP_DIRS+=("$D")
STUB="$D/bin"; mkdir -p "$STUB"
LOG="$D/gh.log"
cat > "$STUB/gh" <<'STUBEOF'
#!/bin/sh
d=$(dirname "$0")/..
echo "$*" >> "$d/gh.log"
case "$1 $2" in
  "pr view")
    [ -f "$d/slow" ] && sleep 30
    [ -f "$d/fail" ] && exit 1
    f="$d/base.$3"; [ -f "$f" ] || f="$d/base"
    cat "$f" ;;
  "repo view")
    [ -f "$d/deffail" ] && exit 1
    cat "$d/default" ;;
  *) exit 1 ;;
esac
STUBEOF
chmod +x "$STUB/gh"
# Tool dirs: TOOLS holds what the hook needs except gh and jq.
TOOLS="$D/tools"; mkdir -p "$TOOLS"
for x in cat sed awk grep sleep mktemp rm head tr cut; do ln -s "$(command -v $x)" "$TOOLS/$x"; done
NOJQ="$D/nojq"; mkdir -p "$NOJQ"; cp -R "$TOOLS"/. "$NOJQ"/; ln -s "$STUB/gh" "$NOJQ/gh"
NOGH="$D/nogh"; mkdir -p "$NOGH"; cp -R "$TOOLS"/. "$NOGH"/; ln -s "$(command -v jq)" "$NOGH/jq"
BASH_BIN=$(command -v bash)

reset() { rm -f "$D"/base "$D"/base.* "$D"/fail "$D"/slow "$D"/deffail "$LOG"; printf 'main\n' > "$D/default"; }
setbase() { printf '%s\n' "$1" > "$D/base"; }
# g <command-string> [PATH-dir] : run the hook with a payload for that command
g() {
  local json; json=$(jq -n --arg c "$1" '{tool_input:{command:$c}}')
  local p="${2:-$STUB:$PATH}"
  OUT=$(cd "$R" && printf '%s' "$json" | env PATH="$p" "$BASH_BIN" hooks/merge-guard.sh 2>&1); RC=$?
}
M='gh pr merge 7 --repo o/r --merge'

reset; setbase feat/x
t "base feat/x is allowed"; g "$M"; assert_rc 0
t "base feat/x passes the gh pr view arguments (--repo and PR number)"
if grep -q 'pr view 7 --repo o/r' "$LOG"; then pass; else fail "log: $(cat "$LOG" 2>/dev/null)"; fi
t "-R o/r is read and passed to gh pr view"; reset; setbase feat/x; g 'gh pr merge 7 -R o/r --merge'
if [ "$RC" = 0 ] && grep -q 'pr view 7 --repo o/r' "$LOG"; then pass; else fail "rc=$RC log: $(cat "$LOG" 2>/dev/null)"; fi
t "--repo=o/r is read and passed to gh pr view"; reset; setbase feat/x; g 'gh pr merge 7 --repo=o/r --merge'
if [ "$RC" = 0 ] && grep -q 'pr view 7 --repo o/r' "$LOG"; then pass; else fail "rc=$RC log: $(cat "$LOG" 2>/dev/null)"; fi
t "a PR URL gives the PR number and the repo"; reset; setbase feat/x; g 'gh pr merge https://github.com/o/r/pull/7 --merge'
if [ "$RC" = 0 ] && grep -q 'pr view 7 --repo o/r' "$LOG"; then pass; else fail "rc=$RC log: $(cat "$LOG" 2>/dev/null)"; fi
t "a PR URL repo that differs from --repo (either order) is denied"; reset; setbase feat/x
g 'gh pr merge https://github.com/evil/r/pull/7 --repo o/r --merge'; assert_rc_contains 2 "differ"
g 'gh pr merge --repo o/r https://github.com/evil/r/pull/7 --merge'; assert_rc_contains 2 "differ"
t "a PR URL repo equal to --repo is allowed"; reset; setbase feat/x
g 'gh pr merge https://github.com/o/r/pull/7 --repo o/r --merge'; assert_rc 0
t "env assignments before gh are skipped"; reset; setbase feat/x; g "FOO=1 $M"; assert_rc 0

for b in v5.0.0 main master develop staging production release/1 release-2 hotfix/x; do
  reset; setbase "$b"; t "base $b is denied with the reason on stderr"; g "$M"; assert_rc_contains 2 "human merges"
done
reset; setbase feat/x; printf 'feat/x\n' > "$D/default"
t "base feat/x that is also the default branch is denied"; g "$M"; assert_rc 2
reset; setbase feat/x; touch "$D/deffail"
t "unreadable default branch is denied"; g "$M"; assert_rc 2
reset; setbase feat/x; touch "$D/fail"
t "gh pr view exits nonzero: denied"; g "$M"; assert_rc 2
reset; : > "$D/base"
t "gh pr view prints nothing: denied"; g "$M"; assert_rc 2
reset; setbase 'feat/x garbage'
t "gh pr view prints a bad name: denied"; g "$M"; assert_rc 2
reset; setbase feat/x
t "no gh on PATH: denied"; g "$M" "$NOGH"; assert_rc 2
t "no jq on PATH and a merge payload: denied"; g "$M" "$NOJQ"; assert_rc 2
t "no jq on PATH and a non-merge payload: allowed"; g 'ls -la' "$NOJQ"; assert_rc 0
t "no PR number: denied"; g 'gh pr merge --repo o/r --merge'; assert_rc 2
t "a branch name instead of a PR number: denied"; g 'gh pr merge feat/x --repo o/r'; assert_rc 2
t "no --repo: denied even when GH_REPO is set"; g 'GH_REPO=o/r gh pr merge 7 --merge'; assert_rc 2
t "--auto is denied"; g 'gh pr merge 7 --repo o/r --auto --merge'; assert_rc 2
reset; setbase main
t "--auto on main is denied"; g 'gh pr merge 7 --repo o/r --auto'; assert_rc 2
reset; setbase feat/x
t "--match-head-commit is accepted"; g 'gh pr merge 7 --repo o/r --merge --match-head-commit abc123'; assert_rc 0

reset; setbase feat/x
t "gh api pulls/7/merge on feat/x is allowed"; g 'gh api -X PUT repos/o/r/pulls/7/merge'; assert_rc 0
reset; setbase main
t "gh api pulls/7/merge on main is denied"; g 'gh api -X PUT repos/o/r/pulls/7/merge'; assert_rc 2
t "gh api with {owner}/{repo} placeholders is denied"; g 'gh api -X PUT repos/{owner}/{repo}/pulls/7/merge'; assert_rc 2
t "gh api graphql mergePullRequest is denied"; g "gh api graphql -f query='mutation { mergePullRequest(input: {pullRequestId: \"x\"}) { clientMutationId } }'"; assert_rc 2
t "bash -c with a merge inside is denied"; g 'bash -c "gh pr merge 7 --repo o/r"'; assert_rc 2
t "eval with a merge inside is denied"; g "eval 'gh pr merge 7 --repo o/r'"; assert_rc 2
t "xargs with a merge is denied"; g 'echo 7 | xargs gh pr merge --repo o/r'; assert_rc 2
for c in 'command gh pr merge 7 --repo o/r' 'env gh pr merge 7 --repo o/r' 'exec gh pr merge 7 --repo o/r' 'nohup gh pr merge 7 --repo o/r' 'time gh pr merge 7 --repo o/r' '/usr/bin/gh pr merge 7 --repo o/r' '\gh pr merge 7 --repo o/r' 'x=`gh pr merge 7 --repo o/r`'; do
  reset; setbase feat/x; t "merge not at command position is denied: $c"; g "$c"; assert_rc 2
done
t "gh alias set with merge is denied"; g "gh alias set mm 'pr merge'"; assert_rc 2

reset; setbase feat/x; printf 'main\n' > "$D/base.8"
t "chain: 7 on feat/x, 8 on main: the whole command is denied"; g 'gh pr merge 7 --repo o/r --merge && gh pr merge 8 --repo o/r --merge'; assert_rc 2
t "chain: the denied PR comes first: denied"; g 'gh pr merge 8 --repo o/r --merge; gh pr merge 7 --repo o/r --merge'; assert_rc 2
reset; setbase feat/x
t "chain: both PRs on feat/x: allowed"; g 'gh pr merge 7 --repo o/r --merge && gh pr merge 8 --repo o/r --merge'; assert_rc 0
t "both PRs of a chain were read"
if grep -q 'pr view 7 ' "$LOG" && grep -q 'pr view 8 ' "$LOG"; then pass; else fail "log: $(cat "$LOG")"; fi
t "a merge segment hidden behind a brace group is judged"; reset; setbase main; g '{ gh pr merge 7 --repo o/r; }'; assert_rc 2

reset
t "echo 'gh pr merge 7' is not a merge"; g "echo 'gh pr merge 7'"; assert_rc 0
t "a heredoc commit message that mentions a merge is not a merge"
g "$(printf 'git commit -F - <<'"'"'EOF'"'"'\nfix: gh pr merge 7 --repo o/r\nEOF')"; assert_rc 0
t "a quoted commit message that mentions a merge is not a merge"; g 'git commit -m "docs: never run gh pr merge 7 by hand"'; assert_rc 0
reset; setbase main
t "an unclosed quote that swallows a later merge is denied"; g "$(printf "echo 'x\ngh pr merge 7 --repo o/r")"; assert_rc 2
t "an apostrophe in a comment before a merge on main is denied"; g "$(printf "# don't\ngh pr merge 7 --repo o/r")"; assert_rc 2
reset; setbase feat/x
t "a multi-word quoted --body value does not swallow the PR number"; g 'gh pr merge --body "a b c" 7 --repo o/r --merge'
if [ "$RC" = 0 ] && grep -q 'pr view 7 --repo o/r' "$LOG"; then pass; else fail "rc=$RC out=$OUT log: $(cat "$LOG" 2>/dev/null)"; fi
t "a multi-word quoted --subject value before a PR on main is still denied"; setbase main; g "gh pr merge -t 'x y' 7 --repo o/r"; assert_rc 2
reset; setbase feat/x
t "a quote-split gh word is still judged (main base denied)"; setbase main; g '"g""h" pr merge 7 --repo o/r'; assert_rc 2
t "an upper-case GraphQL-style spelling cannot skip the filter"; g 'gh api graphql -f query="mutation{enablePullRequestAutoMerge(input:{pullRequestId:\"X\"}){clientMutationId}}"'; assert_rc 2
t "gh api graphql enablePullRequestAutoMerge is denied"; g 'gh api graphql -f query=@q.graphql -f x=enablePullRequestAutoMerge'; assert_rc 2
t "gh api repos/o/r/merges is denied"; g 'gh api repos/o/r/merges -f base=main -f head=x'; assert_rc 2
t "a variable-split subcommand is denied"; g 'm=mer; gh pr ${m}ge 7 --repo o/r'; assert_rc 2
t "a split gh name g\${x}h is denied"; g 'x=""; g${x}h pr merge 7 --repo o/r'; assert_rc 2
t "a command name from a variable is denied"; g 'GH=gh; $GH pr merge 7 --repo o/r'; assert_rc 2
t "gh pr view with a variable argument is allowed"; g 'gh pr view $N --json state'; assert_rc 0
t "a variable inside the pr word is denied"; g 'x=r; gh p$x merge 7 --repo o/r'; assert_rc 2
t "a variable as the gh subcommand is denied"; g 'a=pr; gh $a merge 7 --repo o/r'; assert_rc 2
reset; setbase feat/x
t "a command substitution splitting the gh word is denied"; g 'g$(true)h pr merge 7 --repo o/r'; assert_rc 2
t "a command substitution as the gh command is denied"; g '$(echo gh) pr merge 7 --repo o/r'; assert_rc 2
t "a backtick substitution as the gh command is denied"; g '`echo gh` pr merge 7 --repo o/r'; assert_rc 2
t "a quoted substitution as the gh command is denied"; g '"$(echo gh)" pr merge 7 --repo o/r'; assert_rc 2
t "a substitution next to an api merge path is denied"; g 'x=$(echo gh); $x api -X PUT repos/o/r/pulls/7/merge'; assert_rc 2
t "a backslash-newline inside the gh word is denied"; g "$(printf 'g\\\nh pr merge 7 --repo o/r')"; assert_rc 2
t "a backslash-newline inside the merge word is denied"; g "$(printf 'gh pr mer\\\nge 7 --repo o/r')"; assert_rc 2
t "a backslash-newline between words still judges the PR (feat/x allowed)"; g "$(printf 'gh pr merge 7 \\\n --repo o/r --merge')"; assert_rc 0
t "a path with projects before git merge is allowed"; g 'cd $HOME/projects/x && git merge main'; assert_rc 0
t "a path variable with the word merge but no gh pr merge is allowed"; g '$HOME/bin/tool merge'; assert_rc 0
t "echo with a substitution is allowed"; g 'echo $(date)'; assert_rc 0
t "a merge inside a double-quoted substitution is denied"; g 'echo "$(gh pr merge 7 --repo o/r)"'; assert_rc 2
t "a merge inside a double-quoted backtick is denied"; g 'echo "`gh pr merge 7 --repo o/r`"'; assert_rc 2
t "a merge inside an unquoted heredoc substitution is denied"; g "$(printf 'cat <<EOF\n$(gh pr merge 7 --repo o/r)\nEOF')"; assert_rc 2
t "a merge on a later line of a multi-line heredoc substitution is denied"; g "$(printf 'cat <<EOF\n$(\ngh pr merge 7 --repo o/r\n)\nEOF')"; assert_rc 2
t "a merge on a later line of a multi-line heredoc backtick is denied"; g "$(printf 'cat <<EOF\n`\ngh pr merge 7 --repo o/r\n`\nEOF')"; assert_rc 2
t "a multi-line heredoc substitution without a merge is allowed"; g "$(printf 'cat <<EOF\n$(\ndate\n)\nEOF')"; assert_rc 0
t "a commit message with a quoted heredoc that mentions merge is allowed"; g "$(printf 'git commit -m "$(cat <<'"'"'EOF'"'"'\nfix the merge guard\nEOF\n)"')"; assert_rc 0
t "a double-quoted backtick that mentions merge in text is allowed"; g 'git commit -m "docs: `merge` policy"'; assert_rc 0
t "a nested substitution that builds the gh word inside quotes is denied"; g 'echo "$(g$(true)h pr merge 7 --repo o/r)"'; assert_rc 2
t "a double-quoted substitution without a merge is allowed"; g 'echo "today is $(date)"'; assert_rc 0

reset
t "ls exits 0"; g 'ls -la'; assert_rc 0
t "ls does not call gh"; if [ ! -s "$LOG" ]; then pass; else fail "log: $(cat "$LOG")"; fi
t "a gh call that is not a merge is allowed without a base read"; g 'gh pr view 7 --json state'; assert_rc 0
t "gh pr view does not call gh from the guard"; if [ ! -s "$LOG" ]; then pass; else fail "log: $(cat "$LOG")"; fi

reset; setbase feat/x; touch "$D/slow"
t "a stalled gh is killed and the merge is denied within the time budget"
s=$SECONDS; g "$M"; e=$((SECONDS - s))
if [ "$RC" = 2 ] && [ "$e" -lt 20 ]; then pass; else fail "rc=$RC took ${e}s out=$OUT"; fi
rm -f "$D/slow"

reset; setbase feat/x
t "a command name held in a quoted variable is denied"; g 'P="gh pr"; $P merge 7 --repo o/r'; assert_rc 2
t "a command name held in a variable (graphql) is denied"; g 'X=gh; $X api graphql -f query=mergePullRequest'; assert_rc 2
t "a command name held in a braced variable is denied"; g 'P="gh pr"; ${P} merge 7 --repo o/r'; assert_rc 2
t "a variable command name that is not a merge is allowed"; g 'P="ls -l"; $P /tmp'; assert_rc 0
t "a quoted command name before api graphql with a merge mutation is denied"
g '"$(echo gh)" api graphql -f query="mutation { mergePullRequest(input:{}) { x } }"'; assert_rc 2
t "a quoted command name before api with the merges endpoint is denied"
g '"$(echo gh)" api repos/o/r/merges -f base=main'; assert_rc 2
t "a quoted command name before api without a merge word is allowed"; g '"$(echo gh)" api user'; assert_rc 0

# BSD sed does not read \x01 in a pattern: with such a sed first on PATH the SUBST deny must still work.
BSDSED="$D/bsdsed"; mkdir -p "$BSDSED"; cp -R "$TOOLS"/. "$BSDSED"/; ln -s "$(command -v jq)" "$BSDSED/jq"
rm -f "$BSDSED/sed"
cat > "$BSDSED/sed" <<SEDEOF
#!/bin/sh
case "\$*" in *'\\x01'*) cat >/dev/null; exit 0 ;; esac
exec $(command -v sed) "\$@"
SEDEOF
chmod +x "$BSDSED/sed"
reset; setbase feat/x
t "a merge in a substitution inside double quotes is denied without GNU sed x01"
g 'echo "$(cmd $X merge)"' "$STUB:$BSDSED"; assert_rc 2

finish
