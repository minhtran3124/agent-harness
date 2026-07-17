#!/bin/bash
# Contract tests for scripts/init-structure.sh — create-if-missing structural scaffolding.
source "$(dirname "$0")/../lib.sh"

SCRIPT="$ROOT/scripts/init-structure.sh"

DESTS="specs/README.md specs/STATE.md agent-memory/README.md docs/solutions/README.md docs/solutions/INDEX.md docs/solutions/critical-patterns.md techstacks/README.md"

t "bare repo → all 7 structural files created"
d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
out=$(bash "$SCRIPT" --root "$d")
missing=0
for f in $DESTS; do [ -f "$d/$f" ] || missing=1; done
created=$(printf '%s' "$out" | grep -c 'created')
if [ "$missing" -eq 0 ] && [ "$created" -eq 7 ]; then pass
else fail "missing=$missing created=$created out:$out"; fi

t "re-run on a populated repo → all 7 report exists, no clobber"
# mutate one file, re-run, confirm it was NOT overwritten
echo "CUSTOM CONTENT" > "$d/docs/solutions/INDEX.md"
out=$(bash "$SCRIPT" --root "$d")
exists=$(printf '%s' "$out" | grep -c 'exists')
kept=$(grep -c "CUSTOM CONTENT" "$d/docs/solutions/INDEX.md")
if [ "$exists" -eq 7 ] && [ "$kept" -eq 1 ]; then pass
else fail "exists=$exists kept=$kept out:$out"; fi

t "exit 0 even when everything already exists (advisory)"
bash "$SCRIPT" --root "$d" >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 0 ]; then pass; else fail "want exit 0, got $rc"; fi

finish
