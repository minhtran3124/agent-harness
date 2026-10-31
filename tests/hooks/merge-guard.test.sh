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
    h="$d/head"; [ -f "$h" ] || h="$d/headdefault"
    case "$*" in *headRefOid*) printf '%s %s\n' "$(cat "$f")" "$(cat "$h")" ;; *) cat "$f" ;; esac ;;
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

SHA=0123456789abcdef0123456789abcdef01234567
reset() { rm -f "$D"/base "$D"/base.* "$D"/head "$D"/fail "$D"/slow "$D"/deffail "$LOG"; printf 'main\n' > "$D/default"; printf '%s\n' "$SHA" > "$D/headdefault"; }
setbase() { printf '%s\n' "$1" > "$D/base"; }
# g <command-string> [PATH-dir] : run the hook with a payload for that command
g() {
  local json; json=$(jq -n --arg c "$1" --arg m "${MODE-default}" --arg a "${AGENT-}" \
    '{tool_input:{command:$c}} + (if $m == "" then {} else {permission_mode:$m} end) + (if $a == "" then {} else {agent_id:$a} end)')
  local p="${2:-$STUB:$PATH}"
  OUT=$(cd "$R" && printf '%s' "$json" | env PATH="$p" "$BASH_BIN" hooks/merge-guard.sh 2>&1); RC=$?
}
M='gh pr merge 7 --repo o/r --merge'
MA="$M --match-head-commit $SHA"  # a merge into a protected base must pin the approved head

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

# Ticket #545 AC4 (each path stays denied) is covered in this file, not in tests/scripts/merge-deny.test.sh (that
# file tests the setup script that writes permissions.deny). Cases below: --auto, bash -c / eval / xargs wraps,
# gh api and GraphQL merges, gh alias with merge, no gh, no jq, no PR number, unreadable or empty base.
# A plain single merge into a protected base is put to the owner (ask), not run and not denied.
assert_ask() { if [ "$RC" = 0 ] && printf '%s' "$OUT" | jq -e --arg w "$1" '.hookSpecificOutput | .permissionDecision == "ask" and (.permissionDecisionReason | contains($w))' >/dev/null 2>&1; then pass; else fail "rc=$RC out=$OUT"; fi; }
for b in main master develop staging production release/1 release-2; do
  for md in default acceptEdits auto bypassPermissions; do
    reset; setbase "$b"; t "base $b in mode $md: ask naming PR, base and head"; MODE=$md g "$MA"; assert_ask "Merge PR #7 of o/r into $b at $SHA?"
  done
done
reset; setbase trunk; printf 'trunk\n' > "$D/default"
t "base that is the default branch: ask"; g "$MA"; assert_ask "into trunk at $SHA"
for b in v5.0.0 hotfix/x; do
  reset; setbase "$b"; t "base $b (unknown name) is denied with the reason on stderr"; g "$M"; assert_rc_contains 2 "human merges"
done
reset; setbase main
for md in dontAsk plan bogus ""; do
  t "mode '$md': ask is not possible, denied"; MODE=$md g "$MA"; assert_rc_contains 2 "confirmation prompt"
done
t "a subagent (agent_id) is denied"; AGENT=sub1 g "$MA"; assert_rc_contains 2 "subagent"
t "ask output carries no permissionDecision allow"; g "$MA"; if printf '%s' "$OUT" | grep -q '"allow"'; then fail "$OUT"; else pass; fi
t "ask without --match-head-commit: denied, the reason names the head to pin"; g "$M"; assert_rc_contains 2 "add --match-head-commit $SHA"
t "ask with a --match-head-commit of another sha: denied"; g "$M --match-head-commit ffffffffffffffffffffffffffffffffffffffff"; assert_rc_contains 2 "add --match-head-commit $SHA"
t "ask with --admin: the prompt names the bypass"; g "$MA --admin"; assert_ask "WITH --admin"
t "ask with --delete-branch: the prompt names the branch deletion"; g "$MA --delete-branch"; assert_ask "deletes the head branch"
t "ask with --admin=true: the prompt names the bypass"; g "$MA --admin=true"; assert_ask "WITH --admin"
t "ask with bundled -sd: the prompt names the branch deletion"; g "$MA -sd"; assert_ask "deletes the head branch"
t "ask with --delete-branch=true: the prompt names the branch deletion"; g "$MA --delete-branch=true"; assert_ask "deletes the head branch"
no_note() { if [ "$RC" = 0 ] && printf '%s' "$OUT" | jq -e '.hookSpecificOutput | .permissionDecision == "ask" and (.permissionDecisionReason | (contains("WITH --admin") or contains("deletes the head branch")) | not)' >/dev/null 2>&1; then pass; else fail "rc=$RC out=$OUT"; fi; }
for f in --admin=false --admin=0 --admin=F --delete-branch=false --delete-branch=0 -d=false; do
  t "ask with $f: the flag is off, so the prompt names no bypass or deletion"; g "$MA $f"; no_note
done
t "ask with plain -s: no deletion note"; g "$MA -s"; no_note
t "ask with attached body -bfixed: the value is not read as bundled flags"; g "$MA -bfixed"; no_note
t "ask with attached subject -tAdam: the value is not read as bundled flags"; g "$MA -tAdam"; no_note
t "ask with -b <value> containing d: no deletion note"; g "$MA -b dd"; no_note
t "ask with --admin --admin=false: the later off flag wins, no bypass note"; g "$MA --admin --admin=false"; no_note
t "ask with --admin=false --admin: the later on flag wins, the bypass is named"; g "$MA --admin=false --admin"; assert_ask "WITH --admin"
t "ask with --delete-branch --delete-branch=false: no deletion note"; g "$MA --delete-branch --delete-branch=false"; no_note
t "ask with --admin --admin: the bypass is named once"; g "$MA --admin --admin"
if [ "$(printf '%s' "$OUT" | grep -o 'WITH --admin' | wc -l)" = 1 ]; then pass; else fail "$OUT"; fi
t "ask with --match-head-commit=<head>: put to the owner"; g "$M --match-head-commit=$SHA"; assert_ask "at $SHA?"
t "ask merge chained with another command: denied, not put to the owner"; g "$MA && echo extra"; assert_rc_contains 2 "only command"
t "ask merge after another command: denied"; g "echo x; $MA"; assert_rc_contains 2 "only command"
t "ask merge piped into another command: denied"; g "$MA | cat"; assert_rc_contains 2 "only command"
t "bad head sha: denied"; printf 'xyz\n' > "$D/head"; g "$MA"; assert_rc 2
t "short head sha: denied"; printf 'abc123\n' > "$D/head"; g "$MA"; assert_rc 2
rm -f "$D/head"
t "two merges into main in one command: denied"; g 'gh pr merge 7 --repo o/r --merge && gh pr merge 8 --repo o/r --merge'; assert_rc 2
t "two PR numbers in one merge into main: denied"; g 'gh pr merge 7 8 --repo o/r'; assert_rc 2
t "gh api pulls merge into main: denied, no ask"; g 'gh api -X PUT repos/o/r/pulls/7/merge'; assert_rc 2
setbase feat/x; printf 'main\n' > "$D/base.8"
t "main merge next to a feat/* merge: denied"; g 'gh pr merge 7 --repo o/r --merge && gh pr merge 8 --repo o/r --merge'; assert_rc 2
reset; setbase feat/x
t "feat/x merge in mode dontAsk is still allowed (path unchanged)"; MODE=dontAsk g "$M"; assert_rc 0
t "feat/x merge prints no ask"; g "$M"; if [ -z "$OUT" ]; then pass; else fail "$OUT"; fi
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
t "a merge segment hidden behind a brace group is judged (put to the owner)"; reset; setbase main; g "{ gh pr merge 7 --repo o/r --match-head-commit $SHA; }"; assert_ask "into main"

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
t "a multi-word quoted --subject value before a PR on main is still put to the owner"; setbase main; g "gh pr merge -t 'x y' 7 --repo o/r --match-head-commit $SHA"; assert_ask "Merge PR #7"
reset; setbase feat/x
t "a quote-split gh word is still judged (main base put to the owner)"; setbase main; g "\"g\"\"h\" pr merge 7 --repo o/r --match-head-commit $SHA"; assert_ask "into main"
t "an upper-case GraphQL-style spelling cannot skip the filter"; g 'gh api graphql -f query="mutation{enablePullRequestAutoMerge(input:{pullRequestId:\"X\"}){clientMutationId}}"'; assert_rc 2
t "gh api graphql enablePullRequestAutoMerge is denied"; g 'gh api graphql -f query=@q.graphql -f x=enablePullRequestAutoMerge'; assert_rc 2
t "gh api repos/o/r/merges is denied"; g 'gh api repos/o/r/merges -f base=main -f head=x'; assert_rc 2
t "a variable-split subcommand is denied"; g 'm=mer; gh pr ${m}ge 7 --repo o/r'; assert_rc 2
t "a split gh name g\${x}h is denied"; g 'x=""; g${x}h pr merge 7 --repo o/r'; assert_rc 2
t "a command name from a variable is denied"; g 'GH=gh; $GH pr merge 7 --repo o/r'; assert_rc 2
t "gh pr view with a variable argument is allowed"; g 'gh pr view $N --json state'; assert_rc 0
t "a variable inside the pr word is denied"; g 'x=r; gh p$x merge 7 --repo o/r'; assert_rc 2
t "a variable as the gh subcommand is denied"; g 'a=pr; gh $a merge 7 --repo o/r'; assert_rc 2

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

# Probe (opt-in: it starts real `claude -p` sessions, needs a login and costs tokens): what Claude Code does
# with permissionDecision "ask" under default, auto and bypassPermissions. Run with RUN_ASK_PROBE=1.
# Result (ADR 0108, 0109): in each mode the Bash call is NOT run; headless, nobody can answer the prompt.
ask_probe() {
  local mode="$1" pd
  pd=$(mktemp -d); _CLEANUP_DIRS+=("$pd"); mkdir -p "$pd/.claude"
  cat > "$pd/hook.sh" <<'HOOKEOF'
#!/bin/sh
cat >/dev/null
echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"probe ask"}}'
HOOKEOF
  chmod +x "$pd/hook.sh"
  printf '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"%s/hook.sh"}]}]}}' "$pd" > "$pd/.claude/settings.json"
  (cd "$pd" && claude -p --model haiku --permission-mode "$mode" --setting-sources project \
    "Run exactly this Bash command and nothing else: touch $pd/ran. Then say DONE." </dev/null >/dev/null 2>&1)
  if [ -f "$pd/ran" ]; then fail "ask was turned into an allow under $mode"; else pass; fi
}
for mode in default auto bypassPermissions; do
  t "probe: ask is not turned into an allow under $mode (headless claude -p)"
  if [ "${RUN_ASK_PROBE:-}" != 1 ]; then skip "set RUN_ASK_PROBE=1 to run (starts a real claude session)"
  elif ! command -v claude >/dev/null 2>&1; then skip "claude is not installed"
  else ask_probe "$mode"; fi
done

finish
