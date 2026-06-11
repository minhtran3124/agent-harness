#!/usr/bin/env bash
# Install the claude-skills harness into a target project.
#
# Fetches the harness source (git clone into a temp dir, or a local checkout via --source),
# then builds the loadable .claude/ in the target via deploy-harness.sh --target. The target
# root is NEVER used as a staging area, so the installer never deletes target files — at most
# it merge-syncs .claude/ and merges one server entry into .mcp.json.
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
DRY_RUN=0
KEEP_SOURCES=0

# Harness source-of-truth items. Deployed into .claude/ straight from the fetched source;
# copied into the target only with --keep-sources (under .harness-source/), never to the
# target root — a previous installer staged these at the root and pruned them afterward,
# which destroyed real project files when those names already existed (or when run inside
# the harness-skills repo itself).
PAYLOAD=(skills agents hooks rules templates settings.json scripts/deploy-harness.sh)
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

usage() {
  cat <<EOF
Install the claude-skills harness into a target project.

Usage: install-harness.sh [options]

Options:
  -d, --directory <path>  Target project dir (default: current dir)
  -b, --branch <name>     Branch to install from (default: ${BRANCH})
      --source <path>     Use a local claude-skills checkout instead of cloning
  -y, --yes               Non-interactive: re-sync an existing .claude/ without asking
      --force             Same as --yes (kept for compatibility)
      --keep-sources      Also copy the harness sources into <target>/${STAGE_NAME}/
                          for inspection or offline re-sync (default: no copy)
      --dry-run           Show what would happen; write nothing
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
  if [ "$FORCE" -eq 0 ] && [ "$ASSUME_YES" -eq 0 ]; then
    if [ -r /dev/tty ]; then
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
if [ "$DRY_RUN" -eq 1 ]; then
  info "Would run: bash deploy-harness.sh --target $TARGET_DIR (builds .claude/)"
else
  printf '\n'
  bash "$SRC/scripts/deploy-harness.sh" --target "$TARGET_DIR"
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

printf '\n  %s%s✓ Harness installed%s  %s→ %s%s\n' "$G" "$B" "$R" "$D" "$TARGET_DIR" "$R"
printf '  %s↻ Restart Claude Code in that project so it loads the harness.%s\n' "$Y" "$R"
if [ "$UVX_MISSING" -eq 1 ]; then
  warn "Install uv before that restart, or the code-review-graph MCP server cannot launch."
fi
printf '\n'
