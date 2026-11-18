#!/bin/bash
# Acceptance tests for #645: the qa-writer agent runs on Opus 5.5.
# The ship.js stage cases (mo1-mo4) live in tests/workflows/harness.js.
source "$(dirname "$0")/../lib.sh"

AGENT=plugins/harness/agents/qa-writer.md

t "AC5: qa-writer frontmatter has exactly one model: claude-opus-5-5 line"
n=$(cd "$ROOT" && grep -c '^model: claude-opus-5-5' "$AGENT")
[ "$n" = "1" ] && pass || fail "grep -c printed: $n"

t "AC5: qa-writer frontmatter keeps effort: medium"
(cd "$ROOT" && grep -q '^effort: medium' "$AGENT") && pass || fail "no effort: medium line"

finish
