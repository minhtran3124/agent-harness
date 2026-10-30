#!/bin/bash
# Tests for scripts/check-shellcheck.sh: the file list it hands to shellcheck, the skip when
# shellcheck is missing, and the REQUIRE_SHELLCHECK=1 strict mode.
source "$(dirname "$0")/../lib.sh"

BASH_BIN=$(command -v bash)
# A PATH with the basics but no shellcheck, so the "missing" branch runs on any machine.
NOSC=$(mktemp -d); _CLEANUP_DIRS+=("$NOSC")
for b in bash dirname env; do ln -s "$(command -v "$b")" "$NOSC/$b"; done
# A PATH with a fake shellcheck that records its arguments, one per line.
FAKE=$(mktemp -d); _CLEANUP_DIRS+=("$FAKE")
for b in bash dirname env; do ln -s "$(command -v "$b")" "$FAKE/$b"; done
ARGS="$FAKE/args.txt"
printf '#!/bin/bash\n[ "$1" = "--version" ] && { echo "version: fake"; exit 0; }\nprintf "%%s\\n" "$@" > "%s"\n' "$ARGS" > "$FAKE/shellcheck"
chmod +x "$FAKE/shellcheck"

t "check-shellcheck passes the current CI file list to shellcheck"
PATH="$FAKE" "$BASH_BIN" "$ROOT/scripts/check-shellcheck.sh" >/dev/null 2>&1; rc=$?
want=$(cd "$ROOT" && { ls plugins/harness/hooks/*.sh plugins/harness/scripts/*.sh; \
  printf '%s\n' scripts/check-plugin-install.sh scripts/check-plugin-version.sh scripts/check-plugin-validate.sh; })
if [ "$rc" -eq 0 ] && [ "$(cat "$ARGS" 2>/dev/null)" = "$want" ]; then pass; else fail "rc=$rc, args differ from the CI list"; fi

t "the file list holds 9 files"
if [ "$(wc -l < "$ARGS" | tr -d ' ')" = 9 ]; then pass; else fail "got $(wc -l < "$ARGS") files"; fi

t "check-shellcheck skips with one loud line (exit 0) without shellcheck by default"
out=$(PATH="$NOSC" env -u REQUIRE_SHELLCHECK "$BASH_BIN" "$ROOT/scripts/check-shellcheck.sh" 2>&1); rc=$?
if [ "$rc" -eq 0 ] && [ "$(printf '%s\n' "$out" | wc -l | tr -d ' ')" = 1 ] && printf '%s' "$out" | grep -q 'skip'; then pass; else fail "rc=$rc out=$out"; fi

t "check-shellcheck FAILS without shellcheck when REQUIRE_SHELLCHECK=1"
PATH="$NOSC" REQUIRE_SHELLCHECK=1 "$BASH_BIN" "$ROOT/scripts/check-shellcheck.sh" >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 1 ]; then pass; else fail "want exit 1, got $rc"; fi

finish
