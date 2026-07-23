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

# Documented FP (docs/solutions/harness/risk-corroboration-scans-test-comments-for-auth-words.md):
# ordinary English in a shell comment under tests/ must not read as auth surface,
# while a live code line with the same word must still trip the gate.
t "auth word in a tests/ shell COMMENT does not trip the gate (comment-strip fix)"
repo=$(new_repo $H)
stage "$repo" "tests/scripts/demo.test.sh" '# restore the session state and check permission handling
echo ok'
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "auth word in a LIVE code line under tests/ still trips the gate"
repo=$(new_repo $H)
stage "$repo" "tests/scripts/demo.test.sh" 'session_token=$(login "$password")'
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

t "removed comment line does not trip weakening-validation"
repo=$(new_repo $H)
mkdir -p "$repo/tests"
printf '# assert the raise path is covered\necho ok\n' > "$repo/tests/old.test.sh"
git -C "$repo" add tests/old.test.sh >/dev/null 2>&1 && git -C "$repo" commit -qm seed >/dev/null 2>&1
printf 'echo ok\n' > "$repo/tests/old.test.sh"
git -C "$repo" add tests/old.test.sh >/dev/null 2>&1
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "workflow-engine: skills/x/SKILL.md + Lane: normal → BLOCKED (names workflow-engine)"
repo=$(new_repo $H)
stage "$repo" "skills/x/SKILL.md" '# Skill x'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "workflow-engine"

t "workflow-engine: prose docs/notes.md → silent pass (not an engine surface)"
repo=$(new_repo $H)
stage "$repo" "docs/notes.md" '# Notes
Some prose.'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "workflow-engine: skills/README.md → silent pass (inventory prose, not an engine surface)"
repo=$(new_repo $H)
stage "$repo" "skills/README.md" '# Skills inventory'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "workflow-engine: agents/coding.md + Lane: normal → BLOCKED (real agent prompt is an engine surface)"
repo=$(new_repo $H)
stage "$repo" "agents/coding.md" '# Coding agent'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "workflow-engine"

t "workflow-engine: agents/README.md → silent pass (inventory prose, mirrors skills/README.md)"
repo=$(new_repo $H)
stage "$repo" "agents/README.md" '# Agents inventory'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "workflow-engine: agents/PROJECT.template.md → silent pass (fill-in scaffold, not an engine surface)"
repo=$(new_repo $H)
stage "$repo" "agents/PROJECT.template.md" '# Project template'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "workflow-engine: NESTED dispatch prompt skills/x/subagents/y-prompt.md + Lane: normal → BLOCKED"
repo=$(new_repo $H)
stage "$repo" "skills/x/subagents/analyzer-prompt.md" '# Analyzer dispatch prompt'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "workflow-engine"

# ── Manifest-driven gate modes (harness-manifest.json is the authority) ──
# The hook reads the manifest from the INDEX (git show :harness-manifest.json),
# so these cases stage it — a worktree-only manifest must NOT loosen anything.

t "staged manifest mode=warn loosens the category for a below-high-risk lane (exit 0)"
repo=$(new_repo $H)
stage "$repo" "harness-manifest.json" '{"hard_gates":{"detectable":[{"slug":"data-loss/migration","mode":"warn"}]}}'
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "warn-mode"

t "staged manifest mode=block still blocks a below-high-risk lane (exit 2)"
repo=$(new_repo $H)
stage "$repo" "harness-manifest.json" '{"hard_gates":{"detectable":[{"slug":"data-loss/migration","mode":"block"}]}}'
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

t "UNSTAGED worktree mode=warn does NOT loosen — index rules (exit 2, Codex PR#160)"
repo=$(new_repo $H)
# committed manifest says block; worktree edit flips to warn but is never staged
stage "$repo" "harness-manifest.json" '{"hard_gates":{"detectable":[{"slug":"data-loss/migration","mode":"block"}]}}'
git -C "$repo" commit -qm base
printf '%s\n' '{"hard_gates":{"detectable":[{"slug":"data-loss/migration","mode":"warn"}]}}' > "$repo/harness-manifest.json"
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

t "manifest absent from index (consumer repo) → fallback block (exit 2)"
repo=$(new_repo $H)
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

t "malformed staged manifest JSON → fail-safe block (exit 2)"
repo=$(new_repo $H)
stage "$repo" "harness-manifest.json" 'this is not json {'
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

t "manifest warn on one slug does not loosen a sibling prefix slug (auth vs authorization)"
repo=$(new_repo $H)
stage "$repo" "harness-manifest.json" '{"hard_gates":{"detectable":[{"slug":"auth","mode":"warn"}]}}'
stage "$repo" "app/perm.py" 'def check(): return require_role("admin")'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

# ── Diff-size sanity signal (warn-only, never changes exit code) ────────
# Content is deliberately benign (no gate keywords) so no other category trips.

t "diff >150 changed lines + Lane: tiny → /simplify note printed, exit 0"
repo=$(new_repo $H)
big_content=$(for i in $(seq 1 200); do printf 'line %d = %d\n' "$i" "$i"; done)
stage "$repo" "app/data.py" "$big_content"
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "/simplify"

t "diff >600 changed lines + Lane: normal → /simplify note printed, exit 0"
repo=$(new_repo $H)
big_content=$(for i in $(seq 1 700); do printf 'line %d = %d\n' "$i" "$i"; done)
stage "$repo" "app/data.py" "$big_content"
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "/simplify"

t "small diff under both thresholds → no /simplify note"
repo=$(new_repo $H)
small_content=$(for i in $(seq 1 10); do printf 'line %d = %d\n' "$i" "$i"; done)
stage "$repo" "app/data.py" "$small_content"
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
if [ "$RC" -eq 0 ] && ! echo "$OUT" | grep -qF "/simplify"; then pass
else fail "want rc=0 and no /simplify note — rc=$RC out: $(echo "$OUT" | head -3 | tr '\n' ' ')"; fi

finish
