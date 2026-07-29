#!/bin/bash
# Shared active-plan / Lane resolution for the edit-time and commit-time gates.
#
# Three hooks each independently needed to answer "what is the task currently in
# flight?": blast-radius-check.sh (to know which <files> set is in scope),
# risk-corroboration.sh (to know what Lane to corroborate a tripped risk category
# against), and scope-gate.sh (to know whether intake has already run, so it can stop
# re-nudging). The only supported signal is a specs/*/PLAN.md carrying `status:
# active` — deliberately NOT "most recently modified on disk": a stale-but-recently-
# touched spec would misattribute its scope/Lane to unrelated work. This is not
# hypothetical — blast-radius-check.sh used to have exactly that mtime fallback and
# it was removed for this reason (docs/solutions/harness/stale-active-plan-misaims-blast-radius.md).
# risk-corroboration.sh independently grew the same kind of mtime fallback later;
# this file is the fix, unifying both hooks on the one correct signal.
#
# bash 3.2 compatible (macOS default), no GNU-only flags — mirrors hooks/lib/git-command.sh.
#
# Usage:
#   source "$(cd "$(dirname "$0")" && pwd)/lib/lane.sh"
#   plan=$(hook_lib_find_active_plan "$REPO_DIR") || plan=""
#   lane=$(hook_lib_resolve_lane "$REPO_DIR" "$STAGED_PATHS")
#   hook_lib_intake_in_progress "$REPO_DIR" && echo "intake already ran / is in flight"

# hook_lib_find_active_plan <repo_dir>
# Echoes the path to the specs/*/PLAN.md carrying `status: active` (most-recently
# modified first when more than one somehow qualifies) and exits 0. Exits 1 with no
# output when none exists — there is deliberately no other fallback.
hook_lib_find_active_plan() {
  local repo_dir="$1" p
  for p in $(ls -t "$repo_dir"/specs/*/PLAN.md 2>/dev/null); do
    if grep -qiE '^status:[[:space:]]*active' "$p" 2>/dev/null; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

# hook_lib_resolve_lane <repo_dir> <staged_paths_newline_list>
# Resolves the declared Lane for the commit under evaluation:
#   1. A SUMMARY.md staged in THIS commit (read from the index — exact evidence for
#      what is actually being committed).
#   2. Else, the sibling SUMMARY.md of the `status: active` plan (hook_lib_find_active_plan)
#      — the one explicit "this is the task in flight" signal this codebase has.
#   3. Else nothing is printed (empty string, exit 1) — there is nothing to resolve.
# Must run with CWD inside the repo (git show resolves the index relative to CWD).
hook_lib_resolve_lane() {
  local repo_dir="$1" staged_paths="$2" f l plan summary
  for f in $(printf '%s\n' "$staged_paths" | grep -E '(^|/)SUMMARY\.md$' 2>/dev/null || true); do
    l=$(git show ":$f" 2>/dev/null | grep -iE '^Lane:' | head -1)
    if [ -n "$l" ]; then
      echo "$l"
      return 0
    fi
  done
  plan=$(hook_lib_find_active_plan "$repo_dir") || return 1
  summary="$(dirname "$plan")/SUMMARY.md"
  [ -f "$summary" ] || return 1
  grep -iE '^Lane:' "$summary" | head -1
}

# hook_lib_intake_in_progress <repo_dir>
# True (exit 0) when there is live, unfinished intake work for some task: an active
# PLAN.md, or an uncommitted change under specs/ (a just-written SUMMARY.md before its
# first commit — the tiny-lane case, which never gets a PLAN.md at all). Git-native
# only (git status), not find/stat — this hook suite targets both GNU and BSD
# userlands, and relative-date find predicates (`-newermt "-N minutes"`) are not
# portable across them (confirmed directly: this repo's dev machine ships `find` as
# `bfs`, which rejects that syntax outright).
hook_lib_intake_in_progress() {
  local repo_dir="$1"
  hook_lib_find_active_plan "$repo_dir" >/dev/null 2>&1 && return 0
  git -C "$repo_dir" status --porcelain -- specs 2>/dev/null | grep -q .
}
