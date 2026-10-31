#!/bin/bash
# Contract tests for scripts/check-adr-numbers.sh.
source "$(dirname "$0")/../lib.sh"

CHECK="$ROOT/scripts/check-adr-numbers.sh"

adr_dir() {
  local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  for name in "$@"; do : > "$d/$name"; done
  echo "$d"
}

run_check() { OUT=$(bash "$CHECK" "$1" 2>&1); RC=$?; }

t "unique numbers pass"
d=$(adr_dir 0001-a.md 0002-b.md README.md)
run_check "$d"; [ "$RC" = 0 ] && pass || fail "rc=$RC: $OUT"

t "two files with one number fail, and both are named"
d=$(adr_dir 0001-a.md 0002-b.md 0002-c.md)
run_check "$d"
if [ "$RC" = 1 ] && [[ "$OUT" == *0002-b.md* ]] && [[ "$OUT" == *0002-c.md* ]]; then pass; else fail "rc=$RC: $OUT"; fi

t "a file without a number is ignored"
d=$(adr_dir 0001-a.md template.md)
run_check "$d"; [ "$RC" = 0 ] && pass || fail "rc=$RC: $OUT"

t "the repo has no duplicate number"
run_check "$ROOT/docs/adr"; [ "$RC" = 0 ] && pass || fail "rc=$RC: $OUT"

finish
