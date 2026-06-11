#!/bin/bash
# Contract tests for hooks/ruff-on-edit.sh — ruff --fix + format on edited .py; never blocks.
source "$(dirname "$0")/../lib.sh"

H=ruff-on-edit.sh

t "non-.py file → silent exit 0 (ruff not invoked)"
repo=$(new_repo $H)
printf 'hello\n' > "$repo/notes.txt"
run_hook "$repo" $H "$(json_file "$repo/notes.txt")"
assert_silent_ok

t ".py edit always exits 0 (non-blocking contract)"
repo=$(new_repo $H)
printf 'x=1\n' > "$repo/m.py"
run_hook "$repo" $H "$(json_file "$repo/m.py")"
assert_rc 0

if command -v ruff >/dev/null 2>&1; then
  t "ruff reformats a badly-spaced .py file in place"
  repo=$(new_repo $H)
  printf 'x=1+2\n' > "$repo/bad.py"
  run_hook "$repo" $H "$(json_file "$repo/bad.py")"
  if grep -q 'x = 1 + 2' "$repo/bad.py"; then pass; else fail "not reformatted: $(cat "$repo/bad.py")"; fi
else
  t "ruff reformat case"; skip "ruff not installed"
fi

finish
