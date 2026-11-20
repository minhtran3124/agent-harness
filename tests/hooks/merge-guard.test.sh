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
for b in v5.0.0 hotfix/x phase3-ui; do
  reset; setbase "$b"; t "base $b (not protected) is allowed without ask or deny"; g "$M"
  if [ "$RC" = 0 ] && [ -z "$OUT" ]; then pass; else fail "rc=$RC out=$OUT"; fi
done
reset; setbase phase3-ui; t "base phase3-ui in a subagent is allowed"; AGENT=a1 g "$M"; assert_rc 0
reset; setbase phase3-ui; touch "$D/deffail"; t "base phase3-ui with an unreadable default branch is denied"; g "$M"; assert_rc 2
reset; setbase phase3-ui; printf 'phase3-ui\n' > "$D/default"
t "base phase3-ui that is the default branch: ask"; g "$MA"; assert_ask "into phase3-ui at $SHA"
reset; setbase main; t "base main in a subagent is still denied"; AGENT=a1 g "$MA"; assert_rc 2
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
if [ "$(printf '%s' "$OUT" | grep -o 'WITH --admin' | wc -l)" -eq 1 ]; then pass; else fail "$OUT"; fi  # -eq: macOS wc pads with spaces
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

# Issue #671: the word merge in a file name is not a merge when the command is not merge-like (no $ or
# backtick before it) or has no wrapper. The known false positive (a $ before such a name, with a shell)
# stays denied on purpose: an exemption for it was dropped after four security reviews (docs/hooks.md).
reset; setbase main
for c in 'bash tests/hooks/post-merge-hooks.test.sh' 'echo $HOME; grep -n merge_pr tests/scripts/release.test.sh' \
         'bash tests/hooks/post-merge-hooks.test.sh > /tmp/out.log; echo done'; do
  t "#671: a merge-named file with no wrapper or no \$ before it is allowed: $c"; g "$c"; assert_rc 0
done
t "#671: the accepted false positive is denied, as documented"; g 'S=/tmp/x; bash $S/run.sh tests/hooks/post-merge-hooks.test.sh'; assert_rc 2
# A wrapper that runs code from a string or stdin stays denied, including merges built at run time
# (the bypasses found in review of the first fix), and a script-file run that could carry a merge.
for c in 'X="gh pr merge 7 --repo o/r"; bash -c "$X"' 'X=me; bash -c "gh pr ${X}rge 7 --repo o/r"' \
         'C=$(echo gh); bash -c "$C pr merge 7"' 'Y=1; bash -c "echo $Y; gh pr merge 7 --repo o/r"' \
         'U=x; bash -c "gh api -X PUT repos/o/r/pulls/7/merge $U"' 'P=7; eval "gh pr merge $P --repo o/r"' \
         'N=7; bash $HOME/x.sh merge $N' \
         'Y=ge; bash -c "gh api -X PUT repos/o/proj/pulls/7/mer$Y"' \
         "bash -c \$'gh api -X PUT repos/o/r/pulls/7/merg\\x65'; echo post-merge" \
         'X=pr; Y=mer; bash -c "gh $X ${Y}ge 7 --repo o/r"; bash post-merge-hooks.test.sh' \
         'X=me-rge; bash -c "gh pr ${X//-/} 7"' \
         'bash -c "$(printf %s Z2ggcHIgbWVyZ2Ug | base64 -d) 7 --repo o/r"; echo gh merge-base' \
         'A=g; B=h; bash -c "$A$B pr $M 7"; echo post-merge' 'echo gh pr merge 7 | bash; echo $HOME' \
         'S=/r; bash -s < $S/post-merge.sh' 'S=/r; env -S "bash $S/post-merge.sh"' \
         'S=/r; bash $(echo $S)/post-merge.sh' 'S=/r; bash -ec "$S post-merge"' \
         'S=/r; gh_cmd=1; bash $S/post-merge.sh $gh_cmd; gh api repos/o/r/pulls/7 -X PUT'; do
  t "#671: a wrapper that can carry a PR merge is still denied: $c"; g "$c"; assert_rc 2
done
# The security review of the first fix: a merge built at run time from a word with an extra character,
# fed to a shell through a pipe, heredoc, file or wrapper. Each one was denied on main and must stay so.
for c in 'echo gh pr xmerge 7 --repo o/r | sed s/x// | bash' 'echo gh pr Xmerge 7 --repo o/r | tr -d X | sh' \
         'echo gh api -X PUT repos/o/r/pulls/7/xmerge | sed s/x// | bash' \
         'echo gh; v=xmerge; w=xpr; bash -c "gh ${w#x} ${v#x} 7 --repo o/r"' \
         'echo gh; v=xmerge; w=xpr; eval "gh ${w#x} ${v#x} 7 --repo o/r"' \
         "echo gh pr\$'\\x20'merge 7 --repo o/r | bash" \
         'echo gh; source <(echo gh pr xmerge 7 --repo o/r | sed s/x//)' \
         'echo gh pr xmerge 7 --repo o/r | sed s/x// > /tmp/p.sh; bash /tmp/p.sh' \
         "$(printf 'tr -d x <<EOF | bash\ngh pr xmerge 7 --repo o/r\nEOF')" \
         'echo gh; echo pr xmerge 7 --repo o/r | sed s/x// | xargs gh' 'IFS=_; v=gh_pr_merge_7_--repo_o/r; eval $v' \
         'echo gh; v=xmerge; w=xpr; command gh ${w#x} ${v#x} 7 --repo o/r' \
         'echo gh; v=xmerge; w=xpr; time gh ${w#x} ${v#x} 7 --repo o/r' \
         'echo gh; v=xmerge; w=xpr; env -S "gh ${w#x} ${v#x} 7 --repo o/r"' \
         'echo $HOME; echo gh pr xmerge 7 --repo o/r | sed s/x// | bash' \
         'echo gh pr 0merge 7 --repo o/r | cut -c1-6,8- | bash' \
         'echo GH PR XMERGE 7 --REPO O/R | sed s/X// | tr A-Z a-z | bash' \
         'echo gh api -X POST repos/o/r/xmerges -f base=main -f head=x | sed s/x// | bash'; do
  t "#671 review: a merge built at run time stays denied: $c"; g "$c"; assert_rc 2
done
# Second security review of #674: an option that takes a value hid a later -c, a variable operand, stdin
# under another name, and an interpreter writing the script. Each was denied before #674.
for c in "echo \$HOME/xmerge; bash -O extglob -c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; bash +O extglob -c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; bash -o posix -c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; bash --init-file /dev/null -c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; bash -eO extglob -c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; zsh -o shwordsplit -c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; sh -o errexit -c 'M=xmerge G=ig; \${G#i}h pr \${M#x} 7 --repo o/r'" \
         "echo \$HOME/xmerge; F=-c; bash \$F 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; env -- bash -O extglob -c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; nohup bash -O extglob -c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; time -p bash -O extglob -c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; bash -O extglob -c 'gh pr m{e..e}rge 7 --repo o/r' < /dev/null" \
         "echo \$HOME/xmerge; sudo bash -O extglob -c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; command -p bash -O extglob -c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "python3 -c \"open('f.sh','w').write('gh pr xmerge 7 --repo o/r'.replace('x',''))\"; bash f.sh" \
         "echo \$HOME/xmerge; bash /dev/stdin" "echo \$HOME/xmerge; bash -- -c 'gh pr m{e..e}rge 7'"; do
  t "#671 review 2: a shell run with options or a hidden script stays denied: $c"; g "$c"; assert_rc 2
done
# Third security review: an operand that expands to an option, and a writer that is not an interpreter.
# Each was denied before #674 and must stay denied.
for c in "echo \$HOME/xmerge; bash \\-c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; bash [-]c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; bash ?c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; bash {-c,} 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; bash \${F:--c} 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; set -- -c; bash \$1 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; bash \$* 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; A=(-c x); bash \${A[0]} 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; bash \${F%x} 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; A=-; B=c; bash \$A\$B 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; sudo bash \\-c 'gh pr m{e..e}rge 7 --repo o/r'" \
         "echo \$HOME/xmerge; cp /etc/hostname f.sh; sed -i 's/.*/gh pr xmerge 7 --repo o\\/r/;s/x//' f.sh; bash f.sh" \
         "echo \$HOME/xmerge; sed -n 's/.*/gh pr xmerge 7/;s/x//;w f.sh' /etc/hostname; bash f.sh" \
         "echo \$HOME/xmerge; sort -o f.sh g.txt; bash f.sh" "echo \$HOME/xmerge; nodejs w.js; bash f.sh" \
         "echo \$HOME/xmerge; IFS=:; S='-c:g[h] pr m{e..e}rge 7 --repo o/r #'; bash \$S/run.sh"; do
  t "#671 review 3: an option-like operand or a same-call writer stays denied: $c"; g "$c"; assert_rc 2
done

# Issue #677: a literal merge in a shell string behind a keyword, !, an unlisted wrapper, or a path or
# backslash on the shell name was not denied (it reached gh pr merge with no owner prompt).
reset; setbase main
for c in 'if bash -c "gh pr merge 7 --repo o/r"; then :; fi' '! bash -c "gh pr merge 7 --repo o/r"' \
         'while bash -c "gh pr merge 7 --repo o/r"; do break; done' 'until bash -c "gh pr merge 7 --repo o/r"; do :; done' \
         'true; then bash -c "gh pr merge 7 --repo o/r"' \
         'nice bash -c "gh pr merge 7 --repo o/r"' 'timeout 5 bash -c "gh pr merge 7 --repo o/r"' \
         'stdbuf -o0 bash -c "gh pr merge 7 --repo o/r"' 'setsid bash -c "gh pr merge 7 --repo o/r"' \
         'ionice -c2 bash -c "gh pr merge 7 --repo o/r"' 'taskset 1 bash -c "gh pr merge 7 --repo o/r"' \
         '/bin/bash -c "gh pr merge 7 --repo o/r"' '\bash -c "gh pr merge 7 --repo o/r"' \
         '/usr/bin/env bash -c "gh pr merge 7 --repo o/r"' 'if eval "gh pr merge 7 --repo o/r"; then :; fi' \
         '! /bin/sh -c "gh pr merge 7 --repo o/r"' 'if ! bash -c "gh pr merge 7 --repo o/r"; then :; fi'; do
  t "#677: a merge behind a keyword, wrapper or shell path is denied: $c"; g "$c"; assert_rc 2
done
t "#677: a keyword in front of an ordinary command is still allowed"; g 'if true; then echo merged; fi'; assert_rc 0

# Security review of PR #679. F1: a merge next to a keyword is denied, not put to the owner.
reset; setbase main
for c in "! gh pr merge 7 --repo o/r --match-head-commit $SHA" \
         "$(printf 'gh pr merge 7 --repo o/r --match-head-commit %s\nthen' "$SHA")" \
         "$(printf 'gh pr merge 7 --repo o/r --match-head-commit %s\n!' "$SHA")" \
         "if gh pr merge 7 --repo o/r --match-head-commit $SHA" "do gh pr merge 7 --repo o/r --match-head-commit $SHA" \
         "X=1 if gh pr merge 7 --repo o/r --match-head-commit $SHA" \
         "$(printf 'then\ngh pr merge 7 --repo o/r --match-head-commit %s' "$SHA")"; do
  t "#679 review F1: a merge next to a keyword is denied, not asked: $c"; g "$c"; assert_rc 2
done
# F2-F6: an assignment after a keyword, a backslash, glob or = in the shell name, a redirection first,
# zsh prefixes, and common wrappers not listed before. Each reached gh pr merge in a sandbox.
for c in 'if X=1 bash -c "gh pr merge 7 --repo o/r"; then :; fi' '! X=1 bash -c "gh pr merge 7 --repo o/r"' \
         'while X=1 eval "gh pr merge 7 --repo o/r"; do break; done' 'if true; then X=1 bash -c "gh pr merge 7 --repo o/r"; fi' \
         '! X= /bin/bash -c "gh pr merge 7 --repo o/r"' \
         'b\ash -c "gh pr merge 7 --repo o/r"' 'ev\al "gh pr merge 7 --repo o/r"' '/bin/bas[h] -c "gh pr merge 7 --repo o/r"' \
         '/bin/bas? -c "gh pr merge 7 --repo o/r"' '=bash -c "gh pr merge 7 --repo o/r"' \
         '>/dev/null bash -c "gh pr merge 7 --repo o/r"' '</dev/null bash -c "gh pr merge 7 --repo o/r"' \
         '<<<"gh pr merge 7 --repo o/r" bash' 'if >/dev/null bash -c "gh pr merge 7 --repo o/r"; then :; fi' \
         '> /dev/null bash -c "gh pr merge 7 --repo o/r"' '2>/dev/null bash -c "gh pr merge 7 --repo o/r"' \
         'noglob bash -c "gh pr merge 7 --repo o/r"' 'nocorrect bash -c "gh pr merge 7 --repo o/r"' \
         '- bash -c "gh pr merge 7 --repo o/r"' 'repeat 1 bash -c "gh pr merge 7 --repo o/r"' \
         '! noglob eval "gh pr merge 7 --repo o/r"' 'coproc bash -c "gh pr merge 7 --repo o/r"; wait' \
         '{bash,-c,"gh pr merge 7 --repo o/r"}' 'echo "gh pr merge 7 --repo o/r" | $SHELL' \
         'rbash -c "gh pr merge 7 --repo o/r"' 'busybox sh -c "gh pr merge 7 --repo o/r"' \
         'flock /tmp/l bash -c "gh pr merge 7 --repo o/r"' 'script -qc "gh pr merge 7 --repo o/r" /dev/null' \
         'setpriv bash -c "gh pr merge 7 --repo o/r"' 'prlimit bash -c "gh pr merge 7 --repo o/r"' \
         'chrt -o 0 bash -c "gh pr merge 7 --repo o/r"' 'strace -o /dev/null bash -c "gh pr merge 7 --repo o/r"' \
         'fakeroot bash -c "gh pr merge 7 --repo o/r"'; do
  t "#679 review F2-F6: a hidden wrapper is denied: $c"; g "$c"; assert_rc 2
done
reset
t "#679 review: a redirection before an ordinary command is still allowed"; g '>/tmp/out echo merged'; assert_rc 0
t "#679 review: test brackets next to the word merge are still allowed"; g '[ -n "$X" ] && echo merged'; assert_rc 0

# Confirmation review of #679: a backslash inside the gh words, a redirection holding & or |, X+= and
# a[0]= assignments, watch and unshare. Each reached gh pr merge with no prompt before this change.
reset; setbase main
for c in 'g\h pr merge 7 --repo o/r' 'gh pr mer\ge 7 --repo o/r' 'gh p\r merge 7 --repo o/r' \
         '2>&1 bash -c "gh pr merge 7 --repo o/r"' '>&/dev/null bash -c "gh pr merge 7 --repo o/r"' \
         '>| f bash -c "gh pr merge 7 --repo o/r"' 'X+=1 bash -c "gh pr merge 7 --repo o/r"' \
         'a[0]=1 bash -c "gh pr merge 7 --repo o/r"' 'watch -g -n1 "gh pr merge 7 --repo o/r"' \
         'unshare -r bash -c "gh pr merge 7 --repo o/r"'; do
  t "#679 confirm: a hidden merge is denied: $c"; g "$c"; assert_rc 2
done
reset
for c in 'if gh run list --workflow merge.yml; then :; fi' '! gh pr view 5 --json mergedAt' \
         '>/tmp/o gh pr list --search merged' 'ls 2>&1 | grep merge'; do
  t "#679 confirm: a gh read next to a keyword or redirection is allowed: $c"; g "$c"; assert_rc 0
done

# Fourth security review of the dropped #671 exemption: a $VAR/ operand that word-splits into -c, env's
# split-string option in a form the old check missed, and $( assembled from pieces (PS4, test -v). Each ran
# gh pr merge in a sandbox through the exemption; with no exemption they must be denied.
for c in "S='-c \"\$@\" '; bash \$S/post-merge.sh gh pr m{e..e}rge 7 --repo o/r" \
         "printf -v S %s '-c \"\$@\" '; bash \$S/post-merge.sh gh pr m{e..e}rge 7 --repo o/r" \
         "env -vSbash -c '{gh,pr,m{e..e}rge,7,--repo=o/r}' bash tests/post-merge.sh" \
         "env --split=bash -c '{gh,pr,m{e..e}rge,7,--repo=o/r}' bash tests/post-merge.sh" \
         "PS4=\"\\\$\"'(gh pr m{e..e}rge 7 --repo o/r)' bash -x tests/post-merge.sh" \
         "x='a['\"\\\$\"'(gh pr m{e..e}rge 7 --repo o/r)]'; test -v 'b[x]'; bash tests/post-merge.sh"; do
  t "#671 review 4: a script run built to carry a merge is denied: $c"; g "$c"; assert_rc 2
done

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

# Issue #680: merge-like text that is not a judged merge is allowed only in a command that never runs its
# arguments (the allow list). The four classes of the ticket reached gh pr merge with no owner prompt.
NL='
'
reset; setbase main
for c in "python3 -c \"import os; os.system('gh pr merge 7 --repo o/r')\"" \
         "perl -e 'system(\"gh pr merge 7 --repo o/r\")'" \
         "awk 'BEGIN{system(\"gh pr merge 7 --repo o/r\")}'" \
         'find . -exec sh -c "gh pr merge 7 --repo o/r" \;' \
         "git -c alias.x='!gh pr merge 7 --repo o/r' x" \
         "gh pr mer\\${NL}ge 7 --repo o/r" \
         "gh pr mer\\${NL}ge 7 --repo o/r --match-head-commit $SHA"; do
  t "#680: a command of the ticket is denied: $c"; g "$c"; assert_rc 2
done
reset; setbase feat/x
t "#680: a backslash-newline inside the merge word is denied on a feat/* base too"; g "gh pr mer\\${NL}ge 7 --repo o/r"; assert_rc_contains 2 "backslash"
t "#680: a backslash-newline inside the merge word does not skip the pre-filter (gh is not called, the command is denied)"
if [ "$RC" = 2 ] && [ ! -s "$LOG" ]; then pass; else fail "rc=$RC log: $(cat "$LOG" 2>/dev/null)"; fi
reset; setbase main
t "#680: a merge continued on the next line between words is one plain merge, put to the owner"
g "gh pr merge 7 --repo o/r \\${NL}  --match-head-commit $SHA"; assert_ask "Merge PR #7 of o/r into main"
t "#680: an escaped backslash before a newline is not a continuation; the merge on the next line is judged"
g "echo x \\\\${NL}gh pr merge 7 --repo o/r --match-head-commit $SHA"; assert_rc_contains 2 "only command"
# Found while designing #680: the same text reached a command through other quoting, stdin, a variable, the
# environment, a substitution inside quotes or a heredoc. Each was allowed before.
for c in "perl -e 'exec\"gh\",\"pr\",\"merge\",\"7\",\"--repo\",\"o/r\"'" \
         'git -c alias.x=!gh\ pr\ merge\ 7\ --repo\ o/r x' \
         "echo 'gh pr merge 7 --repo o/r' | python3 -c \"import os,sys; os.system(sys.stdin.read())\"" \
         "python3 - <<'EOF'${NL}import os; os.system(\"gh pr merge 7 --repo o/r\")${NL}EOF" \
         "python3 <<< 'import os; os.system(\"gh pr merge 7 --repo o/r\")'" \
         "python3 -c \"import os,sys; os.system('gh pr '+sys.argv[1]+' 7 --repo o/r')\" merge" \
         "X='gh pr merge 7 --repo o/r'; python3 -c \"import os; os.system('\$X')\"" \
         "GIT_SSH_COMMAND='gh pr merge 7 --repo o/r #' git fetch" \
         "GH_PAGER='gh pr merge 9 --repo o/r' gh pr merge 7 --repo o/r --match-head-commit $SHA" \
         "gh api -X PUT 'repos/o/r/pulls/7/merge?a=b&c=d'" \
         "echo 'gh pr merge 7 --repo o/r' > /tmp/x.sh; python3 /tmp/x.sh" \
         "cat <<EOF${NL}\$(gh pr merge 7 --repo o/r)${NL}EOF" \
         "echo \"\$(case x in x) gh pr merge 7 --repo o/r;; esac)\"" \
         "echo \"\$(gh pr merge 7 --repo o/r --match-head-commit $SHA)\"" \
         "echo \\'; gh pr merge 7 --repo o/r --match-head-commit $SHA; echo \\'" \
         "cat <<EOF${NL}x${NL}EO\\${NL}F${NL}gh pr merge 7 --repo o/r --match-head-commit $SHA${NL}EOF" \
         "rg --pre 'sh -c \"gh pr merge 7 --repo o/r\"' x ." \
         "git fetch --upload-pack='gh pr merge 7 --repo o/r #' /tmp/repo" \
         "trap 'gh pr merge 7 --repo o/r' EXIT" "ssh host 'gh pr merge 7 --repo o/r'" \
         "gh pr comment 5 --repo o/r --body \"\$(python3 -c 'import os; os.system(\"gh pr merge 7 --repo o/r\")')\""; do
  t "#680: merge-like text that a command could run is denied: $c"; g "$c"; assert_rc 2
done
# Adversarial review of the #680 design: a heredoc whose end the hook read differently from the shell, an
# allow-list command that evaluates or runs its input after all, text written to a configuration file that
# git reads in the same call, and "pr merge" text with gh after it. Each ran a merge in a stand-in test.
for c in "cat <<EOF-${NL}EOF-${NL}gh pr merge 7 --repo o/r --match-head-commit $SHA${NL}EOF" \
         "cat <<E\\OF${NL}EOF${NL}gh pr merge 7 --repo o/r --match-head-commit $SHA${NL}E" \
         "cat <<EOF${NL}  EOF${NL}echo '${NL}EOF${NL}gh pr merge 7 --repo o/r --match-head-commit $SHA${NL}#'" \
         "cat <<EOF${NL}foo\\${NL}EOF${NL}echo '${NL}EOF${NL}gh pr merge 7 --repo o/r --match-head-commit $SHA${NL}#'" \
         "cat <<A <<B${NL}B${NL}A${NL}echo '${NL}B${NL}gh pr merge 7 --repo o/r --match-head-commit $SHA${NL}#'" \
         "# <<X${NL}gh pr merge 7 --repo o/r --match-head-commit $SHA${NL}X" \
         "[[ 1 -eq 'x[\$(gh pr merge 7 --repo o/r)]' ]]" "test -v 'x[\$(gh pr merge 7 --repo o/r)]'" \
         "printf -v 'x[\$(gh pr merge 7 --repo o/r)]' %s 1" "X='a[\$(gh pr merge 7 --repo o/r)]'; [[ 1 -eq \$X ]]" \
         "cat <<EOF | sort -S 1K --co=sh${NL}gh pr merge 7 --repo o/r${NL}EOF" \
         "git push --e='gh pr merge 7 --repo o/r #' /tmp/bare HEAD" \
         "echo 'fsmonitor = gh pr merge 7 --repo o/r' >> .git/config; git status" \
         "echo 'fsmonitor = gh pr merge 7 --repo o/r' | tee -a .git/config; git status" \
         "E=graphql; gh api \"\$E\" -f query='mutation{mergePullRequest(input:{pullRequestId:\"P\"}){clientMutationId}}'" \
         "gh api graphql -f query='mutation{mergeBranch(input:{repositoryId:\"R\",base:\"main\",head:\"x\"}){clientMutationId}}'" \
         "gh api graphql -f query='mutation{enqueuePullRequest(input:{pullRequestId:\"P\"}){clientMutationId}}'" \
         "echo 'pr merge 7 --repo o/r' | xargs gh" 'set -- pr merge 7 --repo o/r; gh "$@"' \
         "printf 'aliases:\\n  v: pr merge 7 --repo o/r\\n' >> ~/.config/gh/config.yml; gh v"; do
  t "#680 review: a parser gap or an allow-list command that runs its input is denied: $c"; g "$c"; assert_rc 2
done
t "#680 review: a heredoc body after the one plain merge is data; the merge is still put to the owner"
g "$MA --body-file=-<<EOF${NL}  EOF${NL}rm -rf /tmp/victim${NL}EOF"; assert_ask "Merge PR #7 of o/r into main"
t "#680 review: two heredocs on one line are both read as data"; g "cat <<'A' <<'B'${NL}x${NL}A${NL}gh pr merge 7 --repo o/r${NL}B"; assert_rc 0
t "#680: the denial names the command that is not on the allow list"; g "python3 -c \"import os; os.system('gh pr merge 7 --repo o/r')\""; assert_rc_contains 2 "'python3'"
# The allow list: these commands print, store or send the text and never run it. They must stay allowed.
reset
for c in "echo 'gh pr merge 7 --repo o/r'" 'printf "%s\n" "gh pr merge 7"' \
         "git commit -m \"\$(cat <<'EOF'${NL}fix: gh pr merge 7 is denied${NL}EOF${NL})\"" \
         "cd /tmp/x && git add -A && git commit -m \"\$(cat <<'EOF'${NL}fix: gh pr merge 7${NL}EOF${NL})\" && git push -u origin fix/680" \
         "gh pr create --title 'deny gh pr merge in quotes' --body \"\$(cat <<'EOF'${NL}gh pr merge in a string is denied${NL}EOF${NL})\"" \
         'gh pr comment 5 --repo o/r --body "do not run gh pr merge 7 here"' \
         'gh issue create --repo o/r --title x --body "gh pr merge 7 --repo o/r reaches main"' \
         'grep -rn "gh pr merge" plugins/ docs/ | head -20' "rg -n 'gh pr merge|pulls/.*/merge' plugins | wc -l" \
         "cat > /tmp/notes.md <<'EOF'${NL}Run gh pr merge 7 --repo o/r by hand.${NL}EOF" \
         'echo "PR $(gh pr view 5 --repo o/r --json state -q .state) is not merged"' \
         'for f in a b; do echo "gh pr merge $f"; done' \
         'gh pr view 7 --repo o/r --json mergeable,mergeStateStatus && npm test' \
         'gh pr view 7 --repo o/r --json mergeable | python3 -c "import sys,json; print(json.load(sys.stdin))"' \
         "gh api graphql -f query='query(\$o:String!){repository(owner:\$o,name:\"r\"){pullRequest(number:7){mergeable}}}' -f o=o" \
         'BODY="see gh pr merge"; gh pr comment 5 --repo o/r --body "$BODY"'; do
  t "#680: text in a command on the allow list is allowed: $c"; g "$c"
  if [ "$RC" = 0 ] && [ -z "$OUT" ]; then pass; else fail "rc=$RC out=$OUT"; fi
done
# #680 false-positive shapes of the replay on session transcripts: a word that only starts with "merge"
# (mergeable_state), read-only git next to merge text, a write to a file git does not read next to git add,
# and a heredoc with a simple $( ) or $VAR in a gh pr create body. They must stay allowed.
reset
for c in 'git fetch origin && gh api repos/o/r/pulls/7 -q .mergeable_state' \
         "git ls-remote origin refs/pull/7/head; gh api repos/o/r/pulls/7 -q .mergeable_state" \
         "git rev-list --count origin/main..HEAD; git commit -m 'deny gh pr merge in quotes'" \
         "cat > notes.md <<'EOF'${NL}- run gh pr merge 7 --repo o/r after review${NL}EOF${NL}git add notes.md && git commit -m notes" \
         "cat >> docs/hooks.md <<EOF${NL}merge-guard denies gh pr merge in a shell string${NL}EOF${NL}git add docs/hooks.md" \
         "gh pr create --title x --body \"\$(cat <<EOF${NL}gh pr merge in a string is denied${NL}- head: \$(git rev-parse --short HEAD) on \$BRANCH${NL}EOF${NL})\"" \
         "sleep 5; git log --grep='gh pr merge' --oneline | head" \
         "gh api repos/o/r/pulls/7 | jq '.mergeable'; grep -c 'gh pr merge' docs/hooks.md" \
         "sed -n '1,40p' docs/hooks.md; grep -n 'gh pr merge' docs/hooks.md" \
         "git push -u origin fix/x; cat > \$SCRATCH/pr-body.md <<'EOF'${NL}Squash-merge after review; gh pr merge is denied. \${x:-y} \$((1)) are text.${NL}EOF" \
         "cat > \$SCRATCH/gh/pr700.md <<'EOF'${NL}gh pr merge is denied${NL}EOF" \
         "git add -A && git commit -q -F - <<'EOF'${NL}fix: deny gh pr merge in quotes (\$(x) and \${y:z} are text)${NL}EOF" \
         "gh pr create --base main --head x --title t --body-file - <<'EOF'${NL}gh pr merge in a string is denied; \${a[1]}${NL}EOF" \
         "REPO=\$(gh repo view --json nameWithOwner -q .nameWithOwner); cat > \$SCRATCH/body.md <<EOF${NL}PR for \$REPO: gh pr merge is denied in \${REPO} and \\\$((1)).${NL}\$(gh repo view --json nameWithOwner -q .nameWithOwner)${NL}EOF" \
         "f=/tmp/x/body.md && git push 2>&1 | tail -1; cat > \$f <<'EOF'${NL}gh pr merge is denied${NL}EOF" \
         "img(){ echo \"![\$1](\$U/\$1.png?raw=true)\"; }; gh pr create --title t --body \"\$(cat <<EOF${NL}gh pr merge is denied, see \\\`code\\\` here${NL}\$(img before-x)${NL}EOF${NL})\"" \
         "for x in p1 p2; do case \$x in p1) T='a b';; p2) T='c d';; esac; gh issue create --repo o/r --title \"\$T\" --body-file t-\$x.md; done; echo 'gh pr merge is text'" \
         "# add #76 follow-ups (nits); it's done${NL}gh pr view 76 --json body -q .body | grep -c 'gh pr merge'" \
         "# check what gh pr merge would do${NL}gh pr view 7 --repo o/r --json mergeable" \
         "for i in \$(seq 1 3); do r=\$(gh pr view 7 --repo o/r --json statusCheckRollup --jq '.x'); case \"\$r\" in *COMPLETED:SUCCESS*) exit 0;; *FAILURE*) exit 1;; esac; sleep 10; done; echo 'gh pr merge is text'" \
         "cat > \$S/t.md <<'EOF'${NL}*gh pr merge* [x] is text?${NL}EOF" \
         "cat > \$S/pr15.md <<EOF${NL}squash-merge after review; gh pr merge is denied${NL}EOF${NL}gh api -X PATCH 'repos/{owner}/{repo}/pulls/15' -F body=@\$S/pr15.md -q .html_url" \
         "cat > \$S/pr15.md <<EOF${NL}gh pr merge is denied${NL}EOF${NL}gh api -X PATCH \"repos/{owner}/{repo}/pulls/15\" -F body=@\$S/pr15.md" \
         "R=o/r; cat > \$S/x1.md <<EOF${NL}gh pr merge is denied${NL}EOF${NL}gh api repos/\$R/milestones/9 -q '.title'" \
         "R=\$(gh repo view --json nameWithOwner -q .nameWithOwner); gh api repos/\$R/pulls/7 --jq .mergeable" \
         "N=7; gh api repos/o/r/pulls/\$N/comments --paginate -q '.[].body'" \
         "N=\$(cat n.txt); gh api -X PATCH repos/o/r/pulls/\$N -f body=done" \
         "A=pulls/7; B=merge; gh api repos/o/r/\$A/\$B" \
         "bash scripts/run-tests.sh > log; gh api repos/o/r/pulls/699/comments/1/replies -f body=\"Fixed in \${H:0:8}\"" \
         "git ls-files -z | xargs -0 du -ch; gh api repos/o/r/pulls/\$N/comments -f body=x" \
         "grep -qx '.claude.bak/' .git/info/exclude || echo '.claude.bak/' >> .git/info/exclude; cat > /tmp/x/x.md <<'EOF'${NL}gh pr merge is denied${NL}EOF"; do
  t "#680: a replay false-positive shape is allowed: $c"; g "$c"
  if [ "$RC" = 0 ] && [ -z "$OUT" ]; then pass; else fail "rc=$RC out=$OUT"; fi
done
# #680 design review: an expansion that evaluates a value (bash arithmetic and ${!x}, zsh ${(e)x} and $~x), a
# substitution in an unquoted heredoc body, a heredoc that bash ends at "EOF)", an option that makes a listed
# command run a program, and a hook or config file written next to git. Each must be denied.
reset; setbase main
for c in "x='a[\$(gh pr merge 7 --repo o/r)]'; s=hi; echo \${s:x}" "x='a[\$(gh pr merge 7 --repo o/r)]'; echo \$[x]" \
         "x='a[\$(gh pr merge 7 --repo o/r)]'; cat <<EOF${NL}\${s:x}${NL}EOF" \
         "X='\$(gh pr merge 7 --repo o/r)'; echo \"\${(e)X}\"" "X='a[\$(gh pr merge 7 --repo o/r)]'; echo \"\${!X}\"" \
         "X='*(e:gh pr merge 7 --repo o/r:)'; echo \$~X" \
         "python3 -c 'import os; os.system(\"gh pr merge\\x207 --repo o/r\")'" \
         "cat <<EOF${NL}\$(python3 -c \"import os; os.system('gh pr merge 7 --repo o/r')\")${NL}EOF" \
         "X='gh pr merge 7 --repo o/r'; cat <<EOF${NL}\$(bash -c \"\$X\")${NL}EOF" \
         "cat <<EOF${NL}gh pr merge 7 --repo o/r \$(sed 1e x)${NL}EOF" \
         "cat <<EOF${NL}\\\\\\\\\$(gh pr merge 7 --repo o/r)${NL}EOF" \
         "x=\$(cat <<EOF${NL}hi${NL}EOF)${NL}gh pr merge 7 --repo o/r --match-head-commit $SHA${NL}EOF" \
         "rg --pr=./x 'gh pr merge 7 --repo o/r' docs" "git push --rece='gh pr merge 7 --repo o/r' origin x" \
         "git ls-remote -u 'gh pr merge 7 --repo o/r' origin" "git grep -O'sh -c \"gh pr merge 7 --repo o/r\"' foo" \
         "sed -n 1p f -e 'e gh pr merge 7 --repo o/r'" "sed -n '1e gh pr merge 7 --repo o/r' x" \
         "cd .git/hooks && echo 'gh pr merge 7 --repo o/r' > pre-commit && cd ../.. && git commit -m x" \
         "D=.git; echo 'gh pr merge 7 --repo o/r' > \$D/hooks/pre-commit; git commit -m x" \
         "cat > .husky/pre-commit <<'EOF'${NL}gh pr merge 7 --repo o/r${NL}EOF" \
         "echo 'gh pr merge 7 --repo o/r' | tee .git/hooks/pre-commit" \
         "D=.git/hooks; echo 'gh pr merge 7 --repo o/r' > \$D/post-checkout; git status" \
         "echo 'gh pr merge 7 --repo o/r' > \$X/post-checkout; git status" \
         "echo '--pre=sh' > \$S/rg.md; echo 'gh pr merge 7 --repo o/r' > \$S/x.txt; RIPGREP_CONFIG_PATH=\$S/rg.md rg . \$S/x.txt" \
         "echo 'import os; os.system(\"gh pr merge 7 --repo o/r\")' > x.py; cat <<EOF${NL}\$(python3 x.py)${NL}EOF${NL}python3(){ :; }" \
         "f(){ python3 -c \"\$1\"; }; f 'import os; os.system(\"gh pr merge 7 --repo o/r\")'" \
         "f 'import os; os.system(\"gh pr merge 7 --repo o/r\")'; f(){ :; }" \
         "echo 'gh pr merge 7 --repo o/r' > x.sh; case a in b) :;; \$(sh<x.sh)) :;; esac" \
         "echo 'gh pr merge 7 --repo o/r' > x.sh; case a in b) :;; esac; sh<x.sh" \
         "# a comment (with parens); 'quote${NL}python3 -c 'import os; os.system(\"gh pr merge 7 --repo o/r\")'" \
         "echo x # comment${NL}gh pr merge 7 --repo o/r --match-head-commit $SHA" \
         "x='a[\$(gh pr merge 7 --repo o/r)]'; exit \$((x))" \
         "python3 <<EOF${NL}import os; os.system(\"gh pr mer\\${NL}ge 7 --repo o/r\")${NL}EOF" \
         "python3 <<'EOF'${NL}import os; os.system(\"gh pr mer\\${NL}ge 7 --repo o/r\")${NL}EOF" \
         "python3 -c 'import os; os.system(\"gh pr mer\\${NL}ge 7 --repo o/r\")'" \
         "node -e 'require(\"child_process\").execSync(\"gh pr mer\\${NL}ge 7 --repo o/r\")'" \
         "echo 'gh pr mer\\${NL}ge 7 --repo o/r' | python3 -" \
         "printf '#!/bin/sh\\ngh pr merge 7 --repo o/r\\n' | uniq - .git/hooks/pre-commit && git commit --allow-empty -m x" \
         "printf '#!/bin/sh\\ngh pr merge 7 --repo o/r\\n' | sort -o .git/hooks/pre-commit && git commit --allow-empty -m x" \
         "printf '#!/bin/sh\\ngh pr merge 7 --repo o/r\\n' | sort --output=.git/hooks/pre-commit; git commit -m x" \
         "printf 'gh pr merge 7 --repo o/r\\n' > x.sh; git grep --no-index --op=sh -e gh x.sh" \
         "printf 'gh pr merge 7 --repo o/r\\n' > x.sh; git grep --no-index --ope=sh -e gh x.sh" \
         "git log -1 --format='gh pr merge 7 --repo o/r' --outp=.git/hooks/pre-commit" \
         "P=repos/o/r/pulls/7/merge ; gh api -X PUT \$P" "P=repos/o/r/pulls/7; gh api -X PUT \$P/merge" \
         "M=merge; echo 'gh pr merge is text'; gh api -X PUT repos/o/r/pulls/7/\$M" \
         "N=7; echo 'gh pr merge is text'; gh api -X PUT repos/o/r/pulls/\$N/merge" \
         "R='o/r/pulls/7/merge?a='; echo 'gh pr merge is text'; gh api -X PUT repos/\$R/milestones/9" \
         "R=\$(cat r.txt); echo 'gh pr merge is text'; gh api -X PUT repos/\$R/milestones/9" \
         "echo 'gh pr merge is text'; gh api -X PUT 'repos/{owner}/{repo}/{branch}'" \
         "echo 'gh pr merge is text'; gh api -X PUT repos/o/r/pulls/7/\$(echo x)" \
         "echo 'gh pr merge 7 --repo o/r' > q.txt; gh api graphql -F query=@q.txt" \
         "R=o/r; R+=/pulls/7/merge?a=; gh api -X PUT repos/\$R/milestones/9" \
         "R=o/r; R+='/pulls/7/merge?a='; gh api -X PUT repos/\$R/milestones/9" \
         "R=o/r; R[0]=o/r/pulls/7/merge?a=; gh api -X PUT repos/\$R/milestones/9" \
         "R=o/r; declare R=o/r/pulls/7/merge?a=; gh api -X PUT repos/\$R/milestones/9" \
         "R=o/r; read R <<< 'o/r/pulls/7/merge?a='; gh api -X PUT repos/\$R/milestones/9" \
         "R=o/r; printf -v R %s 'o/r/pulls/7/merge?a='; gh api -X PUT repos/\$R/milestones/9" \
         "R=o/r; for R in o/r/pulls/7/merge?a=; do gh api -X PUT repos/\$R/milestones/9; done" \
         "f(){ R=o/r/pulls/7/merge?a=; }; R=o/r; f; gh api -X PUT repos/\$R/milestones/9" \
         "R=o/r; eval 'R=o/r/pulls/7/merge?a='; gh api -X PUT repos/\$R/milestones/9" \
         "R=o/r; : \${R:=x} 'gh pr merge is text'; unset R; gh api -X PUT repos/\$R/milestones/9" \
         "R=o/r; declare -n ref=R; ref=o/r/pulls/7/merge?a=; gh api -X PUT repos/\$R/milestones/9" \
         "R=o/r; mapfile -t R <<< 'o/r/pulls/7/merge?a='; gh api -X PUT repos/\$R/milestones/9" \
         "A=pulls/7; B=merge; gh api -X PUT repos/o/r/\$A/\$B" "B=merge; A=pulls/7; gh api -X PUT repos/o/r/\$A/\$B" \
         "A=pulls/7; B=merge; gh api --method=PUT repos/o/r/\$A/\$B" "A=pulls/7; B=merge; gh api repos/o/r/\$A/\$B -f x=y" \
         "M=PUT; B=merge; gh api -X \$M repos/o/r/pulls/7/\$B" "B=merges; gh api repos/o/r/\$B -f base=main -f head=x" \
         "for B in merge; do gh api -X PUT repos/o/r/pulls/7/\$B; done" \
         "B=mergeable; gh api -X PUT repos/o/r/pulls/7/\${B%able}" \
         "B=merge; gh api -H 'X-HTTP-Method-Override: PUT' repos/o/r/pulls/7/\$B" \
         "B=merge; gh api --header=x-http-method-override:PUT repos/o/r/pulls/7/\$B" \
         "B=( 'merge' ); gh api -X PUT repos/o/r/pulls/7/\$B" "B=(merge); gh api -X PUT repos/o/r/pulls/7/\$B" \
         "B=(x); B+=(merge); gh api -X PUT repos/o/r/pulls/7/\${B[1]}" \
         "f() { gh api -X PUT repos/o/r/pulls/7/\$B; }; B=merge; f" \
         "for i in 1 2; do gh api -X PUT repos/o/r/pulls/7/\$B; B=merge; done" \
         "f() { gh api -X PUT repos/o/r/pulls/7/\$1; }; f merge" \
         "B=mer\\${NL}ge; gh api -X PUT repos/o/r/pulls/7/\$B" "B=\"mer\\${NL}ge\"; gh api -X PUT repos/o/r/pulls/7/\$B" \
         "f() { gh api -X PUT repos/o/r/pulls/7/\$1; }; f mer\\${NL}ge" \
         "for B in mer\\${NL}ge; do gh api -X PUT repos/o/r/pulls/7/\$B; done" \
         "B=me\\rge; gh api -X PUT repos/o/r/pulls/7/\$B" "B=m\"er\"ge; gh api -X PUT repos/o/r/pulls/7/\$B" \
         "B=mer''ge; gh api -X PUT repos/o/r/pulls/7/\$B" "gh api -X PUT repos/o/r/pulls/7/me\\rge" \
         "for n in 72 73; do gh api -X PATCH \"repos/{owner}/{repo}/issues/\$n\" -F body=@f.md; done; python3 -c \"print('merge #76 then close')\"" \
         "cat > \$S/pr-body.md <<EOF${NL}this PR is a merge of two fixes${NL}EOF${NL}gh api -X PATCH repos/\$R/pulls/312 -F body=@\$S/pr-body.md" \
         "gh pr view 7 --json mergeable; for n in 394 397; do gh api -X PATCH repos/o/r/issues/\$n -f state=closed; done" \
         "for n in 72 73; do gh api -X PATCH repos/o/r/issues/\$n -F body=@f.md; done; echo 'PR #247 (merged)'"; do
  t "#680 design review: a command that could run merge text is denied: $c"; g "$c"; assert_rc 2
done
# A quote inside a regex was read as unclosed by the old splitter (denied); the new one reads it like the
# shell, so this grep is allowed now (one of the two old-deny/new-allow shapes of the #680 replay).
reset
t "#680: a grep whose regex holds a quoted gh token pattern is allowed"
g "grep -anEi -e 'gh[pousr]_[A-Za-z0-9]{36}|-----BEGIN [A-Z ]*PRIVATE KEY' -e \"it's\" docs/hooks.md"
if [ "$RC" = 0 ] && [ -z "$OUT" ]; then pass; else fail "rc=$RC out=$OUT"; fi
# A write of merge text to a hook file under a variable directory is still denied.
t "#680: merge text written to \$D/hooks/pre-commit or \$SCRATCH/.git/config is denied"
g "echo 'gh pr merge 7 --repo o/r' > \$SCRATCH/.git/config && git status"; assert_rc 2
reset; setbase main
t "#680: a merge-like --subject on the one plain merge is still put to the owner"; g "$MA --subject \"gh: merge it\""; assert_ask "Merge PR #7 of o/r into main"
# Issue #675 stays open on purpose: a merge that is encoded at run time holds no merge-like text, and text
# matching cannot see it. These tests document the limit; branch protection on main is the backstop.
reset
for c in "python3 -c \"import os; os.system('g'+'h p'+'r mer'+'ge 7 --repo o/r')\"" \
         "python3 -c \"import os,base64; os.system(base64.b64decode('Z2ggcHIgbWVyZ2UgNw==').decode())\"" \
         "B=\$(printf 'm%sge' er); A=pulls/7; gh api -X PUT repos/o/r/\$A/\$B" \
         "A=pulls/7; B=mer; gh api -X PUT repos/o/r/\$A/\${B}ge"; do
  t "#675 (known limit, not closed by #680): a merge encoded at run time is not seen: $c"; g "$c"; assert_rc 0
done

reset; setbase feat/x; touch "$D/slow"
t "a stalled gh is killed and the merge is denied within the time budget"
s=$SECONDS; g "$M"; e=$((SECONDS - s))
if [ "$RC" = 2 ] && [ "$e" -lt 20 ]; then pass; else fail "rc=$RC took ${e}s out=$OUT"; fi
rm -f "$D/slow"

# Probe (opt-in: it starts real `claude -p` sessions, needs a login and costs tokens): what Claude Code does
# with permissionDecision "ask" under default, auto and bypassPermissions. Run with RUN_ASK_PROBE=1.
# Result (ADR 0008, 0009): in each mode the Bash call is NOT run; headless, nobody can answer the prompt.
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
