#!/bin/bash
# Regression guard for contextual-rule delivery to every isolated workflow context.
# It retains the two fixes that escaped PR #141 and delegates the complete consumer
# matrix (main, implementer, task reviewer, plan reviewer, correctness reviewer,
# scorer, intent controller, and resume) to render_skill_prompt.py --check-all.
#
#   P1 (commit d61e155) — skills/subagent-driven-development/implementer-prompt.md
#      gained an explicit "FIRST: Read `rules/auto-correct-scope.md`" so an
#      isolated implementer actually loads the rule (its task text is pasted, so
#      nothing else puts the path-scoped rule in context).
#   P2 (commit 1c0f01d) — the correctness FIND shared fragment
#      completed the inline Rule-4 STOP list to all 8 cases AND added an explicit
#      "**Read `rules/auto-correct-scope.md`**" before Rule-4 classification
#      (the review is plan-blind, so the `paths: specs/**` rule never auto-loads).
#
# Like scorer-threshold-contract.test.sh, this parses the LIVE composed sources (not a
# snapshot): a future edit that drops either explicit Read, or drops a STOP case
# from the reviewer prompt's inline list, fails the suite instead of shipping.
source "$(dirname "$0")/../lib.sh"

IMPL="skills/implement/implementer-prompt.md"
REVIEWER="skills/correctness-review/prompts/shared.md"
COMPOSER="scripts/render_skill_prompt.py"

# The 8 Rule-4 STOP cases, as one stable keyword token each. Registry wording
# (rules/auto-correct-scope.md Rule 4) and the prompt's inline copy have legitimately
# drifted, so we match by case-insensitive substring, not phrase. Each token below is
# a verified substring of the reviewer prompt's STOP region on HEAD:
#   schema        <- "schema change"
#   API contract  <- "API contract change"      (spans a line break; region is collapsed)
#   remov         <- "removing existing behavior"
#   external      <- "new external dependency"
#   auth          <- "auth/authorization design"
#   session       <- "session/transaction scope change"
#   high-blast    <- "high-blast-radius file"
#   replac        <- "replacing a service/pattern"
STOP_TOKENS=("schema" "API contract" "remov" "external" "auth" "session" "high-blast" "replac")

# implementer_read_ok <dir> → 0 iff the implementer prompt still has the FIRST: Read
# instruction for auto-correct-scope.md (the d61e155 fix).
implementer_read_ok() {
  grep -qE 'FIRST: Read .*auto-correct-scope\.md' "$1/$IMPL"
}

# reviewer_read_ok <dir> → 0 iff the shared child prompt still has the explicit bolded
# Read of auto-correct-scope.md before Rule-4 classification (the 1c0f01d fix).
reviewer_read_ok() {
  grep -qE '\*\*Read .*auto-correct-scope\.md' "$1/$REVIEWER"
}

# stop_region <dir> → the reviewer prompt's inline Rule-4 STOP list, collapsed to a
# single line so tokens that wrap across a line break ("API contract") still match.
stop_region() {
  sed -n '/Rule 4 STOP cases:/,/This list is a summary/p' "$1/$REVIEWER" | tr '\n' ' ' | tr -s ' '
}

# stop_cases_ok <dir> → 0 iff every STOP token appears (case-insensitive) in the region.
stop_cases_ok() {
  local region tok
  region=$(stop_region "$1")
  for tok in "${STOP_TOKENS[@]}"; do
    printf '%s' "$region" | grep -qiF "$tok" || return 1
  done
  return 0
}

t "implementer prompt has the FIRST: Read of auto-correct-scope.md (d61e155)"
if implementer_read_ok "$ROOT"; then pass
else fail "no 'FIRST: Read ... auto-correct-scope.md' line in $IMPL"; fi

t "reviewer shared fragment has an explicit Read of auto-correct-scope.md before Rule-4 (1c0f01d)"
if reviewer_read_ok "$ROOT"; then pass
else fail "no explicit '**Read ... auto-correct-scope.md' in $REVIEWER"; fi

t "reviewer STOP list covers all 8 Rule-4 cases (by keyword)"
if stop_cases_ok "$ROOT"; then pass
else
  region=$(stop_region "$ROOT"); missing=""
  for tok in "${STOP_TOKENS[@]}"; do printf '%s' "$region" | grep -qiF "$tok" || missing="$missing [$tok]"; done
  fail "missing STOP token(s):$missing — region: $region"
fi

# The rule is path-scoped, and `paths:` fires on read, never on write — so the plan AUTHOR
# (writing-plans) and the isolated plan REVIEWER each need their own Read or §3 silently stops
# reaching the context that decides acceptance criteria. The canonical CONTEXT_MATRIX owns this
# contract; the mutation cases below prove both entries are enforced.
t "complete contextual-rule consumer matrix is checked"
if python3 "$ROOT/$COMPOSER" --root "$ROOT" --check-all >/dev/null; then pass
else fail "render_skill_prompt.py rejected the live consumer matrix"; fi

t "mutation: deleting either explicit Read is detected"
m=$(mktemp -d); _CLEANUP_DIRS+=("$m")
cp -R "$ROOT/skills" "$m/skills"
sed -i.bak '/FIRST: Read .*auto-correct-scope/d' "$m/$IMPL"     && rm -f "$m/$IMPL.bak"
sed -i.bak '/\*\*Read .*auto-correct-scope/d'    "$m/$REVIEWER" && rm -f "$m/$REVIEWER.bak"
if ! implementer_read_ok "$m" && ! reviewer_read_ok "$m"; then pass
else fail "deleting the Read line was NOT detected — impl_ok=$(implementer_read_ok "$m"; echo $?) rev_ok=$(reviewer_read_ok "$m"; echo $?)"; fi

t "mutation: removing one STOP case from the reviewer shared fragment is detected"
m2=$(mktemp -d); _CLEANUP_DIRS+=("$m2")
cp -R "$ROOT/skills" "$m2/skills"
# Drop the 'high-blast' case (unique to line 175 of the STOP region).
sed -i.bak 's/high-blast-radius//' "$m2/$REVIEWER" && rm -f "$m2/$REVIEWER.bak"
if ! stop_cases_ok "$m2"; then pass
else fail "removing a STOP case (high-blast) was NOT detected by stop_cases_ok"; fi

# asd-ste100 delivery (SC-8). Each isolated consumer must carry its own instruction: the
# implementer sees only its pasted prompt, and compound writes records.
COMPOUND="skills/compound/SKILL.md"

impl_ste_ok() {
  grep -q 'apply `skills/asd-ste100/SKILL.md`' "$1/$IMPL"
}
compound_ste_ok() {
  sed -n '/^## Write canonical records/,/^## Mistake twice/p' "$1/$COMPOUND" \
    | grep -q 'asd-ste100.*STE-flavored'
}
# ste_mutant <file> <sed-pattern> → temp root whose copy of <file> has matching lines deleted.
ste_mutant() {
  local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  mkdir -p "$d/$(dirname "$1")"
  sed "/$2/d" "$ROOT/$1" > "$d/$1"
  printf '%s' "$d"
}

t "implementer prompt applies asd-ste100 to changed prose (SC-8)"
if impl_ste_ok "$ROOT"; then pass; else fail "no asd-ste100 instruction in $IMPL"; fi
t "mutation: deleting the implementer asd-ste100 instruction is detected"
mi=$(ste_mutant "$IMPL" 'asd-ste100')
if ! impl_ste_ok "$mi"; then pass; else fail "removing the implementer instruction was NOT detected"; fi

t "compound applies asd-ste100 to new records (SC-8)"
if compound_ste_ok "$ROOT"; then pass; else fail "no asd-ste100 instruction in $COMPOUND 'Write canonical records'"; fi
t "mutation: deleting the compound asd-ste100 instruction is detected"
mc=$(ste_mutant "$COMPOUND" 'asd-ste100')
if ! compound_ste_ok "$mc"; then pass; else fail "removing the compound instruction was NOT detected"; fi

# rules/research-depth.md is the canonical lane-to-depth mapping (xia2 reads it; feature-intake
# no longer repeats or points to it), so the rule file must hold each rule the removed
# feature-intake section carried.
DEPTH_RULE="rules/research-depth.md"
DEPTH_ANCHORS=(
  'map `high-risk` to **Deep**'
  '`normal` to **Standard**'
  'permit **Quick** only for a `tiny` lane that satisfies every Quick condition'
  'move up on evidence but never down'
)
depth_rule_ok() {
  local text a; text=$(tr -s '[:space:]' ' ' < "$1/$DEPTH_RULE")
  for a in "${DEPTH_ANCHORS[@]}"; do
    printf '%s' "$text" | grep -qF "$a" || return 1
  done
}
t "rules/research-depth.md holds the four lane-to-depth rules (SC-4)"
if depth_rule_ok "$ROOT"; then pass; else fail "a lane-to-depth rule is missing from $DEPTH_RULE"; fi
for a in "${DEPTH_ANCHORS[@]}"; do
  t "mutation: deleting '$a' from $DEPTH_RULE is detected"
  md=$(mktemp -d); _CLEANUP_DIRS+=("$md"); mkdir -p "$md/rules"
  tr -s '[:space:]' ' ' < "$ROOT/$DEPTH_RULE" \
    | awk -v pat="$a" '{ i = index($0, pat); if (i) $0 = substr($0, 1, i-1) substr($0, i+length(pat)); print }' \
    > "$md/$DEPTH_RULE"
  if ! depth_rule_ok "$md"; then pass; else fail "deleting '$a' was NOT detected"; fi
done

finish
