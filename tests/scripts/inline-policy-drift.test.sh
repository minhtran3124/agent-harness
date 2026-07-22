#!/bin/bash
# Registry-anchored drift lint for the Rule-4 STOP list (gh #143, PR #141 P2).
#
# PR #141 P2 escaped because an inline copy of the Rule-4 STOP list (in the
# correctness reviewer prompt) had silently drifted to a 5-of-8 subset of the
# authoritative source. This test is the standing guard: the STOP list lives
# canonically in rules/auto-correct-scope.md (the REGISTRY) and is duplicated,
# in prose, into the correctness-review skill files (the COPIES below). We parse
# the registry's case set down to a per-case anchor KEYWORD, assert every keyword
# appears in the registry AND in each copy, and mutation-check ourselves (drop
# one case from a temp copy → detected) so the lint is provably load-bearing.
#
# Keyword, not phrase: registry and copy wording have legitimately drifted
# (registry "Removing existing functionality" vs a copy's "removing existing
# behavior"; "high-blast-radius files" vs "high-blast file"). The stable contract
# is the concept, so each KEYWORD is a case-insensitive SUBSTRING that is real in
# every copy — collapse whitespace first (the prose spans line breaks).
#
# DIVISION OF LABOR: this file guards the STOP-list *case set* (are all 8 cases
# present in each copy). The DIFFERENT duplicated policy — the scorer threshold
# *number* — is guarded by scorer-threshold-contract.test.sh. Do not merge them.
source "$(dirname "$0")/../lib.sh"

# Canonical source of the STOP list.
REGISTRY="rules/auto-correct-scope.md"

# Known inline copies of the STOP list. Adding a future copy is one line here.
COPIES=(
  "skills/correctness-review/correctness-reviewer-prompt.md"
  "skills/correctness-review/SKILL.md"
)

# The 8 Rule-4 STOP cases, as per-case anchor keywords (see auto-correct-scope.md
# Rule 4). These are the distilled, drift-stable form of the registry case list;
# the "registry contains all 8" case below verifies they still anchor the source.
KEYWORDS=(
  "schema"        # 1. schema changes
  "API contract"  # 2. API contract changes
  "remov"         # 3. removing existing functionality/behavior
  "external"      # 4. new external service dependency
  "auth"          # 5. security-sensitive auth/authz
  "session"       # 6. session/transaction scope
  "high-blast"    # 7. high-blast-radius files
  "replac"        # 8. replacing a service/pattern
)

# stop_list_ok <dir> <relpath> → 0 if every KEYWORD is present in the file,
# non-zero (and prints the first missing keyword to stderr) otherwise.
# Whitespace is collapsed so a keyword split across a line break still matches.
stop_list_ok() {
  local text; text=$(tr '[:space:]' ' ' < "$1/$2")
  local kw
  for kw in "${KEYWORDS[@]}"; do
    if ! printf '%s' "$text" | grep -qiF "$kw"; then
      printf 'missing: %s\n' "$kw" >&2
      return 1
    fi
  done
  return 0
}

t "registry ($REGISTRY) contains all 8 STOP cases"
if stop_list_ok "$ROOT" "$REGISTRY" 2>/dev/null; then pass
else fail "a KEYWORD is not present in the registry — anchors drifted from the source"; fi

for copy in "${COPIES[@]}"; do
  t "inline copy covers all 8 STOP cases: $copy"
  if miss=$(stop_list_ok "$ROOT" "$copy" 2>&1); then pass
  else fail "$copy is missing a STOP case ($miss) — it has drifted from $REGISTRY"; fi
done

t "mutation check: a copy with one dropped STOP case is detected"
m=$(mktemp -d); _CLEANUP_DIRS+=("$m")
cp -R "$ROOT/skills" "$m/skills"
cp -R "$ROOT/rules" "$m/rules"
# Drop exactly one case ("high-blast", present once) from the first copy, as a
# careless future edit that trims the list would.
TARGET="${COPIES[0]}"
grep -iv 'high-blast' "$ROOT/$TARGET" > "$m/$TARGET"
if stop_list_ok "$m" "$TARGET" 2>/dev/null; then
  fail "dropped 'high-blast' from $TARGET but stop_list_ok still passed — the lint is not load-bearing"
else pass; fi

finish
