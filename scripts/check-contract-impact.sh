#!/usr/bin/env bash
# check-contract-impact.sh — advisory contract-impact mapper.
#
# Given a set of changed files, answers: which harness-manifest.json contracts did
# I touch (via `surface`), and whose `consumers` must be re-verified? Always advisory
# (exit 0) — a later task wires this into scripts/harness-audit.sh.
#
# Usage:
#   check-contract-impact.sh [--root DIR] <file> [<file> ...]
#   check-contract-impact.sh [--root DIR] --changed
set -u

ROOT="$(dirname "$0")/.."
CHANGED=0
FILES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --root)    ROOT="$2"; shift 2 ;;
    --changed) CHANGED=1; shift ;;
    *)         FILES+=("$1"); shift ;;
  esac
done

cd "$ROOT" || exit 0
ROOT="$(pwd)"

if [ "$CHANGED" -eq 1 ]; then
  FILES=()
  while IFS= read -r f; do
    [ -n "$f" ] && FILES+=("$f")
  done < <(
    { git diff --name-only HEAD 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null; } | sort -u
  )
fi

[ -f "$ROOT/harness-manifest.json" ] || exit 0
[ "${#FILES[@]}" -gt 0 ] || exit 0

python3 - "$ROOT/harness-manifest.json" "${FILES[@]}" <<'PY'
import json, sys

manifest_path, changed = sys.argv[1], sys.argv[2:]
try:
    with open(manifest_path) as fh:
        data = json.load(fh)
except Exception:
    sys.exit(0)

contracts = data.get("contracts", {})
for slug, spec in contracts.items():
    if slug == "__doc__" or not isinstance(spec, dict):
        continue
    surface = spec.get("surface", [])
    consumers = spec.get("consumers", [])
    for f in changed:
        if f in surface:
            print(f"contract {slug}: surface {f} → verify consumers: {', '.join(consumers)}")
PY

exit 0
