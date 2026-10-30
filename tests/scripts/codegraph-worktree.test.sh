#!/bin/bash
# The research stage deletes <worktree>/.codegraph before it returns (#526, ADR 0122): its untracked
# .gitignore makes `git worktree remove` fail without --force. This test proves both halves on a real
# codegraph. It skips when codegraph is not installed, so CI machines without it stay green.
source "$(dirname "$0")/../lib.sh"

t "git worktree remove fails with a leftover .codegraph and works once it is deleted"
if ! command -v codegraph >/dev/null 2>&1; then
  skip "codegraph is not installed"
  finish
  exit 0
fi

REPO=$(mktemp -d); _CLEANUP_DIRS+=("$REPO")
git -C "$REPO" init -q -b main 2>/dev/null || git -C "$REPO" init -q
git -C "$REPO" config user.email test@test
git -C "$REPO" config user.name test
printf 'function buildWidget(opts) { return opts.size; }\n' > "$REPO/a.js"
git -C "$REPO" add -A
git -C "$REPO" commit -q -m init

mkwt() { # mkwt <dir>: a detached worktree with a codegraph index in it
  git -C "$REPO" worktree add -q --detach "$1" HEAD || return 1
  (cd "$1" && CODEGRAPH_NO_DAEMON=1 CODEGRAPH_TELEMETRY=0 codegraph init --yes >/dev/null 2>&1) || return 1
  [ -d "$1/.codegraph" ]
}

PARENT=$(mktemp -d); _CLEANUP_DIRS+=("$PARENT")
if ! mkwt "$PARENT/left" || ! mkwt "$PARENT/clean"; then fail "could not create a worktree with a codegraph index"; finish; exit 1; fi
if git -C "$REPO" worktree remove "$PARENT/left" >/dev/null 2>&1; then
  fail "remove succeeded with a leftover .codegraph; the cleanup step would not be needed"
else
  rm -rf "$PARENT/clean/.codegraph"
  if git -C "$REPO" worktree remove "$PARENT/clean" >/dev/null 2>&1 && [ ! -d "$PARENT/clean" ]; then pass
  else fail "remove failed after .codegraph was deleted"; fi
fi
git -C "$REPO" worktree remove --force "$PARENT/left" >/dev/null 2>&1
finish
