#!/usr/bin/env bash
# SessionStart hook: apply harness-models.json to the deployed agent and skill frontmatter.
# Thin wrapper: pipes the SessionStart JSON on stdin to apply_model_config.py --hook, which
# filters on `source` (startup/clear only), validates, writes, and prints any hook JSON.
# NEVER blocks: every path exits 0; a missing python3, applier or project root is a silent no-op.
#
# Verifies:        nothing at commit time; it applies the validated user file at session start.
# Does not verify: that the running session picks up a rewritten agent file (it may apply from
#                  the next session), or that the hook is registered in settings.json.

set -u

# HOOK_DIR locates the applier that ships beside this hook (scripts/ in the source repo,
# .claude/scripts/ in a consumer). The project root never comes from HOOK_DIR
# (scripts/check-hook-root-source.sh).
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
APPLIER="$HOOK_DIR/../scripts/apply_model_config.py"

[ -n "$ROOT" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
[ -f "$APPLIER" ] || exit 0

python3 "$APPLIER" --hook --project-root "$ROOT" 2>/dev/null
exit 0
