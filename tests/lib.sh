#!/bin/bash
# Shared helpers for harness contract tests. Source from a *.test.sh file:
#
#   source "$(dirname "$0")/../lib.sh"
#   t "describes the case"; run_hook "$repo" my-hook.sh "$(json_cmd 'git commit -m x')"
#   assert_rc 2
#   finish
#
# Design: hooks have a pure contract (stdin JSON → exit code + stderr). Hooks that need
# git state resolve the repo root FROM THEIR OWN LOCATION (git -C "$(dirname $0)" ...),
# so tests copy the hook under test into a throwaway mktemp git repo and run it there —
# fully hermetic, nothing in the real repo is touched.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0; FAIL=0; SKIP=0; XFAIL=0
CURRENT=""
_CLEANUP_DIRS=()

if [ -t 1 ]; then _G=$'\033[32m'; _R=$'\033[31m'; _Y=$'\033[33m'; _D=$'\033[2m'; _X=$'\033[0m'; else _G=; _R=; _Y=; _D=; _X=; fi

t()     { CURRENT="$1"; }
pass()  { PASS=$((PASS+1)); printf '  %sok%s    %s\n' "$_G" "$_X" "$CURRENT"; }
fail()  { FAIL=$((FAIL+1)); printf '  %sFAIL%s  %s\n        %s\n' "$_R" "$_X" "$CURRENT" "$1"; }
skip()  { SKIP=$((SKIP+1)); printf '  %sskip%s  %s — %s\n' "$_Y" "$_X" "$CURRENT" "$1"; }
# Known bug, documented and awaiting an approved fix: the case runs but an "incorrect"
# result is expected. Keeps the suite green while keeping the bug visible in every run.
xfail() { XFAIL=$((XFAIL+1)); printf '  %sxfail%s %s — known bug: %s\n' "$_Y" "$_X" "$CURRENT" "$1"; }

# new_repo <hook.sh>... → echoes a fresh git repo dir with those hooks copied into hooks/
new_repo() {
  local d; d=$(mktemp -d)
  _CLEANUP_DIRS+=("$d")
  git -C "$d" init -q -b main 2>/dev/null || git -C "$d" init -q
  git -C "$d" config user.email test@test
  git -C "$d" config user.name test
  mkdir -p "$d/hooks"
  # Shared hook lib (sourced by the git-command gates) must travel with the hook.
  [ -d "$ROOT/hooks/lib" ] && cp -R "$ROOT/hooks/lib" "$d/hooks/"
  local h
  for h in "$@"; do cp "$ROOT/hooks/$h" "$d/hooks/"; done
  echo "$d"
}

# stage <repo> <relpath> <content> — create a file and git add it
stage() {
  mkdir -p "$1/$(dirname "$2")"
  printf '%s\n' "$3" > "$1/$2"
  git -C "$1" add -f "$2"
}

# run_hook <repo> <hook.sh> <json-stdin> [VAR=val ...] — sets OUT (stdout+stderr) and RC.
# Runs with CWD = repo (as the real harness does): SCRIPT_DIR-based hooks resolve the same
# root either way, and CWD-based hooks (check-untracked-py) need it.
run_hook() {
  local repo="$1" hook="$2" json="$3"; shift 3
  OUT=$(cd "$repo" && printf '%s' "$json" | env "$@" bash "hooks/$hook" 2>&1); RC=$?
}

json_cmd()    { printf '{"tool_input":{"command":"%s"}}' "$1"; }
json_file()   { printf '{"tool_input":{"file_path":"%s"}}' "$1"; }
json_prompt() { printf '{"prompt":"%s"}' "$1"; }

assert_rc() {
  if [ "$RC" -eq "$1" ]; then pass; else fail "rc=$RC, want $1 — out: $(echo "$OUT" | head -3 | tr '\n' ' ')"; fi
}
assert_rc_contains() { # assert_rc_contains <rc> <substring>
  if [ "$RC" -eq "$1" ] && echo "$OUT" | grep -qF "$2"; then pass
  else fail "rc=$RC (want $1), grep '$2' — out: $(echo "$OUT" | head -4 | tr '\n' ' ')"; fi
}
assert_silent_ok() {
  if [ "$RC" -eq 0 ] && [ -z "$OUT" ]; then pass; else fail "want silent rc=0; rc=$RC out:[$(echo "$OUT" | head -2 | tr '\n' ' ')]"; fi
}

# Shared pytest venv (created once per machine, reused across runs) + a `python` shim dir
# to prepend to PATH — hooks prefer `python`, macOS/CI often only have `python3`.
ensure_pyenv() {
  PYENV_DIR="${TMPDIR:-/tmp}/harness-tests-venv"
  if [ ! -x "$PYENV_DIR/bin/python" ]; then
    python3 -m venv "$PYENV_DIR" >/dev/null 2>&1 || return 1
  fi
  if ! "$PYENV_DIR/bin/python" -c 'import pytest, pytest_cov' 2>/dev/null; then
    "$PYENV_DIR/bin/pip" install -q pytest pytest-cov >/dev/null 2>&1 || return 1
  fi
  "$PYENV_DIR/bin/python" -c 'import pytest, pytest_cov' 2>/dev/null || return 1
  PYSHIM=$(mktemp -d); _CLEANUP_DIRS+=("$PYSHIM")
  printf '#!/bin/bash\nexec "%s/bin/python" "$@"\n' "$PYENV_DIR" > "$PYSHIM/python"
  chmod +x "$PYSHIM/python"
}

finish() {
  local rc=0
  [ "$FAIL" -gt 0 ] && rc=1
  printf '\n  %s: %s%d passed%s' "$(basename "$0")" "$_G" "$PASS" "$_X"
  [ "$FAIL" -gt 0 ]  && printf ', %s%d FAILED%s' "$_R" "$FAIL" "$_X"
  [ "$SKIP" -gt 0 ]  && printf ', %d skipped' "$SKIP"
  [ "$XFAIL" -gt 0 ] && printf ', %d known-bug (xfail)' "$XFAIL"
  printf '\n'
  local d; for d in "${_CLEANUP_DIRS[@]}"; do rm -rf "$d"; done
  exit "$rc"
}
