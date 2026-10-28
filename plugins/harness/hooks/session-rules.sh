#!/bin/bash
# SessionStart hook: deliver rules/behavior.md as session context.
# A plugin has no "rules" component, so the plugin's one rule file reaches the model here.
# Prints the SessionStart JSON envelope. No jq: the text is escaped with sed and awk.
# Exit 0 always; a missing rule file prints nothing.
ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
FILE="$ROOT/rules/behavior.md"
[ -f "$FILE" ] || exit 0
TAB=$(printf '\t')
BODY=$(sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e "s/$TAB/\\\\t/g" -e 's/\r$//' "$FILE" \
  | awk '{ printf "%s%s", $0, "\\n" }')
printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$BODY"
exit 0
