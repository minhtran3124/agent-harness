#!/bin/bash
# Contract tests for the correctness-review scorer threshold (gh #152, PR #153).
#
# The scorer emits DISCRETE anchor scores (0|25|50|75|100) while the fix-loop
# threshold is prose duplicated across several skill files. With threshold 80,
# the "75 — Highly confident" anchor could never enter the fix-loop — and CI
# stayed green because nothing asserted the anchors and the threshold stay
# compatible. These tests are that assertion: they parse the live skill files,
# so a later isolated edit that bumps one copy (or re-breaks the anchor/threshold
# fit) fails the suite instead of shipping silently.
source "$(dirname "$0")/../lib.sh"

SCORER="skills/correctness-review/correctness-scorer-prompt.md"

# anchors_of <dir> → echoes the discrete anchor list, one per line (from the JSON schema)
anchors_of() {
  grep -oE '"score": <[0-9|]+>' "$1/$SCORER" | head -1 | grep -oE '[0-9]+'
}

# default_of <dir> → echoes the default threshold declared in the scorer prompt
default_of() {
  grep -oE 'default threshold is \*\*[0-9]+\*\*' "$1/$SCORER" | head -1 | grep -oE '[0-9]+'
}

# refs_of <dir> → every threshold number referenced anywhere under skills/, one per line.
# Patterns cover the known phrasings; a new phrasing with a drifted number is still
# caught as long as it reuses any of these shapes.
refs_of() {
  grep -rhoE 'THRESHOLD\([0-9]+\)|threshold\(?[0-9]+\)?|scoring [0-9]+ or|score >= [0-9]+|below \*\*[0-9]+\*\*|default \*\*[0-9]+\*\*' \
    "$1/skills" | grep -oE '[0-9]+'
}

t "scorer schema declares a discrete anchor set"
ANCHORS=$(anchors_of "$ROOT")
if [ -n "$ANCHORS" ] && [ "$(echo "$ANCHORS" | wc -l)" -ge 3 ]; then pass
else fail "could not parse anchors from $SCORER — got: [$ANCHORS]"; fi

t "scorer prompt declares a default threshold"
DEFAULT=$(default_of "$ROOT")
if [ -n "$DEFAULT" ]; then pass
else fail "no 'default threshold is **NN**' line in $SCORER"; fi

t "a non-maximal anchor can pass the threshold (the gh#152 regression)"
MAXA=$(echo "$ANCHORS" | sort -n | tail -1)
BEST_BELOW_MAX=$(echo "$ANCHORS" | sort -n | grep -vx "$MAXA" | tail -1)
if [ -n "$BEST_BELOW_MAX" ] && [ "$BEST_BELOW_MAX" -ge "$DEFAULT" ]; then pass
else fail "threshold $DEFAULT is only reachable by the max anchor $MAXA (next anchor: $BEST_BELOW_MAX) — 'highly confident' can never enter the fix-loop"; fi

t "threshold respects the documented floor of 60"
if [ "$DEFAULT" -ge 60 ]; then pass
else fail "threshold $DEFAULT is below the floor (60) — admits every unreadable-file-capped 50"; fi

t "every threshold reference under skills/ equals the default ($DEFAULT)"
DRIFT=$(refs_of "$ROOT" | grep -vx "$DEFAULT" | sort -u)
if [ -z "$DRIFT" ]; then pass
else fail "drifted threshold value(s): $(echo "$DRIFT" | tr '\n' ' ')— run: grep -rnE 'THRESHOLD\\(|threshold ' skills/"; fi

t "mutation check: a single drifted copy is detected"
m=$(mktemp -d); _CLEANUP_DIRS+=("$m")
cp -R "$ROOT/skills" "$m/skills"
# Bump exactly one consumer's copy, as a careless future edit would.
sed -i.bak "s/THRESHOLD($DEFAULT)/THRESHOLD(95)/" "$m/skills/subagent-driven-development/SKILL.md"
rm -f "$m/skills/subagent-driven-development/SKILL.md.bak"
MUT_DRIFT=$(refs_of "$m" | grep -vx "$DEFAULT" | sort -u)
if [ -n "$MUT_DRIFT" ]; then pass
else fail "mutated copy (95) was not detected — refs_of patterns have gone stale"; fi

finish
