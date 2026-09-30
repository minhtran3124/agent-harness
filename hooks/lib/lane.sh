#!/bin/bash
# Shared active-plan / Lane resolution for hooks/commit-gate.sh.
#
# commit-gate.sh needs to answer "what is the task currently in flight?" twice: check_plan_scope
# (which <files> set is in scope) and check_risk (what Lane to corroborate a tripped risk
# category against). The only supported signal is a specs/*/PLAN.md carrying `status: active`
# — deliberately NOT "most recently modified on disk": a stale-but-recently-touched spec would
# misattribute its scope/Lane to unrelated work. This is not hypothetical — the plan-scope check
# once had exactly that mtime fallback and it was removed for this reason
# (docs/solutions/harness/stale-active-plan-misaims-blast-radius.md). The Lane lookup later
# grew the same kind of mtime fallback; this file is the fix, unifying both on the one signal.
#
# bash 3.2 compatible (macOS default), no GNU-only flags — mirrors hooks/lib/git-command.sh.
#
# Usage:
#   source "$(cd "$(dirname "$0")" && pwd)/lib/lane.sh"
#   plan=$(hook_lib_find_active_plan "$REPO_DIR") || plan=""
#   lane=$(hook_lib_resolve_lane "$REPO_DIR" "$STAGED_PATHS")

# hook_lib_find_active_plan <repo_dir>
# Echoes the path to the specs/*/PLAN.md carrying `status: active` and exits 0. Exits 1
# with no output when none exists — there is deliberately no other fallback.
#
# Fast-path: a single `grep -l` across all plan files, not one grep process per file. When
# zero plans are active (the common case — this runs on every edit) that is one process
# instead of N; `head -1` short-circuits at the first hit (SIGPIPE ends grep before it
# scans the rest). The rare multi-active case resolves to the FIRST FOUND — lexical glob
# order of the spec dirs, not most-recently-modified as the prior mtime scan did.
hook_lib_find_active_plan() {
  local repo_dir="$1" match
  match=$(grep -lEi '^status:[[:space:]]*active' "$repo_dir"/specs/*/PLAN.md 2>/dev/null | head -1)
  [ -n "$match" ] && { printf '%s\n' "$match"; return 0; }
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
