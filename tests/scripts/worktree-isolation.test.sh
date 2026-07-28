#!/bin/bash
source "$(dirname "$0")/../../tests/lib.sh"
SCRIPT="skills/using-git-worktrees/scripts/detect-isolation.sh"

t "main checkout is not reported as isolated"
repo=$(new_repo)
OUT=$(bash "$ROOT/$SCRIPT" "$repo"); RC=$?
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q '"mode":"main-worktree"' && echo "$OUT" | grep -q '"isolated":false'; then pass; else fail "$OUT"; fi

t "linked worktree is reported as isolated"
linked=$(mktemp -d); rmdir "$linked"
git -C "$repo" commit --allow-empty -qm seed
git -C "$repo" worktree add -q -b feat/isolation "$linked"
OUT=$(bash "$ROOT/$SCRIPT" "$linked"); RC=$?
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q '"mode":"linked-worktree"' && echo "$OUT" | grep -q '"isolated":true'; then pass; else fail "$OUT"; fi
git -C "$repo" worktree remove --force "$linked"

t "non-git input fails with a useful error"
empty=$(mktemp -d)
OUT=$(bash "$ROOT/$SCRIPT" "$empty" 2>&1); RC=$?
if [ "$RC" -eq 2 ] && echo "$OUT" | grep -q 'not a git worktree'; then pass; else fail "rc=$RC $OUT"; fi
rm -rf "$empty"

finish
