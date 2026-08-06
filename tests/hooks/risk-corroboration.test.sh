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

# These test repos stage no index manifest, so the hook uses the embedded defaults
# (hooks/lib/gate-modes.default.sh) where workflow-engine is warn — the surface is
# still detected and named, but the commit is allowed with a note (exit 0).
t "workflow-engine: skills/x/SKILL.md + Lane: normal → warn note, allowed (names workflow-engine, exit 0)"
repo=$(new_repo $H)
stage "$repo" "skills/x/SKILL.md" '# Skill x'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "workflow-engine"

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

t "workflow-engine: agents/coding.md + Lane: normal → warn note, allowed (real agent prompt is an engine surface, exit 0)"
repo=$(new_repo $H)
stage "$repo" "agents/coding.md" '# Coding agent'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "workflow-engine"

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

t "workflow-engine: NESTED dispatch prompt skills/x/subagents/y-prompt.md + Lane: normal → warn note, allowed (exit 0)"
repo=$(new_repo $H)
stage "$repo" "skills/x/subagents/analyzer-prompt.md" '# Analyzer dispatch prompt'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "workflow-engine"

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

t "manifest absent from index (consumer repo) → embedded default (data-loss/migration = block, exit 2)"
repo=$(new_repo $H)
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

# ── Invariant #2 (SC-8): mode policy is index/embedded ONLY — never .claude/ ──
# BYPASS GUARD: a worktree .claude/harness-manifest.json with EVERY category flipped to
# warn must NOT loosen the auth gate. .claude/ is gitignored/agent-writable in consumers;
# the hook reads only `git show :harness-manifest.json` (root, index) and the embedded
# defaults, so this file is invisible and auth still blocks a below-high-risk lane.
t "SC-8 bypass guard: .claude/harness-manifest.json all-warn does NOT loosen auth (exit 2)"
repo=$(new_repo $H)
mkdir -p "$repo/.claude"
cat > "$repo/.claude/harness-manifest.json" <<'EOF'
{"hard_gates":{"detectable":[
  {"slug":"auth","mode":"warn"},
  {"slug":"authorization","mode":"warn"},
  {"slug":"data-loss/migration","mode":"warn"},
  {"slug":"audit/security","mode":"warn"},
  {"slug":"external-provider","mode":"warn"},
  {"slug":"public-contract","mode":"warn"},
  {"slug":"weakening-validation","mode":"warn"},
  {"slug":"high-blast","mode":"warn"},
  {"slug":"workflow-engine","mode":"warn"}
]}}
EOF
stage "$repo" "app/auth.py" 'def login(password): return password'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

# Meta-repo behavior preserved: with the tracked INDEX manifest present, index modes win
# (this is what the .claude bypass above is denied from doing). auth=warn in the index
# loosens the auth gate; the same all-warn content in .claude/ above did not.
t "meta-repo: tracked index manifest (auth=warn) wins → auth loosened, allowed (exit 0)"
repo=$(new_repo $H)
stage "$repo" "harness-manifest.json" '{"hard_gates":{"detectable":[{"slug":"auth","mode":"warn"}]}}'
stage "$repo" "app/auth.py" 'def login(password): return password'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "warn-mode"

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

t "large diff confined to .claude/ (excluded from CODE_ADDED, no other gate) + Lane: tiny → /simplify note still fires (unfiltered numstat)"
repo=$(new_repo $H)
big_content=$(for i in $(seq 1 200); do printf 'line %d = %d\n' "$i" "$i"; done)
stage "$repo" ".claude/rules/notes.md" "$big_content"
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "/simplify"

# Regression for the -U0 numstat bug (gh-159 fix-loop round 2): `-U0` forces `git diff`
# to emit patch mode, so `--numstat` output was numstat rows PLUS the full unified diff
# body — the awk parser then mis-read a content line's SECOND whitespace token as the
# numstat "removed" column whenever it looked numeric (e.g. "timeout 30000" → +=30000).
# True line count here (25 new lines) stays well under the tiny-lane 150 threshold; the
# buggy version inflated it into the tens of thousands and fired the note incorrectly.
t "moderate diff (~25 lines) with numeric-looking tokens under tiny threshold → no /simplify note (guards -U0 numstat-inflation regression)"
repo=$(new_repo $H)
numeric_content=$(for i in $(seq 1 25); do printf 'timeout %d\n' "$((i * 1000))"; done)
stage "$repo" "app/config.py" "$numeric_content"
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "/simplify"

t "small diff under both thresholds → no /simplify note"
repo=$(new_repo $H)
small_content=$(for i in $(seq 1 10); do printf 'line %d = %d\n' "$i" "$i"; done)
stage "$repo" "app/data.py" "$small_content"
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "/simplify"

# ── Lane resolution fallback (hooks/lib/lane.sh) — F1 regression coverage ──
# The commit under test touches NO specs/ path, so there is no staged SUMMARY.md to
# read. Before the fix, risk-corroboration.sh fell back to "most recently modified
# specs/*/SUMMARY.md on disk" — an unrelated, merely-recently-touched spec could
# corroborate (or wrongly block) a commit it has nothing to do with. The fix requires
# an explicit `status: active` PLAN.md instead of a bare mtime guess.

t "commit touching no specs/ path does NOT borrow an unrelated (non-active) spec's Lane — no active plan, no lane declared → warns, does not corroborate as high-risk"
repo=$(new_repo $H)
# An unrelated, non-active spec sits on disk with a high-risk Lane and is the most
# recently modified SUMMARY.md — the old mtime fallback would have picked this up.
mkdir -p "$repo/specs/unrelated-recent-task"
printf 'Lane: high-risk\n' > "$repo/specs/unrelated-recent-task/SUMMARY.md"
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "no declared Lane"

t "commit touching no specs/ path DOES corroborate against the status:active plan's Lane"
repo=$(new_repo $H)
mkdir -p "$repo/specs/active-task"
printf 'Lane: high-risk\n' > "$repo/specs/active-task/SUMMARY.md"
git -C "$repo" add -f specs/active-task/SUMMARY.md >/dev/null 2>&1
cat > "$repo/specs/active-task/PLAN.md" <<'EOF'
---
status: active
---
EOF
git -C "$repo" add -f specs/active-task/PLAN.md >/dev/null 2>&1
git -C "$repo" commit -qm "seed active task" >/dev/null 2>&1
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "corroborated"

t "commit touching no specs/ path, active plan is below high-risk → BLOCKED (fallback still enforces, not just corroborates)"
repo=$(new_repo $H)
mkdir -p "$repo/specs/active-task"
printf 'Lane: normal\n' > "$repo/specs/active-task/SUMMARY.md"
git -C "$repo" add -f specs/active-task/SUMMARY.md >/dev/null 2>&1
cat > "$repo/specs/active-task/PLAN.md" <<'EOF'
---
status: active
---
EOF
git -C "$repo" add -f specs/active-task/PLAN.md >/dev/null 2>&1
git -C "$repo" commit -qm "seed active task" >/dev/null 2>&1
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

finish
