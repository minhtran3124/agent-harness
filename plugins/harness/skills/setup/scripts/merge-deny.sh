#!/bin/bash
# Merge the harness permissions.deny rules into a project settings.json.
# Usage: merge-deny.sh [--dry-run] <settings.json>
#   Keeps every existing key and every existing deny entry (their order first), appends the
#   harness rules that are missing, and writes nothing when nothing is missing (idempotent).
#   A missing file is created as {} first. --dry-run prints the diff and changes nothing.
# Exit: 0 done or already merged, 1 usage, 2 the file is not a valid JSON object or its permissions
#       is not an object or its deny is not an array (file untouched), 3 jq is not installed. Needs jq. Bash 3.2 safe. jq rewrites the file with 2-space indent.
set -eu

DRY=0
if [ "${1:-}" = "--dry-run" ]; then DRY=1; shift; fi
[ "$#" -eq 1 ] || { echo "usage: merge-deny.sh [--dry-run] <settings.json>" >&2; exit 1; }
FILE=$1
command -v jq >/dev/null 2>&1 || { echo "merge-deny: jq is required (install jq, then re-run)" >&2; exit 3; }

RULES='["Read(./.env)","Read(./.env.*)","Edit(./.env)","Edit(./.env.*)","Bash(git push --force*)","Bash(git push -f*)","Bash(git push * main)","Bash(git push * master)","Bash(git push *:main)","Bash(git push *:refs/heads/main)","Bash(git push * +main)","Bash(git push *:master)","Bash(git push *:refs/heads/master)","Bash(git push * +master)"]'

if [ -f "$FILE" ]; then
  jq -e 'type == "object"' "$FILE" >/dev/null 2>&1 \
    || { echo "merge-deny: $FILE is not a valid JSON object; not touching it" >&2; exit 2; }
  jq -e '(.permissions // {}) | type == "object" and ((.deny // []) | type == "array")' "$FILE" >/dev/null 2>&1 \
    || { echo "merge-deny: $FILE has a permissions or deny value of the wrong type; not touching it" >&2; exit 2; }
  CUR=$(cat "$FILE")
else
  CUR='{}'
fi

NEW=$(printf '%s' "$CUR" | jq --argjson r "$RULES" '
  .permissions = ((.permissions // {}) | .deny = (((.deny // []) + $r) | reduce .[] as $x ([]; if index($x) then . else . + [$x] end)))')

SAME=0
if [ -f "$FILE" ] && [ "$(printf '%s' "$CUR" | jq -S .)" = "$(printf '%s' "$NEW" | jq -S .)" ]; then SAME=1; fi

if [ "$DRY" -eq 1 ]; then
  if [ "$SAME" -eq 1 ]; then echo "deny rules already present in $FILE"; exit 0; fi
  TMP=$(mktemp)
  printf '%s\n' "$CUR" | jq . > "$TMP"
  printf '%s\n' "$NEW" | diff -u "$TMP" - || true
  rm -f "$TMP"
  exit 0
fi

if [ "$SAME" -eq 1 ]; then echo "deny rules already present in $FILE"; exit 0; fi
mkdir -p "$(dirname "$FILE")"
TMP=$(mktemp "$FILE.XXXXXX")
printf '%s\n' "$NEW" > "$TMP"
mv "$TMP" "$FILE"
echo "merged deny rules into $FILE"
