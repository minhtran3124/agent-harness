#!/bin/bash
source "$(dirname "$0")/../lib.sh"
SKILL="skills/compound/SKILL.md"

t "compound preserves all four complete-track gates"
for track in bug knowledge decision failure; do grep -q "| $track |" "$ROOT/$SKILL" || { fail "missing $track"; finish; }; done
pass

t "compound delegates index construction to its deterministic authority"
grep -q 'scripts/rebuild_solution_index.py' "$ROOT/$SKILL" && grep -q 'Do not manually scan/sort/render' "$ROOT/$SKILL" && pass || fail "index authority missing"

t "compound keeps promotion and proposed-ratchet handling"
grep -q 'critical-patterns.md' "$ROOT/$SKILL" && grep -q 'proposed:' "$ROOT/$SKILL" && pass || fail "promotion or ratchet missing"

finish
