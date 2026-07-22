#!/bin/bash
# Regression guard for the two context-propagation fixes that escaped PR #141
# (gh #143). Both defects were "the path-scoped auto-correct-scope rule never
# reaches the subagent that classifies self-fixes against it":
#
#   P1 (commit d61e155) — skills/subagent-driven-development/implementer-prompt.md
#      gained an explicit "FIRST: Read `.claude/rules/auto-correct-scope.md`" so an
#      isolated implementer actually loads the rule (its task text is pasted, so
#      nothing else puts the path-scoped rule in context).
#   P2 (commit 1c0f01d) — skills/correctness-review/correctness-reviewer-prompt.md
#      completed the inline Rule-4 STOP list to all 8 cases AND added an explicit
#      "**Read `.claude/rules/auto-correct-scope.md`**" before Rule-4 classification
#      (the review is plan-blind, so the `paths: specs/**` rule never auto-loads).
#
# Like scorer-threshold-contract.test.sh, this parses the LIVE skill files (not a
# snapshot): a future edit that drops either explicit Read, or drops a STOP case
# from the reviewer prompt's inline list, fails the suite instead of shipping.
source "$(dirname "$0")/../lib.sh"

IMPL="skills/subagent-driven-development/implementer-prompt.md"
REVIEWER="skills/correctness-review/correctness-reviewer-prompt.md"

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

# reviewer_read_ok <dir> → 0 iff the reviewer prompt still has the explicit bolded
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

t "reviewer prompt has an explicit Read of auto-correct-scope.md before Rule-4 (1c0f01d)"
if reviewer_read_ok "$ROOT"; then pass
else fail "no explicit '**Read ... auto-correct-scope.md' in $REVIEWER"; fi

t "reviewer STOP list covers all 8 Rule-4 cases (by keyword)"
if stop_cases_ok "$ROOT"; then pass
else
  region=$(stop_region "$ROOT"); missing=""
  for tok in "${STOP_TOKENS[@]}"; do printf '%s' "$region" | grep -qiF "$tok" || missing="$missing [$tok]"; done
  fail "missing STOP token(s):$missing — region: $region"
fi

t "mutation: deleting either explicit Read is detected"
m=$(mktemp -d); _CLEANUP_DIRS+=("$m")
cp -R "$ROOT/skills" "$m/skills"
sed -i.bak '/FIRST: Read .*auto-correct-scope/d' "$m/$IMPL"     && rm -f "$m/$IMPL.bak"
sed -i.bak '/\*\*Read .*auto-correct-scope/d'    "$m/$REVIEWER" && rm -f "$m/$REVIEWER.bak"
if ! implementer_read_ok "$m" && ! reviewer_read_ok "$m"; then pass
else fail "deleting the Read line was NOT detected — impl_ok=$(implementer_read_ok "$m"; echo $?) rev_ok=$(reviewer_read_ok "$m"; echo $?)"; fi

t "mutation: removing one STOP case from the reviewer prompt is detected"
m2=$(mktemp -d); _CLEANUP_DIRS+=("$m2")
cp -R "$ROOT/skills" "$m2/skills"
# Drop the 'high-blast' case (unique to line 175 of the STOP region).
sed -i.bak 's/high-blast-radius//' "$m2/$REVIEWER" && rm -f "$m2/$REVIEWER.bak"
if ! stop_cases_ok "$m2"; then pass
else fail "removing a STOP case (high-blast) was NOT detected by stop_cases_ok"; fi

finish
