#!/bin/bash
# Contract tests for the setup skill: its SKILL.md steps and the old-install finder.
source "$(dirname "$0")/../lib.sh"

DIR="$ROOT/plugins/harness/skills/setup"
SKILL="$DIR/SKILL.md"
OLD="$DIR/scripts/old-install.sh"

t "SKILL.md frontmatter: name setup, user-invoked only, declares allowed-tools"
fm=$(awk 'NR==1&&/^---$/{inb=1;next} inb&&/^---$/{exit} inb' "$SKILL")
if printf '%s\n' "$fm" | grep -q '^name: setup$' && printf '%s\n' "$fm" | grep -q '^disable-model-invocation: true$' \
   && printf '%s\n' "$fm" | grep -qE '^allowed-tools:.*AskUserQuestion'; then pass; else fail "frontmatter: $fm"; fi

t "SKILL.md is at most 80 lines and under 600 words"
lines=$(wc -l < "$SKILL" | tr -d ' '); words=$(wc -w < "$SKILL" | tr -d ' ')
if [ "$lines" -le 80 ] && [ "$words" -lt 600 ]; then pass; else fail "lines=$lines words=$words"; fi

t "SKILL.md runs init-structure, creates PROJECT.md, merges deny, ignores specs/"
if grep -q '${CLAUDE_PLUGIN_ROOT}/scripts/init-structure.sh' "$SKILL" \
   && grep -q 'agents/PROJECT.md' "$SKILL" && grep -q 'merge-deny.sh' "$SKILL" \
   && grep -q '\.gitignore' "$SKILL" && grep -q 'specs/' "$SKILL"; then pass; else fail "a setup step is missing"; fi

t "SKILL.md asks before deleting an old install and deletes only listed paths"
if grep -q 'AskUserQuestion' "$SKILL" && grep -q 'old-install.sh' "$SKILL" && grep -q 'only those paths' "$SKILL"; then pass
else fail "the approval step is missing"; fi

t "every file the SKILL.md names under CLAUDE_SKILL_DIR exists"
ok=1
for f in $(grep -oE '\$\{CLAUDE_SKILL_DIR\}/[A-Za-z0-9_./-]+' "$SKILL" | sed 's#\${CLAUDE_SKILL_DIR}/##' | sort -u); do
  [ -f "$DIR/$f" ] || { ok=0; echo "        missing: $f"; }
done
[ "$ok" -eq 1 ] && pass || fail "a referenced file is missing"

t "the PROJECT.md template resource and the init-structure templates exist"
if [ -f "$DIR/resources/PROJECT.template.md" ] && [ -f "$ROOT/plugins/harness/templates/structure/specs-README.md" ] \
   && [ -x "$ROOT/plugins/harness/scripts/init-structure.sh" ]; then pass; else fail "a setup resource is missing"; fi

t "old-install.sh lists harness-named files and leaves the project's own files out"
d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
mkdir -p "$d/.claude/skills/intake" "$d/.claude/skills/my-own" "$d/.claude/hooks" "$d/.claude/agents" "$d/.claude/workflows" "$d/.claude/templates"
: > "$d/.claude/hooks/secrets-scan.sh"; : > "$d/.claude/hooks/my-hook.sh"; : > "$d/.claude/agents/implementer.md"
: > "$d/.claude/agents/my-agent.md"; : > "$d/.claude/workflows/ship.js"; : > "$d/.claude/.harness-deployed"; : > "$d/.claude/settings.local.json"
OUT=$(bash "$OLD" "$d"); RC=$?
want="intake secrets-scan.sh implementer.md ship.js .harness-deployed templates"
miss=""; for w in $want; do printf '%s\n' "$OUT" | grep -q "$w" || miss="$miss $w"; done
if [ "$RC" -eq 0 ] && [ -z "$miss" ] && ! printf '%s\n' "$OUT" | grep -qE 'my-own|my-hook|my-agent|settings.local'; then pass
else fail "rc=$RC missing:$miss out: $OUT"; fi

t "old-install.sh deletes nothing and prints nothing for a project without .claude/"
d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
OUT=$(bash "$OLD" "$d"); RC=$?
if [ "$RC" -eq 0 ] && [ -z "$OUT" ]; then pass; else fail "rc=$RC out: $OUT"; fi

t "old-install.sh did not remove anything it listed"
d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); mkdir -p "$d/.claude/skills/intake"
bash "$OLD" "$d" >/dev/null
if [ -d "$d/.claude/skills/intake" ]; then pass; else fail "the finder deleted a path"; fi

t "old-install.sh --strip-hooks removes only the hooks that point into .claude/hooks/"
if ! command -v jq >/dev/null 2>&1; then skip "jq is not installed"
else
  d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  cat > "$d/s.json" <<'JSON'
{"model":"opus","hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"$CLAUDE_PROJECT_DIR/.claude/hooks/secrets-scan.sh"}]}],"PostToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"$CLAUDE_PROJECT_DIR/.claude/hooks/pr-opened.sh"},{"type":"command","command":"my-own-hook.sh"}]}]}}
JSON
  bash "$OLD" --strip-hooks "$d/s.json" >/dev/null; rc=$?
  if [ "$rc" -eq 0 ] && jq -e '.model == "opus" and (.hooks | has("PreToolUse") | not) and (.hooks.PostToolUse | length) == 1 and .hooks.PostToolUse[0].hooks == [{"type":"command","command":"my-own-hook.sh"}]' "$d/s.json" >/dev/null; then pass
  else fail "rc=$rc file: $(cat "$d/s.json")"; fi
fi

finish
