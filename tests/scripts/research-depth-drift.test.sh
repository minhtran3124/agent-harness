#!/bin/bash
# Registry-anchored drift lint for the research-depth *external surface* rule.
#
# Why this exists: the Coverage rule used to demand official documentation at
# Standard and multiple upstream sources at Deep, unconditionally. It now demands
# them only when the change has an EXTERNAL SURFACE, and requires an explicit
# `- none (local-only; no external surface)` when it does not. That definition is
# now stated in three places, because agents read the skill and fill the template —
# they do not read rules/research-depth.md. Three copies of one definition with no
# guard is exactly the `stale-inline-policy` escape the review-chain fixture pins.
#
# Registry: rules/research-depth.md. Copies: the two xia2 files an agent actually
# loads. Same discipline as tests/scripts/inline-policy-drift.test.sh (Rule-4 STOP
# list) — parse to per-concept anchor keywords, assert each is present in the
# registry AND every copy, then mutation-check ourselves so the lint is provably
# load-bearing.
#
# DIVISION OF LABOR: inline-policy-drift.test.sh guards the Rule-4 STOP case set;
# scorer-threshold-contract.test.sh guards the scorer threshold number; this file
# guards the external-surface trigger set. Do not merge them.
#
# Keyword, not phrase: wording may legitimately differ between a rule's prose and a
# skill's imperative step. Each KEYWORD is a case-insensitive SUBSTRING that must be
# real in every copy; whitespace is collapsed first because the prose wraps.
#
# Verifies:        every external-surface trigger, and the `- none` sentinel, appear
#                  in the registry and in each copy.
# Does not verify: that the copies say the same thing *about* those triggers, or that
#                  any agent obeys them. Traceability tier, not truth.
source "$(dirname "$0")/../lib.sh"

# Canonical source of the Coverage / external-surface rule.
REGISTRY="rules/research-depth.md"

# The contexts an xia2 agent actually loads. Adding a future policy-bearing consumer
# is one line here.
COPIES=(
  "skills/xia2/SKILL.md"
  "skills/xia2/references/research-brief-template.md"
)

# The external-surface trigger set plus the sentinel that makes "no external source"
# distinguishable from "research skipped". Dropping any one of these is the drift
# that would quietly restore the old unconditional reading.
KEYWORDS=(
  "external surface"   # the concept itself — the whole point of the rule
  "depend"             # trigger 1: adds or upgrades a dependency
  "integrat"           # trigger 2: integrates an external system
  "version-specific"   # trigger 3: relies on a version-specific API
  "local-only"         # the `- none (local-only; no external surface)` sentinel
)

# surface_rule_ok <dir> <relpath> → 0 if every KEYWORD is present in the file,
# non-zero (and prints the first missing keyword to stderr) otherwise.
surface_rule_ok() {
  local text; text=$(tr -s '[:space:]' ' ' < "$1/$2")
  local kw
  for kw in "${KEYWORDS[@]}"; do
    if ! printf '%s' "$text" | grep -qiF "$kw"; then
      printf 'missing: %s\n' "$kw" >&2
      return 1
    fi
  done
  return 0
}

t "registry ($REGISTRY) states the full external-surface trigger set"
if surface_rule_ok "$ROOT" "$REGISTRY" 2>/dev/null; then pass
else fail "a KEYWORD is not present in the registry — anchors drifted from the source"; fi

for copy in "${COPIES[@]}"; do
  t "consumer context carries the external-surface rule: $copy"
  if miss=$(surface_rule_ok "$ROOT" "$copy" 2>&1); then pass
  else fail "$copy is missing part of the rule ($miss) — it has drifted from $REGISTRY"; fi
done

# The rule is worthless if a copy still asserts the OLD unconditional reading
# alongside the new one — a reader would follow whichever they hit first.
t "no copy still demands official documentation unconditionally at Standard"
stale=""
for copy in "${COPIES[@]}" "$REGISTRY"; do
  text=$(tr -s '[:space:]' ' ' < "$ROOT/$copy")
  # The retired sentence shape: "Standard ... official documentation" with no
  # intervening mention of the surface condition.
  if printf '%s' "$text" | grep -qiE 'Standard adds upstream and official docs'; then
    stale="$stale $copy"
  fi
done
if [ -z "$stale" ]; then pass; else fail "retired unconditional wording still present in:$stale"; fi

t "mutation check: a copy with the surface condition stripped is detected"
m=$(mktemp -d); _CLEANUP_DIRS+=("$m")
cp -R "$ROOT/skills" "$m/skills"
cp -R "$ROOT/rules" "$m/rules"
# Strip every line naming the condition, as a careless future edit reverting to the
# unconditional rule would.
TARGET="${COPIES[0]}"
grep -iv 'external surface' "$ROOT/$TARGET" > "$m/$TARGET"
if surface_rule_ok "$m" "$TARGET" 2>/dev/null; then
  fail "stripped 'external surface' from $TARGET but surface_rule_ok still passed — the lint is not load-bearing"
else pass; fi

t "mutation check: dropping only the local-only sentinel is detected"
m2=$(mktemp -d); _CLEANUP_DIRS+=("$m2")
cp -R "$ROOT/skills" "$m2/skills"
cp -R "$ROOT/rules" "$m2/rules"
# The subtler regression: the trigger set survives but "state it explicitly" is lost,
# which silently restores an empty Source Pack as an acceptable answer.
grep -iv 'local-only' "$ROOT/$REGISTRY" > "$m2/$REGISTRY"
if surface_rule_ok "$m2" "$REGISTRY" 2>/dev/null; then
  fail "dropped the local-only sentinel from $REGISTRY but the lint still passed"
else pass; fi

finish
