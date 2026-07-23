#!/bin/bash
# PreToolUse hook: corroborate the declared Lane against the staged diff.
#
# The diff cannot lie about what it touched. If the staged changes trip a
# hard-gate signal (auth, authorization, data-loss/migration, audit, external
# provider, public contract, weakening validation, high-blast files) but the
# declared Lane in specs/<slug>/SUMMARY.md is below `high-risk`, the commit is
# BLOCKED (exit 2) — the agent under-classified its own work.
#
# CANONICAL GATE LIST + MODES: harness-manifest.json (hard_gates.detectable). The
# manifest is the mode authority — category_mode() reads each slug's `mode` (block|warn)
# from it at runtime. Only the add_cat detector set is mirrored here;
# scripts/check_manifest.py fails CI if that set drifts from the manifest.
# To loosen or re-tighten a gate, edit its manifest `mode` field — not this file.
#
# Safety for a docs/framework repo:
#   - Keyword categories scan only ADDED CODE lines, excluding prose
#     (*.md, docs/, specs/, skills/) and the hooks/ dir itself (scanners
#     contain the very keywords they look for). Path categories use file paths.
#   - When a signal is present but NO Lane is declared, this WARNS (exit 0)
#     rather than blocking — there is nothing to corroborate against.
#     Set RISK_CORROBORATION_STRICT=1 to make the no-Lane case fail-closed.
#   - Per-category mode (block|warn) is read from harness-manifest.json at runtime.
#     Unknown slug / missing mode / missing or invalid manifest => block (fail-safe).
#     Consumer repos have no manifest at their root, so every category blocks there.
#     (Assumes `jq`, which stdin parsing already requires — without jq this hook
#     never gates anything at all; that is pre-existing behavior, not mode fallback.)
#
# Exits 0 to allow, 2 to block. No set -e (flow is controlled explicitly).

INPUT=$(cat /dev/stdin)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Only gate git commit (tokenizing matcher — resists cd/&&/-C/-c bypass)
source "$(cd "$(dirname "$0")" && pwd)/lib/git-command.sh" 2>/dev/null
# Fail closed: if the matcher lib is missing, block rather than skip corroboration.
command -v hook_cmd_is_git_commit >/dev/null 2>&1 || {
  echo "[RISK] git-command matcher lib missing — redeploy harness (blocking to fail safe)." >&2
  exit 2
}
hook_cmd_is_git_commit "$COMMAND" || exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
[ -z "$REPO_DIR" ] && REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR" || exit 0

# ── Per-category mode: harness-manifest.json is the authority ────────────
# Durable loosening: set the category's "mode" to "warn" in harness-manifest.json.
# Session-scoped loosening: list categories in RISK_WARN_CATEGORIES (comma/space
# separated), e.g. RISK_WARN_CATEGORIES="data-loss/migration". The variable must be
# in the HOOK'S OWN process environment — .claude/settings.local.json -> "env", or a
# var exported in the session. An inline `VAR=x git commit` prefix does NOT work:
# a PreToolUse hook runs before the command, so the prefix never reaches it.
# Loosen one at a time; never auth/external-provider first; revert on any incident.
# Read the manifest from the INDEX (`git show :path`), not the worktree — the risk
# signals and the Lane are both index-side, so the mode must be too. Otherwise an
# UNSTAGED "mode": "warn" edit would loosen a gate for a commit whose tree still
# ships block-mode (Codex review, PR #160). Index copy absent/invalid => "" => block.
GATE_MODES=$(git show :harness-manifest.json 2>/dev/null | jq -r \
  '.hard_gates.detectable[]? | "\(.slug)=\(.mode // "block")"' 2>/dev/null || true)

category_mode() {
  local _wl
  _wl=$(echo " ${RISK_WARN_CATEGORIES:-} " | tr ',' ' ')
  case "$_wl" in
    *" $1 "*) echo "warn"; return ;;
  esac
  # Manifest lookup — anything but an explicit "warn" blocks (fail-safe: absent
  # slug, missing mode, missing/unreadable/invalid manifest all fall through).
  if printf '%s\n' "$GATE_MODES" | grep -qxF "$1=warn"; then
    echo "warn"
  else
    echo "block"
  fi
}

# ── Gather the staged diff ───────────────────────────────────────────────
STAGED_PATHS=$(git diff --cached --name-only 2>/dev/null || true)
[ -z "$STAGED_PATHS" ] && exit 0

# Added CODE lines only — exclude prose and the hooks dir (scanners self-trip).
# Full-line comments (`# …`) are stripped before scanning: natural-language words
# like "session" or "permission" in a comment are not auth surface (documented FP:
# docs/solutions/harness/risk-corroboration-scans-test-comments-for-auth-words.md).
# Deliberately NOT excluding tests/ wholesale — a test that adds real auth code
# must stay visible to the gate; only prose comments are blind-spotted.
CODE_ADDED=$(git diff --cached -U0 -- . ':!*.md' ':!docs/' ':!specs/' ':!skills/' ':!hooks/' ':!.claude/' 2>/dev/null \
  | grep -E '^\+[^+]' | grep -vE '^\+[[:space:]]*#' || true)
# Removed lines (for weakening-validation), same exclusions + comment strip
CODE_REMOVED=$(git diff --cached -U0 -- . ':!*.md' ':!docs/' ':!specs/' ':!skills/' ':!hooks/' ':!.claude/' 2>/dev/null \
  | grep -E '^-[^-]' | grep -vE '^-[[:space:]]*#' || true)

# ── Resolve the declared Lane ────────────────────────────────────────────
# Moved ahead of category scanning so the diff-size signal below (which needs
# LANE_VAL) still runs even when no hard-gate category trips (that path exits
# early, before the original Lane-resolution block further down).
LANE=""
# Prefer a SUMMARY.md staged in this commit
for f in $(echo "$STAGED_PATHS" | grep -E '(^|/)SUMMARY\.md$' || true); do
  L=$(git show ":$f" 2>/dev/null | grep -iE '^Lane:' | head -1)
  [ -n "$L" ] && LANE="$L" && break
done
# Else the most recently modified specs/*/SUMMARY.md on disk
if [ -z "$LANE" ]; then
  RECENT=$(ls -t specs/*/SUMMARY.md 2>/dev/null | head -1)
  [ -n "$RECENT" ] && LANE=$(grep -iE '^Lane:' "$RECENT" | head -1)
fi
# Normalize: extract tiny|normal|high-risk
LANE_VAL=$(echo "$LANE" | tr 'A-Z' 'a-z' | grep -oE 'tiny|normal|high-risk' | head -1)

# ── Diff-size sanity signal (warn-only — never affects exit code) ────────
# Large diffs for a lightweight declared lane are a simplicity smell.
# tiny=150, normal=600 changed (added+removed) lines; high-risk / no lane:
# no threshold (ceremony is already expected, or there is nothing to compare
# against).
count_lines() {
  [ -z "$1" ] && { echo 0; return; }
  printf '%s\n' "$1" | grep -c '^'
}
CHANGED_LINES=$(( $(count_lines "$CODE_ADDED") + $(count_lines "$CODE_REMOVED") ))
SIZE_THRESHOLD=""
case "$LANE_VAL" in
  tiny)   SIZE_THRESHOLD=150 ;;
  normal) SIZE_THRESHOLD=600 ;;
esac
if [ -n "$SIZE_THRESHOLD" ] && [ "$CHANGED_LINES" -gt "$SIZE_THRESHOLD" ]; then
  echo "[RISK CORROBORATION] note: $CHANGED_LINES changed lines for a Lane: $LANE_VAL task — consider running /simplify before commit." >&2
fi

TRIPPED=""
add_cat() { TRIPPED="$TRIPPED $1"; }

# ── Path-based categories (reliable) ─────────────────────────────────────
echo "$STAGED_PATHS" | grep -qE '(^|/)settings\.json$|^hooks/|(^|/)\.claude/hooks/|render_plan\.py$' && add_cat "high-blast"
echo "$STAGED_PATHS" | grep -qE '(^|/)(migrations?|alembic)/' && add_cat "data-loss/migration"
echo "$STAGED_PATHS" | grep -qE '(^|/)(requirements[^/]*\.txt|package\.json|pyproject\.toml|go\.mod|Gemfile)$' && add_cat "external-provider"
echo "$STAGED_PATHS" | grep -E '^skills/[^/]+/SKILL\.md$|^skills/[^/]+/.*prompt[^/]*\.md$|^agents/[^/]+\.md$|^rules/[^/]+\.md$' | grep -qvE '(^|/)(README\.md|[A-Za-z0-9_-]+\.template\.md)$' && add_cat "workflow-engine"

# ── Keyword categories (added code lines only) ───────────────────────────
echo "$CODE_ADDED" | grep -qiE '(login|logout|\bsession\b|jwt|password|refresh_token|oauth|set_cookie|bcrypt|hashpw)' && add_cat "auth"
echo "$CODE_ADDED" | grep -qiE '(\brole\b|permission|is_admin|require_role|authorize|rbac|tenant_id|company_id|access_control)' && add_cat "authorization"
echo "$CODE_ADDED" | grep -qiE '(audit_log|access_log|encrypt|decrypt|\bpii\b|sensitive_data)' && add_cat "audit/security"
echo "$CODE_ADDED" | grep -qiE '(stripe|twilio|sendgrid|boto3|paypal|\bwebhook)' && add_cat "external-provider"
echo "$CODE_ADDED" | grep -qiE '(@app\.(get|post|put|delete|patch)|@router\.(get|post|put|delete|patch)|openapi)' && add_cat "public-contract"
echo "$CODE_ADDED" | grep -qiE '(DROP TABLE|DELETE FROM|TRUNCATE|ALTER TABLE|op\.drop|drop_table|drop_column)' && add_cat "data-loss/migration"
echo "$CODE_REMOVED" | grep -qiE '(assert |validator|required=True|\braise )' && add_cat "weakening-validation"

# De-duplicate tripped categories
TRIPPED=$(echo "$TRIPPED" | tr ' ' '\n' | grep -v '^$' | sort -u | tr '\n' ' ')
[ -z "$TRIPPED" ] && exit 0

# Partition into blocking vs warn-only by per-category mode
BLOCKING=""
WARNING=""
for cat in $TRIPPED; do
  if [ "$(category_mode "$cat")" = "block" ]; then
    BLOCKING="$BLOCKING $cat"
  else
    WARNING="$WARNING $cat"
  fi
done

# ── Decision ─────────────────────────────────────────────────────────────
if [ -n "$WARNING" ]; then
  echo "[RISK CORROBORATION] note: warn-mode categories present:$WARNING" >&2
fi

if [ -z "$BLOCKING" ]; then
  exit 0
fi

if [ "$LANE_VAL" = "high-risk" ]; then
  echo "[RISK CORROBORATION] hard-gate signals$BLOCKING corroborated by Lane: high-risk — OK." >&2
  exit 0
fi

if [ -n "$LANE_VAL" ]; then
  echo "[RISK CORROBORATION] BLOCKED (exit 2)." >&2
  echo "  Staged diff trips hard-gate categories:$BLOCKING" >&2
  echo "  But specs SUMMARY declares  Lane: $LANE_VAL  (below high-risk)." >&2
  echo "  Re-classify via /feature-intake (set Lane: high-risk), or have a human narrow scope." >&2
  echo "  Loosen: set the category's \"mode\" to \"warn\" in harness-manifest.json (durable), or put" >&2
  echo "  RISK_WARN_CATEGORIES in .claude/settings.local.json -> env (an inline VAR=x prefix never reaches a PreToolUse hook)." >&2
  exit 2
fi

# No declared Lane
if [ "${RISK_CORROBORATION_STRICT:-0}" = "1" ]; then
  echo "[RISK CORROBORATION] BLOCKED (strict, no Lane declared)." >&2
  echo "  Staged diff trips hard-gate categories:$BLOCKING" >&2
  echo "  Declare a Lane in specs/<slug>/SUMMARY.md (run /feature-intake) before committing." >&2
  exit 2
fi

echo "[RISK CORROBORATION] WARNING — hard-gate signals with no declared Lane:$BLOCKING" >&2
echo "  Nothing to corroborate against. If this is real change work, run /feature-intake" >&2
echo "  and record a Lane in specs/<slug>/SUMMARY.md. (Set RISK_CORROBORATION_STRICT=1 to enforce.)" >&2
exit 0
