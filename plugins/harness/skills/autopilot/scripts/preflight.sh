#!/usr/bin/env bash
# Preflight for /harness:autopilot: run in step 1, before triage, so a run stops early with a clear
# message instead of failing in the middle.
#
# Usage: preflight.sh --repo-dir <checkout dir>
#
# Verifies:        git, gh, jq and python3 are in PATH; gh auth status exits 0; specs/ is ignored in
#                  the checkout (git check-ignore). A missing tool skips the check that needs it.
# Does not verify: a system package that only a build shows as missing, or a tool's version.
#
# Output: one stdout line per failed check (missing: git|gh|jq|python3, missing: gh auth,
# missing: git repo, missing: specs/ ignore) and exit 1; else "preflight: ok" and exit 0.
# Exit 2: no --repo-dir, or the dir does not exist. Writes nothing. Uses only bash builtins, git
# and gh.
set -u

usage() { echo "usage: preflight.sh --repo-dir <dir>" >&2; exit 2; }

dir=''
while [ $# -gt 0 ]; do
  case $1 in
    --repo-dir) [ $# -ge 2 ] || usage; dir=$2; shift 2 ;;
    *) usage ;;
  esac
done
if [ -z "$dir" ] || [ ! -d "$dir" ]; then usage; fi

failed=0
miss() { echo "missing: $1"; failed=1; }

for tool in git gh jq python3; do
  command -v "$tool" >/dev/null 2>&1 || miss "$tool"
done

if command -v gh >/dev/null 2>&1; then
  gh auth status --hostname github.com >/dev/null 2>&1 || miss 'gh auth'
fi

if command -v git >/dev/null 2>&1; then
  git -C "$dir" check-ignore -q --no-index specs/x 2>/dev/null
  case $? in
    0) ;;
    1) miss 'specs/ ignore' ;;
    *) miss 'git repo' ;;
  esac
fi

[ "$failed" = 0 ] || exit 1
echo 'preflight: ok'
