#!/bin/bash
# Tests for the CI helper scripts: check-plugin-version.sh, the REQUIRE_CLAUDE_CLI strict mode of
# check-plugin-validate.sh and check-plugin-install.sh, and the install script's config-dir guard.
source "$(dirname "$0")/../lib.sh"

# A PATH that has bash and the basics but no `claude`, so the "CLI missing" branch is exercised
# even on a machine that has the CLI installed.
NOCLAUDE=$(mktemp -d); _CLEANUP_DIRS+=("$NOCLAUDE")
for b in bash dirname mkdir env; do ln -s "$(command -v "$b")" "$NOCLAUDE/$b"; done
BASH_BIN=$(command -v bash)

# ── check-plugin-version.sh ───────────────────────────────────────────────────
mk_ver() { # <VERSION> <manifest version>
  local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  mkdir -p "$d/plugins/harness/.claude-plugin"
  printf '%s\n' "$1" > "$d/VERSION"
  printf '{\n  "name": "harness",\n  "version": "%s"\n}\n' "$2" > "$d/plugins/harness/.claude-plugin/plugin.json"
  echo "$d"
}
t "check-plugin-version passes when plugin.json matches VERSION"
d=$(mk_ver 5.0.0 5.0.0)
if bash "$ROOT/scripts/check-plugin-version.sh" --root "$d" >/dev/null 2>&1; then pass; else fail "rejected a match"; fi

t "check-plugin-version fails when plugin.json differs from VERSION"
d=$(mk_ver 5.0.1 5.0.0)
if bash "$ROOT/scripts/check-plugin-version.sh" --root "$d" >/dev/null 2>&1; then fail "accepted a mismatch"; else pass; fi

t "check-plugin-version fails when the manifest has no version line"
d=$(mk_ver 5.0.0 5.0.0); printf '{ "name": "harness" }\n' > "$d/plugins/harness/.claude-plugin/plugin.json"
if bash "$ROOT/scripts/check-plugin-version.sh" --root "$d" >/dev/null 2>&1; then fail "accepted a missing version"; else pass; fi

t "the real repo has plugin.json version == VERSION"
if bash "$ROOT/scripts/check-plugin-version.sh" --root "$ROOT" >/dev/null 2>&1; then pass; else fail "repo out of sync"; fi

# ── REQUIRE_CLAUDE_CLI strict mode ────────────────────────────────────────────
t "check-plugin-validate skips (exit 0) without the CLI by default"
if PATH="$NOCLAUDE" env -u REQUIRE_CLAUDE_CLI "$BASH_BIN" "$ROOT/scripts/check-plugin-validate.sh" 2>&1 | grep -q 'skip'; then pass; else fail "no skip message"; fi
PATH="$NOCLAUDE" env -u REQUIRE_CLAUDE_CLI "$BASH_BIN" "$ROOT/scripts/check-plugin-validate.sh" >/dev/null 2>&1; rc=$?
t "check-plugin-validate exits 0 when skipping"
if [ "$rc" -eq 0 ]; then pass; else fail "exit $rc"; fi

t "check-plugin-validate FAILS without the CLI when REQUIRE_CLAUDE_CLI=1"
PATH="$NOCLAUDE" REQUIRE_CLAUDE_CLI=1 "$BASH_BIN" "$ROOT/scripts/check-plugin-validate.sh" >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 1 ]; then pass; else fail "want exit 1, got $rc"; fi

# ── check-plugin-install.sh ───────────────────────────────────────────────────
t "check-plugin-install refuses to run when CLAUDE_CONFIG_DIR is unset"
env -u CLAUDE_CONFIG_DIR "$BASH_BIN" "$ROOT/scripts/check-plugin-install.sh" >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 2 ]; then pass; else fail "want exit 2, got $rc"; fi

t "check-plugin-install refuses to run when CLAUDE_CONFIG_DIR is the real ~/.claude"
if [ -d "$HOME/.claude" ]; then
  CLAUDE_CONFIG_DIR="$HOME/.claude" "$BASH_BIN" "$ROOT/scripts/check-plugin-install.sh" >/dev/null 2>&1; rc=$?
  if [ "$rc" -eq 2 ]; then pass; else fail "want exit 2, got $rc"; fi
else skip "no ~/.claude on this machine"; fi

cfg=$(mktemp -d); _CLEANUP_DIRS+=("$cfg")
t "check-plugin-install skips (exit 0) without the CLI by default"
PATH="$NOCLAUDE" CLAUDE_CONFIG_DIR="$cfg" env -u REQUIRE_CLAUDE_CLI "$BASH_BIN" "$ROOT/scripts/check-plugin-install.sh" >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 0 ]; then pass; else fail "exit $rc"; fi

t "check-plugin-install FAILS without the CLI when REQUIRE_CLAUDE_CLI=1"
PATH="$NOCLAUDE" CLAUDE_CONFIG_DIR="$cfg" REQUIRE_CLAUDE_CLI=1 "$BASH_BIN" "$ROOT/scripts/check-plugin-install.sh" >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 1 ]; then pass; else fail "want exit 1, got $rc"; fi

finish
