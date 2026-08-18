#!/usr/bin/env bash
# Render and deploy the Codex hybrid adapter without replacing user-owned state.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
TARGET_DIR="$PWD"
CODEX_BIN="${CODEX_BIN:-codex}"
CODEX_HOME_ARG="${CODEX_HOME:-}"
DRY_RUN=0
OVERWRITE=0
REMOVE=0

usage() {
  cat <<'EOF'
Usage: deploy-codex-adapter.sh [options]

Options:
  --source <path>          Harness source checkout (default: script parent)
  --target <path>          Target project (default: current directory)
  --codex-bin <path>       Codex executable (default: codex)
  --codex-home <path>      Explicit Codex state root (useful for isolated installs/tests)
  --yes                    Non-interactive; conflicts still keep the local copy
  --overwrite-conflicts    Replace edited harness-owned files/managed AGENTS.md block
  --dry-run                Validate and report without writing or invoking Codex
  --remove                 Remove this deployment; preserve edited/user-owned files
  -h, --help               Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --source) ROOT="${2:?--source needs a path}"; shift 2 ;;
    --target) TARGET_DIR="${2:?--target needs a path}"; shift 2 ;;
    --codex-bin) CODEX_BIN="${2:?--codex-bin needs a path}"; shift 2 ;;
    --codex-home) CODEX_HOME_ARG="${2:?--codex-home needs a path}"; shift 2 ;;
    --yes) shift ;;
    --overwrite-conflicts) OVERWRITE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --remove) REMOVE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'codex-deploy: unknown option: %s\n' "$1" >&2; exit 2 ;;
  esac
done

ROOT="$(cd "$ROOT" && pwd -P)"
mkdir -p "$TARGET_DIR"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd -P)"
[ "$TARGET_DIR" != "/" ] || {
  printf 'codex-deploy: refusing to use the filesystem root as a target\n' >&2
  exit 1
}
STATE_DIR="$TARGET_DIR/.codex/.agent-harness"
MARKET_DIR="$STATE_DIR/marketplace"
STATE_FILE="$STATE_DIR/deployment-manifest.json"
MARKET_NAME="agent-harness-local"
PLUGIN_REF="agent-harness@$MARKET_NAME"

for _managed_parent in "$TARGET_DIR/.codex" "$STATE_DIR" "$MARKET_DIR"; do
  if [ -L "$_managed_parent" ]; then
    printf 'codex-deploy: managed path cannot be a symlink: %s\n' "$_managed_parent" >&2
    exit 1
  fi
done

command -v python3 >/dev/null 2>&1 || {
  printf 'codex-deploy: python3 is required\n' >&2
  exit 1
}
if [ "$DRY_RUN" -eq 0 ]; then
  command -v "$CODEX_BIN" >/dev/null 2>&1 || [ -x "$CODEX_BIN" ] || {
    printf 'codex-deploy: Codex executable not found: %s\n' "$CODEX_BIN" >&2
    exit 1
  }
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/codex-harness-deploy.XXXXXX")"
MARKET_SWAPPED=0
HAD_PREVIOUS_MARKET=0
cleanup() {
  _cleanup_rc=$?
  trap - EXIT HUP INT TERM
  if [ "$MARKET_SWAPPED" -eq 1 ]; then
    restore_previous_market
  fi
  rm -rf "$WORK"
  exit "$_cleanup_rc"
}
trap cleanup EXIT HUP INT TERM

run_codex() {
  if [ -n "$CODEX_HOME_ARG" ]; then
    CODEX_HOME="$CODEX_HOME_ARG" "$CODEX_BIN" plugin "$@"
  else
    "$CODEX_BIN" plugin "$@"
  fi
}

remove_plugin_state() {
  run_codex remove "$PLUGIN_REF" --json >/dev/null 2>&1 || true
  run_codex marketplace remove "$MARKET_NAME" --json >/dev/null 2>&1 || true
}

restore_previous_market() {
  MARKET_SWAPPED=0
  if [ -f "$STATE_FILE" ] || [ -d "$MARKET_DIR" ]; then
    remove_plugin_state
  fi
  if [ -d "$WORK/previous-marketplace" ]; then
    rm -rf "$MARKET_DIR"
    mkdir -p "$STATE_DIR"
    mv "$WORK/previous-marketplace" "$MARKET_DIR"
    run_codex marketplace add "$MARKET_DIR" --json >/dev/null 2>&1 || true
    run_codex add "$PLUGIN_REF" --json >/dev/null 2>&1 || true
  elif [ "$HAD_PREVIOUS_MARKET" -eq 1 ] && [ -d "$MARKET_DIR" ]; then
    # A signal may arrive after the rollback guard is armed but before the first
    # rename. In that narrow window MARKET_DIR is still the previous source.
    run_codex marketplace add "$MARKET_DIR" --json >/dev/null 2>&1 || true
    run_codex add "$PLUGIN_REF" --json >/dev/null 2>&1 || true
  else
    rm -rf "$MARKET_DIR"
    rmdir "$STATE_DIR" "$TARGET_DIR/.codex" 2>/dev/null || true
  fi
}

sync_project() {
  _mode=$1
  _project=${2:-}
  python3 - "$TARGET_DIR" "$STATE_FILE" "$_project" "$OVERWRITE" "$_mode" <<'PY'
import hashlib
import json
import os
import pathlib
import shutil
import sys
import tempfile

target, state_path, project_arg = map(pathlib.Path, sys.argv[1:4])
overwrite = sys.argv[4] == "1"
mode = sys.argv[5]
begin = "<!-- agent-harness:begin -->"
end = "<!-- agent-harness:end -->"
block = (
    begin
    + "\nRead `.codex/harness-instructions.md` before using the Agent Harness.\n"
    + end
)


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def digest_file(path):
    return digest_bytes(path.read_bytes())


def atomic_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(value)
        temporary = pathlib.Path(handle.name)
    os.replace(temporary, path)


def safe_relative(value):
    path = pathlib.PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise SystemExit(f"codex-deploy: unsafe managed path: {value}")
    return path


def target_path(value):
    relative = safe_relative(value)
    candidate = target / relative
    resolved_parent = candidate.parent.resolve()
    try:
        resolved_parent.relative_to(target.resolve())
    except ValueError as exc:
        raise SystemExit(f"codex-deploy: managed path escapes through a symlink: {value}") from exc
    return candidate


if state_path.exists():
    try:
        old = json.loads(state_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"codex-deploy: invalid deployment manifest: {exc}")
    if old.get("schema_version") != 1:
        raise SystemExit("codex-deploy: unsupported deployment manifest")
else:
    old = {"schema_version": 1, "project_files": {}, "sidecars": {}}

old_files = old.get("project_files", {})
old_sidecars = old.get("sidecars", {})
if not isinstance(old_files, dict) or not isinstance(old_sidecars, dict):
    raise SystemExit("codex-deploy: malformed managed-path inventory")
for value in (*old_files, *old_sidecars):
    safe_relative(value)

new_files = {}
new_sidecars = {}
desired = {}
if mode == "install":
    project = project_arg
    if not project.is_dir():
        raise SystemExit("codex-deploy: rendered project overlay is missing")
    for source in sorted(path for path in project.rglob("*") if path.is_file()):
        relative = source.relative_to(project).as_posix()
        safe_relative(relative)
        desired[relative] = source.read_bytes()


def remove_if_unchanged(relative, expected):
    path = target_path(relative)
    if path.is_file() and digest_file(path) == expected:
        path.unlink()
        return True
    return not path.exists()


if mode == "remove":
    for relative, expected in old_sidecars.items():
        remove_if_unchanged(relative, expected)
    for relative, expected in old_files.items():
        if not remove_if_unchanged(relative, expected):
            print(f"codex-deploy: preserved edited managed file {relative}")
            new_files[relative] = expected
else:
    for relative, incoming in desired.items():
        destination = target_path(relative)
        incoming_hash = digest_bytes(incoming)
        previous_hash = old_files.get(relative)
        if not destination.exists() or (
            destination.is_file() and digest_file(destination) == incoming_hash
        ):
            atomic_write(destination, incoming)
            new_files[relative] = incoming_hash
        elif destination.is_file() and previous_hash == digest_file(destination):
            atomic_write(destination, incoming)
            new_files[relative] = incoming_hash
        elif overwrite:
            atomic_write(destination, incoming)
            new_files[relative] = incoming_hash
        else:
            sidecar_relative = relative + ".harness-incoming"
            sidecar = target_path(sidecar_relative)
            atomic_write(sidecar, incoming)
            new_sidecars[sidecar_relative] = incoming_hash
            if previous_hash:
                new_files[relative] = previous_hash
            print(f"codex-deploy: kept local {relative}; wrote {sidecar_relative}")

    for relative, expected in old_files.items():
        if relative in desired:
            continue
        if not remove_if_unchanged(relative, expected):
            new_files[relative] = expected
            print(f"codex-deploy: preserved edited retired file {relative}")

agents = target / "AGENTS.md"
agents_sidecar_relative = "AGENTS.md.harness-incoming"
agents_sidecar = target / agents_sidecar_relative
old_block_hash = old.get("agents_block_hash")
new_block_hash = None
if agents.exists():
    original = agents.read_text()
else:
    original = ""
begin_count = original.count(begin)
end_count = original.count(end)

if mode == "remove":
    if begin_count == end_count == 1:
        start = original.index(begin)
        finish = original.index(end, start) + len(end)
        current = original[start:finish]
        if old_block_hash and digest_bytes(current.encode()) == old_block_hash:
            remaining = (original[:start] + original[finish:]).strip()
            if remaining:
                atomic_write(agents, (remaining + "\n").encode())
            else:
                agents.unlink()
        else:
            print("codex-deploy: preserved edited AGENTS.md managed block")
    if agents_sidecar.exists() and old_sidecars.get(agents_sidecar_relative) == digest_file(agents_sidecar):
        agents_sidecar.unlink()
elif begin_count == end_count == 0:
    candidate = original.rstrip()
    if candidate:
        candidate += "\n\n"
    candidate += block + "\n"
    atomic_write(agents, candidate.encode())
    new_block_hash = digest_bytes(block.encode())
elif begin_count == end_count == 1 and original.index(begin) < original.index(end):
    start = original.index(begin)
    finish = original.index(end, start) + len(end)
    current = original[start:finish]
    current_hash = digest_bytes(current.encode())
    if current == block or current_hash == old_block_hash or overwrite:
        candidate = original[:start] + block + original[finish:]
        atomic_write(agents, candidate.encode())
        new_block_hash = digest_bytes(block.encode())
    else:
        candidate = original[:start] + block + original[finish:]
        atomic_write(agents_sidecar, candidate.encode())
        new_sidecars[agents_sidecar_relative] = digest_bytes(candidate.encode())
        new_block_hash = old_block_hash
        print("codex-deploy: kept edited AGENTS.md block; wrote AGENTS.md.harness-incoming")
else:
    candidate = original.rstrip() + "\n\n" + block + "\n"
    atomic_write(agents_sidecar, candidate.encode())
    new_sidecars[agents_sidecar_relative] = digest_bytes(candidate.encode())
    print("codex-deploy: malformed AGENTS.md markers; wrote AGENTS.md.harness-incoming")

for relative, expected in old_sidecars.items():
    if relative in new_sidecars:
        continue
    sidecar = target_path(relative)
    if sidecar.is_file() and digest_file(sidecar) == expected:
        sidecar.unlink()

if mode == "remove":
    if new_files:
        updated = {
            "schema_version": 1,
            "project_files": dict(sorted(new_files.items())),
            "sidecars": {},
            "agents_block_hash": old_block_hash,
            "plugin": old.get("plugin", {}),
        }
        atomic_write(state_path, (json.dumps(updated, indent=2, sort_keys=True) + "\n").encode())
    elif state_path.exists():
        state_path.unlink()
else:
    updated = {
        "schema_version": 1,
        "project_files": dict(sorted(new_files.items())),
        "sidecars": dict(sorted(new_sidecars.items())),
        "agents_block_hash": new_block_hash,
        "plugin": {
            "marketplace": "agent-harness-local",
            "reference": "agent-harness@agent-harness-local",
        },
    }
    atomic_write(state_path, (json.dumps(updated, indent=2, sort_keys=True) + "\n").encode())

for directory in (target / ".codex/agents", target / ".codex", state_path.parent):
    try:
        directory.rmdir()
    except OSError:
        pass
PY
}

if [ "$REMOVE" -eq 1 ]; then
  if [ "$DRY_RUN" -eq 1 ]; then
    printf 'codex-deploy: would remove plugin, marketplace, and unchanged manifest-owned paths\n'
    exit 0
  fi
  if [ -f "$STATE_FILE" ] || [ -d "$MARKET_DIR" ]; then
    remove_plugin_state
  fi
  sync_project remove
  rm -rf "$MARKET_DIR"
  rmdir "$STATE_DIR" "$TARGET_DIR/.codex" 2>/dev/null || true
  printf 'codex-deploy: removal complete\n'
  exit 0
fi

[ -f "$ROOT/scripts/render_codex_adapter.py" ] || {
  printf 'codex-deploy: source is missing scripts/render_codex_adapter.py\n' >&2
  exit 1
}
if [ -f "$STATE_FILE" ] && [ ! -d "$MARKET_DIR" ]; then
  printf 'codex-deploy: deployment manifest exists but its marketplace source is missing\n' >&2
  exit 1
fi
python3 "$ROOT/scripts/render_codex_adapter.py" --root "$ROOT" --output "$WORK/rendered"

STAGED_MARKET="$WORK/marketplace"
mkdir -p "$STAGED_MARKET/.agents/plugins" "$STAGED_MARKET/plugins"
cp -R "$WORK/rendered/plugin" "$STAGED_MARKET/plugins/agent-harness"
python3 - "$STAGED_MARKET/.agents/plugins/marketplace.json" <<'PY'
import json
import pathlib
import sys

payload = {
    "interface": {"displayName": "Agent Harness Local"},
    "name": "agent-harness-local",
    "plugins": [
        {
            "category": "Developer Tools",
            "name": "agent-harness",
            "policy": {"authentication": "ON_INSTALL", "installation": "AVAILABLE"},
            "source": {"path": "./plugins/agent-harness", "source": "local"},
        }
    ],
}
pathlib.Path(sys.argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY

if [ "$DRY_RUN" -eq 1 ]; then
  printf 'codex-deploy: would install %s and sync manifest-owned project files\n' "$PLUGIN_REF"
  exit 0
fi

mkdir -p "$STATE_DIR"
if [ -d "$MARKET_DIR" ]; then
  HAD_PREVIOUS_MARKET=1
  MARKET_SWAPPED=1
  mv "$MARKET_DIR" "$WORK/previous-marketplace"
else
  MARKET_SWAPPED=1
fi
mv "$STAGED_MARKET" "$MARKET_DIR"
if [ "$HAD_PREVIOUS_MARKET" -eq 1 ]; then
  remove_plugin_state
fi
if ! run_codex marketplace add "$MARKET_DIR" --json >/dev/null; then
  restore_previous_market
  printf 'codex-deploy: marketplace install failed; previous state restored\n' >&2
  exit 1
fi
if ! run_codex add "$PLUGIN_REF" --json >/dev/null; then
  restore_previous_market
  printf 'codex-deploy: plugin install failed; previous state restored\n' >&2
  exit 1
fi

if ! sync_project install "$WORK/rendered/project"; then
  restore_previous_market
  printf 'codex-deploy: project sync failed; plugin state restored\n' >&2
  exit 1
fi
rm -rf "$WORK/previous-marketplace"
MARKET_SWAPPED=0
printf 'codex-deploy: installed %s without replacing unrelated Codex state\n' "$PLUGIN_REF"
