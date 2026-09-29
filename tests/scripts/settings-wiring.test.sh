#!/bin/bash
# Wiring smoke test: settings.json and the deployed .claude/settings.json must be internally
# consistent — valid JSON, every registered hook command resolves to an executable bash
# script, and the derivation (root relative path → $CLAUDE_PROJECT_DIR/.claude/<path>) holds.
# This tests the wiring, not the hook bodies (those are the tests/hooks/ suites).
source "$(dirname "$0")/../lib.sh"
cd "$ROOT" || exit 1

t "settings.json is valid JSON"
if jq -e . settings.json >/dev/null 2>&1; then pass; else fail "settings.json does not parse"; fi

t "every settings.json hook command resolves to an executable file with a bash shebang"
ok=1
while IFS= read -r cmd; do
  [ -z "$cmd" ] && continue
  case "$cmd" in '$CLAUDE_PROJECT_DIR/'*) cmd="${cmd#\$CLAUDE_PROJECT_DIR/}"; cmd="${cmd#.claude/}" ;; esac
  if [ ! -f "$cmd" ]; then ok=0; echo "        missing: $cmd"; continue; fi
  head -1 "$cmd" | grep -q '^#!.*sh' || { ok=0; echo "        no shebang: $cmd"; }
  # Registered as a bare command (no `bash` prefix): without the execute bit the runtime gets
  # exit 126, which is not a block, so every gate in the hook is silently skipped.
  [ -x "$cmd" ] || { ok=0; echo "        not executable: $cmd"; }
  # The tracked mode is what deploy propagates (no chmod anywhere), so check the index too:
  # a local chmod +x must not mask a committed 100644.
  mode=$(git ls-files -s -- "$cmd" | awk '{print $1}')
  [ -z "$mode" ] || [ "$mode" = "100755" ] || { ok=0; echo "        tracked mode $mode (want 100755): $cmd"; }
done < <(jq -r '.hooks[]?[]?.hooks[]?.command // empty' settings.json)
[ "$ok" -eq 1 ] && pass || fail "one or more commands unresolved / not a shell script"

if [ -f .claude/settings.json ]; then
  t ".claude/settings.json is valid JSON"
  if jq -e . .claude/settings.json >/dev/null 2>&1; then pass; else fail ".claude/settings.json does not parse"; fi

  t "deploy derivation holds: each root command maps to \$CLAUDE_PROJECT_DIR/.claude/<path>"
  root_cmds=$(jq -r '.hooks[]?[]?.hooks[]?.command // empty' settings.json | sort)
  # derive_settings may append one ` --profile <p>` to a command; compare without it.
  drv_cmds=$(jq -r '.hooks[]?[]?.hooks[]?.command // empty' .claude/settings.json \
    | sed -E 's/ --profile [A-Za-z0-9_-]+$//' | sort)
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
