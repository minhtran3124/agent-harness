#!/usr/bin/env bash
# Fetch or use a local harness checkout, then deploy its Codex adapter.
set -euo pipefail

REPO_URL="${CS_REPO_URL:-https://github.com/minhtran3124/agent-harness}"
BRANCH="${CS_BRANCH:-simplify}"
TARGET_DIR="$PWD"
SOURCE_DIR=""
FORWARD_ARGS=()

usage() {
  cat <<EOF
Usage: install-codex-harness.sh [options]

Options:
  -d, --directory <path>   Target project (default: current directory)
  -b, --branch <name>      Git branch when fetching (default: $BRANCH)
  --source <path>          Use a local harness checkout instead of cloning
  --codex-bin <path>       Codex executable
  --codex-home <path>      Explicit Codex state root
  --yes                    Non-interactive; keep local files on conflict
  --overwrite-conflicts    Replace edited harness-managed files/AGENTS.md block
  --dry-run                Validate and report without writing
  --remove                 Remove this Codex harness deployment
  -h, --help               Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    -d|--directory) TARGET_DIR="${2:?--directory needs a path}"; shift 2 ;;
    -b|--branch) BRANCH="${2:?--branch needs a name}"; shift 2 ;;
    --source) SOURCE_DIR="${2:?--source needs a path}"; shift 2 ;;
    --codex-bin|--codex-home) FORWARD_ARGS+=("$1" "${2:?$1 needs a path}"); shift 2 ;;
    --yes|--overwrite-conflicts|--dry-run|--remove) FORWARD_ARGS+=("$1"); shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'codex-install: unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done

mkdir -p "$TARGET_DIR"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd -P)"
WORK=""
cleanup() { [ -z "$WORK" ] || rm -rf "$WORK"; }
trap cleanup EXIT HUP INT TERM

if [ -n "$SOURCE_DIR" ]; then
  SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd -P)"
else
  command -v git >/dev/null 2>&1 || {
    printf 'codex-install: git is required unless --source is provided\n' >&2
    exit 1
  }
  WORK="$(mktemp -d "${TMPDIR:-/tmp}/codex-harness-install.XXXXXX")"
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$WORK/source" >/dev/null 2>&1 || {
    printf 'codex-install: clone failed; use --source for an offline install\n' >&2
    exit 1
  }
  SOURCE_DIR="$WORK/source"
fi

[ -f "$SOURCE_DIR/scripts/deploy-codex-adapter.sh" ] || {
  printf 'codex-install: invalid source checkout\n' >&2
  exit 1
}
bash "$SOURCE_DIR/scripts/deploy-codex-adapter.sh" \
  --source "$SOURCE_DIR" --target "$TARGET_DIR" ${FORWARD_ARGS[@]+"${FORWARD_ARGS[@]}"}
