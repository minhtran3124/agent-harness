#!/bin/bash
# Regression tests: install-harness.sh must gitignore the derived .claude/ tree.
#
# Why this exists: .claude/ ships four visual-planner .py files. Left untracked, they trip
# hooks/check-untracked-py.sh, which DENIES every `git commit` and `git push` — so a fresh
# consumer installs the harness and is then unable to commit anything. Found by the 2026-07-23
# sandbox walk (specs/slim-skill-surface, Task 5.1). The paired hook fix lives in
# tests/hooks/check-untracked-py.test.sh.
#
# Append-only contract: add the pattern when absent, never rewrite or duplicate existing lines.
source "$(dirname "$0")/../lib.sh"

INSTALL="$ROOT/scripts/install-harness.sh"

install_into() { # install_into <dir>
  ( cd "$1" && bash "$INSTALL" --source "$ROOT" --yes ) >/dev/null 2>&1
}

new_target() { # bare git repo with one commit
  local d
  d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  git -C "$d" init -q -b main
  printf 'x\n' > "$d/a.txt"
  git -C "$d" add -A
  git -C "$d" -c user.email=t@t -c user.name=t commit -qm init >/dev/null
  printf '%s' "$d"
}

t "fresh install creates .gitignore listing .claude/"
d=$(new_target)
install_into "$d"
if [ -f "$d/.gitignore" ] && grep -qE '^\.claude/$' "$d/.gitignore"; then pass
else fail "no .claude/ entry in .gitignore: $(cat "$d/.gitignore" 2>&1)"; fi

t "the deployed .claude/ is actually ignored by git afterwards"
d=$(new_target)
install_into "$d"
if git -C "$d" check-ignore -q .claude; then pass
else fail ".claude/ is still visible to git after install"; fi

t "no untracked .py remains, so the commit gate does not deny"
d=$(new_target)
install_into "$d"
loose=$(git -C "$d" ls-files --others --exclude-standard | grep -E '\.py$' || true)
if [ -z "$loose" ]; then pass; else fail "untracked .py survives install: $loose"; fi

t "re-install does not duplicate the .claude/ entry"
d=$(new_target)
install_into "$d"
install_into "$d"
n=$(grep -cE '^\.claude/$' "$d/.gitignore")
if [ "$n" = "1" ]; then pass; else fail "expected 1 .claude/ line, got $n"; fi

t "an existing .claude entry is respected, not re-appended"
d=$(new_target)
printf 'node_modules/\n.claude\n' > "$d/.gitignore"
install_into "$d"
n=$(grep -cE '^[[:space:]]*/?\.claude/?[[:space:]]*$' "$d/.gitignore")
if [ "$n" = "1" ]; then pass; else fail "expected the pre-existing entry alone, got $n"; fi

t "existing .gitignore content is preserved (append-only, never rewritten)"
d=$(new_target)
printf 'node_modules/\ndist/\n' > "$d/.gitignore"
install_into "$d"
if grep -qE '^node_modules/$' "$d/.gitignore" && grep -qE '^dist/$' "$d/.gitignore" \
   && grep -qE '^\.claude/$' "$d/.gitignore"; then pass
else fail "prior entries lost: $(cat "$d/.gitignore")"; fi

t "a .gitignore with no trailing newline is not corrupted"
d=$(new_target)
printf 'dist/' > "$d/.gitignore"   # deliberately no trailing \n
install_into "$d"
if grep -qE '^dist/$' "$d/.gitignore" && grep -qE '^\.claude/$' "$d/.gitignore"; then pass
else fail "line merge corrupted the file: $(cat "$d/.gitignore")"; fi

finish
