#!/bin/bash
# Merge the harness permissions.allow rule (Bash(gh pr merge *)) into a settings file.
# Usage: merge-allow.sh [--dry-run] <settings.json>
#   Keeps every existing key and every existing allow entry (their order first), appends the
#   harness rule if it is missing, and writes nothing when nothing is missing (idempotent).
#   A missing file is created as {} first. --dry-run prints the diff and changes nothing.
# Exit: 0 done or already merged, 1 usage, 2 the file is not a valid JSON object or its permissions
#       is not an object or its allow is not an array (file untouched),
#       3 jq is not installed. Needs jq. Bash 3.2 safe. jq rewrites the file with 2-space indent.
set -eu

DRY=0
if [ "${1:-}" = "--dry-run" ]; then DRY=1; shift; fi
[ "$#" -eq 1 ] || { echo "usage: merge-allow.sh [--dry-run] <settings.json>" >&2; exit 1; }
FILE=$1
command -v jq >/dev/null 2>&1 || { echo "merge-allow: jq is required (install jq, then re-run)" >&2; exit 3; }

RULES='["Bash(gh pr merge *)"]'

if [ -f "$FILE" ]; then
  jq -e 'type == "object"' "$FILE" >/dev/null 2>&1 \
    || { echo "merge-allow: $FILE is not a valid JSON object; not touching it" >&2; exit 2; }
  jq -e '(if has("permissions") then .permissions else {} end) | type == "object" and ((if has("allow") then .allow else [] end) | type == "array")' "$FILE" >/dev/null 2>&1 \
    || { echo "merge-allow: $FILE has a permissions or allow value of the wrong type; not touching it" >&2; exit 2; }
  CUR=$(cat "$FILE")
else
  CUR='{}'
fi

NEW=$(printf '%s' "$CUR" | jq --argjson r "$RULES" '
  def uniq: reduce .[] as $x ([]; if index($x) then . else . + [$x] end);
  .permissions = ((.permissions // {})
    | .allow = (((.allow // []) + $r) | uniq))')

SAME=0
if [ -f "$FILE" ] && [ "$(printf '%s' "$CUR" | jq -S .)" = "$(printf '%s' "$NEW" | jq -S .)" ]; then SAME=1; fi

if [ "$DRY" -eq 1 ]; then
  if [ "$SAME" -eq 1 ]; then echo "allow rule already present in $FILE"; exit 0; fi
  TMP=$(mktemp)
  printf '%s\n' "$CUR" | jq . > "$TMP"
  printf '%s\n' "$NEW" | diff -u "$TMP" - || true
  rm -f "$TMP"
  exit 0
fi

if [ "$SAME" -eq 1 ]; then echo "allow rule already present in $FILE"; exit 0; fi
# Write through a symlink to its real target, keep the file mode, and never leave a temp file behind.
n=0
while [ -L "$FILE" ] && [ "$n" -lt 20 ]; do
  LINK=$(readlink "$FILE")
  case "$LINK" in /*) FILE=$LINK ;; *) FILE=$(dirname "$FILE")/$LINK ;; esac
  n=$((n + 1))
done
mkdir -p "$(dirname "$FILE")"
TMP=$(mktemp "$FILE.XXXXXX")
trap 'rm -f "$TMP"' EXIT
if [ -f "$FILE" ]; then cp -p "$FILE" "$TMP"; else chmod 0644 "$TMP"; fi
printf '%s\n' "$NEW" > "$TMP"
mv "$TMP" "$FILE"
trap - EXIT
echo "merged allow rule into $FILE"
