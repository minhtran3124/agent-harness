#!/bin/bash
# Integration tests for scripts/install-harness.sh — installs from this checkout
# (--source) into throwaway target dirs. Frozen from the 6-case suite that shipped
# the MCP wiring (commit ea3182f).
source "$(dirname "$0")/../lib.sh"

INSTALL="$ROOT/scripts/install-harness.sh"

target() { local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); echo "$d"; }
run_install() { # run_install <target> [extra args/env...]
  local tgt="$1"; shift
  OUT=$(bash "$INSTALL" --source "$ROOT" --yes -d "$tgt" "$@" 2>&1); RC=$?
}

t "dry-run on a fresh target reports the MCP step and writes nothing"
tgt=$(target)
OUT=$(bash "$INSTALL" --source "$ROOT" --dry-run -d "$tgt" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF "would create  .mcp.json" && [ ! -e "$tgt/.claude" ] && [ ! -e "$tgt/.mcp.json" ]; then
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

t "missing uvx warns at preflight but does not fail the install"
tgt=$(target)
OUT=$(env PATH=/usr/bin:/bin bash "$INSTALL" --source "$ROOT" --dry-run -d "$tgt" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF "uvx not found"; then pass; else
  command -v uvx >/dev/null 2>&1 && [ "$RC" -eq 0 ] && skip "uvx reachable even at /usr/bin:/bin" || fail "rc=$RC"
fi

finish
