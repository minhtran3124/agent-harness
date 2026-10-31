#!/bin/bash
# Run shellcheck over the harness shell scripts. CI and a contributor run the same file list.
#
# Verifies:        shellcheck exits 0 for plugins/harness/hooks/*.sh, plugins/harness/scripts/*.sh
#                  and the three scripts/check-plugin-*.sh.
# Does not verify: any other shell file, or the shell inside skill markdown (see
#                  lint-skill-bash.sh).
#
# Without shellcheck it prints one skip line and exits 0, so a contributor is not blocked. CI sets
# REQUIRE_SHELLCHECK=1, which turns that skip into a failure: a gate that quietly vanishes when
# the install breaks is no gate. Same convention as REQUIRE_CLAUDE_CLI=1.
set -u
cd "$(dirname "$0")/.." || exit 1

if ! command -v shellcheck >/dev/null 2>&1; then
  if [ "${REQUIRE_SHELLCHECK:-}" = 1 ]; then
    echo "  ✗ shellcheck: not installed and REQUIRE_SHELLCHECK=1" >&2
    exit 1
  fi
  echo "  skip — shellcheck not installed; CI will fail this"
  exit 0
fi

shellcheck --version
shellcheck plugins/harness/hooks/*.sh plugins/harness/scripts/*.sh \
  scripts/check-plugin-install.sh scripts/check-plugin-version.sh scripts/check-plugin-validate.sh \
  scripts/check-tag-version.sh
