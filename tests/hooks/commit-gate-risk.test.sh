#!/bin/bash
# Contract tests for check_risk in hooks/commit-gate.sh — lane-vs-diff corroboration of the
# hard-gate categories: lane vs diff, strict, RISK_WARN_CATEGORIES, regex precision,
# workflow-engine warn, index-only gate modes (SC-8), the diff-size note, the active-plan
# Lane fallback, the shipped-manifest warn-mode smoke, repo-root resolution, ticket-prefixed
# spec slugs, and the --profile minimal/strict behavior of check_risk.
source "$(dirname "$0")/../lib.sh"

H=commit-gate.sh
# Real Claude Bash payload shape (tool_name present): takes the one-jq fast path, so no case
# here depends on python3.
json_bash() { jq -cn --arg c "$1" '{tool_name:"Bash",tool_input:{command:$c}}'; }
COMMIT_JSON=$(json_bash 'git commit -m x')


t "non-commit command is ignored (silent, exit 0)"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_bash 'git status')"
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

# Documented false positive (docs/solutions/harness/, auth words in test comments):
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

t "diff >150 changed lines + Lane: tiny → simplify-pass note printed, exit 0"
repo=$(new_repo $H)
big_content=$(for i in $(seq 1 200); do printf 'line %d = %d\n' "$i" "$i"; done)
stage "$repo" "app/data.py" "$big_content"
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "simplify pass"

t "diff >600 changed lines + Lane: normal → simplify-pass note printed, exit 0"
repo=$(new_repo $H)
big_content=$(for i in $(seq 1 700); do printf 'line %d = %d\n' "$i" "$i"; done)
stage "$repo" "app/data.py" "$big_content"
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "simplify pass"

t "large diff confined to .claude/ (excluded from CODE_ADDED, no other gate) + Lane: tiny → simplify note still fires (unfiltered numstat)"
repo=$(new_repo $H)
big_content=$(for i in $(seq 1 200); do printf 'line %d = %d\n' "$i" "$i"; done)
stage "$repo" ".claude/generated/notes.md" "$big_content"
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "simplify pass"

# Regression for the -U0 numstat bug (gh-159 fix-loop round 2): `-U0` forces `git diff`
# to emit patch mode, so `--numstat` output was numstat rows PLUS the full unified diff
# body — the awk parser then mis-read a content line's SECOND whitespace token as the
# numstat "removed" column whenever it looked numeric (e.g. "timeout 30000" → +=30000).
# True line count here (25 new lines) stays well under the tiny-lane 150 threshold; the
# buggy version inflated it into the tens of thousands and fired the note incorrectly.
t "moderate diff (~25 lines) with numeric-looking tokens under tiny threshold → no simplify note (guards -U0 numstat-inflation regression)"
repo=$(new_repo $H)
numeric_content=$(for i in $(seq 1 25); do printf 'timeout %d\n' "$((i * 1000))"; done)
stage "$repo" "app/config.py" "$numeric_content"
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "simplify pass"

t "small diff under both thresholds → no simplify note"
repo=$(new_repo $H)
small_content=$(for i in $(seq 1 10); do printf 'line %d = %d\n' "$i" "$i"; done)
stage "$repo" "app/data.py" "$small_content"
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "simplify pass"

# ── Lane resolution fallback (hooks/lib/lane.sh) — F1 regression coverage ──
# The commit under test touches NO specs/ path, so there is no staged SUMMARY.md to
# read. Before the fix, the gate fell back to "most recently modified
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

# ── Shipped-manifest warn-mode smoke ──────────────────────────────────────
# Runs against a COPY OF THE REAL harness-manifest.json — proving the shipped manifest, not a
# fixture, produces the intended behavior:
#   1. A Lane: normal commit whose diff trips only weakening-validation (a removed `raise`
#      line) is allowed with a note.
#   2. The loosening is scoped: the same commit ALSO touching hooks/ trips high-blast
#      (block-mode) and is still denied.

t "real manifest: removed raise + Lane: normal → warn-mode note, allowed (exit 0)"
repo=$(new_repo $H)
cp "$ROOT/harness-manifest.json" "$repo/"
git -C "$repo" add -f harness-manifest.json
stage "$repo" "app/svc.py" 'def f(x):
    if not x:
        raise ValueError("x")
    return x'
git -C "$repo" commit -qm base
printf '%s\n' 'def f(x):' '    return x' > "$repo/app/svc.py"
git -C "$repo" add app/svc.py
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "warn-mode"

t "real manifest: same diff + hooks/ file → high-blast still blocks (exit 2)"
repo=$(new_repo $H)
cp "$ROOT/harness-manifest.json" "$repo/"
git -C "$repo" add -f harness-manifest.json
stage "$repo" "app/svc.py" 'def f(x):
    if not x:
        raise ValueError("x")
    return x'
git -C "$repo" commit -qm base
printf '%s\n' 'def f(x):' '    return x' > "$repo/app/svc.py"
git -C "$repo" add app/svc.py
stage "$repo" "hooks/new-gate.sh" '#!/bin/bash'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

# ── Embedded defaults (SC-7): NO manifest anywhere in the index ──────────────
# new_repo copies hooks/lib (incl. gate-modes.default.sh) but stages no manifest, so
# `git show :harness-manifest.json` misses and check_risk sources the embedded defaults —
# the same 2-warn/7-block parity as the shipped manifest, NOT block-all.

t "embedded defaults: workflow-engine surface + Lane: normal → warn note, allowed (exit 0)"
repo=$(new_repo $H)
stage "$repo" "skills/x/SKILL.md" '# Skill x'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "workflow-engine"

t "embedded defaults: auth code + Lane: tiny → block (exit 2)"
repo=$(new_repo $H)
stage "$repo" "app/auth.py" 'def login(password): return password'
stage "$repo" "specs/x/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

t "embedded defaults: hooks/ file (high-blast) + Lane: normal → block (exit 2)"
repo=$(new_repo $H)
stage "$repo" "hooks/new-gate.sh" '#!/bin/bash'
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "high-blast"

# ── Repo-root resolution (specs/fix-hook-project-root-resolution) ─────────
# The hook is placed inside a FOREIGN git repo whose staged hooks/* trips high-blast; the
# project is CWD / CLAUDE_PROJECT_DIR. check_risk must inspect the project, never the repo
# that happens to contain the hook file. Under RISK_CORROBORATION_STRICT=1 a signal with no
# declared Lane exits 2, which makes the wrong-repo outcome observable.

# foreign_host → echoes a git repo that HOSTS commit-gate.sh but is NOT the project.
foreign_host() {
  local d; d=$(mktemp -d)
  _CLEANUP_DIRS+=("$d")
  git -C "$d" init -q -b main 2>/dev/null || git -C "$d" init -q
  git -C "$d" config user.email test@test
  git -C "$d" config user.name test
  mkdir -p "$d/hooks"
  [ -d "$ROOT/hooks/lib" ] && cp -R "$ROOT/hooks/lib" "$d/hooks/"
  cp "$ROOT/hooks/$H" "$d/hooks/"
  printf 'decoy\n' > "$d/hooks/decoy-gate-tripper.sh"
  git -C "$d" add -f hooks/decoy-gate-tripper.sh
  echo "$d"
}

# run_from <project> <host> <json> [VAR=val ...] — hook lives in <host>; CWD is <project>.
run_from() {
  local proj="$1" host="$2" json="$3"; shift 3
  OUT=$(cd "$proj" && printf '%s' "$json" | env "$@" bash "$host/hooks/$H" 2>&1); RC=$?
}

t "repo root: hook hosted in a foreign git repo does NOT inspect that repo (CWD wins)"
proj=$(new_repo); host=$(foreign_host)
stage "$proj" "README.md" "harmless"
run_from "$proj" "$host" "$COMMIT_JSON" RISK_CORROBORATION_STRICT=1
assert_rc 0

t "repo root: CLAUDE_PROJECT_DIR wins over the foreign host repo"
proj=$(new_repo); host=$(foreign_host)
stage "$proj" "README.md" "harmless"
run_from "/" "$host" "$COMMIT_JSON" RISK_CORROBORATION_STRICT=1 CLAUDE_PROJECT_DIR="$proj"
assert_rc 0

t "repo root: still BLOCKS on a real signal in the PROJECT (resolution did not disable check_risk)"
proj=$(new_repo); host=$(foreign_host)
mkdir -p "$proj/hooks"; stage "$proj" "hooks/real.sh" "echo real"
run_from "$proj" "$host" "$COMMIT_JSON" RISK_CORROBORATION_STRICT=1
assert_rc 2

t "repo root: no resolvable project root → BLOCKS rather than guessing"
host=$(foreign_host); outside=$(mktemp -d); _CLEANUP_DIRS+=("$outside")
run_from "$outside" "$host" "$COMMIT_JSON"
assert_rc_contains 2 "cannot determine the project root"

# ── Ticket-prefixed spec slugs (issue #121) ───────────────────────────────
# Lane is resolved from specs/<anything>/SUMMARY.md, not from slug shape.
GH="gh-999-fixture"

t "reads Lane: high-risk from a gh-prefixed SUMMARY → corroborated"
repo=$(new_repo $H)
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
stage "$repo" "specs/$GH/SUMMARY.md" "Lane: high-risk"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "corroborated"

t "still blocks a low lane declared in a gh-prefixed SUMMARY"
repo=$(new_repo $H)
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
stage "$repo" "specs/$GH/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "BLOCKED"

# ── Profiles ──────────────────────────────────────────────────────────────
t "--profile minimal skips check_risk: tripped block-mode category + Lane: normal → allowed (exit 0)"
repo=$(new_repo $H)
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
stage "$repo" "specs/x/SUMMARY.md" "Lane: normal"
run_hook_args "$repo" $H "$COMMIT_JSON" --profile minimal
assert_rc_not_contains 0 "RISK CORROBORATION"

t "--profile strict blocks a tripped category with no declared Lane (exit 2, no env var)"
repo=$(new_repo $H)
stage "$repo" "alembic/versions/abc_add_table.py" "def upgrade(): pass"
run_hook_args "$repo" $H "$COMMIT_JSON" --profile strict
assert_rc_contains 2 "strict, no Lane declared"

finish
