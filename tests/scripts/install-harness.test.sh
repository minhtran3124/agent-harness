#!/bin/bash
# Integration tests for scripts/install-harness.sh — installs from this checkout
# (--source) into throwaway target dirs. The installer never reads, writes or backs up
# a consumer .mcp.json; the .mcp.json cases below assert it is left byte-identical.
source "$(dirname "$0")/../lib.sh"

INSTALL="$ROOT/scripts/install-harness.sh"
MEMORY_DIR="agent""-memory"

# Sets TARGET in the calling shell: $(target) would run in a subshell and lose the cleanup entry.
target() { TARGET=$(mktemp -d); _CLEANUP_DIRS+=("$TARGET"); }
run_install() { # run_install <target> [extra args/env...]
  local tgt="$1"; shift
  OUT=$(bash "$INSTALL" --source "$ROOT" --yes -d "$tgt" "$@" 2>&1); RC=$?
}

t "dry-run on a fresh target writes nothing"
target; tgt=$TARGET
OUT=$(bash "$INSTALL" --source "$ROOT" --dry-run -d "$tgt" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && ! echo "$OUT" | grep -qF ".mcp.json" && ! echo "$OUT" | grep -qiF "$MEMORY_DIR" && [ ! -e "$tgt/.claude" ] && [ ! -e "$tgt/.mcp.json" ] && [ -z "$(find "$tgt" -mindepth 1 -print -quit)" ]; then
  pass
else
  fail "rc=$RC, .claude exists: $([ -e "$tgt/.claude" ] && echo yes || echo no)"
fi

t "fresh install creates no .mcp.json, builds .claude/, prunes root sources"
target; tgt=$TARGET
run_install "$tgt"
if [ "$RC" -eq 0 ] \
   && [ ! -e "$tgt/.mcp.json" ] && ! echo "$OUT" | grep -qF ".mcp.json" \
   && [ -d "$tgt/.claude/skills" ] && [ ! -e "$tgt/skills" ]; then
  pass
else
  fail "rc=$RC — .mcp.json/.claude/prune state wrong: $(ls -a "$tgt" | tr '\n' ' ')"
fi

t "fresh install scaffolds five structural files and memory-free agents"
target; tgt=$TARGET
run_install "$tgt"
if [ "$RC" -eq 0 ] \
   && [ -f "$tgt/specs/README.md" ] && [ ! -e "$tgt/specs/STATE.md" ] \
   && [ -f "$tgt/docs/solutions/README.md" ] && [ -f "$tgt/docs/solutions/INDEX.md" ] \
   && [ -f "$tgt/docs/solutions/critical-patterns.md" ] && [ -f "$tgt/techstacks/README.md" ] \
   && [ ! -e "$tgt/$MEMORY_DIR" ] \
   && ! grep -q '^memory:' "$tgt/.claude/agents/implementer.md" \
   && ! grep -q '^memory:' "$tgt/.claude/agents/intent-reviewer.md" \
   && ! grep -q '^memory:' "$tgt/.claude/agents/test-runner.md"; then
  pass
else
  fail "rc=$RC — structural scaffolding missing: $(ls -a "$tgt" | tr '\n' ' ')"
fi

t "fresh install emits Claude-bound agents, not source-time binding metadata"
target; tgt=$TARGET
run_install "$tgt"
if [ "$RC" -eq 0 ] \
   && grep -q '^model: claude-sonnet-5-5$' "$tgt/.claude/agents/intent-reviewer.md" \
   && grep -q '^tools: Glob, Grep, Read, Bash$' "$tgt/.claude/agents/intent-reviewer.md" \
   && [ ! -e "$tgt/.claude/agents/agent-contracts.json" ] \
   && [ ! -e "$tgt/.claude/agents/runtime-bindings.json" ]; then
  pass
else
  fail "rc=$RC — agent renderer output/boundary is wrong"
fi

t "reinstall does not recreate the removed directory"
target; tgt=$TARGET
run_install "$tgt"
run_install "$tgt"
if [ "$RC" -eq 0 ] && [ ! -e "$tgt/$MEMORY_DIR" ]; then pass; else fail "rc=$RC"; fi

t "pre-existing consumer directory is untouched"
target; tgt=$TARGET
mkdir -p "$tgt/$MEMORY_DIR/nested"
printf 'KEEP ME\n' > "$tgt/$MEMORY_DIR/KEEP.md"
printf 'NESTED\n' > "$tgt/$MEMORY_DIR/nested/value.txt"
manifest_before=$(find "$tgt/$MEMORY_DIR" -type f -print | sed "s#^$tgt/$MEMORY_DIR/##" | sort)
content_before=$(cat "$tgt/$MEMORY_DIR/KEEP.md")
run_install "$tgt"
manifest_after=$(find "$tgt/$MEMORY_DIR" -type f -print | sed "s#^$tgt/$MEMORY_DIR/##" | sort)
content_after=$(cat "$tgt/$MEMORY_DIR/KEEP.md")
if [ "$RC" -eq 0 ] && [ "$manifest_before" = "$manifest_after" ] && [ "$content_before" = "$content_after" ]; then pass; else fail "rc=$RC manifest/content changed"; fi

t "install never clobbers a pre-existing structural file"
target; tgt=$TARGET
mkdir -p "$tgt/docs/solutions"
printf 'MY REAL INDEX\n' > "$tgt/docs/solutions/INDEX.md"
run_install "$tgt"
if [ "$RC" -eq 0 ] && [ "$(cat "$tgt/docs/solutions/INDEX.md")" = "MY REAL INDEX" ]; then
  pass
else
  fail "rc=$RC — pre-existing INDEX.md was clobbered: [$(cat "$tgt/docs/solutions/INDEX.md" 2>&1)]"
fi

assert_mcp_untouched() { # assert_mcp_untouched <target> <copy taken before install>
  if [ "$RC" -eq 0 ] && cmp -s "$2" "$1/.mcp.json" && ! ls "$1"/.harness-backup-*/.mcp.json >/dev/null 2>&1; then
    pass
  else
    fail "rc=$RC content=[$(cat "$1/.mcp.json" 2>&1)] backup=$(ls "$1"/.harness-backup-* 2>/dev/null | head -1)"
  fi
}

t "existing .mcp.json with other servers is left byte-identical (no backup)"
target; tgt=$TARGET
echo '{"mcpServers":{"context7":{"type":"http","url":"https://example.com"}}}' > "$tgt/.mcp.json"
target; before="$TARGET/mcp.json"; cp "$tgt/.mcp.json" "$before"
run_install "$tgt"
assert_mcp_untouched "$tgt" "$before"

t "re-install on a target with .mcp.json leaves it unchanged"
run_install "$tgt"
assert_mcp_untouched "$tgt" "$before"

t "existing .mcp.json with a code-review-graph entry is left byte-identical (no backup)"
target; tgt=$TARGET
echo '{"mcpServers":{"code-review-graph":{"command":"uvx","args":["code-review-graph","serve"]}}}' > "$tgt/.mcp.json"
target; before="$TARGET/mcp.json"; cp "$tgt/.mcp.json" "$before"
run_install "$tgt"
assert_mcp_untouched "$tgt" "$before"

t "invalid existing .mcp.json is left untouched without a warning"
target; tgt=$TARGET
printf 'NOT JSON {' > "$tgt/.mcp.json"
target; before="$TARGET/mcp.json"; cp "$tgt/.mcp.json" "$before"
run_install "$tgt"
if echo "$OUT" | grep -qF "not valid JSON"; then
  fail "installer warned about .mcp.json"
else
  assert_mcp_untouched "$tgt" "$before"
fi

t "missing uvx is not mentioned and does not fail the install"
target; tgt=$TARGET
OUT=$(env PATH=/usr/bin:/bin bash "$INSTALL" --source "$ROOT" --dry-run -d "$tgt" 2>&1); RC=$?
assert_rc_not_contains 0 "uvx"

finish
