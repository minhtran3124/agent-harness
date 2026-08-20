#!/bin/bash
# Safeguard-parity contract tests (gh #213).
#
# The harness states the same load-bearing invariants in more than one place: a rule
# names a marker, and an agent or skill prompt is claimed (often in CLAUDE.md) to enforce
# the very same marker. Nothing re-checks that the marker actually still lives in every
# context that is supposed to carry it, so an isolated edit to one file can silently
# break the parity while CI stays green. These tests are that cross-context assertion:
# they read the live prose under rules/, agents/, and skills/ and fail the suite the
# moment a marker goes missing from any context that must carry it.
#
# Comparison is whitespace-normalized (all whitespace runs collapse to single spaces)
# so reflow, re-wrapping, or reformatting of the prose cannot false-fail a check.
#
# Later waves append additional check families (negative assertions, proximity windows,
# template heading parity) to THIS file, each just before the final finish call.
source "$(dirname "$0")/../lib.sh"

# norm_file ROOT RELPATH: whitespace-normalized file contents on stdout.
# Returns nonzero (and prints nothing) when the file is absent, so a missing file can
# never masquerade as a silent pass -- the caller turns the nonzero into a fail.
norm_file() {
  local path="$1/$2"
  [ -f "$path" ] || return 1
  awk 'BEGIN{RS="\036"}{gsub(/[[:space:]]+/," ");printf "%s",$0}' "$path"
}

# assert_marker ROOT MARKER RELPATH...: checker function (mirrors the
# scorer-threshold-contract idiom: takes a root dir so a mutation self-check can run the
# exact same checker against a mutated mktemp copy). Prints the space-separated list of
# files that do NOT contain the whitespace-normalized marker and returns nonzero; prints
# nothing and returns 0 when every file carries it. A missing file is reported as a miss.
# Markers are authored pre-normalized (single internal spaces) so normalized file
# content can be matched against them directly.
assert_marker() {
  local root="$1" marker="$2"; shift 2
  local missing="" f content
  for f in "$@"; do
    if ! content=$(norm_file "$root" "$f"); then
      missing="$missing $f(missing-file)"; continue
    fi
    case "$content" in
      *"$marker"*) ;;
      *) missing="$missing $f" ;;
    esac
  done
  [ -z "$missing" ] && return 0
  printf '%s' "${missing# }"
  return 1
}

# -- Cross-context positive markers -------------------------------------------
# One row per invariant; the why-comment on the preceding line names the claim it guards.

# why: CLAUDE.md and behavior.md section 1 claim all three files score findings against this absence-claim rule.
t "marker: not_observed != absent holds across all three reviewer contexts"
miss=$(assert_marker "$ROOT" 'not_observed != absent' \
  rules/behavior.md \
  agents/reviewer.md \
  skills/correctness-review/correctness-scorer-prompt.md)
if [ -z "$miss" ]; then pass; else fail "'not_observed != absent' missing in: $miss"; fi

# why: spec_verdict is one field of the two-verdict task-review schema; prompt and skill must agree.
t "marker: spec_verdict names the schema field in both SDD contexts"
miss=$(assert_marker "$ROOT" 'spec_verdict' \
  skills/subagent-driven-development/task-reviewer-prompt.md \
  skills/subagent-driven-development/SKILL.md)
if [ -z "$miss" ]; then pass; else fail "'spec_verdict' missing in: $miss"; fi

# why: quality_verdict is the paired second field of that same two-verdict schema.
t "marker: quality_verdict names the schema field in both SDD contexts"
miss=$(assert_marker "$ROOT" 'quality_verdict' \
  skills/subagent-driven-development/task-reviewer-prompt.md \
  skills/subagent-driven-development/SKILL.md)
if [ -z "$miss" ]; then pass; else fail "'quality_verdict' missing in: $miss"; fi

# why: unmodified-line is the scorer auto-0 flag; the shared prompt and scorer prompt must both carry it.
t "marker: unmodified-line auto-0 flag is shared by both scorer prompts"
miss=$(assert_marker "$ROOT" 'unmodified-line' \
  skills/correctness-review/correctness-scorer-prompt.md \
  skills/correctness-review/prompts/shared.md)
if [ -z "$miss" ]; then pass; else fail "'unmodified-line' missing in: $miss"; fi

# why: quality verdicts is the prose form of the two-verdict pair; reviewer agent and skill index must agree.
t "marker: quality verdicts (prose form) appears in agent + README contexts"
miss=$(assert_marker "$ROOT" 'quality verdicts' \
  agents/task-reviewer.md \
  skills/README.md)
if [ -z "$miss" ]; then pass; else fail "'quality verdicts' missing in: $miss"; fi

# why: two verdicts is the prose form of the pair named in the autonomy rule and the skill index.
t "marker: two verdicts (prose form) appears in rule + README contexts"
miss=$(assert_marker "$ROOT" 'two verdicts' \
  rules/auto-correct-scope.md \
  skills/README.md)
if [ -z "$miss" ]; then pass; else fail "'two verdicts' missing in: $miss"; fi

# -- Mutation self-check ------------------------------------------------------
# Proves assert_marker actually detects a stripped marker, so a checker that has quietly
# gone stale (always-passing) fails the suite instead of shipping silently.
t "mutation check: seeded cross-context drift is detected"
m=$(mktemp -d); _CLEANUP_DIRS+=("$m")
mkdir -p "$m/rules" "$m/agents" "$m/skills/correctness-review"
cp "$ROOT/rules/behavior.md" "$m/rules/behavior.md"
cp "$ROOT/agents/reviewer.md" "$m/agents/reviewer.md"
cp "$ROOT/skills/correctness-review/correctness-scorer-prompt.md" "$m/skills/correctness-review/correctness-scorer-prompt.md"
# Fixture guard: a failed mktemp/mkdir/cp must never masquerade as detection.
if [ -n "$m" ] && [ -d "$m" ] && [ -f "$m/rules/behavior.md" ]; then
  # Negative control: every copy carries the marker before we mutate it.
  pre=$(assert_marker "$m" 'not_observed != absent' \
    rules/behavior.md \
    agents/reviewer.md \
    skills/correctness-review/correctness-scorer-prompt.md)
  if [ -n "$pre" ]; then
    fail "negative control failed: unmutated copies already report a miss: $pre"
  else
    # Strip the marker from exactly one copy, as a careless future edit would.
    sed -i.bak '/not_observed != absent/d' "$m/rules/behavior.md"
    rm -f "$m/rules/behavior.md.bak"
    mut=$(assert_marker "$m" 'not_observed != absent' \
      rules/behavior.md \
      agents/reviewer.md \
      skills/correctness-review/correctness-scorer-prompt.md)
    # Detection must name the mutated file, not merely be non-empty.
    case "$mut" in
      *rules/behavior.md*) pass ;;
      *) fail "mutation not localized to behavior.md (got: '$mut') -- assert_marker has gone stale" ;;
    esac
  fi
else
  fail "fixture setup failed (m='$m') -- cannot trust the mutation result"
fi

finish
