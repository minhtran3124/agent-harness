#!/usr/bin/env bash
# Install the claude-skills harness into a target project.
#
# Fetches the harness source (git clone into a temp dir, or a local checkout via --source),
# then builds the loadable .claude/ in the target via deploy-harness.sh --target, and scaffolds
# the workflow's structural dirs (specs/, docs/solutions/) via
# init-structure.sh — CREATE-IF-MISSING only. The installer never DELETES or OVERWRITES a
# target file: it merge-syncs .claude/, merges one server entry into .mcp.json, and only ADDS
# structural files that are absent. (The historical data-loss incident was a prior installer
# staging payload at the root then *pruning* it — deletion, which create-if-missing never does.)
# Designed to run piped:
#   curl -fsSL https://raw.githubusercontent.com/minhtran3124/harness-skills/main/scripts/install-harness.sh | bash -s -- --yes
#
# Usage:  bash scripts/install-harness.sh [options]
set -euo pipefail

# ---------- config (overridable by env or flags) ----------
REPO_URL="${CS_REPO_URL:-https://github.com/minhtran3124/harness-skills}"
BRANCH="${CS_BRANCH:-main}"
TARGET_DIR="$PWD"
SOURCE_DIR=""
ASSUME_YES=0
FORCE=0
OVERWRITE_CONFLICTS=0
DRY_RUN=0
KEEP_SOURCES=0

# Harness source-of-truth items. Deployed into .claude/ straight from the fetched source;
# copied into the target only with --keep-sources (under .harness-source/), never to the
# target root — a previous installer staged these at the root and pruned them afterward,
# which destroyed real project files when those names already existed (or when run inside
# the harness-skills repo itself).
PAYLOAD=(skills agents hooks rules templates settings.json scripts/deploy-harness.sh scripts/init-structure.sh VERSION CHANGELOG.md)
STAGE_NAME=".harness-source"

# ---------- styling ----------
if [ -t 1 ]; then
  B=$'\033[1m'; D=$'\033[2m'; R=$'\033[0m'; G=$'\033[32m'; C=$'\033[36m'; Y=$'\033[33m'; M=$'\033[35m'; RED=$'\033[31m'
else
  B=; D=; R=; G=; C=; Y=; M=; RED=
fi
log()  { printf '  %s\n' "$*"; }
ok()   { printf '  %s✓%s %s\n' "$G" "$R" "$*"; }
info() { printf '  %s•%s %s\n' "$C" "$R" "$*"; }
warn() { printf '  %s⚠ %s%s\n' "$Y" "$*" "$R"; }
fail() { printf '\n  %s✗ %s%s\n\n' "$RED" "$*" "$R" >&2; exit 1; }

# True only when this process can actually open its controlling terminal. `[ -r /dev/tty ]`
# is NOT equivalent: access(2) sees the mode bits of the /dev/tty alias node and reports it
# readable even after setsid(), so a tty-less run would fall into the prompt branch and die
# on `printf > /dev/tty`. Mirrors have_tty() in deploy-harness.sh.
have_tty() { (exec < /dev/tty) 2>/dev/null; }

usage() {
  cat <<EOF
Install the claude-skills harness into a target project.

Usage: install-harness.sh [options]

Options:
  -d, --directory <path>  Target project dir (default: current dir)
  -b, --branch <name>     Branch to install from (default: ${BRANCH})
      --source <path>     Use a local claude-skills checkout instead of cloning
  -y, --yes               Non-interactive: re-sync an existing .claude/ without asking.
                          Protected files (bootstrap-generated, e.g. rules/architecture.md)
                          keep your local copy; the incoming version is saved alongside as
                          <file>.harness-incoming for review.
      --force             Same as --yes (kept for compatibility) — NOT "overwrite": protected
                          files are still kept, not clobbered. Use --overwrite-conflicts for that.
      --overwrite-conflicts  Non-interactive: replace protected files with the incoming
                          harness version instead of keeping your local copy (no prompt,
                          no .harness-incoming sidecar). Implies --yes: it consents to the
                          re-sync of an existing .claude/ as well.
      --keep-sources      Also copy the harness sources into <target>/${STAGE_NAME}/
                          for inspection or offline re-sync (default: no copy)
      --dry-run           Show what would happen, including any protected-file conflicts;
                          write nothing
  -h, --help              Show this help

Examples:
  curl -fsSL https://raw.githubusercontent.com/minhtran3124/harness-skills/${BRANCH}/scripts/install-harness.sh | bash -s -- --yes
  bash scripts/install-harness.sh --directory /path/to/project --yes
  bash scripts/install-harness.sh --source . --dry-run -d /tmp/demo
EOF
}

# ---------- args ----------
while [ $# -gt 0 ]; do
  case "$1" in
    -d|--directory) TARGET_DIR="${2:?--directory needs a path}"; shift 2 ;;
    -b|--branch)    BRANCH="${2:?--branch needs a name}"; shift 2 ;;
    --source)       SOURCE_DIR="${2:?--source needs a path}"; shift 2 ;;
    -y|--yes)       ASSUME_YES=1; shift ;;
    --force)        FORCE=1; ASSUME_YES=1; shift ;;
    --overwrite-conflicts) OVERWRITE_CONFLICTS=1; shift ;;
    --keep-sources) KEEP_SOURCES=1; shift ;;
    --dry-run)      DRY_RUN=1; shift ;;
    -h|--help)      usage; exit 0 ;;
    *)              fail "Unknown option: $1  (see --help)" ;;
  esac
done

mkdir -p "$TARGET_DIR"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd -P)"

printf '\n  %s%s🧙 claude-skills harness — installer%s\n' "$B" "$M" "$R"
printf '  %s→ %s%s\n\n' "$D" "$TARGET_DIR" "$R"

# ---------- prerequisites ----------
command -v jq  >/dev/null 2>&1 || fail "jq is required (deploy step needs it). Install jq and re-run."
if [ -z "$SOURCE_DIR" ]; then
  command -v git >/dev/null 2>&1 || fail "git is required to clone (or pass --source <local checkout>)."
fi
UVX_MISSING=0
if ! command -v uvx >/dev/null 2>&1; then
  UVX_MISSING=1
  warn "uvx not found — the code-review-graph MCP server launches through it."
  printf '  %s  Install uv:  curl -LsSf https://astral.sh/uv/install.sh | sh%s\n' "$D" "$R"
fi

# ---------- resolve source ----------
CLEANUP=""
if [ -n "$SOURCE_DIR" ]; then
  SRC="$(cd "$SOURCE_DIR" && pwd -P)" || fail "--source path not found: $SOURCE_DIR"
  info "Source: local checkout ${B}$SRC${R}"
else
  TMP="$(mktemp -d)"; CLEANUP="$TMP"
  trap '[ -n "$CLEANUP" ] && rm -rf "$CLEANUP"' EXIT
  info "Cloning ${B}$REPO_URL${R} ${D}($BRANCH)${R}…"
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP/src" >/dev/null 2>&1 \
    || fail "Clone failed. Check the repo URL / branch, or use --source <local checkout>."
  SRC="$TMP/src"
fi
[ -d "$SRC/skills" ] || fail "Source does not look like claude-skills (no skills/ dir): $SRC"
[ -f "$SRC/scripts/deploy-harness.sh" ] || fail "Source is missing scripts/deploy-harness.sh: $SRC"
ok "Source ready"

# ---------- existing-harness check ----------
if [ -e "$TARGET_DIR/.claude/settings.json" ] && [ "$DRY_RUN" -eq 0 ]; then
  warn "Existing harness found in target (.claude/) — it will be re-synced (merge; non-harness entries kept)."
  info "Protected files (e.g. rules/architecture.md) keep your local copy by default; incoming saved as <file>.harness-incoming. Pass --overwrite-conflicts to replace them instead."
  # --overwrite-conflicts is itself a non-interactive consent to re-sync: it names the
  # destructive outcome explicitly, so re-asking "Re-sync it? [y/N]" adds nothing.
  if [ "$FORCE" -eq 0 ] && [ "$ASSUME_YES" -eq 0 ] && [ "$OVERWRITE_CONFLICTS" -eq 0 ]; then
    if have_tty; then
      printf '  Re-sync it? [y/N] ' > /dev/tty
      IFS= read -r reply < /dev/tty
      case "$reply" in y|Y|yes|YES) ;; *) fail "Aborted (no changes made)." ;; esac
    else
      fail "Existing .claude/ present. Re-run with --yes to re-sync it."
    fi
  fi
fi

# Root-level harness sources are a leftover of the old installer layout (it staged the
# payload at the target root). They are left untouched — but only flag them in a consuming
# project: in the harness-skills repo itself they ARE the source of truth.
if [ ! -f "$TARGET_DIR/scripts/install-harness.sh" ]; then
  LEGACY=()
  for item in "${PAYLOAD[@]}"; do
    [ -e "$TARGET_DIR/$item" ] && LEGACY+=("$item")
  done
  if [ "${#LEGACY[@]}" -gt 0 ]; then
    warn "Found root-level harness files from an older install layout: ${LEGACY[*]}"
    info "They are no longer used (the harness lives in .claude/) and were left untouched — remove them manually if they are not your project's own files."
  fi
fi

# ---------- wire MCP config (.mcp.json at target root; merge, never overwrite) ----------
# Runs BEFORE the deploy step so its .mcp.json canary passes. Claude Code reads .mcp.json at
# the project ROOT (not inside .claude/). An existing file may carry the project's own
# servers — the code-review-graph entry is merged in, never replacing the file wholesale.
MCP_SRV='{"command":"uvx","args":["code-review-graph","serve"]}'
if [ -f "$SRC/.mcp.json" ]; then
  s="$(jq -c '.mcpServers["code-review-graph"] // empty' "$SRC/.mcp.json" 2>/dev/null || true)"
  [ -n "$s" ] && MCP_SRV="$s"
fi
MCP_DST="$TARGET_DIR/.mcp.json"
BACKUP_DIR="$TARGET_DIR/.harness-backup-$(date +%Y%m%d-%H%M%S)"
if [ "$DRY_RUN" -eq 1 ]; then
  if [ ! -f "$MCP_DST" ]; then
    log "would create  .mcp.json (code-review-graph via uvx)"
  elif ! jq -e . "$MCP_DST" >/dev/null 2>&1; then
    log "would skip  .mcp.json (existing file is not valid JSON)"
  elif jq -e '.mcpServers["code-review-graph"]' "$MCP_DST" >/dev/null 2>&1; then
    log "would leave  .mcp.json unchanged (code-review-graph already wired)"
  else
    log "would merge  code-review-graph into existing .mcp.json"
  fi
elif [ ! -f "$MCP_DST" ]; then
  printf '{"mcpServers":{"code-review-graph":%s}}' "$MCP_SRV" | jq . > "$MCP_DST"
  ok "Wired ${B}.mcp.json${R} (code-review-graph via uvx)"
elif ! jq -e . "$MCP_DST" >/dev/null 2>&1; then
  warn "Existing .mcp.json is not valid JSON — left untouched."
  info "Add manually: ${D}\"code-review-graph\": $MCP_SRV  under  mcpServers${R}"
elif jq -e '.mcpServers["code-review-graph"]' "$MCP_DST" >/dev/null 2>&1; then
  ok ".mcp.json already wires code-review-graph — left unchanged"
else
  mkdir -p "$BACKUP_DIR"
  cp "$MCP_DST" "$BACKUP_DIR/.mcp.json"
  TMP_MCP="$(mktemp)"
  jq --argjson srv "$MCP_SRV" '.mcpServers["code-review-graph"] = $srv' "$MCP_DST" > "$TMP_MCP"
  mv "$TMP_MCP" "$MCP_DST"
  ok "Merged code-review-graph into existing ${B}.mcp.json${R} ${D}(backup: ${BACKUP_DIR#$TARGET_DIR/}/.mcp.json)${R}"
fi

# ---------- build .claude/ via deploy-harness (straight from the fetched source) ----------
# --yes/--overwrite-conflicts are forwarded so a non-interactive re-sync resolves protected-file
# conflicts (keep-mine or overwrite) instead of hanging on deploy's own prompt; --dry-run is
# forwarded so the dry-run path actually reaches deploy's conflict report (see deploy-harness.sh
# preflight_protected, which exits 0 before any write).
DEPLOY_ARGS=(--target "$TARGET_DIR")
[ "$ASSUME_YES" -eq 1 ] && DEPLOY_ARGS+=(--yes)
[ "$OVERWRITE_CONFLICTS" -eq 1 ] && DEPLOY_ARGS+=(--overwrite-conflicts)
if [ "$DRY_RUN" -eq 1 ]; then
  DEPLOY_ARGS+=(--dry-run)
else
  printf '\n'
fi
bash "$SRC/scripts/deploy-harness.sh" "${DEPLOY_ARGS[@]}"

# ---------- scaffold structural dirs (create-if-missing; never deletes/overwrites) ----------
# Folds the standalone scripts/init-structure.sh into install so users run one command.
# Safe by construction: it only writes a structural file when its destination is absent.
if [ "$DRY_RUN" -eq 1 ]; then
  info "Would scaffold specs/, docs/solutions/ (create-if-missing)"
  info "Would ensure .gitignore lists .claude/"
else
  printf '\n'
  bash "$SRC/scripts/init-structure.sh" --root "$TARGET_DIR"
fi

# ---------- ensure .claude/ is gitignored (append-only; never rewrites the file) ----------
# .claude/ is a derived artifact — it is rebuilt from source on every deploy, so committing it
# is wrong. It also carries .py files (visual-planner), and an untracked .py denies every commit
# via hooks/check-untracked-py.sh. Without this line a fresh consumer installs the harness and
# then cannot commit at all. Append only when the pattern is absent; never touch existing lines.
#
# Three things this must NOT do, each found by review:
#   1. Ignore a .claude/ the consumer already TRACKS. Some projects deliberately commit
#      .claude/ to share settings with their team. Appending the pattern there would hide the
#      ~90 files the deploy just wrote — git keeps showing only the already-tracked ones, and
#      the developer pushes a half-updated harness with no warning. Detect and skip.
#   2. Override a deliberate .claude-scoped rule. `.claude/*` + `!.claude/settings.json` is a
#      common shape; neither line matches an anchored `.claude/?` pattern, so a naive guard
#      appends `.claude/` — which excludes the DIRECTORY, making the negation unreachable
#      (git cannot re-include a file whose parent dir is excluded). Any line mentioning
#      .claude means the consumer already decided. Skip.
#   3. Abort the install. This is a convenience step running after the deploy already
#      succeeded; a read-only or directory .gitignore must not kill the script under
#      `set -euo pipefail` and swallow the success banner. Bound the whole block.
if [ "$DRY_RUN" -eq 0 ]; then
  GI="$TARGET_DIR/.gitignore"
  gi_skip=""
  if git -C "$TARGET_DIR" ls-files --error-unmatch -- .claude >/dev/null 2>&1; then
    gi_skip="tracked"
  elif [ -f "$GI" ] && grep -qE '(^|[^[:alnum:]_.-])!?/?\.claude(/|$|/\*)' "$GI" 2>/dev/null; then
    gi_skip="declared"
  fi
  if [ -n "$gi_skip" ]; then
    if [ "$gi_skip" = "tracked" ]; then
      warn ".claude/ is tracked in this repo — leaving .gitignore alone."
      warn "  The deploy wrote files into a tracked tree; review 'git status' before committing."
    fi
  elif ! {
        { [ ! -s "$GI" ] || [ -z "$(tail -c 1 "$GI" 2>/dev/null)" ] || printf '\n' >> "$GI"; } &&
        printf '# Harness: .claude/ is derived — rebuilt by deploy-harness.sh on every sync\n.claude/\n' >> "$GI"
      } 2>/dev/null; then
    warn "could not update .gitignore — add '.claude/' to it manually."
  elif [ -z "$gi_skip" ]; then
    ok ".gitignore now lists .claude/"
  fi
fi

# ---------- optional: keep a copy of the sources in the target ----------
STAGE_DIR="$TARGET_DIR/$STAGE_NAME"
if [ "$KEEP_SOURCES" -eq 1 ]; then
  if [ "$DRY_RUN" -eq 1 ]; then
    info "Would copy harness sources to $STAGE_NAME/"
  else
    rm -rf "$STAGE_DIR"
    mkdir -p "$STAGE_DIR"
    for item in "${PAYLOAD[@]}"; do
      [ -e "$SRC/$item" ] || continue
      mkdir -p "$(dirname "$STAGE_DIR/$item")"
      cp -R "$SRC/$item" "$STAGE_DIR/$item"
    done
    ok "Sources copied to ${B}$STAGE_NAME/${R} ${D}(re-sync: bash $STAGE_NAME/scripts/deploy-harness.sh --target .)${R}"
  fi
fi

HARNESS_VERSION=$( [ -f "$SRC/VERSION" ] && tr -d '[:space:]' < "$SRC/VERSION" || echo "unknown" )
if [ "$DRY_RUN" -eq 1 ]; then
  # Deploy already reported what it would do and wrote nothing. Claiming "installed"
  # here would contradict it on the very next line.
  printf '\n  %s%s✓ Dry run complete%s %s(v%s)%s  %s→ nothing was written to %s%s\n' "$G" "$B" "$R" "$D" "$HARNESS_VERSION" "$R" "$D" "$TARGET_DIR" "$R"
  printf '\n'
  exit 0
fi
printf '\n  %s%s✓ Harness installed%s %s(v%s)%s  %s→ %s%s\n' "$G" "$B" "$R" "$D" "$HARNESS_VERSION" "$R" "$D" "$TARGET_DIR" "$R"
printf '  %s↻ Restart Claude Code in that project so it loads the harness.%s\n' "$Y" "$R"
if [ "$UVX_MISSING" -eq 1 ]; then
  warn "Install uv before that restart, or the code-review-graph MCP server cannot launch."
fi
printf '\n'
