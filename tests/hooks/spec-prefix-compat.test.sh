#!/bin/bash
# Regression tests for issue #121: ticket-prefixed spec folders (specs/gh-<n>-<slug>/,
# specs/lin-<TICKET-ID>-<slug>/) pass every hook exactly like plain slugs — proves the
# grandfathering claim mechanically (gates parse specs/<anything>/, not slug shape).
# The escalation, lane-evidence, and Lane-resolution cases for hooks/commit-gate.sh live in
# tests/hooks/commit-gate-evidence.test.sh and tests/hooks/commit-gate-risk.test.sh.
source "$(dirname "$0")/../lib.sh"

GH="gh-999-fixture"
LIN="lin-ENG-315-fixture"
COMMIT_JSON=$(json_cmd 'git commit -m x')

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

# ── commit-gate.sh check_plan_scope: active-plan lookup finds a prefixed folder ──
H=commit-gate.sh

# prefixed_plan <repo> — active PLAN.md inside specs/$GH with app/foo.py in scope.
# Markdown task syntax (not legacy XML): a fenced <task> XML literal inside THIS plan
# would flip render_plan/check_plan_scope into XML mode on the real PLAN.md; markdown
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

t "active PLAN.md in a gh-prefixed folder is found: out-of-scope commit warns"
repo=$(new_repo $H)
prefixed_plan "$repo"
stage "$repo" "app/rogue.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "blast-radius"

t "in-scope commit under the prefixed plan has no scope note"
repo=$(new_repo $H)
prefixed_plan "$repo"
stage "$repo" "app/foo.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "blast-radius"

finish
