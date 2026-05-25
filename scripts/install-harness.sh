#!/usr/bin/env bash
# Install the claude-skills harness into a target project.
#
# Fetches the harness source (git clone, or a local checkout via --source), copies the
# source-of-truth layout into the target, then builds the loadable .claude/ via deploy-harness.sh.
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

# What gets installed into the target (source-of-truth layout; deploy-harness.sh derives .claude/).
PAYLOAD=(skills agents hooks rules templates settings.json scripts/deploy-harness.sh)

# ---------- styling ----------
if [ -t 1 ]; then
  B=$'\033[1m'; D=$'\033[2m'; R=$'\033[0m'; G=$'\033[32m'; C=$'\033[36m'; Y=$'\033[33m'; M=$'\033[35m'; RED=$'\033[31m'
else
  B=; D=; R=; G=; C=; Y=; M=; RED=
fi
log()  { printf '  %s\n' "$*"; }
ok()   { printf '  %s✓%s %s\n' "$G" "$R" "$*"; }
info() { printf '  %s•%s %s\n' "$C" "$R" "$*"; }
fail() { printf '\n  %s✗ %s%s\n\n' "$RED" "$*" "$R" >&2; exit 1; }

usage() {
  cat <<EOF
Install the claude-skills harness into a target project.

Usage: install-harness.sh [options]

Options:
  -d, --directory <path>  Target project dir (default: current dir)
  -b, --branch <name>     Branch to install from (default: ${BRANCH})
      --source <path>     Use a local claude-skills checkout instead of cloning
  -y, --yes               Non-interactive: back up + overwrite existing harness files
      --force             Overwrite without prompting (after backup)
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
ok "Source ready"

# ---------- conflict check ----------
EXISTING=()
for item in "${PAYLOAD[@]}"; do
  [ -e "$TARGET_DIR/$item" ] && EXISTING+=("$item")
done
if [ "${#EXISTING[@]}" -gt 0 ] && [ "$DRY_RUN" -eq 0 ]; then
  printf '  %s⚠ Existing harness files in target:%s %s\n' "$Y" "$R" "${EXISTING[*]}"
  if [ "$FORCE" -eq 0 ] && [ "$ASSUME_YES" -eq 0 ]; then
    if [ -r /dev/tty ]; then
      printf '  Back up and overwrite them? [y/N] ' > /dev/tty
      IFS= read -r reply < /dev/tty
      case "$reply" in y|Y|yes|YES) ;; *) fail "Aborted (no changes made)." ;; esac
    else
      fail "Existing files present. Re-run with --yes (back up + overwrite) or --force."
    fi
  fi
fi

# ---------- copy payload (with backup) ----------
BACKUP_DIR="$TARGET_DIR/.harness-backup-$(date +%Y%m%d-%H%M%S)"
copied=0 backed=0
for item in "${PAYLOAD[@]}"; do
  src="$SRC/$item"; dst="$TARGET_DIR/$item"
  [ -e "$src" ] || { info "skip (not in source): $item"; continue; }
  if [ "$DRY_RUN" -eq 1 ]; then
    [ -e "$dst" ] && log "would back up + replace  $item" || log "would create  $item"
    copied=$((copied+1)); continue
  fi
  if [ -e "$dst" ]; then
    mkdir -p "$(dirname "$BACKUP_DIR/$item")"
    cp -R "$dst" "$BACKUP_DIR/$item"
    rm -rf "$dst"
    backed=$((backed+1))
  fi
  mkdir -p "$(dirname "$dst")"
  cp -R "$src" "$dst"
  copied=$((copied+1))
done
if [ "$DRY_RUN" -eq 1 ]; then
  ok "Dry run — $copied item(s) would be installed; nothing written."
else
  ok "Installed $copied item(s)${backed:+, backed up $backed existing}"
  [ "$backed" -gt 0 ] && info "Backup: ${D}${BACKUP_DIR#$TARGET_DIR/}${R} ${Y}(merge any custom settings.json yourself)${R}"
fi

# ---------- build .claude/ via deploy-harness ----------
if [ "$DRY_RUN" -eq 1 ]; then
  info "Would run: bash scripts/deploy-harness.sh (builds .claude/)"
else
  printf '\n'
  ( cd "$TARGET_DIR" && bash scripts/deploy-harness.sh )
fi

printf '\n  %s%s✓ Harness installed%s  %s→ %s%s\n' "$G" "$B" "$R" "$D" "$TARGET_DIR" "$R"
printf '  %s↻ Restart Claude Code in that project so it loads the harness.%s\n\n' "$Y" "$R"
