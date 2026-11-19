#!/bin/bash
# Acceptance tests for #686: clean-worktrees dry run (CLEAN_DRY_RUN=1).
# Every case builds its own temp repo with a bare remote r1 and a gh stub that reports a merged PR
# at the exact tip of a branch, then runs plugins/harness/hooks/clean-worktrees.sh from outside.
source "$(dirname "$0")/../lib.sh"

HOOK="$ROOT/plugins/harness/hooks/clean-worktrees.sh"

# mk: fresh $MAIN (on main) with remote r1 ($REM) and a gh stub dir $STUB.
# The gh stub answers `gh pr view <n>` with a merged PR whose head is $STUB/head7 (for PR 7), and
# `gh pr list --head <branch> ...` with the current tip of <branch> (a merged PR at the exact tip).
mk() {
  MAIN=$(mktemp -d); REM=$(mktemp -d); STUB=$(mktemp -d); _CLEANUP_DIRS+=("$MAIN" "$REM" "$STUB")
  git init -q --bare -b main "$REM"
  git -C "$MAIN" init -q -b main; git -C "$MAIN" config user.email t@t; git -C "$MAIN" config user.name t
  git -C "$MAIN" commit -q --allow-empty -m base
  git -C "$MAIN" remote add r1 "$REM"; git -C "$MAIN" push -q r1 main; git -C "$MAIN" fetch -q r1
  cat > "$STUB/gh" <<EOF
#!/bin/sh
case "\$1 \$2" in
  "pr view")
    case "\$3" in
      7) printf '{"state":"MERGED","headRefName":"%s"}\n' "\$(cat "$STUB/head7" 2>/dev/null)" ;;
      *) exit 1 ;;
    esac ;;
  "pr list") git -C "$MAIN" rev-parse -q --verify "refs/heads/\$4" ;;
esac
exit 0
EOF
  chmod +x "$STUB/gh"
}
# merged_wt <branch>: a branch with one commit, merged into main, checked out in its own worktree.
# Sets WTP to the worktree path as git lists it.
merged_wt() {
  local p="$MAIN-wt-${1//\//_}"; _CLEANUP_DIRS+=("$p")
  git -C "$MAIN" worktree add -q -b "$1" "$p" main
  git -C "$p" commit -q --allow-empty -m "w-$1"
  git -C "$MAIN" merge -q --no-ff "$1" -m "m-$1"
  WTP=$(git -C "$MAIN" worktree list --porcelain | awk -v b="refs/heads/$1" '/^worktree /{w=substr($0,10)} $0=="branch " b {print w}')
}
# merged_br <branch>: a branch with one commit merged into main, not checked out anywhere.
merged_br() {
  git -C "$MAIN" branch -q "$1" main; git -C "$MAIN" checkout -q "$1"
  git -C "$MAIN" commit -q --allow-empty -m "w-$1"; git -C "$MAIN" checkout -q main
  git -C "$MAIN" merge -q --no-ff "$1" -m "m-$1"
}
has() { git -C "$MAIN" rev-parse -q --verify "refs/heads/$1" >/dev/null; }
# runh <cwd> <mode> [VAR=value ...]: stdout -> OUT, stderr -> ERR, exit -> RC; stdin is /dev/null
runh() {
  local cwd=$1 mode=$2; shift 2
  local e; e=$(mktemp); _CLEANUP_DIRS+=("$e")
  # shellcheck disable=SC2086
  OUT=$(cd "$cwd" && env CLEAN_REMOTE=r1 "$@" PATH="$STUB:$PATH" bash "$HOOK" $mode </dev/null 2>"$e"); RC=$?
  ERR=$(cat "$e")
}
# runp <cmd> [VAR=value ...]: PostToolUse mode with a Bash payload for <cmd>, run from $MAIN
runp() {
  local cmd=$1; shift
  OUT=$(cd "$MAIN" && jq -n --arg c "$cmd" '{tool_name:"Bash",tool_input:{command:$c}}' \
    | env CLEAN_REMOTE=r1 "$@" PATH="$STUB:$PATH" bash "$HOOK" PostToolUse 2>/dev/null); RC=$?
}
# lines: normalise each output line (drop leading blanks or a "- " bullet, trailing blanks)
lines() { printf '%s\n' "$1" | sed -E 's/^[[:space:]]*(- )?//; s/[[:space:]]+$//'; }
nline() { lines "$1" | grep -cFx "$2"; }               # count of exact lines
ctx() { printf '%s' "$1" | jq -r '.hookSpecificOutput.additionalContext // empty' 2>/dev/null; }
# has_branch_line <text> <name>: "would delete branch <name>" not followed by more name characters
has_branch_line() { printf '%s\n' "$1" | grep -qE "would delete branch $(printf '%s' "$2" | sed 's/[.[\*^$/]/\\&/g')([^-A-Za-z0-9_./]|$)"; }

# ---- AC1 / AC2: by hand ---------------------------------------------------------------------------
# AC1: "With CLEAN_DRY_RUN=1, a run by hand in a temp repo with a merged branch checked out in a
# worktree leaves both the branch and the worktree in place and exits 0."
mk; merged_wt feat
t "AC1: by hand with CLEAN_DRY_RUN=1 keeps the merged branch and its worktree, exit 0"
runh "$MAIN" "" CLEAN_DRY_RUN=1
if [ "$RC" = 0 ] && has feat && [ -d "$WTP" ]; then pass; else fail "rc=$RC branch=$(has feat && echo kept || echo GONE) wt=$([ -d "$WTP" ] && echo kept || echo GONE) out=$OUT err=$ERR"; fi

# AC2: "In that run, stdout has the line `would remove worktree <path>` for the worktree and the line
# `would delete branch <name>` for the branch, one line each per candidate."
t "AC2: by hand, stdout has exactly one 'would remove worktree <path>' line and one 'would delete branch feat' line"
nw=$(nline "$OUT" "would remove worktree $WTP"); nb=$(nline "$OUT" "would delete branch feat")
if [ "$nw" = 1 ] && [ "$nb" = 1 ]; then pass; else fail "worktree lines=$nw branch lines=$nb stdout=$OUT"; fi

mk; merged_wt feat; merged_wt feat2; WTP1=$(git -C "$MAIN" worktree list --porcelain | awk '/^worktree /{w=substr($0,10)} $0=="branch refs/heads/feat" {print w}')
t "AC2: two candidates get one 'would remove worktree' and one 'would delete branch' line each"
runh "$MAIN" "" CLEAN_DRY_RUN=1
if [ "$(nline "$OUT" "would remove worktree $WTP1")" = 1 ] && [ "$(nline "$OUT" "would remove worktree $WTP")" = 1 ] \
   && [ "$(nline "$OUT" "would delete branch feat")" = 1 ] && [ "$(nline "$OUT" "would delete branch feat2")" = 1 ] \
   && has feat && has feat2; then pass; else fail "rc=$RC stdout=$OUT"; fi

# ---- AC3: hook modes ------------------------------------------------------------------------------
# AC3: "With CLEAN_DRY_RUN=1 in SessionStart mode and in PostToolUse mode (a real `gh pr merge <n>`
# payload), no worktree or branch is removed, and the hookSpecificOutput.additionalContext summary has
# both `would ...` lines."
mk; merged_wt feat
t "AC3: SessionStart with CLEAN_DRY_RUN=1 removes nothing; additionalContext has both 'would' lines"
runh "$MAIN" SessionStart CLEAN_DRY_RUN=1
C=$(ctx "$OUT")
if [ "$RC" = 0 ] && has feat && [ -d "$WTP" ] && printf '%s' "$C" | grep -qF "would remove worktree $WTP" && has_branch_line "$C" feat; then pass
else fail "rc=$RC branch=$(has feat && echo kept || echo GONE) wt=$([ -d "$WTP" ] && echo kept || echo GONE) out=$OUT"; fi

mk; merged_wt feat; printf 'feat' > "$STUB/head7"
t "AC3: PostToolUse 'gh pr merge 7' with CLEAN_DRY_RUN=1 removes nothing; additionalContext has both 'would' lines"
runp 'gh pr merge 7 --squash' CLEAN_DRY_RUN=1
C=$(ctx "$OUT")
if [ "$RC" = 0 ] && has feat && [ -d "$WTP" ] && printf '%s' "$C" | grep -qF "would remove worktree $WTP" && has_branch_line "$C" feat; then pass
else fail "rc=$RC branch=$(has feat && echo kept || echo GONE) wt=$([ -d "$WTP" ] && echo kept || echo GONE) out=$OUT"; fi

# ---- AC4: CLEAN_RECREATE --------------------------------------------------------------------------
# AC4: "With CLEAN_DRY_RUN=1 and a CLEAN_RECREATE name that is missing on the remote (ls-remote exit
# 2), nothing is pushed (the remote still lacks the branch) and the output has
# `would recreate branch <name>`. `git fetch --prune` still runs."
mk
t "AC4: CLEAN_RECREATE name missing on the remote: nothing pushed, output has 'would recreate branch automation'"
runh "$MAIN" "" CLEAN_DRY_RUN=1 CLEAN_RECREATE=automation
if [ "$RC" = 0 ] && ! git -C "$REM" rev-parse -q --verify refs/heads/automation >/dev/null \
   && printf '%s\n%s\n' "$OUT" "$ERR" | grep -qE 'would recreate branch automation([^-A-Za-z0-9_./]|$)'; then pass
else fail "rc=$RC remote automation=$(git -C "$REM" rev-parse -q --verify refs/heads/automation || echo absent) out=$OUT err=$ERR"; fi

mk; git -C "$MAIN" push -q r1 main:refs/heads/gone; git -C "$MAIN" fetch -q r1; git -C "$REM" branch -q -D gone
t "AC4: with CLEAN_DRY_RUN=1, git fetch --prune still runs (a remote-tracking ref deleted on the remote is pruned)"
runh "$MAIN" "" CLEAN_DRY_RUN=1 CLEAN_RECREATE=automation
if ! git -C "$MAIN" rev-parse -q --verify refs/remotes/r1/gone >/dev/null; then pass; else fail "refs/remotes/r1/gone still there; out=$OUT err=$ERR"; fi

# ---- AC5: no simulated refusal --------------------------------------------------------------------
# AC5: "The dry run does not simulate a refusal for a dirty or locked worktree: such a candidate
# still gets the `would remove worktree` and `would delete branch` lines."
mk; merged_wt dirty; DWT=$WTP; echo x > "$DWT/new.txt"; git -C "$DWT" add new.txt
merged_wt locked; LWT=$WTP; git -C "$MAIN" worktree lock "$LWT"
t "AC5: a dirty worktree still gets both 'would' lines in a dry run"
runh "$MAIN" "" CLEAN_DRY_RUN=1
if [ "$(nline "$OUT" "would remove worktree $DWT")" = 1 ] && [ "$(nline "$OUT" "would delete branch dirty")" = 1 ] && [ -f "$DWT/new.txt" ]; then pass; else fail "stdout=$OUT"; fi
t "AC5: a locked worktree still gets both 'would' lines in a dry run"
if [ "$(nline "$OUT" "would remove worktree $LWT")" = 1 ] && [ "$(nline "$OUT" "would delete branch locked")" = 1 ] && [ -d "$LWT" ]; then pass; else fail "stdout=$OUT"; fi

# ---- AC6: same candidates, protections kept -------------------------------------------------------
# AC6: "The dry run picks the same candidates as a real run. Protected names (main, master, develop,
# release/*, release-*, CLEAN_KEEP, the current branch) and the session/live-process worktrees are
# still kept, with no `would ...` line for them."
mk
for b in master develop release/1.0 release-2.0 automation; do merged_br "$b"; done
merged_wt feat; FWT=$WTP
merged_wt cur; SWT=$WTP          # the session's own worktree (cwd of the run)
merged_wt busy; BWT=$WTP         # a worktree another live process uses
(cd "$BWT" && exec sleep 120) & LIVEPID=$!
sleep 1
runh "$SWT" SessionStart CLEAN_DRY_RUN=1 CLEAN_KEEP=automation
C=$(ctx "$OUT")
t "AC6: protected names, CLEAN_KEEP, the current branch and the live-process worktree get no 'would' line in a dry run"
bad=""
for b in main master develop release/1.0 release-2.0 automation cur busy; do has_branch_line "$C" "$b" && bad="$bad $b"; done
for p in "$MAIN" "$SWT" "$BWT"; do printf '%s\n' "$C" | grep -qE "would remove worktree $(printf '%s' "$p" | sed 's/[.[\*^$/]/\\&/g')([^-A-Za-z0-9_./]|$)" && bad="$bad $p"; done
if [ -z "$bad" ] && has_branch_line "$C" feat && printf '%s' "$C" | grep -qF "would remove worktree $FWT"; then pass; else fail "lines for:$bad ctx=$C"; fi
DRY=$(printf '%s\n' "$C" | grep -oE 'would delete branch [^ ;,]+' | sed 's/^would delete branch //' | sort -u | tr '\n' ' ')
t "AC6: the dry run kept every branch and worktree in place"
all_there=1
for b in master develop release/1.0 release-2.0 automation feat cur busy; do has "$b" || all_there=0; done
for p in "$FWT" "$SWT" "$BWT"; do [ -d "$p" ] || all_there=0; done
if [ "$all_there" = 1 ]; then pass; else fail "something was removed in a dry run; out=$OUT"; fi
t "AC6: the dry run names exactly the branches a real run then deletes"
runh "$SWT" SessionStart CLEAN_KEEP=automation
REAL=""
for b in master develop release/1.0 release-2.0 automation feat cur busy; do has "$b" || REAL="$REAL$b
"; done
REAL=$(printf '%s' "$REAL" | sort -u | tr '\n' ' ')
kill "$LIVEPID" 2>/dev/null; wait "$LIVEPID" 2>/dev/null
if [ -n "$DRY" ] && [ "$DRY" = "$REAL" ]; then pass; else fail "dry run: [$DRY] real run deleted: [$REAL]"; fi

# ---- AC7: existing behaviour unchanged ------------------------------------------------------------
# AC7: "Without CLEAN_DRY_RUN (or with a value other than 1), the existing clean-worktrees tests pass
# unchanged."
for v in unset 0 true yes; do
  t "AC7: the existing clean-worktrees tests pass with CLEAN_DRY_RUN=$v"
  if [ "$v" = unset ]; then out=$(env -u CLEAN_DRY_RUN bash "$ROOT/tests/hooks/post-merge-hooks.test.sh" 2>&1); rc=$?
  else out=$(CLEAN_DRY_RUN=$v bash "$ROOT/tests/hooks/post-merge-hooks.test.sh" 2>&1); rc=$?; fi
  if [ "$rc" = 0 ]; then pass; else fail "rc=$rc; $(printf '%s\n' "$out" | grep -E 'FAIL' | head -3 | tr '\n' ' ')"; fi
done

mk; merged_wt feat
t "AC7: by hand with CLEAN_DRY_RUN=0 the merged branch and worktree are removed and no 'would' line is printed"
runh "$MAIN" "" CLEAN_DRY_RUN=0
if ! has feat && [ ! -d "$WTP" ] && ! printf '%s\n' "$OUT" | grep -q 'would '; then pass; else fail "rc=$RC out=$OUT"; fi

# ---- AC8: docs ------------------------------------------------------------------------------------
# AC8: "The script header comment and the docs/hooks.md settings table describe CLEAN_DRY_RUN."
t "AC8: the clean-worktrees.sh header comment describes CLEAN_DRY_RUN"
HEADER=$(awk 'NR==1 && /^#!/ {next} /^#/ {print; next} {exit}' "$HOOK")
if printf '%s' "$HEADER" | grep -qF 'CLEAN_DRY_RUN'; then pass; else fail "no CLEAN_DRY_RUN in the leading comment block"; fi
t "AC8: docs/hooks.md settings table has a CLEAN_DRY_RUN row"
if sed -n '/^### `clean-worktrees.sh`/,/^### /p' "$ROOT/docs/hooks.md" | grep -qE '^\| `CLEAN_DRY_RUN` \|'; then pass; else fail "no | \`CLEAN_DRY_RUN\` | row in the clean-worktrees section"; fi

# ---- AC9: suite and shellcheck --------------------------------------------------------------------
# AC9: "`bash scripts/run-tests.sh` and `bash scripts/check-shellcheck.sh` both exit 0."
t "AC9: scripts/check-shellcheck.sh exits 0"
out=$(cd "$ROOT" && bash scripts/check-shellcheck.sh 2>&1); rc=$?
if [ "$rc" = 0 ]; then pass; else fail "rc=$rc; $(printf '%s\n' "$out" | tail -5 | tr '\n' ' ')"; fi
t "AC9: scripts/run-tests.sh exits 0 and ends with ALL GREEN"
if [ -n "${HARNESS_ACCEPTANCE_NESTED:-}" ]; then skip "nested run"; else
  out=$(cd "$ROOT" && HARNESS_ACCEPTANCE_NESTED=1 bash scripts/run-tests.sh 2>&1); rc=$?
  if [ "$rc" -eq 0 ] && printf '%s\n' "$out" | tail -5 | grep -q 'ALL GREEN'; then pass; else fail "rc=$rc; tail: $(printf '%s\n' "$out" | tail -3 | tr '\n' ' ')"; fi
fi

finish
