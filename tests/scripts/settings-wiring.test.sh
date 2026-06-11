#!/bin/bash
# Wiring smoke test: settings.json and the deployed .claude/settings.json must be internally
# consistent — valid JSON, every registered hook command resolves to an executable bash
# script, and the derivation (root relative path → $CLAUDE_PROJECT_DIR/.claude/<path>) holds.
# This tests the wiring, not the hook bodies (those are the tests/hooks/ suites).
source "$(dirname "$0")/../lib.sh"
cd "$ROOT" || exit 1

t "settings.json is valid JSON"
if jq -e . settings.json >/dev/null 2>&1; then pass; else fail "settings.json does not parse"; fi

t "every settings.json hook command resolves to a file with a bash shebang"
ok=1
while IFS= read -r cmd; do
  [ -z "$cmd" ] && continue
  case "$cmd" in '$CLAUDE_PROJECT_DIR/'*) cmd="${cmd#\$CLAUDE_PROJECT_DIR/}"; cmd="${cmd#.claude/}" ;; esac
  if [ ! -f "$cmd" ]; then ok=0; echo "        missing: $cmd"; continue; fi
  head -1 "$cmd" | grep -q '^#!.*sh' || { ok=0; echo "        no shebang: $cmd"; }
done < <(jq -r '.hooks[]?[]?.hooks[]?.command // empty' settings.json)
[ "$ok" -eq 1 ] && pass || fail "one or more commands unresolved / not a shell script"

if [ -f .claude/settings.json ]; then
  t ".claude/settings.json is valid JSON"
  if jq -e . .claude/settings.json >/dev/null 2>&1; then pass; else fail ".claude/settings.json does not parse"; fi

  t "deploy derivation holds: each root command maps to \$CLAUDE_PROJECT_DIR/.claude/<path>"
  root_cmds=$(jq -r '.hooks[]?[]?.hooks[]?.command // empty' settings.json | sort)
  drv_cmds=$(jq -r '.hooks[]?[]?.hooks[]?.command // empty' .claude/settings.json | sort)
  expected=$(echo "$root_cmds" | while IFS= read -r c; do
    # absolute paths and $-vars are left unchanged by deploy; relative paths are prefixed
    if [ "${c#/}" != "$c" ] || [ "${c#\$}" != "$c" ]; then
      echo "$c"
    else
      echo "\$CLAUDE_PROJECT_DIR/.claude/$c"
    fi
  done | sort)
  if [ "$drv_cmds" = "$expected" ]; then pass
  else fail "derived commands differ from expectation:\n        got:  $(echo "$drv_cmds" | tr '\n' ' ')\n        want: $(echo "$expected" | tr '\n' ' ')"; fi
else
  t ".claude/settings.json checks"; skip ".claude/ not built (run scripts/deploy-harness.sh)"
fi

finish
