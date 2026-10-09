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

finish
