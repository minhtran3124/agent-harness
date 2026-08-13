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

IMPL="skills/subagent-driven-development/implementer-prompt.md"
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

# terminology_reads_ok <dir> → 0 iff BOTH consumers of rules/terminology.md §3 still carry
# an explicit Read. The rule is path-scoped, and `paths:` fires on read, never on write — so
# the plan AUTHOR (writing-plans) and the isolated plan REVIEWER each need their own Read or
# §3 silently stops reaching the context that decides acceptance criteria.
PLAN_AUTHOR="skills/writing-plans/SKILL.md"
PLAN_REVIEWER="skills/writing-plans/plan-document-reviewer-prompt.md"
terminology_reads_ok() {
  grep -qE '\*\*Read `rules/terminology\.md`\*\*' "$1/$PLAN_AUTHOR" &&
  grep -qE '\*\*Read `rules/terminology\.md`\*\*' "$1/$PLAN_REVIEWER"
}

t "writing-plans author and isolated plan reviewer both explicitly Read terminology.md"
if terminology_reads_ok "$ROOT"; then pass
else fail "missing '**Read \`rules/terminology.md\`**' in $PLAN_AUTHOR and/or $PLAN_REVIEWER"; fi

t "mutation: deleting either terminology.md Read is detected"
m3=$(mktemp -d); _CLEANUP_DIRS+=("$m3")
cp -R "$ROOT/skills" "$m3/skills"
sed -i.bak 's/\*\*Read `rules\/terminology\.md`\*\*//' "$m3/$PLAN_REVIEWER" && rm -f "$m3/$PLAN_REVIEWER.bak"
if ! terminology_reads_ok "$m3"; then pass
else fail "deleting the reviewer's terminology.md Read was NOT detected"; fi

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

finish
