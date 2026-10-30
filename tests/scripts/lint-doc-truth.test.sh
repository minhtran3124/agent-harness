#!/bin/bash
# Contract tests for scripts/lint-doc-truth.sh.
#
# The scope cases are the point: agents/*.md and rules/*.md were NOT linted until
# PR #121, which is how stale `skills/xia2/PROJECT.md` pointers survived in agents/
# (found by hand in PR #119). These tests are the regression guard against a future
# edit narrowing DOCS back to the four top-level docs.
source "$(dirname "$0")/../lib.sh"

LINT="$ROOT/scripts/lint-doc-truth.sh"

# A minimal repo the lint can run against: one wired hook, a CLAUDE.md table row
# describing it, and a plugin hooks.json registering it. Anything the lint's part-3
# hook-table check needs, and nothing else.
lint_repo() {
  local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  P="$d/plugins/harness"
  mkdir -p "$d/scripts" "$P/hooks" "$P/agents" "$P/rules" "$P/skills"
  cp "$LINT" "$d/scripts/"
  printf '#!/bin/bash\nexit 0\n' > "$P/hooks/demo.sh"
  cat > "$d/CLAUDE.md" <<'MD'
# demo

| Hook | Trigger | Action | Wired |
|---|---|---|---|
| `demo.sh` | PreToolUse | demo | ✅ |
MD
  cat > "$P/hooks/hooks.json" <<'JSON'
{"hooks":{"PreToolUse":[{"hooks":[{"type":"command","command":"bash","args":["${CLAUDE_PLUGIN_ROOT}/hooks/demo.sh"]}]}]}}
JSON
  : > "$d/README.md"
  : > "$d/HARNESS.md"
  mkdir -p "$d/docs"; : > "$d/docs/hooks.md"
  : > "$P/skills/README.md"
  echo "$d"
}

run_lint() { OUT=$(cd "$1" && bash scripts/lint-doc-truth.sh 2>&1); RC=$?; }

t "baseline fixture is clean (exit 0)"
r=$(lint_repo)
run_lint "$r"
assert_rc 0

t "SCOPE: a dangling path in rules/*.md is caught (regression guard for DOCS)"
r=$(lint_repo)
printf 'See `rules/nope.md` for details.\n' > "$r/plugins/harness/rules/behavior.md"
run_lint "$r"
assert_rc_contains 1 "rules/nope.md"

t "a dangling path in the plugin tree is caught even when the repo has that file"
r=$(lint_repo)
mkdir -p "$r/scripts"; : > "$r/scripts/only-in-repo.sh"
mkdir -p "$r/plugins/harness/skills/demo"
printf 'Run `scripts/only-in-repo.sh` first.\n' > "$r/plugins/harness/skills/demo/SKILL.md"
run_lint "$r"
assert_rc_contains 1 "plugin tree: skills/demo/SKILL.md:1 -> scripts/only-in-repo.sh"

t "a CLAUDE_PLUGIN_ROOT and a CLAUDE_SKILL_DIR path that exist in the plugin pass"
r=$(lint_repo)
mkdir -p "$r/plugins/harness/skills/demo/scripts" "$r/plugins/harness/scripts"
: > "$r/plugins/harness/skills/demo/scripts/x.sh"; : > "$r/plugins/harness/scripts/y.py"
printf 'Run `${CLAUDE_SKILL_DIR}/scripts/x.sh` and `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/y.py`.\n' > "$r/plugins/harness/skills/demo/SKILL.md"
run_lint "$r"
assert_rc 0

t "a CLAUDE_PLUGIN_ROOT path that does not exist in the plugin is caught"
r=$(lint_repo)
mkdir -p "$r/plugins/harness/skills/demo"
printf 'Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gone.py`.\n' > "$r/plugins/harness/skills/demo/SKILL.md"
run_lint "$r"
assert_rc_contains 1 "scripts/gone.py"

t "a hook marked wired in CLAUDE.md but missing from hooks.json is caught"
r=$(lint_repo)
printf '{"hooks":{}}\n' > "$r/plugins/harness/hooks/hooks.json"
run_lint "$r"
assert_rc_contains 1 "'demo.sh' is wired but it is not in"

t "a repo settings.json that also wires hooks is caught (it would run twice)"
r=$(lint_repo)
printf '{"hooks":{"PreToolUse":[{"hooks":[{"command":"x"}]}]}}\n' > "$r/settings.json"
run_lint "$r"
assert_rc_contains 1 "would run twice"

t "SCOPE: a dangling path in agents/*.md is caught (regression guard for DOCS)"
r=$(lint_repo)
printf 'Read `agents/ghost.md` first.\n' > "$r/plugins/harness/agents/implementer.md"
run_lint "$r"
assert_rc_contains 1 "agents/ghost.md"

t "a real path in rules/*.md passes"
r=$(lint_repo)
printf 'Registered in `hooks/demo.sh`.\n' > "$r/plugins/harness/rules/behavior.md"
run_lint "$r"
assert_rc 0

t "placeholder paths in rules/*.md are skipped, not flagged"
r=$(lint_repo)
printf 'Write `tests/services/test_<entity>.py` next to it.\n' > "$r/plugins/harness/rules/local-rule.md"
run_lint "$r"
assert_rc 0

t "empty agents/ and rules/ produce no 'core doc missing' (nullglob guard)"
r=$(lint_repo)
rmdir "$r/plugins/harness/agents" "$r/plugins/harness/rules"
run_lint "$r"
if [ "$RC" -eq 0 ] && ! echo "$OUT" | grep -q 'core doc missing'; then pass
else fail "rc=$RC out: $(echo "$OUT" | head -3 | tr '\n' ' ')"; fi

t "an unknown root in a backticked token is still out of scope (no false positive)"
r=$(lint_repo)
printf 'Upstream lives at `someorg/somerepo`.\n' > "$r/plugins/harness/rules/behavior.md"
run_lint "$r"
assert_rc 0

finish
