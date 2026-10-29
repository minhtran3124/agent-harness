#!/bin/bash
# Contract test: intake needs a Verify: row; no row gives CONFIRM; auto mode records needs_review.
source "$(dirname "$0")/../lib.sh"

SKILL="$ROOT/plugins/harness/skills/intake/SKILL.md"

t "READY requires a Verify: row"
if grep -qF 'a `Verify:` row exists' "$SKILL"; then pass; else fail "READY Verify: condition"; fi

t "CONFIRM rule: missing Verify: row is drafted and the accepted row goes to the Confirmed decisions comment"
if grep -qF 'A missing `Verify:` row is one of them' "$SKILL" && grep -qF 'accepted row goes into the Confirmed decisions comment' "$SKILL"; then pass; else fail "CONFIRM rule"; fi

t "auto mode records the drafted row as a needs_review decision"
if grep -qF 'A drafted `Verify:` row is a decision with `needs_review: true`' "$SKILL"; then pass; else fail "auto-mode rule"; fi

t "SKILL.md stays under 600 words"
words=$(wc -w < "$SKILL" | tr -d ' ')
if [ "$words" -lt 600 ]; then pass; else fail "words=$words"; fi
finish
