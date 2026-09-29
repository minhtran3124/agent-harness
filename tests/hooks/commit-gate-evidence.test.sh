#!/bin/bash
# Contract tests for hooks/commit-gate.sh evidence checks, default (standard) profile:
#   check_escalations    — pending escalations deny commits touching their slug
#   check_lane_evidence  — verify_summary.py --lane on each staged SUMMARY.md
#   check_run_state      — RUN.json / events.jsonl travel with the spec
# Prefixed spec folders (specs/gh-<n>-<slug>/, specs/lin-<ID>-<slug>/) behave like plain slugs.
source "$(dirname "$0")/../lib.sh"

H=commit-gate.sh
COMMIT_JSON=$(jq -cn '{tool_name:"Bash",tool_input:{command:"git commit -m x"}}')

# ── check_escalations: deny-on-no-response (review C5) ─────────────────────
t "staged spec file + pending escalation in that slug → BLOCKED (exit 2)"
repo=$(new_repo $H)
stage "$repo" "specs/demo/SUMMARY.md" "Lane: normal"
stage "$repo" "specs/demo/ESCALATIONS.md" '## E001
- question: widen the regex?
- decision: pending'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "deny-on-no-response"

t "same commit recording the decision self-unblocks (staged copy wins)"
repo=$(new_repo $H)
stage "$repo" "specs/demo/SUMMARY.md" "Lane: normal"
stage "$repo" "specs/demo/ESCALATIONS.md" '## E001
- question: widen the regex?
- decision: A (accepted)
- decided_by: human
- decided_at: 2026-07-16'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "Escalations... PASSED"

t "pending escalation on disk does NOT block commits that leave the slug untouched"
repo=$(new_repo $H)
mkdir -p "$repo/specs/other"
printf -- '- decision: pending\n' > "$repo/specs/other/ESCALATIONS.md"
stage "$repo" "README.md" "docs change"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "unstaged pending ESCALATIONS.md on disk still blocks a commit touching its slug"
repo=$(new_repo $H)
mkdir -p "$repo/specs/demo"
printf -- '- decision: pending\n' > "$repo/specs/demo/ESCALATIONS.md"
stage "$repo" "specs/demo/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "deny-on-no-response"

GH="gh-999-fixture"
LIN="lin-ENG-315-fixture"

t "pending escalation in a gh-prefixed slug → BLOCKED"
repo=$(new_repo $H)
stage "$repo" "specs/$GH/SUMMARY.md" "Lane: normal"
stage "$repo" "specs/$GH/ESCALATIONS.md" '## E001
- decision: pending'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "deny-on-no-response"

t "recorded decision in the gh-prefixed slug self-unblocks"
repo=$(new_repo $H)
stage "$repo" "specs/$GH/SUMMARY.md" "Lane: normal"
stage "$repo" "specs/$GH/ESCALATIONS.md" '## E001
- decision: A (accepted)'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "Escalations... PASSED"

# ── check_run_state: RUN.json / events.jsonl must travel with the spec ──────
t "untracked RUN.json beside a staged spec file → BLOCKED (exit 2)"
repo=$(new_repo $H)
stage "$repo" "specs/demo/SUMMARY.md" "Lane: tiny"
printf '{"state":"planning"}\n' > "$repo/specs/demo/RUN.json"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "specs/demo/RUN.json exists but is UNTRACKED"

t "untracked events.jsonl beside a staged spec file → BLOCKED (exit 2)"
repo=$(new_repo $H)
stage "$repo" "specs/demo/PLAN.md" "status: draft"
printf '{"event":"intake"}\n' > "$repo/specs/demo/events.jsonl"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "specs/demo/events.jsonl exists but is UNTRACKED"

t "staging RUN.json + events.jsonl in the same commit passes"
repo=$(new_repo $H)
stage "$repo" "specs/demo/SUMMARY.md" "Lane: tiny"
stage "$repo" "specs/demo/RUN.json" '{"state":"planning"}'
stage "$repo" "specs/demo/events.jsonl" '{"event":"intake"}'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "Run-state artifacts... PASSED"

t "tracked RUN.json with unstaged edits → warns, does not block"
repo=$(new_repo $H)
stage "$repo" "specs/demo/RUN.json" '{"state":"planning"}'
git -C "$repo" commit -qm seed
printf '{"state":"implementing"}\n' > "$repo/specs/demo/RUN.json"
stage "$repo" "specs/demo/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "has unstaged changes"

t "untracked RUN.json does NOT block a commit that leaves the slug untouched"
repo=$(new_repo $H)
mkdir -p "$repo/specs/other"
printf '{"state":"planning"}\n' > "$repo/specs/other/RUN.json"
stage "$repo" "README.md" "docs change"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "Run-state artifacts"

t "REQUIRE_RUN_STATE_STAGED=0 downgrades the untracked block to a warning"
repo=$(new_repo $H)
stage "$repo" "specs/demo/SUMMARY.md" "Lane: tiny"
printf '{"state":"planning"}\n' > "$repo/specs/demo/RUN.json"
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_RUN_STATE_STAGED=0
assert_rc_contains 0 "UNTRACKED"

# ── check_lane_evidence: mechanizes rules/auto-correct-scope.md ─────────────
# Wired in response to the PR #119 review: lane evidence was proven by unit tests but
# never invoked against a real SUMMARY.
LANE_PY="$ROOT/scripts/verify_summary.py"
LANE_TINY=$'Lane: tiny\nConfidence: high\nReason: a real filled reason\n'
LANE_NORMAL_BAD=$'Lane: normal\nConfidence: high\nReason: a real filled reason\n\n### Verify\n\n| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n| p | `<command>` | 0 | placeholder only |\n'
LANE_NORMAL_OK=$'Lane: normal\nConfidence: high\nReason: a real filled reason\n\n### Verify\n\n| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n| p | `true` | 0 | a real command |\n'

# lane_repo → a repo with scripts/verify_summary.py present
lane_repo() {
  local r; r=$(new_repo $H)
  mkdir -p "$r/scripts"; cp "$LANE_PY" "$r/scripts/"
  echo "$r"
}

t "normal lane whose ### Verify holds only placeholders → BLOCKED"
repo=$(lane_repo)
stage "$repo" "specs/demo/SUMMARY.md" "$LANE_NORMAL_BAD"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "Lane evidence... FAILED"

t "the block names the real SUMMARY path, not the temp file"
assert_rc_contains 2 "specs/demo/SUMMARY.md"

t "normal lane with a real ### Verify row → PASSES"
repo=$(lane_repo)
stage "$repo" "specs/demo/SUMMARY.md" "$LANE_NORMAL_OK"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "Lane evidence... PASSED"

t "tiny lane needs only a filled header (evidence scales with lane)"
repo=$(lane_repo)
stage "$repo" "specs/demo/SUMMARY.md" "$LANE_TINY"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "Lane evidence... PASSED"

t "same commit fixing the evidence self-unblocks (staged copy wins)"
repo=$(lane_repo)
mkdir -p "$repo/specs/demo"
printf '%s\n' "$LANE_NORMAL_BAD" > "$repo/specs/demo/SUMMARY.md"   # failing copy on disk
git -C "$repo" add -f specs/demo/SUMMARY.md
printf '%s\n' "$LANE_NORMAL_OK" > "$repo/specs/demo/SUMMARY.md"    # fixed, then staged
git -C "$repo" add -f specs/demo/SUMMARY.md
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "Lane evidence... PASSED"

# SC coverage must be judged against the INDEXED PLAN, not the working tree: staging a
# PLAN that declares an SC contract and then editing it away before `git commit` used to
# make the gate fail open while the staged contract went in (PR #157 review, P2).
LANE_SC_PLAN=$'# demo\n\n## 3. Success Criteria\n\n| ID | Behavior | Check | Expected |\n| --- | --- | --- | --- |\n| SC-1 | first | `true` | exit 0 |\n| SC-2 | second | `false` | exit 1 |\n'
LANE_SC_SUMMARY=$'Lane: normal\nConfidence: high\nReason: a real filled reason\n\n### Verify\n\n| Check | Command | Exit | Notes | Criterion |\n| --- | --- | --- | --- | --- |\n| c1 | `true` | 0 | real | SC-1 |\n'

t "staged PLAN's SC table is enforced even after the worktree PLAN is emptied"
repo=$(lane_repo)
stage "$repo" "specs/demo/PLAN.md" "$LANE_SC_PLAN"
stage "$repo" "specs/demo/SUMMARY.md" "$LANE_SC_SUMMARY"
printf '# demo\n\nno SC table here\n' > "$repo/specs/demo/PLAN.md"   # worktree edit, unstaged
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "SC-2"

t "SC coverage complete against the staged PLAN → PASSES"
repo=$(lane_repo)
stage "$repo" "specs/demo/PLAN.md" "$LANE_SC_PLAN"
stage "$repo" "specs/demo/SUMMARY.md" "${LANE_SC_SUMMARY}"$'| c2 | `false` | 1 | real | SC-2 |\n'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "Lane evidence... PASSED"

t "a commit touching no specs/ path is unaffected"
repo=$(lane_repo)
mkdir -p "$repo/specs/other"
printf '%s\n' "$LANE_NORMAL_BAD" > "$repo/specs/other/SUMMARY.md"
stage "$repo" "README.md" "docs only"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "a slug dir with no SUMMARY.md (PLAN only) does not block"
repo=$(lane_repo)
stage "$repo" "specs/demo/PLAN.md" "# plan"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "python3 absent → skip with a notice, never block (fail-open)"
repo=$(lane_repo)
stage "$repo" "specs/demo/SUMMARY.md" "$LANE_NORMAL_BAD"
nopy=$(mktemp -d); _CLEANUP_DIRS+=("$nopy")
IFS=: read -ra _pd <<< "$PATH"
for d in "${_pd[@]}"; do
  [ -d "$d" ] || continue
  for f in "$d"/*; do
    b=$(basename "$f")
    case "$b" in python|python3|python3.*) continue ;; esac
    [ -e "$nopy/$b" ] || ln -s "$f" "$nopy/$b" 2>/dev/null
  done
done
run_hook "$repo" $H "$COMMIT_JSON" PATH="$nopy"
assert_rc_contains 0 "Lane evidence skipped"

t "lane evidence FAILS on a lin-prefixed SUMMARY and names its real path"
repo=$(lane_repo)
stage "$repo" "specs/$LIN/SUMMARY.md" "$LANE_NORMAL_BAD"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "specs/$LIN/SUMMARY.md"

t "lane evidence PASSES on a lin-prefixed SUMMARY with a real row"
repo=$(lane_repo)
stage "$repo" "specs/$LIN/SUMMARY.md" "$LANE_NORMAL_OK"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "Lane evidence... PASSED"

finish
