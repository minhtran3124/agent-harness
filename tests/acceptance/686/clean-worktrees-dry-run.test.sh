#!/bin/bash
# Acceptance tests for #686: clean-worktrees.sh dry run (CLEAN_DRY_RUN=1).
# Outside-in only: each case builds its own temp repo with a bare remote, runs the script in one
# mode (by hand, SessionStart, PostToolUse) and checks refs, `git worktree list`, the worktree
# admin dir, .git/config, the remote refs and the printed lines.
# Owner answer (dry-run scope): "Skip every write (Recommended)" = No delete, remove, prune, config
# write or push. Prints 'would recreate <remote>/<name>' instead of pushing. `git fetch --prune`
# still runs, because it only updates remote-tracking refs.
# shellcheck source=../../lib.sh
source "$(dirname "$0")/../../lib.sh"

SCRIPT="$ROOT/plugins/harness/hooks/clean-worktrees.sh"
GIT=$(command -v git)

# A PATH with every command of the current PATH except gh (for the no-gh rules).
NOGH=$(mktemp -d); _CLEANUP_DIRS+=("$NOGH")
IFS=: read -r -a _pdirs <<< "$PATH"
for _d in "${_pdirs[@]}"; do
  [ -d "$_d" ] || continue
  for _f in "$_d"/*; do
    _n=${_f##*/}
    [ "$_n" = gh ] && continue
    [ -x "$_f" ] && [ ! -e "$NOGH/$_n" ] && ln -s "$_f" "$NOGH/$_n" 2>/dev/null
  done
done

g() { "$GIT" -C "$MAIN" "$@"; }

new_base() {
  BASE=$(cd "$(mktemp -d)" && pwd -P); _CLEANUP_DIRS+=("$BASE")
  MAIN="$BASE/main"; REM="$BASE/remote.git"; STUB="$BASE/stub"; mkdir -p "$STUB"
  "$GIT" init -q --bare -b main "$REM"
  "$GIT" init -q -b main "$MAIN"; g config user.email t@t; g config user.name t
  g commit -q --allow-empty -m base
  g remote add r1 "$REM"; g push -q r1 main; g fetch -q r1
}

# Fixture G (gh present):
#   feat     in worktree $BASE/wt-feat, merged, a merged PR (7) has its exact tip -> chosen
#   develop  merged, merged PR at its tip -> protected name, kept
#   keepme   merged, merged PR at its tip -> CLEAN_KEEP name, kept
#   stale    in worktree $BASE/wt-stale whose directory is gone (prunable), not merged
#   automation  CLEAN_RECREATE name missing on the remote
build_g() {
  new_base
  WT="$BASE/wt-feat"
  g worktree add -q -b feat "$WT"; "$GIT" -C "$WT" commit -q --allow-empty -m work
  g merge -q --no-ff feat -m m-feat
  local b
  for b in develop keepme; do
    g checkout -q -b "$b"; g commit -q --allow-empty -m "w-$b"; g checkout -q main
    g merge -q --no-ff "$b" -m "m-$b"
  done
  g worktree add -q -b stale "$BASE/wt-stale"; "$GIT" -C "$BASE/wt-stale" commit -q --allow-empty -m stale
  rm -rf "$BASE/wt-stale"
  g push -q r1 main; g fetch -q r1
  cat > "$STUB/gh" <<EOF
#!/bin/sh
case "\$1 \$2" in
  "pr view") case "\$3" in 7) echo '{"state":"MERGED","headRefName":"feat"}' ;; *) exit 1 ;; esac ;;
  "pr list") case "\$4" in
      feat) echo $(g rev-parse feat) ;;
      develop) echo $(g rev-parse develop) ;;
      keepme) echo $(g rev-parse keepme) ;;
    esac ;;
esac
exit 0
EOF
  chmod +x "$STUB/gh"
  USE_GH=1
}

# Fixture N (no gh):
#   gone1        pushed with upstream, merged into r1/main, deleted on the remote -> upstream-gone rule
#   release-2.0  same as gone1 but a protected name -> kept
#   worktree-a   agent branch, not checked out, tip contained in r1/other -> worktree-* rule
build_n() {
  new_base
  local b
  for b in gone1 release-2.0; do
    g checkout -q -b "$b"; g commit -q --allow-empty -m "w-$b"
    g push -q -u r1 "$b" 2>/dev/null; g checkout -q main
    g merge -q --no-ff "$b" -m "m-$b"; g push -q r1 main
    "$GIT" -C "$REM" branch -q -D "$b"
  done
  g checkout -q -b worktree-a main; g commit -q --allow-empty -m wa; g checkout -q main
  g push -q r1 worktree-a:refs/heads/other; g fetch -q r1
  USE_GH=0
}

# run_mode <by-hand|SessionStart|PostToolUse> <dry 0|1>: sets OUT (stdout), ERR, RC and LINES
# (stdout by hand, additionalContext in a hook mode).
run_mode() {
  local mode=$1 dry=$2 path arg=() input=/dev/null
  if [ "$USE_GH" = 1 ]; then path="$STUB:$PATH"; else path="$NOGH"; fi
  local envs=(CLEAN_REMOTE=r1 CLEAN_RECREATE=automation CLEAN_KEEP=keepme PATH="$path")
  [ "$dry" = 1 ] && envs+=(CLEAN_DRY_RUN=1)
  [ "$mode" != by-hand ] && arg=("$mode")
  if [ "$mode" = PostToolUse ]; then
    printf '%s' '{"tool_input":{"command":"gh pr merge 7"}}' > "$BASE/payload.json"; input="$BASE/payload.json"
  fi
  OUT=$(cd "$MAIN" && env -u CLAUDE_PROJECT_DIR -u CLEAN_DRY_RUN -u CLEAN_STRICT -u CLEAN_BUDGET \
        -u CLEAN_KEEP -u CLEAN_RECREATE -u CLEAN_REMOTE "${envs[@]}" "$BASH" "$SCRIPT" "${arg[@]}" <"$input" 2>"$BASE/stderr")
  RC=$?; ERR=$(cat "$BASE/stderr")
  if [ "$mode" = by-hand ]; then LINES=$OUT
  else LINES=$(printf '%s' "$OUT" | jq -r '.hookSpecificOutput.additionalContext // empty' 2>/dev/null); fi
}

heads()     { g for-each-ref --format='%(refname) %(objectname)' refs/heads; }
wtlist()    { g worktree list --porcelain; }
admin()     { ls -1A "$MAIN/.git/worktrees" 2>/dev/null; }
config()    { cat "$MAIN/.git/config"; }
remheads()  { "$GIT" -C "$REM" for-each-ref --format='%(refname) %(objectname)' refs/heads; }
names()     { g for-each-ref --format='%(refname:short)' refs/heads | LC_ALL=C sort; }
remnames()  { "$GIT" -C "$REM" for-each-ref --format='%(refname:short)' refs/heads | LC_ALL=C sort; }
# live worktree paths (directory exists), relative to $BASE
livewt()    { wtlist | sed -n 's/^worktree //p' | while IFS= read -r p; do [ -d "$p" ] && printf '%s\n' "${p#"$BASE"/}"; done | LC_ALL=C sort; }

# Sets from the dry-run lines (worktree paths relative to $BASE)
would_branches() { printf '%s\n' "$LINES" | sed -n 's/^would delete branch //p' | LC_ALL=C sort; }
would_wts()      { printf '%s\n' "$LINES" | sed -n 's/^would remove worktree //p' | while IFS= read -r p; do printf '%s\n' "${p#"$BASE"/}"; done | LC_ALL=C sort; }
would_recreate() { printf '%s\n' "$LINES" | sed -n 's/^would recreate //p' | LC_ALL=C sort; }
has_line()       { printf '%s\n' "$LINES" | grep -qFx -- "$1"; }

# real_sets <fixture> <mode>: build the fixture, run without CLEAN_DRY_RUN, set REAL_D (deleted
# branches), REAL_W (removed worktrees, relative), REAL_R (recreated remote branches as r1/<name>).
real_sets() {
  "build_$1"
  local hb wb rb
  hb=$(names); wb=$(livewt); rb=$(remnames)
  run_mode "$2" 0
  REAL_D=$(comm -23 <(printf '%s\n' "$hb") <(names) | sed '/^$/d')
  REAL_W=$(comm -23 <(printf '%s\n' "$wb") <(livewt) | sed '/^$/d')
  REAL_R=$(comm -13 <(printf '%s\n' "$rb") <(remnames) | sed '/^$/d; s|^|r1/|')
}

# dry_case <fixture> <mode>: build the fixture, snapshot, dry run, set the B_*/A_* snapshots.
dry_case() {
  "build_$1"
  B_HEADS=$(heads); B_WT=$(wtlist); B_ADMIN=$(admin); B_CONFIG=$(config); B_REM=$(remheads)
  run_mode "$2" 1
  A_HEADS=$(heads); A_WT=$(wtlist); A_ADMIN=$(admin); A_CONFIG=$(config); A_REM=$(remheads)
}

# ---------------------------------------------------------------------------------------------
# AC1: "With `CLEAN_DRY_RUN=1` in the environment, the script removes no worktree and deletes no
# branch, in every mode (by hand, `SessionStart`, `PostToolUse`)."
for fx in g n; do
  for mode in by-hand SessionStart PostToolUse; do
    [ "$fx" = n ] && [ "$mode" = PostToolUse ] && continue  # PostToolUse needs gh
    t "AC1: CLEAN_DRY_RUN=1 removes no worktree and deletes no branch ($mode, fixture $fx)"
    dry_case "$fx" "$mode"
    if [ "$RC" = 0 ] && [ "$A_HEADS" = "$B_HEADS" ] && [ "$A_WT" = "$B_WT" ] && { [ "$fx" = n ] || [ -d "$WT" ]; }; then pass
    else fail "rc=$RC heads-before=[$B_HEADS] heads-after=[$A_HEADS] wt-after=[$A_WT] out=$OUT err=$ERR"; fi
  done
done

# AC1 + owner answer: "No delete, remove, prune, config write or push."
for fx in g n; do
  for mode in by-hand SessionStart PostToolUse; do
    [ "$fx" = n ] && [ "$mode" = PostToolUse ] && continue
    t "AC1 (owner: skip every write): CLEAN_DRY_RUN=1 makes no prune, no config write and no push ($mode, fixture $fx)"
    dry_case "$fx" "$mode"
    if [ "$A_ADMIN" = "$B_ADMIN" ] && [ "$A_CONFIG" = "$B_CONFIG" ] && [ "$A_REM" = "$B_REM" ]; then pass
    else fail "admin [$B_ADMIN]->[$A_ADMIN] config-changed=$([ "$A_CONFIG" = "$B_CONFIG" ] || echo yes) remote [$B_REM]->[$A_REM] out=$OUT"; fi
  done
done

# ---------------------------------------------------------------------------------------------
# AC2: "For each branch it would delete, it prints one line `would delete branch <name>`, and for
# each worktree it would remove, one line `would remove worktree <path>`. By hand these lines go to
# stdout; in hook modes they go where the script already reports (the SessionStart summary)."
t "AC2: by hand, the would-delete and would-remove lines go to stdout"
dry_case g by-hand
if has_line "would delete branch feat" && has_line "would remove worktree $WT" \
   && ! printf '%s' "$ERR" | grep -q '^would '; then pass; else fail "stdout=[$OUT] stderr=[$ERR]"; fi

t "AC2: by hand, one would-delete line per chosen branch without gh (gone1, worktree-a)"
dry_case n by-hand
if has_line "would delete branch gone1" && has_line "would delete branch worktree-a" \
   && [ "$(printf '%s\n' "$LINES" | grep -cFx 'would delete branch gone1')" = 1 ]; then pass; else fail "stdout=[$OUT] stderr=[$ERR]"; fi

t "AC2: SessionStart puts the lines in the additionalContext summary"
dry_case g SessionStart
if [ "$(printf '%s' "$OUT" | jq -r .hookSpecificOutput.hookEventName 2>/dev/null)" = SessionStart ] \
   && printf '%s\n' "$LINES" | head -1 | grep -q '^Worktree cleanup:' \
   && has_line "would delete branch feat" && has_line "would remove worktree $WT"; then pass; else fail "out=$OUT"; fi

t "AC2: SessionStart without gh lists gone1 and worktree-a in additionalContext"
dry_case n SessionStart
if has_line "would delete branch gone1" && has_line "would delete branch worktree-a"; then pass; else fail "out=$OUT"; fi

t "AC2: PostToolUse (gh pr merge 7) puts the lines in additionalContext"
dry_case g PostToolUse
if [ "$(printf '%s' "$OUT" | jq -r .hookSpecificOutput.hookEventName 2>/dev/null)" = PostToolUse ] \
   && printf '%s\n' "$LINES" | grep -q '^Worktree cleanup:' \
   && has_line "would delete branch feat" && has_line "would remove worktree $WT"; then pass; else fail "out=$OUT"; fi

# Owner answer: "Prints 'would recreate <remote>/<name>' instead of pushing."
t "AC2 (owner): by hand, CLEAN_RECREATE prints 'would recreate r1/automation' and pushes nothing"
dry_case g by-hand
if has_line "would recreate r1/automation" && ! "$GIT" -C "$REM" rev-parse -q --verify refs/heads/automation >/dev/null; then pass
else fail "stdout=[$OUT] remote=[$(remheads)]"; fi

# ---------------------------------------------------------------------------------------------
# AC3: "Everything else it does today stays as it is: the same branches are chosen, the protected
# names are still kept, and without `CLEAN_DRY_RUN` the behavior is unchanged."
for fx in g n; do
  for mode in by-hand SessionStart PostToolUse; do
    [ "$fx" = n ] && [ "$mode" = PostToolUse ] && continue
    t "AC3: a dry run chooses the same branches, worktrees and recreates as a real run on an identical repo ($mode, fixture $fx)"
    real_sets "$fx" "$mode"
    dry_case "$fx" "$mode"
    DB=$(would_branches); DW=$(would_wts); DR=$(would_recreate)
    if [ -n "$REAL_D" ] && [ "$DB" = "$REAL_D" ] && [ "$DW" = "$REAL_W" ] && [ "$DR" = "$REAL_R" ]; then pass
    else fail "real: D=[$REAL_D] W=[$REAL_W] R=[$REAL_R]; dry: D=[$DB] W=[$DW] R=[$DR]; dry out=$OUT"; fi
  done
done

for mode in by-hand SessionStart PostToolUse; do
  t "AC3: a dry run still keeps the protected names develop and the CLEAN_KEEP name keepme ($mode)"
  dry_case g "$mode"
  if [ -n "$LINES" ] && ! has_line "would delete branch develop" && ! has_line "would delete branch keepme" && ! has_line "would delete branch main"; then pass
  else fail "lines=[$LINES]"; fi
done

for mode in by-hand SessionStart; do
  t "AC3: a dry run without gh keeps the protected name release-2.0 ($mode)"
  dry_case n "$mode"
  if [ -n "$LINES" ] && ! has_line "would delete branch release-2.0"; then pass; else fail "lines=[$LINES]"; fi
done

# Unchanged behavior without CLEAN_DRY_RUN (these may already pass today).
t "AC3: without CLEAN_DRY_RUN, by hand still deletes feat, removes its worktree, keeps develop/keepme and recreates automation"
build_g; run_mode by-hand 0
if ! g rev-parse -q --verify refs/heads/feat >/dev/null && [ ! -d "$WT" ] \
   && g rev-parse -q --verify refs/heads/develop >/dev/null && g rev-parse -q --verify refs/heads/keepme >/dev/null \
   && [ "$("$GIT" -C "$REM" rev-parse -q --verify refs/heads/automation)" = "$("$GIT" -C "$REM" rev-parse refs/heads/main)" ] \
   && ! printf '%s' "$OUT" | grep -q '^would '; then pass; else fail "out=$OUT err=$ERR"; fi

t "AC3: without CLEAN_DRY_RUN, SessionStart still deletes feat and removes its worktree"
build_g; run_mode SessionStart 0
if ! g rev-parse -q --verify refs/heads/feat >/dev/null && [ ! -d "$WT" ] && has_line "removed feat and worktree $WT"; then pass; else fail "out=$OUT"; fi

t "AC3: without CLEAN_DRY_RUN, PostToolUse still deletes feat and removes its worktree"
build_g; run_mode PostToolUse 0
if ! g rev-parse -q --verify refs/heads/feat >/dev/null && [ ! -d "$WT" ]; then pass; else fail "out=$OUT"; fi

t "AC3: without CLEAN_DRY_RUN and without gh, gone1 and worktree-a are deleted and release-2.0 is kept"
build_n; run_mode by-hand 0
if ! g rev-parse -q --verify refs/heads/gone1 >/dev/null && ! g rev-parse -q --verify refs/heads/worktree-a >/dev/null \
   && g rev-parse -q --verify refs/heads/release-2.0 >/dev/null; then pass; else fail "out=$OUT"; fi

# ---------------------------------------------------------------------------------------------
# AC4: "The script header and `docs/hooks.md` describe the new setting."
t "AC4: the script header (leading comment block) describes CLEAN_DRY_RUN"
HEADER=$(awk 'NR==1 && /^#!/ {next} /^#/ {print; next} {exit}' "$SCRIPT")
if printf '%s' "$HEADER" | grep -q 'CLEAN_DRY_RUN'; then pass; else fail "no CLEAN_DRY_RUN in the header comment"; fi

t "AC4: docs/hooks.md describes CLEAN_DRY_RUN in the clean-worktrees.sh section"
SECTION=$(awk '/^### `clean-worktrees.sh`/ {on=1; print; next} on && /^### / {exit} on {print}' "$ROOT/docs/hooks.md")
if printf '%s' "$SECTION" | grep -q 'CLEAN_DRY_RUN'; then pass; else fail "no CLEAN_DRY_RUN in the clean-worktrees.sh section of docs/hooks.md"; fi

finish
