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
# describing it, and a settings.json registering it. Anything the lint's part-3
# hook-table check needs, and nothing else.
lint_repo() {
  local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  mkdir -p "$d/scripts" "$d/hooks" "$d/agents" "$d/rules" "$d/skills"
  cp "$LINT" "$d/scripts/"
  printf '#!/bin/bash\nexit 0\n' > "$d/hooks/demo.sh"
  cat > "$d/CLAUDE.md" <<'MD'
# demo

| Hook | Trigger | Action | Wired |
|---|---|---|---|
| `demo.sh` | PreToolUse | demo | ✅ |
MD
  cat > "$d/settings.json" <<'JSON'
{"hooks":{"PreToolUse":[{"hooks":[{"command":"hooks/demo.sh"}]}]}}
JSON
  : > "$d/README.md"
  : > "$d/HARNESS.md"
  : > "$d/skills/README.md"
  echo "$d"
}

run_lint() { OUT=$(cd "$1" && bash scripts/lint-doc-truth.sh 2>&1); RC=$?; }

t "baseline fixture is clean (exit 0)"
r=$(lint_repo)
run_lint "$r"
assert_rc 0

t "SCOPE: a dangling path in rules/*.md is caught (regression guard for DOCS)"
r=$(lint_repo)
printf 'See `rules/nope.md` for details.\n' > "$r/rules/behavior.md"
run_lint "$r"
assert_rc_contains 1 "rules/nope.md"

t "SCOPE: a dangling path in agents/*.md is caught (regression guard for DOCS)"
r=$(lint_repo)
printf 'Read `agents/ghost.md` first.\n' > "$r/agents/coding.md"
run_lint "$r"
assert_rc_contains 1 "agents/ghost.md"

t "a real path in rules/*.md passes"
r=$(lint_repo)
printf 'Registered in `hooks/demo.sh`.\n' > "$r/rules/behavior.md"
run_lint "$r"
assert_rc 0

t "placeholder paths in rules/*.md are skipped, not flagged"
r=$(lint_repo)
printf 'Write `tests/services/test_<entity>.py` next to it.\n' > "$r/rules/plan-format.md"
run_lint "$r"
assert_rc 0

t "empty agents/ and rules/ produce no 'core doc missing' (nullglob guard)"
r=$(lint_repo)
rmdir "$r/agents" "$r/rules"
run_lint "$r"
if [ "$RC" -eq 0 ] && ! echo "$OUT" | grep -q 'core doc missing'; then pass
else fail "rc=$RC out: $(echo "$OUT" | head -3 | tr '\n' ' ')"; fi

t "an unknown root in a backticked token is still out of scope (no false positive)"
r=$(lint_repo)
printf 'Upstream lives at `someorg/somerepo`.\n' > "$r/rules/behavior.md"
run_lint "$r"
assert_rc 0

finish
