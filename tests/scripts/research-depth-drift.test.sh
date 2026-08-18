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
#
# MULTI-WORD ON PURPOSE. An earlier draft used the stems `depend` and `integrat`, which
# were vacuous: `integrat` matched "integrations" in SKILL.md's frontmatter description
# (line 3) and `depend` matched "independently" (line 19), while in the registry both
# matched the *portable classifier* prose that predates this rule. Deleting the entire
# trigger clause from the Coverage text left the lint green. Each phrase below occurs
# exactly once per file — verified — so it can only be satisfied by the rule itself.
KEYWORDS=(
  "external surface"                # the concept itself — the whole point of the rule
  "upgrades a dependency"           # trigger 1
  "integrates an external system"   # trigger 2
  "version-specific API"            # trigger 3
  "local-only"                      # the `- none (local-only; no external surface)` sentinel
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

# The rule is worthless if a copy still asserts the OLD unconditional reading alongside
# the new one — a reader would follow whichever they hit first. Each retired sentence is
# listed verbatim (from `git show 1f1c351`); an earlier draft checked only the SKILL.md
# phrasing, so restoring the registry's own bullet went undetected.
STALE_SENTENCES=(
  "Standard: Quick coverage plus upstream patterns and version-matched official documentation"
  "Standard adds upstream and official docs"
  # SKILL.md frontmatter `description:` — the routing text an agent sees FIRST, and the
  # copy that survived the original propagation because it does not look like policy prose.
  "upstream patterns, and version-matched official docs"
)
# NOT listed: the template's `_(Standard + Deep only. Skip if Quick mode.)_`. That string is
# still CORRECT under `## Upstream Findings` — the new rule keeps upstream patterns
# unconditional at Standard/Deep and narrows only official docs. Grepping it file-wide
# would fail on legitimate text, so the Docs Findings section is checked by scope below.
t "no file restores a retired unconditional sentence"
stale=""
for copy in "${COPIES[@]}" "$REGISTRY"; do
  text=$(tr -s '[:space:]' ' ' < "$ROOT/$copy")
  for s in "${STALE_SENTENCES[@]}"; do
    if printf '%s' "$text" | grep -qiF "$s"; then stale="$stale $copy"; fi
  done
done
if [ -z "$stale" ]; then pass; else fail "retired unconditional wording still present in:$stale"; fi

# Section-scoped: the template's Docs Findings block is the one that must carry the
# condition. A regression that reverts just that marker leaves "external surface"
# elsewhere in the file, so a file-wide keyword check cannot see it.
docs_findings_block() {
  awk '/^## Docs Findings/{f=1;next} /^## /{f=0} f' "$1/skills/xia2/references/research-brief-template.md"
}
t "template's Docs Findings section states the surface condition, not an unconditional one"
if docs_findings_block "$ROOT" | grep -qiF "external surface"; then pass
else fail "Docs Findings no longer names the external-surface condition — reverted to depth-only"; fi

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

# PER-TRIGGER mutation. The bug this replaces: stem anchors (`depend`, `integrat`) were
# satisfied by unrelated words elsewhere in the same file, so deleting a trigger from the
# Coverage clause left the lint green. One case per trigger proves each anchor is real.
for trig in "upgrades a dependency" "integrates an external system" "version-specific API"; do
  t "mutation check: deleting trigger '$trig' from ${COPIES[0]} is detected"
  md=$(mktemp -d); _CLEANUP_DIRS+=("$md")
  cp -R "$ROOT/skills" "$md/skills"
  cp -R "$ROOT/rules" "$md/rules"
  # Collapse BEFORE removing: these phrases wrap across lines in the real files (SKILL.md
  # breaks "integrates an external / system"), and a line-wise gsub silently removes
  # nothing — which reads as "the anchor is vacuous" when the harness simply missed.
  # surface_rule_ok collapses too, so mutating collapsed text is the faithful comparison.
  tr -s '[:space:]' ' ' < "$ROOT/${COPIES[0]}" \
    | awk -v pat="$trig" '{gsub(pat, ""); print}' > "$md/${COPIES[0]}"
  if surface_rule_ok "$md" "${COPIES[0]}" 2>/dev/null; then
    fail "deleted '$trig' from ${COPIES[0]} but the lint still passed — that anchor is vacuous"
  else pass; fi
done

# Mutation for the OTHER direction: the keyword checks prove text was not deleted; this
# proves a retired claim being ADDED BACK is caught. Nothing else in the suite covers it.
t "mutation check: restoring the registry's retired unconditional bullet is detected"
mr=$(mktemp -d); _CLEANUP_DIRS+=("$mr")
cp -R "$ROOT/rules" "$mr/rules"
cp "$ROOT/$REGISTRY" "$mr/$REGISTRY"
printf '\n- Standard: Quick coverage plus upstream patterns and version-matched official documentation.\n' >> "$mr/$REGISTRY"
found=0
text=$(tr -s '[:space:]' ' ' < "$mr/$REGISTRY")
for s in "${STALE_SENTENCES[@]}"; do
  if printf '%s' "$text" | grep -qiF "$s"; then found=1; fi
done
if [ "$found" -eq 1 ]; then pass
else fail "re-added the retired registry bullet but the stale-sentence check did not see it"; fi

finish
