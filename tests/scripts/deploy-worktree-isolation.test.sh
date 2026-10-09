#!/bin/bash
# Tests for deploy-harness.sh derive-time transforms staying out of nested checkouts (issue #276).
# Harness worktrees live at <repo>/.claude/worktrees/<name>, inside the derived .claude/ tree, so a
# recursive walk of .claude/ reaches their SOURCE files. A deploy in one checkout must never
# rewrite helper paths or strip harness-only regions in another checkout's files.
source "$(dirname "$0")/../lib.sh"

DEPLOY="$ROOT/scripts/deploy-harness.sh"
new_target() { local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); echo "$d"; }
deploy() { bash "$DEPLOY" --target "$1" </dev/null >/dev/null 2>&1; }

# A source doc that both transforms would change: a root-relative helper path and a fenced region.
seed_doc() {
  mkdir -p "$(dirname "$1")"
  cat > "$1" <<'EOF'
Run `python3 scripts/verify_summary.py --lane x` and read harness-manifest.json.
<!-- harness-only:begin -->
maintenance-only rationale
<!-- harness-only:end -->
tail line
EOF
}

t "a file under .claude/worktrees/<name>/ is byte-for-byte unchanged by a deploy"
T=$(new_target)
F="$T/.claude/worktrees/x/skills/foo.md"; seed_doc "$F"; before=$(cat "$F")
deploy "$T"
if [ "$(cat "$F")" = "$before" ]; then pass
else fail "worktree source doc was rewritten: $(diff <(printf '%s\n' "$before") "$F" | head -3 | tr '\n' ' ')"; fi

t "a nested checkout elsewhere under .claude/ (own .git file) is left unchanged"
T=$(new_target)
mkdir -p "$T/.claude/other-checkout"
printf 'gitdir: /nonexistent/.git/worktrees/other\n' > "$T/.claude/other-checkout/.git"
F="$T/.claude/other-checkout/docs/notes.md"; seed_doc "$F"; before=$(cat "$F")
deploy "$T"
if [ "$(cat "$F")" = "$before" ]; then pass
else fail "nested checkout doc was rewritten"; fi

t "a nested repository under .claude/ (own .git dir) is left unchanged"
T=$(new_target)
mkdir -p "$T/.claude/vendor-repo/.git"
F="$T/.claude/vendor-repo/README.md"; seed_doc "$F"; before=$(cat "$F")
deploy "$T"
if [ "$(cat "$F")" = "$before" ]; then pass
else fail "nested repository doc was rewritten"; fi

t "derived docs are still transformed when a worktree is present (skip is not a disable)"
T=$(new_target); seed_doc "$T/.claude/worktrees/x/skills/foo.md"
deploy "$T"
D="$T/.claude/skills/feature-intake/SKILL.md"
if grep -qF 'python3 .claude/scripts/verify_summary.py' "$D" \
   && ! grep -qF 'harness-only:begin' "$T/.claude/skills/README.md"; then pass
else fail "derived feature-intake path not rewritten, or README fence not stripped"; fi

t "a synced dir the consumer keeps under git still gets its harness docs transformed"
T=$(new_target)
mkdir -p "$T/.claude/skills/.git"
deploy "$T"
if grep -qF 'python3 .claude/scripts/verify_summary.py' "$T/.claude/skills/feature-intake/SKILL.md"; then pass
else fail "harness doc inside a git-managed .claude/skills/ was skipped by the nested-checkout guard"; fi

t "a consumer's nested checkout under .claude/skills/ keeps its tests (strip_skill_tests)"
T=$(new_target)
S="$T/.claude/skills/consumer-sub"
mkdir -p "$S/tests" "$S/lib"
printf 'gitdir: /nonexistent/.git/modules/consumer-sub\n' > "$S/.git"
echo a > "$S/tests/test_a.py"; echo b > "$S/lib/test_b.py"
deploy "$T"
if [ -f "$S/tests/test_a.py" ] && [ -f "$S/lib/test_b.py" ] \
   && [ ! -e "$T/.claude/skills/xia2/tests" ] && [ ! -e "$T/.claude/skills/visual-planner/test_render_plan.py" ]; then pass
else fail "nested checkout lost its tests, or harness skill tests were not stripped"; fi

t "strip_skill_tests: a nested-checkout tests/ dir and a dangling .git symlink are both left alone"
T=$(new_target)
A="$T/.claude/skills/fixtures-sub"; B="$T/.claude/skills/moved-gitdir"
mkdir -p "$A/tests" "$B/tests"
printf 'gitdir: /nonexistent/.git/modules/fixtures\n' > "$A/tests/.git"; echo a > "$A/tests/test_a.py"
ln -s /nonexistent/gitdir "$B/.git"; echo b > "$B/tests/test_b.py"
deploy "$T"
if [ -f "$A/tests/test_a.py" ] && [ -f "$A/tests/.git" ] && [ -f "$B/tests/test_b.py" ]; then pass
else fail "a nested checkout's tests were deleted (tests/.git or dangling .git symlink not honoured)"; fi

t "strip_skill_tests: a symlinked test_*.py in a plain consumer skill is still stripped"
T=$(new_target)
mkdir -p "$T/.claude/skills/plain"; ln -s /nonexistent/x.py "$T/.claude/skills/plain/test_link.py"
deploy "$T"
if [ ! -L "$T/.claude/skills/plain/test_link.py" ]; then pass
else fail "symlinked test_*.py survived the strip (regression vs find -delete)"; fi

finish
