#!/bin/bash
# Regression tests for specs/fix-hook-project-root-resolution.
#
# The defect: hooks resolved the repo root with `git -C "$SCRIPT_DIR" rev-parse --show-toplevel`.
# When a hook is installed OUTSIDE the project (plugin packaging) and its own directory happens to
# sit inside ANY git repo, that command exits 0 and returns THAT repo — so a gate inspects the
# wrong repository and reports success. Measured by spike on 2026-09-09.
#
# These cases put the hook inside a FOREIGN git repo and assert it acts on the project (CWD /
# CLAUDE_PROJECT_DIR), never on the repo that happens to contain the hook file. The commit-gate
# equivalents live in tests/hooks/commit-gate.test.sh and tests/hooks/commit-gate-risk.test.sh.
source "$(dirname "$0")/../lib.sh"

# foreign_host <hook.sh>... -> echoes a git repo that HOSTS the hooks but is NOT the project.
# Staged content here is the decoy: a pre-fix hook resolves to this repo and sees it.
foreign_host() {
  local d; d=$(mktemp -d)
  _CLEANUP_DIRS+=("$d")
  git -C "$d" init -q -b main 2>/dev/null || git -C "$d" init -q
  git -C "$d" config user.email test@test
  git -C "$d" config user.name test
  mkdir -p "$d/hooks"
  [ -d "$ROOT/hooks/lib" ] && cp -R "$ROOT/hooks/lib" "$d/hooks/"
  local h; for h in "$@"; do cp "$ROOT/hooks/$h" "$d/hooks/"; done
  # Decoy staged content: hooks/* trips the `high-blast` hard gate.
  printf 'decoy\n' > "$d/hooks/decoy-gate-tripper.sh"
  git -C "$d" add -f hooks/decoy-gate-tripper.sh
  echo "$d"
}

# run_from <project> <host> <hook.sh> <json> [VAR=val ...]
# Hook lives in <host>; CWD is <project>. Sets OUT and RC.
run_from() {
  local proj="$1" host="$2" hook="$3" json="$4"; shift 4
  OUT=$(cd "$proj" && printf '%s' "$json" | env "$@" bash "$host/hooks/$hook" 2>&1); RC=$?
}

# session-knowledge spells the same defect as `git -C "$HOOK_DIR"`, so the first version of the
# ratchet (which grepped for SCRIPT_DIR by name) missed it and PR #221 left it unfixed. Found by
# the code review of PR #222. It runs with stderr closed and must stay silent in every branch.
t "session-knowledge: no resolvable project root -> silent exit 0, never blocks"
host=$(foreign_host session-knowledge.sh); outside=$(mktemp -d); _CLEANUP_DIRS+=("$outside")
run_from "$outside" "$host" session-knowledge.sh '{}'
if [ "$RC" -ne 0 ]; then fail "rc=$RC, want 0 — out: $OUT"; else pass; fi

# The host repo carries a docs/solutions KB; the project does not. A hook that resolved to its own
# location would load the host's KB into the session. It must load nothing.
t "session-knowledge: hook hosted in a foreign git repo does NOT load that repo's knowledge base"
proj=$(new_repo); host=$(foreign_host session-knowledge.sh)
mkdir -p "$host/docs/solutions"
printf '# Index\n| [decoy](decoy.md) | knowledge |\n' > "$host/docs/solutions/INDEX.md"
printf '# Critical\n- DECOY-FROM-HOST-REPO\n' > "$host/docs/solutions/critical-patterns.md"
run_from "$proj" "$host" session-knowledge.sh '{}'
case "$OUT" in
  *DECOY-FROM-HOST-REPO*) fail "loaded the host repo's KB — resolved its own location, not the project" ;;
  *)                      pass ;;
esac

finish
