#!/bin/bash
# Regression tests for issue #121: ticket-prefixed spec folders (specs/gh-<n>-<slug>/,
# specs/lin-<TICKET-ID>-<slug>/) pass every hook exactly like plain slugs — proves the
# grandfathering claim mechanically (gates parse specs/<anything>/, not slug shape).
source "$(dirname "$0")/../lib.sh"

GH="gh-999-fixture"
LIN="lin-ENG-315-fixture"
COMMIT_JSON=$(json_cmd 'git commit -m x')

# ── commit-quality-gate.sh: Check 1.5 (escalations) slug extraction ──
H=commit-quality-gate.sh

t "Check 1.5: pending escalation in a gh-prefixed slug → BLOCKED"
repo=$(new_repo $H)
stage "$repo" "specs/$GH/SUMMARY.md" "Lane: normal"
stage "$repo" "specs/$GH/ESCALATIONS.md" '## E001
- decision: pending'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "deny-on-no-response"

t "Check 1.5: recorded decision in the gh-prefixed slug self-unblocks"
repo=$(new_repo $H)
stage "$repo" "specs/$GH/SUMMARY.md" "Lane: normal"
stage "$repo" "specs/$GH/ESCALATIONS.md" '## E001
- decision: A (accepted)'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "Escalations... PASSED"

# ── commit-quality-gate.sh: Check 1.6 (lane evidence) on a lin-prefixed SUMMARY ──
LANE_PY="$ROOT/scripts/verify_summary.py"
LANE_BAD=$'Lane: normal\nConfidence: high\nReason: a real filled reason\n\n### Verify\n\n| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n| p | `<command>` | 0 | placeholder only |\n'
LANE_OK=$'Lane: normal\nConfidence: high\nReason: a real filled reason\n\n### Verify\n\n| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n| p | `true` | 0 | a real command |\n'

t "Check 1.6: lane evidence FAILS on a lin-prefixed SUMMARY and names its real path"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$LANE_PY" "$repo/scripts/"
stage "$repo" "specs/$LIN/SUMMARY.md" "$LANE_BAD"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "specs/$LIN/SUMMARY.md"

t "Check 1.6: lane evidence PASSES on a lin-prefixed SUMMARY with a real row"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$LANE_PY" "$repo/scripts/"
stage "$repo" "specs/$LIN/SUMMARY.md" "$LANE_OK"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "Lane evidence... PASSED"

# ── risk-corroboration.sh: Lane resolved from a staged gh-prefixed SUMMARY ──
H=risk-corroboration.sh

t "risk-corroboration reads Lane: high-risk from a gh-prefixed SUMMARY → corroborated"
repo=$(new_repo $H)
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
stage "$repo" "specs/$GH/SUMMARY.md" "Lane: high-risk"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "corroborated"

t "risk-corroboration still blocks a low lane declared in a gh-prefixed SUMMARY"
repo=$(new_repo $H)
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
stage "$repo" "specs/$GH/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

# ── branch-isolation-guard.sh: specs/* exemption covers prefixed paths ──
H=branch-isolation-guard.sh

t "prefixed specs/ bookkeeping stays writable on main (intake exemption)"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_file "$repo/specs/$GH/SUMMARY.md")"
assert_silent_ok

t "code file on main is still denied (exemption not loosened by the fixture)"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_file "$repo/app/x.py")"
assert_rc_contains 0 '"permissionDecision":"deny"'

# ── blast-radius-check.sh: active-plan lookup finds a prefixed folder ──
H=blast-radius-check.sh

# prefixed_plan <repo> — active PLAN.md inside specs/$GH with app/foo.py in scope.
# Markdown task syntax (not legacy XML): a fenced <task> XML literal inside THIS plan
# would flip render_plan/blast-radius into XML mode on the real PLAN.md; markdown
# fixtures keep the plan and the test file identical and safe.
prefixed_plan() {
  mkdir -p "$1/specs/$GH"
  cat > "$1/specs/$GH/PLAN.md" <<'EOF'
---
status: active
---
### Task 1.1 — t (wave 1)

- **Files:** app/foo.py
- **Action:** x
- **Verify:** `true`
- **Done:** ok
EOF
}

t "active PLAN.md in a gh-prefixed folder is found: out-of-scope edit warns"
repo=$(new_repo $H)
prefixed_plan "$repo"
run_hook "$repo" $H "$(json_file "$repo/app/rogue.py")"
assert_rc_contains 0 "blast-radius"

t "in-scope edit under the prefixed plan stays silent"
repo=$(new_repo $H)
prefixed_plan "$repo"
run_hook "$repo" $H "$(json_file "$repo/app/foo.py")"
assert_silent_ok

# ── render-plan-on-write.sh: path filter matches a prefixed PLAN.md ──
H=render-plan-on-write.sh

if command -v python3 >/dev/null 2>&1 && [ -f "$ROOT/skills/visual-planner/render_plan.py" ]; then
  t "prefixed specs/<gh>/PLAN.md matches the path filter → PLAN.html rendered"
  repo=$(new_repo $H)
  mkdir -p "$repo/skills/visual-planner"
  cp "$ROOT/skills/visual-planner/render_plan.py" "$repo/skills/visual-planner/"
  [ -f "$ROOT/skills/visual-planner/template.html" ] && cp "$ROOT/skills/visual-planner/template.html" "$repo/skills/visual-planner/"
  mkdir -p "$repo/specs/$GH"
  cat > "$repo/specs/$GH/PLAN.md" <<'EOF'
---
slug: gh-999-fixture
status: active
---
# Fixture
## 1. Motivation
x
## 4. Tasks
### Task 1.1 — do (wave 1)

- **Files:** a.py
- **Action:** do
- **Verify:** `true`
- **Done:** ok
EOF
  run_hook "$repo" $H "$(json_file "$repo/specs/$GH/PLAN.md")"
  if [ -f "$repo/specs/$GH/PLAN.html" ]; then pass
  else fail "rc=$RC html missing — out: $(echo "$OUT" | head -2 | tr '\n' ' ')"; fi
else
  t "render-plan prefixed-path case"; skip "python3 or render engine unavailable"
fi

finish
