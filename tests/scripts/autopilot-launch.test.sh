#!/bin/bash
# Contract test: autopilot step 8 launches ship by a name the plugin registers.
source "$(dirname "$0")/../lib.sh"

SKILL="$ROOT/plugins/harness/skills/autopilot/SKILL.md"
PJSON="$ROOT/plugins/harness/.claude-plugin/plugin.json"
SHIP="$ROOT/plugins/harness/workflows/ship.js"

t "SKILL.md step 8 launches by name harness:ship and names no scriptPath"
if grep -qF 'name: "harness:ship"' "$SKILL" && ! grep -qF 'scriptPath' "$SKILL"; then pass; else fail "step 8 launch route"; fi

t "plugin.json registers ./workflows/ship.js and ship.js is named ship, so <plugin>:ship = harness:ship"
pname=$(sed -n 's/^ *"name": *"\([^"]*\)",$/\1/p' "$PJSON" | head -1)
wname=$(sed -n "s/^ *name: *'\([^']*\)',$/\1/p" "$SHIP" | head -1)
if grep -qF '"./workflows/ship.js"' "$PJSON" && [ "$pname:$wname" = "harness:ship" ]; then pass; else fail "plugin=$pname workflow=$wname"; fi

t "SKILL.md stays under 600 words"
words=$(wc -w < "$SKILL" | tr -d ' ')
if [ "$words" -lt 600 ]; then pass; else fail "words=$words"; fi
finish
