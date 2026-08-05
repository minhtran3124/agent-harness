#!/bin/bash
# Integration tests for scripts/install-harness.sh — installs from this checkout
# (--source) into throwaway target dirs. Frozen from the 6-case suite that shipped
# the MCP wiring (commit ea3182f).
source "$(dirname "$0")/../lib.sh"

INSTALL="$ROOT/scripts/install-harness.sh"
MEMORY_DIR="agent""-memory"

target() { local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); echo "$d"; }
run_install() { # run_install <target> [extra args/env...]
  local tgt="$1"; shift
  OUT=$(bash "$INSTALL" --source "$ROOT" --yes -d "$tgt" "$@" 2>&1); RC=$?
}

t "dry-run on a fresh target writes nothing"
tgt=$(target)
OUT=$(bash "$INSTALL" --source "$ROOT" --dry-run -d "$tgt" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF "would create  .mcp.json" && ! echo "$OUT" | grep -qiF "$MEMORY_DIR" && [ ! -e "$tgt/.claude" ] && [ ! -e "$tgt/.mcp.json" ] && [ -z "$(find "$tgt" -mindepth 1 -print -quit)" ]; then
  pass
else
  fail "rc=$RC, .claude exists: $([ -e "$tgt/.claude" ] && echo yes || echo no)"
fi

t "fresh install creates valid .mcp.json, builds .claude/, prunes root sources"
tgt=$(target)
run_install "$tgt"
if [ "$RC" -eq 0 ] \
   && jq -e '.mcpServers["code-review-graph"]' "$tgt/.mcp.json" >/dev/null 2>&1 \
   && [ -d "$tgt/.claude/skills" ] && [ ! -e "$tgt/skills" ]; then
  pass
else
  fail "rc=$RC — mcp/.claude/prune state wrong: $(ls -a "$tgt" | tr '\n' ' ')"
fi

t "fresh install scaffolds six structural files and memory-free agents"
tgt=$(target)
run_install "$tgt"
if [ "$RC" -eq 0 ] \
   && [ -f "$tgt/specs/README.md" ] && [ -f "$tgt/specs/STATE.md" ] \
   && [ -f "$tgt/docs/solutions/README.md" ] && [ -f "$tgt/docs/solutions/INDEX.md" ] \
   && [ -f "$tgt/docs/solutions/critical-patterns.md" ] && [ -f "$tgt/techstacks/README.md" ] \
   && [ ! -e "$tgt/$MEMORY_DIR" ] \
   && ! grep -q '^memory:' "$tgt/.claude/agents/coding.md" \
   && ! grep -q '^memory:' "$tgt/.claude/agents/reviewer.md" \
   && ! grep -q '^memory:' "$tgt/.claude/agents/test-runner.md"; then
  pass
else
  fail "rc=$RC — structural scaffolding missing: $(ls -a "$tgt" | tr '\n' ' ')"
fi

t "reinstall does not recreate the removed directory"
tgt=$(target)
run_install "$tgt"
run_install "$tgt"
if [ "$RC" -eq 0 ] && [ ! -e "$tgt/$MEMORY_DIR" ]; then pass; else fail "rc=$RC"; fi

t "pre-existing consumer directory is untouched"
tgt=$(target)
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
tgt=$(target)
mkdir -p "$tgt/docs/solutions"
printf 'MY REAL INDEX\n' > "$tgt/docs/solutions/INDEX.md"
run_install "$tgt"
if [ "$RC" -eq 0 ] && [ "$(cat "$tgt/docs/solutions/INDEX.md")" = "MY REAL INDEX" ]; then
  pass
else
  fail "rc=$RC — pre-existing INDEX.md was clobbered: [$(cat "$tgt/docs/solutions/INDEX.md" 2>&1)]"
fi

t "existing .mcp.json with other servers is merged, not replaced (backup taken)"
tgt=$(target)
echo '{"mcpServers":{"context7":{"type":"http","url":"https://example.com"}}}' > "$tgt/.mcp.json"
run_install "$tgt"
keys=$(jq -r '.mcpServers | keys | join(",")' "$tgt/.mcp.json" 2>/dev/null)
if [ "$RC" -eq 0 ] && [ "$keys" = "code-review-graph,context7" ] && ls "$tgt"/.harness-backup-*/.mcp.json >/dev/null 2>&1; then
  pass
else
  fail "rc=$RC keys=[$keys] backup=$(ls "$tgt"/.harness-backup-* 2>/dev/null | head -1)"
fi

t "re-install on an already-wired target is idempotent"
run_install "$tgt"
assert_rc_contains 0 "already wires code-review-graph"

t "invalid existing .mcp.json is left untouched with a warning"
tgt=$(target)
printf 'NOT JSON {' > "$tgt/.mcp.json"
run_install "$tgt"
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF "not valid JSON" && [ "$(cat "$tgt/.mcp.json")" = "NOT JSON {" ]; then
  pass
else
  fail "rc=$RC content=[$(cat "$tgt/.mcp.json")]"
fi

t "install deploys scripts/ so a deployed skill helper can load its dependency"
# E003 (specs/require-claude-simplify-gate/): skills/**/scripts/simplify_record.py resolves
# check_review_receipt.py through the repo root. Without a deployed .claude/scripts/ it died at
# import — before argparse — in every consuming repo. Run the DEPLOYED copy, not the source.
tgt=$(target)
run_install "$tgt"
helper="$tgt/.claude/skills/subagent-driven-development/scripts/simplify_record.py"
if [ "$RC" -eq 0 ] && [ -f "$tgt/.claude/scripts/check_review_receipt.py" ] \
   && [ -f "$helper" ] && (cd /tmp && python3 "$helper" --help >/dev/null 2>&1); then
  pass
else
  fail "rc=$RC — deployed helper cannot load its dependency: $(cd /tmp && python3 "$helper" --help 2>&1 | tail -1)"
fi

t "a consumer's own scripts/ is not reported as harness leftovers"
# `scripts` joined PAYLOAD for E003, but no prior installer ever staged it at a consumer root.
# Scanning PAYLOAD for legacy paths would tell every project with a scripts/ dir to delete it.
tgt=$(target)
mkdir -p "$tgt/scripts"
printf 'echo mine\n' > "$tgt/scripts/build.sh"
run_install "$tgt"
if [ "$RC" -eq 0 ] && [ -f "$tgt/scripts/build.sh" ] \
   && ! echo "$OUT" | grep -qE "older install layout:.*(^|[[:space:]])scripts([[:space:]]|$)"; then
  pass
else
  fail "rc=$RC — consumer scripts/ flagged as legacy or removed: $(echo "$OUT" | grep -i 'older install layout' || echo 'file missing')"
fi

t "missing uvx warns at preflight but does not fail the install"
tgt=$(target)
OUT=$(env PATH=/usr/bin:/bin bash "$INSTALL" --source "$ROOT" --dry-run -d "$tgt" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF "uvx not found"; then pass; else
  command -v uvx >/dev/null 2>&1 && [ "$RC" -eq 0 ] && skip "uvx reachable even at /usr/bin:/bin" || fail "rc=$RC"
fi

finish
