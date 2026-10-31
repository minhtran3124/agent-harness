#!/bin/bash
# Wiring smoke test: the plugin's hooks/hooks.json must be internally consistent. It must be valid
# JSON, every registered hook is exec form (`bash` plus a script argument under
# ${CLAUDE_PLUGIN_ROOT}/hooks/), every script resolves to a file with a bash shebang that is
# mode 100755 in the index, and the repo's own settings.json wires no hooks (they would run
# twice) and keeps the approved permissions.deny list.
# This tests the wiring, not the hook bodies (those are the tests/hooks/ suites).
source "$(dirname "$0")/../lib.sh"
cd "$ROOT" || exit 1

HOOKS=plugins/harness/hooks/hooks.json

t "hooks.json is valid JSON"
if jq -e . "$HOOKS" >/dev/null 2>&1; then pass; else fail "$HOOKS does not parse"; fi

t "every hook is exec form: command is bash, first arg is under \${CLAUDE_PLUGIN_ROOT}/hooks/"
bad=$(jq -r '.hooks[][].hooks[] | select(.type != "command" or .command != "bash" or ((.args[0] // "") | startswith("${CLAUDE_PLUGIN_ROOT}/hooks/") | not)) | tojson' "$HOOKS")
if [ -z "$bad" ]; then pass; else fail "not exec form: $bad"; fi

t "every registered script exists, has a bash shebang and is mode 100755 in the index"
ok=1
while IFS= read -r arg; do
  [ -z "$arg" ] && continue
  f="plugins/harness/hooks/${arg#\$\{CLAUDE_PLUGIN_ROOT\}/hooks/}"
  if [ ! -f "$f" ]; then ok=0; echo "        missing: $f"; continue; fi
  head -1 "$f" | grep -q '^#!.*sh' || { ok=0; echo "        no shebang: $f"; }
  mode=$(git ls-files -s -- "$f" | awk '{print $1}')
  [ -z "$mode" ] || [ "$mode" = "100755" ] || { ok=0; echo "        tracked mode $mode (want 100755): $f"; }
done < <(jq -r '.hooks[][].hooks[] | .args[0] // empty' "$HOOKS")
[ "$ok" -eq 1 ] && pass || fail "one or more hook scripts unresolved or not 100755"

t "every hooks/*.sh in the plugin is registered in hooks.json"
ok=1
for f in plugins/harness/hooks/*.sh; do
  jq -e --arg n "hooks/$(basename "$f")" '[.hooks[][].hooks[] | .args[]? | select(endswith($n))] | length > 0' "$HOOKS" >/dev/null || { ok=0; echo "        not registered: $f"; }
done
[ "$ok" -eq 1 ] && pass || fail "a hook script is on disk but not wired"

t "the repo's settings.json wires no hooks (the plugin's hooks.json does)"
if jq -e '(.hooks // {}) | length == 0' settings.json >/dev/null 2>&1; then pass
else fail "settings.json has hooks: $(jq -c .hooks settings.json)"; fi

t "permissions.deny holds the approved rules and settings.json has no allow rules"
if jq -e '(.permissions.deny | index("Read(./.env)") and index("Edit(./.env)") and index("Bash(git push --force*)") and index("Bash(git push * main)")) and (.permissions | has("allow") | not)' settings.json >/dev/null; then pass
else fail "permissions: $(jq -c .permissions settings.json)"; fi

t "settings.json permissions.deny equals the RULES list in the setup script (same entries, same order)"
rules=$(sed -n "s/^RULES='\\(.*\\)'\$/\\1/p" plugins/harness/skills/setup/scripts/merge-deny.sh)
if [ -n "$rules" ] && [ "$(printf '%s' "$rules" | jq -c .)" = "$(jq -c .permissions.deny settings.json)" ]; then pass
else fail "settings.json deny: $(jq -c .permissions.deny settings.json) / RULES: $rules"; fi

t "permissions.deny blocks the refspec and plus forms for main and master"
if jq -e '.permissions.deny as $d | all("Bash(git push *:main)","Bash(git push *:refs/heads/main)","Bash(git push * +main)","Bash(git push *:master)","Bash(git push *:refs/heads/master)","Bash(git push * +master)"; . as $r | $d | index($r))' settings.json >/dev/null; then pass
else fail "a push-form deny pattern is missing: $(jq -c .permissions.deny settings.json)"; fi

finish
