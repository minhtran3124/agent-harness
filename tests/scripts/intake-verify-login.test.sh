#!/bin/bash
# Contract test: intake checks the login variables by name and never reads .env.
source "$(dirname "$0")/../lib.sh"

SKILL="$ROOT/plugins/harness/skills/intake/SKILL.md"
REF="$ROOT/plugins/harness/skills/intake/references/verify-login.md"

t "verify-login.md exists"
if [ -f "$REF" ]; then pass; else fail "missing $REF"; fi

t "the check is test -n"
if grep -qF 'test -n "$VERIFY_USER"' "$REF"; then pass; else fail "test -n"; fi

t "never print a value"
if grep -qF 'Never print a value' "$REF"; then pass; else fail "print rule"; fi

t "never read .env, with the honest settings.json note"
if grep -qF 'Never read, grep or list `.env` or any secrets file. This is a rule in the text only' "$REF"; then pass; else fail ".env rule"; fi

t "three answers in order, throwaway credentials first"
if grep -qF '1. Use throwaway credentials for a local test server (recommended).' "$REF" \
  && grep -qF '2. The owner sets the variables, then the run starts.' "$REF" \
  && grep -qF '3. Skip the login steps of the `Verify:` row.' "$REF" \
  && [ "$(grep -n 'Use throwaway' "$REF" | cut -d: -f1)" -lt "$(grep -n 'owner sets the variables' "$REF" | cut -d: -f1)" ]; then pass; else fail "answers"; fi

t "accepted answer goes into the Confirmed decisions comment"
if grep -qF 'goes into the Confirmed decisions comment' "$REF"; then pass; else fail "comment rule"; fi

t "SKILL.md points to references/verify-login.md"
if grep -qF 'references/verify-login.md' "$SKILL"; then pass; else fail "pointer"; fi

t "allowed-tools holds Bash(test -n *)"
if grep -E '^allowed-tools:' "$SKILL" | grep -qF 'Bash(test -n *)'; then pass; else fail "allowed-tools"; fi

t "SKILL.md stays under 600 words"
words=$(wc -w < "$SKILL" | tr -d ' ')
if [ "$words" -lt 600 ]; then pass; else fail "words=$words"; fi
finish
