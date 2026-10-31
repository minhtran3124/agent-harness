#!/bin/bash
# Two ADR files must not share a number. write_adrs.py picks the next number from the local
# docs/adr/ only, so two open branches can take the same one; this fails once both are on a tree.
#
# Usage: bash scripts/check-adr-numbers.sh [adr-dir]   (default: docs/adr)
# Verifies:        numbers are unique inside one tree.
# Does not verify: numbers across open branches. Nothing reserves a number.
set -u
cd "$(dirname "$0")/.." || exit 1
DIR="${1:-docs/adr}"

DUPES=""
PREV_NUM=""; PREV_NAME=""
for path in "$DIR"/[0-9][0-9][0-9][0-9]-*.md; do
  [ -f "$path" ] || continue
  name="${path##*/}"
  num="${name%%-*}"
  if [ "$num" = "$PREV_NUM" ]; then
    DUPES="$DUPES $PREV_NAME $name"
  fi
  PREV_NUM="$num"; PREV_NAME="$name"
done

if [ -n "$DUPES" ]; then
  echo "  ✗ ADR files share a number; give the newer file the next free number:" >&2
  for name in $DUPES; do echo "      $name" >&2; done
  exit 1
fi
echo "  ✓ ADR numbers are unique"
exit 0
