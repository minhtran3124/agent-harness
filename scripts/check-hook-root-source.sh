#!/bin/bash
# Ratchet: no hook may derive the repository root from its own location.
#
# `git -C "$SCRIPT_DIR" rev-parse --show-toplevel` is correct only while hooks are copied INTO the
# project. A hook installed outside it (plugin packaging) whose own directory sits inside ANY git
# repo gets exit 0 and THAT repo back — the gate then audits the wrong repository and reports
# success. Measured by spike, 2026-09-09; see specs/fix-hook-project-root-resolution/design.md.
#
# Verifies:        no non-comment line in hooks/ resolves a repo root from $SCRIPT_DIR / $0.
# Does not verify: that the replacement resolution is correct, or that a hook uses REPO_DIR at all.
#                  That is tests/hooks/repo-root-resolution.test.sh (truth tier).
set -u
cd "$(dirname "$0")/.." || exit 1

# Non-comment lines only: this change deliberately documents the banned pattern in prose.
# Match ANY own-location variable, not the literal name SCRIPT_DIR. The first version of this
# ratchet grepped for SCRIPT_DIR by name and therefore missed hooks/session-knowledge.sh, which
# spells the same defect `git -C "$HOOK_DIR" ...` — found by the code review of PR #222. The
# banned thing is deriving the root from the hook's own location, whatever the variable is called.
HITS=$(grep -rnE 'rev-parse --show-toplevel' hooks/ 2>/dev/null \
  | grep -vE ':[0-9]+:[[:space:]]*#' \
  | grep -E 'git -C "\$\{?[A-Za-z_][A-Za-z0-9_]*_DIR\}?"|git -C "\$\(dirname "\$0"\)"|git -C "\$\(cd "\$\(dirname')

if [ -n "$HITS" ]; then
  echo "  ✗ hook resolves its repo root from its own location:" >&2
  printf '%s\n' "$HITS" | sed 's/^/      /' >&2
  echo "      Use: REPO_DIR=\"\${CLAUDE_PROJECT_DIR:-\$(git rev-parse --show-toplevel 2>/dev/null)}\"" >&2
  echo "      See specs/fix-hook-project-root-resolution/design.md" >&2
  exit 1
fi
echo "  ✓ no hook derives its repo root from SCRIPT_DIR"
exit 0
