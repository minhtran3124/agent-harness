#!/bin/bash
# Contract tests for hooks/risk-corroboration.sh — the lane-vs-diff corroboration gate.
source "$(dirname "$0")/../lib.sh"

H=risk-corroboration.sh
COMMIT_JSON=$(json_cmd 'git commit -m x')

t "non-commit command is ignored (silent, exit 0)"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_cmd 'git status')"
assert_silent_ok

t "commit with nothing staged passes"
repo=$(new_repo $H)
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "migration path + Lane: normal → BLOCKED (exit 2)"
repo=$(new_repo $H)
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

t "migration path + Lane: high-risk → corroborated (exit 0)"
repo=$(new_repo $H)
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
stage "$repo" "specs/x/SUMMARY.md" "Lane: high-risk"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "corroborated"

t "auth keyword in added code + Lane: tiny → BLOCKED"
repo=$(new_repo $H)
stage "$repo" "app/auth.py" 'def login(password): return password'
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

t "hard-gate signal with NO declared Lane → warns but allows (exit 0)"
repo=$(new_repo $H)
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "no declared Lane"

t "same, RISK_CORROBORATION_STRICT=1 → BLOCKED"
repo=$(new_repo $H)
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
run_hook "$repo" $H "$COMMIT_JSON" RISK_CORROBORATION_STRICT=1
assert_rc_contains 2 "BLOCKED"

t "RISK_WARN_CATEGORIES loosens a category to warn (exit 0)"
repo=$(new_repo $H)
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON" RISK_WARN_CATEGORIES="data-loss/migration"
assert_rc_contains 0 "warn-mode"

t "prose-only diff (docs/md) trips nothing even with auth words"
repo=$(new_repo $H)
stage "$repo" "docs/notes.md" 'the login password jwt flow'
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "high-blast path (root hooks/) + Lane: normal → BLOCKED"
repo=$(new_repo $H)
stage "$repo" "hooks/new-hook.sh" 'echo hi'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "high-blast"

t ".claude/hooks/ path also trips high-blast"
repo=$(new_repo $H)
stage "$repo" ".claude/hooks/new-hook.sh" 'echo hi'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "high-blast"

t "tests/hooks/ does NOT trip high-blast (regex precision — no false positive)"
repo=$(new_repo $H)
stage "$repo" "tests/hooks/branch-guard.test.sh" 'echo hi'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

finish
