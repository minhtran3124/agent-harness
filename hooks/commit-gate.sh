#!/bin/bash
# PreToolUse(Bash) commit gate: the single hook that gates `git commit` and `git push`.
#
# Usage: hooks/commit-gate.sh [--profile minimal|standard|strict]   (payload JSON on stdin)
#
# Flow (specs/simplify-hook-surface/design.md §2.1):
#   1. Parse the payload once — one jq for a Claude Bash payload, the normalizer otherwise.
#      An unclassifiable payload blocks (exit 2).
#   2. Anything that is not `git commit` / `git push` exits 0 here (the common case).
#   3. Resolve the profile (default standard; an unknown value warns and runs standard).
#   4. `git push` runs only check_untracked_py (strict), then exits.
#   5. `git commit` resolves the repo root, computes STAGED_PATHS, SPEC_SLUGS, LANE_VAL and
#      VERIFY_SUMMARY once, then runs the check functions below in a fixed order.
#
# Blocks with exit 2 (message on stderr), except the untracked-.py deny, which prints a
# permissionDecision:"deny" JSON on stdout and exits 0. Never exit 1: it is non-blocking.
# No set -e: flow is controlled explicitly. bash 3.2 compatible.
#
# Profiles (per-check membership):
#   check_untracked_py                        strict
#   check_secrets                             all
#   check_escalations / check_lane_evidence   standard, strict
#   check_run_state / check_risk              standard, strict (strict implies RISK_CORROBORATION_STRICT=1)
#   check_plan_scope                          standard, strict (warn; BLAST_RADIUS_STRICT=1 blocks)
#   check_app_gates                           strict, or REQUIRE_APP_GATES=1 in any profile

INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

# ── 1. Parse ─────────────────────────────────────────────────────────────
# Fast path: `tool_name == "Bash"` with a non-empty string command is the one shape the
# normalizer can only ever classify as shell/known, so resolving it here is equivalent —
# and it keeps the common case at one jq with no Python process. This hook runs on EVERY
# Bash tool call. Anything else goes to the normalizer.
CMD=$(printf '%s' "$INPUT" | jq -r '
  if (.tool_name == "Bash") and (.tool_input.command | type == "string") and (.tool_input.command != "")
  then .tool_input.command else empty end' 2>/dev/null)

if [ -z "$CMD" ]; then
  NORMALIZER="$SCRIPT_DIR/lib/normalize-tool-input.py"
  if command -v python3 >/dev/null 2>&1 && [ -f "$NORMALIZER" ]; then
    NORMALIZED=$(printf '%s' "$INPUT" | python3 "$NORMALIZER" --root "$ROOT" 2>/dev/null)
  else
    NORMALIZED='{"status":"unknown","tool_class":"unknown","command":null,"diagnostics":["normalizer-unavailable"]}'
  fi
  # One jq for the gate decision (all three values are single-line by construction:
  # status/tool_class are enum tokens, diagnostics are fixed slugs joined with ", ").
  { read -r STATUS; read -r TOOL_CLASS; read -r DIAG; } <<EOF
$(printf '%s' "$NORMALIZED" | jq -r '
    (.status // "unknown"),
    (.tool_class // "unknown"),
    ((.diagnostics // []) | join(", "))' 2>/dev/null)
EOF
  if [ "${STATUS:-unknown}" != "known" ] || [ "${TOOL_CLASS:-unknown}" != "shell" ]; then
    echo "[COMMIT GATE] could not safely classify Bash payload (${DIAG:-unparsed payload}) — redeploy/update the harness normalizer (blocking to fail safe)." >&2
    exit 2
  fi
  # Command is extracted separately: it may be multi-line, which a line-oriented read
  # would silently truncate — and a truncated command is what the git matcher tokenizes.
  CMD=$(printf '%s' "$NORMALIZED" | jq -r '.command // ""' 2>/dev/null)
fi

# ── 2. Filter: git commit / push only (tokenizing matcher — resists cd/&&/-C/-c bypass) ──
source "$SCRIPT_DIR/lib/git-command.sh" 2>/dev/null
# Fail closed: if the matcher lib is missing, block rather than skip every gate below.
command -v hook_cmd_is_git_commit_or_push >/dev/null 2>&1 \
  && command -v hook_cmd_is_git_commit >/dev/null 2>&1 || {
  echo "[COMMIT GATE] git-command matcher lib missing — redeploy harness (blocking to fail safe)." >&2
  exit 2
}
hook_cmd_is_git_commit_or_push "$CMD" || exit 0

# ── 3. Profile ───────────────────────────────────────────────────────────
PROFILE=standard
while [ $# -gt 0 ]; do
  case "$1" in
    --profile)   PROFILE="${2:-}"; shift 2 2>/dev/null || shift ;;
    --profile=*) PROFILE="${1#--profile=}"; shift ;;
    *)           shift ;;
  esac
done
case "$PROFILE" in
  minimal|standard|strict) ;;
  *)
    echo "[COMMIT GATE] unknown --profile '$PROFILE' — running the standard profile." >&2
    PROFILE=standard
    ;;
esac

# profile_allows <check> — the per-check membership table in the header, as data.
profile_allows() {
  case "$PROFILE:$1" in
    strict:*)             return 0 ;;
    standard:untracked_py) return 1 ;;
    standard:*)           return 0 ;;
    minimal:secrets)      return 0 ;;
    *)                    return 1 ;;
  esac
}

# ─────────────────────────────────────────────
# check_untracked_py: untracked .py files would break CI imports
# ─────────────────────────────────────────────
# Runs from CWD, before the commit context is resolved (push has no commit context).
check_untracked_py() {
  # Exclude the deployed harness itself. The anchor matters: `git ls-files` returns
  # repo-relative paths, so a root-level deployment is `.claude/<dir>/...` with NO leading
  # slash — a bare `/\.claude/` pattern misses it and denies every commit in a fresh consumer
  # whose .gitignore does not yet list .claude/. Match both `.claude/…` and `app/.claude/…`.
  FILES=$(git ls-files --others --exclude-standard 2>/dev/null | grep -E '\.py$' | grep -vE '(^|/)\.claude/')
  if [ -n "$FILES" ]; then
    jq -cn --arg f "$FILES" '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: ("Untracked .py not staged (would break CI imports):\n" + $f + "\n\nRun: git add <files> — or gitignore if intentional.")
      }
    }'
    # The deny above is the decision; nothing further needs to run.
    exit 0
  fi
}

profile_allows untracked_py && check_untracked_py

# ── 4. Push: nothing else applies ────────────────────────────────────────
hook_cmd_is_git_commit "$CMD" || exit 0

# ── 5. Commit context (computed once) ────────────────────────────────────
source "$SCRIPT_DIR/lib/lane.sh" 2>/dev/null
# Fail closed: a missing Lane-resolution lib must not silently let corroboration run
# against no Lane at all.
command -v hook_lib_resolve_lane >/dev/null 2>&1 || {
  echo "[COMMIT GATE] lane lib missing — redeploy harness (blocking to fail safe)." >&2
  exit 2
}

# Resolve the repo root. Order matters and is load-bearing (specs/fix-hook-project-root-resolution):
# NEVER derive it from SCRIPT_DIR. A hook installed outside the project (plugin packaging) whose own
# directory sits inside ANY git repo would resolve to THAT repo, and this gate would then audit the
# wrong repository and report success. The runtime's own answer comes first; git-from-CWD is second
# so tests/lib.sh (which cds into a temp repo and sets no CLAUDE_PROJECT_DIR) still resolves.
# SCRIPT_DIR remains only for locating libs.
REPO_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
if [ -z "$REPO_DIR" ] || [ ! -d "$REPO_DIR" ]; then
  echo "[COMMIT GATE] BLOCKED — cannot determine the project root." >&2
  echo "  CLAUDE_PROJECT_DIR is unset and CWD is not inside a git work tree." >&2
  echo "  Refusing to guess: a gate that resolves the wrong repo passes silently." >&2
  exit 2
fi
cd "$REPO_DIR" || exit 2

STAGED_PATHS=$(git diff --cached --name-only 2>/dev/null || true)
SPEC_SLUGS=$(printf '%s\n' "$STAGED_PATHS" | grep -oE '^specs/[^/]+/' | sort -u || true)

# Declared Lane: prefer a staged SUMMARY.md, else the status:active plan's sibling
# SUMMARY.md (hooks/lib/lane.sh) — never a "most recently modified on disk" guess.
LANE=$(hook_lib_resolve_lane "$REPO_DIR" "$STAGED_PATHS")
# Normalize: extract tiny|normal|high-risk
LANE_VAL=$(echo "$LANE" | tr 'A-Z' 'a-z' | grep -oE 'tiny|normal|high-risk' | head -1)

# The lane/evidence helper. The harness repo keeps it at scripts/; a CONSUMER repo receives the
# deployed copy at .claude/scripts/. Empty when neither exists — lane evidence and the Verify
# re-run stay fail-open on that.
VERIFY_SUMMARY=""
for _vs_cand in scripts/verify_summary.py .claude/scripts/verify_summary.py; do
  if [ -f "$_vs_cand" ]; then VERIFY_SUMMARY="$_vs_cand"; break; fi
done

# ─────────────────────────────────────────────
# check_secrets: secrets scan + staged .env (no python3 required)
# ─────────────────────────────────────────────
check_secrets() {
  echo "[COMMIT GATE] Secrets scan..." >&2

  # Get staged diff, exclude test files, examples, and docs.
  # Test exclusions are DEPTH-INDEPENDENT and cover both layouts: a bare ':!tests/' pathspec only
  # matches a repo-root `tests/`, so in a monorepo (`apps/api/tests/`) or a JS tree (`__tests__/`)
  # every placeholder credential in a test file reached the matcher below. `'x'.repeat(32)` assigned
  # to a const named SECRET is what that looks like: a hard block on content with no secret in it.
  STAGED_DIFF=$(git diff --cached -U0 -- ':!*tests/*' ':!*__tests__/*' ':!*.example' ':!*.md' ':!docs/' 2>/dev/null || true)

  if echo "$STAGED_DIFF" | grep -qEi '(sk-[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|password\s*=\s*["'"'"'][^"'"'"']+|passwd\s*=|api_key\s*=\s*["'"'"'][^"'"'"']+|apikey\s*=\s*["'"'"'][^"'"'"']+|client_secret\s*=\s*["'"'"'][^"'"'"']+|\bsecret\s*=\s*["'"'"'][^"'"'"']+)'; then
    echo "[COMMIT GATE] Secrets scan... FAILED" >&2
    echo "  BLOCKED: Potential secrets detected in staged changes." >&2
    echo "  Run 'git diff --cached' to review." >&2
    exit 2
  fi

  # Check for .env files staged
  if printf '%s\n' "$STAGED_PATHS" | grep -qE '\.env$'; then
    echo "[COMMIT GATE] Secrets scan... FAILED" >&2
    echo "  BLOCKED: .env file staged for commit." >&2
    exit 2
  fi

  echo "[COMMIT GATE] Secrets scan... PASSED" >&2
}

# ─────────────────────────────────────────────
# check_escalations: pending escalations (deny-on-no-response, mechanized)
# ─────────────────────────────────────────────
# templates/ESCALATIONS.template.md declares deny-on-no-response; this makes it
# real (review 2026-07-16 finding C5: a spec shipped with decision: pending).
# Scope: block only commits that touch specs/<slug>/ for a slug whose
# ESCALATIONS.md still has a pending decision — recording the decision in the
# same commit unblocks (the staged copy is what gets checked).
check_escalations() {
  for slug_dir in $SPEC_SLUGS; do
    esc="${slug_dir}ESCALATIONS.md"
    # Prefer the staged copy (a commit recording the decision must self-unblock)
    esc_content=$(git show ":$esc" 2>/dev/null || cat "$esc" 2>/dev/null || true)
    [ -z "$esc_content" ] && continue
    if echo "$esc_content" | grep -qiE '^[-*]?[[:space:]]*decision:[[:space:]]*pending'; then
      echo "[COMMIT GATE] Escalations... FAILED" >&2
      echo "  BLOCKED: $esc has 'decision: pending' (deny-on-no-response)." >&2
      echo "  A human records the decision in that file (decision/decided_by/decided_at)," >&2
      echo "  then this commit unblocks. See rules/orchestration.md → Escalation decision." >&2
      exit 2
    fi
  done
  echo "[COMMIT GATE] Escalations... PASSED" >&2
}

# ─────────────────────────────────────────────
# check_lane_evidence: lane evidence (mechanizes rules/auto-correct-scope.md)
# ─────────────────────────────────────────────
# rules/auto-correct-scope.md calls scripts/verify_summary.py --lane the single
# source of truth for the lane -> evidence mapping, but nothing originally invoked it
# (PR #119 review finding: the script was proven by unit tests and then never
# run against a real SUMMARY). This makes the mapping real.
# Scope mirrors check_escalations: only commits touching specs/<slug>/, and the STAGED
# SUMMARY is what gets checked, so a commit that records the evidence
# self-unblocks. Fail-open when python3 is unavailable (a missing interpreter
# must not gate commits — same convention as the Verify re-run in check_app_gates).
check_lane_evidence() {
  [ -n "$SPEC_SLUGS" ] || return 0
  if command -v python3 >/dev/null 2>&1 && [ -n "$VERIFY_SUMMARY" ]; then
    EV_FAILED=0
    for slug_dir in $SPEC_SLUGS; do
      summary="${slug_dir}SUMMARY.md"
      plan="${slug_dir}PLAN.md"
      # Materialize the INDEXED spec pair into one temp dir: the gate must judge the
      # tree that is actually being committed, not the working copy. Staging a PLAN
      # with an SC contract and then editing/removing it before `git commit` must not
      # let the commit through against different (or absent) criteria.
      ev_dir=$(mktemp -d 2>/dev/null) || continue
      ev_tmp="$ev_dir/SUMMARY.md"
      # Prefer the staged copy; fall back to on-disk (slug touched but SUMMARY unstaged)
      if ! git show ":$summary" >"$ev_tmp" 2>/dev/null; then
        if [ -f "$summary" ]; then
          cp "$summary" "$ev_tmp" 2>/dev/null || { rm -rf "$ev_dir"; continue; }
        else
          # No SUMMARY at all for this slug — not this check's business
          # (a slug dir can hold only PLAN.md/design.md).
          rm -rf "$ev_dir"; continue
        fi
      fi
      # Same rule for the PLAN that supplies the SC table. `git show :PLAN.md` covers
      # both "staged edit" and "tracked, unmodified"; the on-disk fallback only fires
      # for an untracked PLAN (which the commit is not recording anyway).
      if ! git show ":$plan" >"$ev_dir/PLAN.md" 2>/dev/null; then
        rm -f "$ev_dir/PLAN.md"
        [ -f "$plan" ] && cp "$plan" "$ev_dir/PLAN.md" 2>/dev/null || true
      fi
      # Capture rather than stream: the script names the temp path, which would
      # be meaningless to the committer. Re-label it as the real SUMMARY.
      # --plan-dir points SC-coverage at the materialized index copy — the sibling
      # lookup would otherwise resolve against the working tree.
      # Warn-first advisories (e.g. the `### Not auto-verified` rollout) are printed
      # by --lane on a PASSING run too, so the output is relayed on both paths. A
      # warning only echoed on failure is a warning nobody ever reads.
      if ! ev_out=$(python3 "$VERIFY_SUMMARY" --lane "$ev_tmp" --plan-dir "$ev_dir" 2>&1); then
        echo "${ev_out//$ev_tmp/$summary}" >&2
        EV_FAILED=1
      else
        echo "${ev_out//$ev_tmp/$summary}" | grep '^[[:space:]]*!' >&2 || true
      fi
      rm -rf "$ev_dir"
    done
    if [ "$EV_FAILED" = "1" ]; then
      echo "[COMMIT GATE] Lane evidence... FAILED" >&2
      echo "  BLOCKED: a staged SUMMARY.md is missing the evidence its Lane requires." >&2
      echo "  tiny -> Lane/Confidence/Reason filled; normal -> + a real ### Verify row;" >&2
      echo "  high-risk -> + a non-empty ### Rollback. See rules/auto-correct-scope.md." >&2
      exit 2
    fi
    echo "[COMMIT GATE] Lane evidence... PASSED" >&2
  else
    echo "[COMMIT GATE] Lane evidence skipped: python3 or verify_summary.py unavailable (looked in scripts/ and .claude/scripts/)." >&2
  fi
}

# ─────────────────────────────────────────────
# check_run_state: run-state artifacts travel with the spec (RUN.json + events.jsonl)
# ─────────────────────────────────────────────
# `.gitignore` says "RUN.json + events.jsonl stay tracked", but nothing enforced it:
# feature-intake creates RUN.json best-effort and no skill ever named it in a
# `git add`, so whether the run record reached the PR depended on whether the
# agent happened to stage the whole slug directory (observed: two merged consumer
# PRs whose RUN.json/events.jsonl were still untracked on disk afterwards).
# Scope mirrors check_escalations: only commits touching specs/<slug>/. Two tiers:
#   - UNTRACKED on disk and not staged  -> BLOCK (the file would never reach git)
#   - tracked but with UNSTAGED changes -> warn (an appended event left behind)
# Verifies: the artifact's git state (untracked / unstaged / staged).
# Does not verify: the artifact's content or that its state matches the PLAN.
# Break-glass: REQUIRE_RUN_STATE_STAGED=0 downgrades the block to a warning.
check_run_state() {
  RS_BLOCKED=0
  for slug_dir in $SPEC_SLUGS; do
    for rs_name in RUN.json events.jsonl; do
      rs="${slug_dir}${rs_name}"
      [ -f "$rs" ] || continue
      # Staged (added or modified) in this commit — fine either way.
      if printf '%s\n' "$STAGED_PATHS" | grep -qxF "$rs"; then continue; fi
      if ! git ls-files --error-unmatch "$rs" >/dev/null 2>&1; then
        if [ "${REQUIRE_RUN_STATE_STAGED:-1}" = "0" ]; then
          echo "  ! $rs exists but is UNTRACKED — it will not reach the PR. Run: git add $rs" >&2
        else
          echo "  BLOCKED: $rs exists but is UNTRACKED — it will not reach the PR." >&2
          RS_BLOCKED=1
        fi
      elif ! git diff --quiet -- "$rs" 2>/dev/null; then
        echo "  ! $rs has unstaged changes that this commit leaves behind. Run: git add $rs" >&2
      fi
    done
  done
  if [ "$RS_BLOCKED" = "1" ]; then
    echo "[COMMIT GATE] Run-state artifacts... FAILED" >&2
    echo "  RUN.json / events.jsonl are tracked artifacts (.gitignore only excludes the .lock)." >&2
    echo "  Stage them by name in this commit (REQUIRE_RUN_STATE_STAGED=0 downgrades to a warning)." >&2
    exit 2
  fi
  [ -n "$SPEC_SLUGS" ] && echo "[COMMIT GATE] Run-state artifacts... PASSED" >&2
  return 0
}

# ─────────────────────────────────────────────
# check_risk: corroborate the declared Lane against the staged diff
# ─────────────────────────────────────────────
# The diff cannot lie about what it touched. If the staged changes trip a
# hard-gate signal (auth, authorization, data-loss/migration, audit, external
# provider, public contract, weakening validation, high-blast files) but the
# declared Lane is below `high-risk`, the commit is BLOCKED (exit 2) — the agent
# under-classified its own work.
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
#     Set RISK_CORROBORATION_STRICT=1 (implied by --profile strict) to make the
#     no-Lane case fail-closed.
#   - Per-category mode (block|warn) comes from EXACTLY TWO index-safe sources: the
#     git INDEX copy of harness-manifest.json (`git show :path`), else the embedded
#     defaults in hooks/lib/gate-modes.default.sh (2 warn / 7 block parity). A worktree
#     or .claude/ policy file is NEVER read (invariant #2, SC-8). Unknown slug / missing
#     mode within a present index manifest still => block (fail-safe). Consumer repos
#     with no tracked manifest get the embedded parity, not block-all.

# Per-category mode: harness-manifest.json is the authority.
# Durable loosening: set the category's "mode" to "warn" in harness-manifest.json.
# Session-scoped loosening: list categories in RISK_WARN_CATEGORIES (comma/space
# separated), e.g. RISK_WARN_CATEGORIES="data-loss/migration". The variable must be
# in the HOOK'S OWN process environment — .claude/settings.local.json -> "env", or a
# var exported in the session. An inline `VAR=x git commit` prefix does NOT work:
# a PreToolUse hook runs before the command, so the prefix never reaches it.
# Loosen one at a time; never auth/external-provider first; revert on any incident.
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

check_risk() {
  # Read the manifest from the INDEX (`git show :path`), not the worktree — the risk
  # signals and the Lane are both index-side, so the mode must be too. Otherwise an
  # UNSTAGED "mode": "warn" edit would loosen a gate for a commit whose tree still
  # ships block-mode (Codex review, PR #160). INVARIANT #2 (SC-8): mode policy comes
  # from EXACTLY TWO index-safe sources — the git INDEX here, else the embedded defaults
  # below. NEVER a worktree file and NEVER .claude/harness-manifest.json.
  GATE_MODES=$(git show :harness-manifest.json 2>/dev/null | jq -r \
    '.hard_gates.detectable[]? | "\(.slug)=\(.mode // "block")"' 2>/dev/null || true)
  # Index copy absent/unreadable/invalid => fall back to the embedded defaults shipped
  # beside this hook (2 warn / 7 block parity), NOT block-all. The defaults are compile-
  # time constants inside the harness's own trust boundary — an unstaged edit cannot
  # touch them — so a consumer repo that does not track the manifest still gets the
  # intended modes. (Missing default file => "" => every category blocks, still fail-safe.)
  if [ -z "$GATE_MODES" ]; then
    source "$SCRIPT_DIR/lib/gate-modes.default.sh" 2>/dev/null
    GATE_MODES="$GATE_MODES_DEFAULT"
  fi

  [ -z "$STAGED_PATHS" ] && return 0

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

  # ── Diff-size sanity signal (warn-only — never affects exit code) ──
  # Large diffs for a lightweight declared lane are a simplicity smell.
  # tiny=150, normal=600 changed (added+removed) lines; high-risk / no lane:
  # no threshold (ceremony is already expected, or there is nothing to compare
  # against) — skip the numstat scan entirely for those, it's the common case.
  SIZE_THRESHOLD=""
  case "$LANE_VAL" in
    tiny)   SIZE_THRESHOLD=150 ;;
    normal) SIZE_THRESHOLD=600 ;;
  esac
  if [ -n "$SIZE_THRESHOLD" ]; then
    # Deliberately UNFILTERED (no pathspec exclusions) — unlike $CODE_ADDED/$CODE_REMOVED
    # above, this signal must see the full diff (skills/, hooks/, docs/, etc. included)
    # or a large diff confined to those excluded paths would compute near-zero and never
    # warn. --numstat gives "<added>\t<removed>\t<path>" per file; binary files report
    # "-\t-\t<path>" and are skipped (treated as 0, not an arithmetic error).
    CHANGED_LINES=$(git diff --cached --numstat 2>/dev/null | awk '
      { a=$1; r=$2; if (a ~ /^[0-9]+$/) sum+=a; if (r ~ /^[0-9]+$/) sum+=r }
      END { print sum+0 }
    ')
    if [ "$CHANGED_LINES" -gt "$SIZE_THRESHOLD" ]; then
      echo "[RISK CORROBORATION] note: $CHANGED_LINES changed lines for a Lane: $LANE_VAL task — consider running the simplify pass before commit." >&2
    fi
  fi

  TRIPPED=""
  add_cat() { TRIPPED="$TRIPPED $1"; }

  # ── Path-based categories (reliable) ──
  echo "$STAGED_PATHS" | grep -qE '(^|/)settings\.json$|^hooks/|(^|/)\.claude/hooks/|render_plan\.py$' && add_cat "high-blast"
  echo "$STAGED_PATHS" | grep -qE '(^|/)(migrations?|alembic)/' && add_cat "data-loss/migration"
  echo "$STAGED_PATHS" | grep -qE '(^|/)(requirements[^/]*\.txt|package\.json|pyproject\.toml|go\.mod|Gemfile)$' && add_cat "external-provider"
  echo "$STAGED_PATHS" | grep -E '^skills/[^/]+/SKILL\.md$|^skills/[^/]+/.*prompt[^/]*\.md$|^agents/[^/]+\.md$|^rules/[^/]+\.md$' | grep -qvE '(^|/)(README\.md|[A-Za-z0-9_-]+\.template\.md)$' && add_cat "workflow-engine"

  # ── Keyword categories (added code lines only) ──
  echo "$CODE_ADDED" | grep -qiE '(login|logout|\bsession\b|jwt|password|refresh_token|oauth|set_cookie|bcrypt|hashpw)' && add_cat "auth"
  echo "$CODE_ADDED" | grep -qiE '(\brole\b|permission|is_admin|require_role|authorize|rbac|tenant_id|company_id|access_control)' && add_cat "authorization"
  echo "$CODE_ADDED" | grep -qiE '(audit_log|access_log|encrypt|decrypt|\bpii\b|sensitive_data)' && add_cat "audit/security"
  echo "$CODE_ADDED" | grep -qiE '(stripe|twilio|sendgrid|boto3|paypal|\bwebhook)' && add_cat "external-provider"
  echo "$CODE_ADDED" | grep -qiE '(@app\.(get|post|put|delete|patch)|@router\.(get|post|put|delete|patch)|openapi)' && add_cat "public-contract"
  echo "$CODE_ADDED" | grep -qiE '(DROP TABLE|DELETE FROM|TRUNCATE|ALTER TABLE|op\.drop|drop_table|drop_column)' && add_cat "data-loss/migration"
  echo "$CODE_REMOVED" | grep -qiE '(assert |validator|required=True|\braise )' && add_cat "weakening-validation"

  # De-duplicate tripped categories
  TRIPPED=$(echo "$TRIPPED" | tr ' ' '\n' | grep -v '^$' | sort -u | tr '\n' ' ')
  [ -z "$TRIPPED" ] && return 0

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

  # ── Decision ──
  if [ -n "$WARNING" ]; then
    echo "[RISK CORROBORATION] note: warn-mode categories present:$WARNING" >&2
  fi

  if [ -z "$BLOCKING" ]; then
    return 0
  fi

  if [ "$LANE_VAL" = "high-risk" ]; then
    echo "[RISK CORROBORATION] hard-gate signals$BLOCKING corroborated by Lane: high-risk — OK." >&2
    return 0
  fi

  if [ -n "$LANE_VAL" ]; then
    echo "[RISK CORROBORATION] BLOCKED (exit 2)." >&2
    echo "  Staged diff trips hard-gate categories:$BLOCKING" >&2
    echo "  But specs SUMMARY declares  Lane: $LANE_VAL  (below high-risk)." >&2
    echo "  Re-classify with the feature-intake skill (set Lane: high-risk), or have a human narrow scope." >&2
    echo "  Loosen: set the category's \"mode\" to \"warn\" in harness-manifest.json (durable), or put" >&2
    echo "  RISK_WARN_CATEGORIES in .claude/settings.local.json -> env (an inline VAR=x prefix never reaches a PreToolUse hook)." >&2
    exit 2
  fi

  # No declared Lane
  if [ "${RISK_CORROBORATION_STRICT:-0}" = "1" ] || [ "$PROFILE" = "strict" ]; then
    echo "[RISK CORROBORATION] BLOCKED (strict, no Lane declared)." >&2
    echo "  Staged diff trips hard-gate categories:$BLOCKING" >&2
    echo "  Declare a Lane in specs/<slug>/SUMMARY.md (run the feature-intake skill) before committing." >&2
    exit 2
  fi

  echo "[RISK CORROBORATION] WARNING — hard-gate signals with no declared Lane:$BLOCKING" >&2
  echo "  Nothing to corroborate against. If this is real change work, run the feature-intake skill" >&2
  echo "  and record a Lane in specs/<slug>/SUMMARY.md. (Set RISK_CORROBORATION_STRICT=1 to enforce.)" >&2
  return 0
}

# ─────────────────────────────────────────────
# check_plan_scope: staged paths outside the active PLAN.md <files> set
# ─────────────────────────────────────────────
# Catches scope creep at each commit (a wave touching files it never declared). Default is
# a WARN on stderr; BLAST_RADIUS_STRICT=1 blocks. No-op when: no active PLAN.md exists, the
# plan declares no <files>, or the staged path is bookkeeping (specs/, docs/, *.md).
# `status: active` is the ONLY thing that arms this check — there is deliberately no "else
# most recent" fallback: a shipped plan's <files> set is a record of what that work touched,
# not a scope constraint on everything that comes after it.
check_plan_scope() {
  PLAN=$(hook_lib_find_active_plan "$REPO_DIR") || return 0

  # Declared files: <files>...</files> tags (XML syntax) plus `- **Files:** ...`
  # field bullets (markdown syntax, rules/plan-format.md "Task Schema — two
  # syntaxes"). Both comma-separated; union of the two sets. Fenced examples may
  # leak into the set — harmless for an advisory allowlist (extra entries only).
  DECLARED_XML=$(grep -oE '<files>[^<]*</files>' "$PLAN" 2>/dev/null \
    | sed -E 's#</?files>##g')
  DECLARED_MD=$(grep -iE '^[-*][[:space:]]+\*\*Files(:\*\*|\*\*:)' "$PLAN" 2>/dev/null \
    | sed -E 's/^[-*][[:space:]]+\*\*[Ff]iles(:\*\*|\*\*:)[[:space:]]*//')
  DECLARED=$(printf '%s\n%s\n' "$DECLARED_XML" "$DECLARED_MD" \
    | tr ',' '\n' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' | grep -v '^$')
  [ -z "$DECLARED" ] && return 0

  OUTSIDE=""
  while IFS= read -r REL; do
    [ -n "$REL" ] || continue
    case "$REL" in specs/*|docs/*|*.md) continue ;; esac
    INSCOPE=0
    bREL=$(basename "$REL")
    while IFS= read -r d; do
      [ -z "$d" ] && continue
      [ "$REL" = "$d" ] && INSCOPE=1 && break
      case "$REL" in */"$d") INSCOPE=1; break ;; esac
      [ "$bREL" = "$(basename "$d")" ] && INSCOPE=1 && break
    done <<EOF
$DECLARED
EOF
    if [ "$INSCOPE" -eq 0 ]; then
      OUTSIDE="${OUTSIDE}${OUTSIDE:+
}$REL"
    fi
  done <<EOF
$STAGED_PATHS
EOF

  [ -n "$OUTSIDE" ] || return 0
  if [ "${BLAST_RADIUS_STRICT:-0}" = "1" ]; then
    echo "[BLAST RADIUS] Paths outside the active plan's <files> set (${PLAN#"$REPO_DIR"/}):" >&2
    printf '%s\n' "$OUTSIDE" >&2
    echo "  Scope creep — escalate, or add the files to the plan." >&2
    exit 2
  fi
  OUTSIDE_DISPLAY=$(printf '%s\n' "$OUTSIDE" | paste -sd ',' -)
  echo "[BLAST RADIUS] blast-radius: staged path(s) $OUTSIDE_DISPLAY which are NOT in the active plan <files> set (${PLAN#"$REPO_DIR"/}). If intentional, add them to the plan; otherwise treat as scope creep and consider escalating per rules/orchestration.md." >&2
}

# ─────────────────────────────────────────────
# check_app_gates: debug artifacts, ### Verify evidence, targeted tests (app/**/*.py)
# ─────────────────────────────────────────────
check_app_gates() {
  # ── Debug artifacts in app/ code ──
  echo "[COMMIT GATE] Debug artifacts..." >&2

  # Only check added lines (lines starting with +) in app/**/*.py
  DEBUG_DIFF=$(git diff --cached -U0 -- 'app/**/*.py' 2>/dev/null || true)
  ADDED_LINES=$(echo "$DEBUG_DIFF" | grep -E '^\+[^+]' || true)

  if echo "$ADDED_LINES" | grep -qE '(breakpoint\(\)|import pdb|from pdb)'; then
    echo "[COMMIT GATE] Debug artifacts... FAILED" >&2
    echo "  BLOCKED: Found breakpoint()/pdb in staged app/ code." >&2
    exit 2
  fi

  # Check for bare print( — only lines that START with print( (after whitespace)
  if echo "$ADDED_LINES" | grep -qE '^\+\s*print\('; then
    echo "[COMMIT GATE] Debug artifacts... FAILED" >&2
    echo "  BLOCKED: Found bare print() in staged app/ code." >&2
    echo "  Use logger instead, or remove debug prints." >&2
    exit 2
  fi

  echo "[COMMIT GATE] Debug artifacts... PASSED" >&2

  # ── Evidence (### Verify) required for app/ changes (opt-in via REQUIRE_VERIFY=1) ──
  if [[ "${REQUIRE_VERIFY:-0}" == "1" ]]; then
    APP_STAGED=$(printf '%s\n' "$STAGED_PATHS" | grep -E '^app/.*\.py$' || true)
    if [[ -n "$APP_STAGED" ]]; then
      SUMMARY=$(printf '%s\n' "$STAGED_PATHS" | grep -E '(^|/)SUMMARY\.md$' | head -1)
      [[ -z "$SUMMARY" ]] && SUMMARY=$(ls -t specs/*/SUMMARY.md 2>/dev/null | head -1)
      if [[ -z "$SUMMARY" ]] || ! grep -qE '^### Verify' "$SUMMARY" 2>/dev/null; then
        echo "[COMMIT GATE] Evidence... FAILED" >&2
        echo "  BLOCKED: app/ changes staged but no '### Verify' block in specs/<slug>/SUMMARY.md." >&2
        echo "  Record the command(s) run + results (evidence over assertion), or unset REQUIRE_VERIFY." >&2
        exit 2
      fi
      echo "[COMMIT GATE] Evidence (### Verify present)... PASSED" >&2

      # Re-run the ### Verify table so proof is machine-verified, not self-reported.
      # Degrade (warn, do not block) when python3 or the script is unavailable —
      # a missing interpreter must not gate commits (fail-open, like the `|| true`
      # convention elsewhere in this hook).
      SLUG=$(basename "$(dirname "$SUMMARY")")
      if command -v python3 >/dev/null 2>&1 && [[ -n "$VERIFY_SUMMARY" ]]; then
        if ! python3 "$VERIFY_SUMMARY" --check "$SLUG" >&2; then
          echo "[COMMIT GATE] Evidence (### Verify re-run)... FAILED" >&2
          echo "  BLOCKED: claimed Exit codes in $SUMMARY do not match a fresh run (see mismatch above)." >&2
          echo "  Fix the commands/exit codes in the ### Verify table, or unset REQUIRE_VERIFY." >&2
          exit 2
        fi
        echo "[COMMIT GATE] Evidence (### Verify re-run)... PASSED" >&2
      else
        echo "[COMMIT GATE] Evidence re-run skipped: python3 or verify_summary.py unavailable (scripts/, .claude/scripts/) — presence check only." >&2
      fi
    fi
  fi

  # ── Targeted tests for changed app/ files ──
  # Collect staged app/**/*.py files
  CHANGED_APP_FILES=$(git diff --cached --name-only -- 'app/**/*.py' 2>/dev/null || true)

  if [[ -z "$CHANGED_APP_FILES" ]]; then
    echo "[COMMIT GATE] No app/ Python files staged — skipping tests." >&2
    return 0
  fi

  # Map app files to test files
  TEST_FILES=""
  FILE_COUNT=0

  while IFS= read -r app_file; do
    [[ -z "$app_file" ]] && continue

    # Strip app/ prefix, get directory and filename
    relative="${app_file#app/}"
    dir_part=$(dirname "$relative")
    base_name=$(basename "$relative" .py)

    # Build candidate test paths (check nested first, then flattened)
    candidates=(
      "tests/${dir_part}/test_${base_name}.py"
      "tests/$(dirname "$dir_part")/test_${base_name}.py"
    )

    for candidate in "${candidates[@]}"; do
      if [[ -f "$candidate" ]]; then
        TEST_FILES="$TEST_FILES $candidate"
        FILE_COUNT=$((FILE_COUNT + 1))
        break
      fi
    done
  done <<< "$CHANGED_APP_FILES"

  if [[ -z "$TEST_FILES" ]]; then
    echo "[COMMIT GATE] No matching test files found — skipping tests." >&2
    return 0
  fi

  echo "[COMMIT GATE] Running tests for $FILE_COUNT changed file(s)..." >&2

  # Run pytest — no coverage, no integration tests, stop at first failure
  # shellcheck disable=SC2086
  OUTPUT=$(python -m pytest $TEST_FILES -x -q --tb=short --no-cov -m "not integration" -p no:cacheprovider 2>&1)
  RESULT=$?

  echo "$OUTPUT" | tail -20 >&2

  if [[ $RESULT -ne 0 ]]; then
    echo "[COMMIT GATE] Tests... FAILED" >&2
    echo "  BLOCKED: Fix test failures before committing." >&2
    exit 2
  fi

  echo "[COMMIT GATE] Tests... PASSED" >&2

  # ── Hint: crystallization reminder ──
  STAGED_APP_COUNT=$(git diff --cached --name-only -- 'app/**/*.py' 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$STAGED_APP_COUNT" -ge 5 ]]; then
    echo "" >&2
    echo "  ★ Large session detected ($STAGED_APP_COUNT app/ files)." >&2
    echo "    Consider running the compound skill to crystallize learnings." >&2
    echo "" >&2
  fi
}

# ── 6. Run the checks in a fixed order ───────────────────────────────────
check_secrets
profile_allows escalations   && check_escalations
profile_allows lane_evidence && check_lane_evidence
profile_allows run_state     && check_run_state
profile_allows risk          && check_risk
profile_allows plan_scope    && check_plan_scope
if [ "$PROFILE" = "strict" ] || [ "${REQUIRE_APP_GATES:-}" = "1" ]; then
  check_app_gates
else
  echo "[COMMIT GATE] App checks (debug artifacts / evidence / targeted tests) skipped: set REQUIRE_APP_GATES=1 to enable." >&2
fi

exit 0
