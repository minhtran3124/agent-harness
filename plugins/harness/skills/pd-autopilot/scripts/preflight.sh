#!/usr/bin/env bash
# Preflight for /harness:pd-autopilot: run in step 1, before triage, so a run stops early with a clear
# message instead of failing in the middle.
#
# Usage: preflight.sh --repo-dir <checkout dir>
#
# Verifies:        git, gh, jq and python3 are in PATH; gh auth status exits 0 for the origin host (github.com without origin); specs/ is ignored in
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

# The gh host comes from the origin remote, so a GitHub Enterprise checkout checks its own host; an SSH alias
# resolves to its HostName; no origin or an unparsed URL falls back to github.com.
# ssh_real <host>: the HostName an SSH config alias maps to (ssh -G), or <host> unchanged when ssh is
# missing or prints no hostname line.
ssh_real() {
  local real=''
  command -v ssh >/dev/null 2>&1 && real=$(ssh -G "$1" 2>/dev/null | awk '$1 == "hostname" { print $2; exit }')
  printf '%s\n' "${real:-$1}"
}

gh_host() {
  local url host
  url=$(git -C "$dir" remote get-url origin 2>/dev/null) || url=''
  case $url in
    ssh://*) host=${url#*://}; host=${host#*@}; host=${host%%/*}; host=$(ssh_real "${host%%:*}") ;;
    *://*) host=${url#*://}; host=${host#*@}; host=${host%%/*}; host=${host%%:*} ;;
    *@*:*) host=${url#*@}; host=$(ssh_real "${host%%:*}") ;;
    *) host='' ;;
  esac
  printf '%s\n' "${host:-github.com}"
}

if command -v gh >/dev/null 2>&1; then
  gh auth status --hostname "$(gh_host)" >/dev/null 2>&1 || miss 'gh auth'
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
