#!/usr/bin/env bash
# Measure Codex hybrid packaging and record the direct-project evidence boundary safely.

set -u

usage() {
  cat <<'EOF'
Usage: probe_codex_packaging.sh --output DIR --codex-bin PATH [options]

The probe uses local fixture sources only. It redirects both HOME and CODEX_HOME
to fresh temporary directories before invoking Codex. By default it makes no
model call. Pass --allow-live-model-probe to explicitly authorize one disposable
runtime execution probe. Use --auth-file PATH to seed only its disposable Codex state.
EOF
}

die() {
  printf 'codex-packaging-probe: %s\n' "$1" >&2
  exit 2
}

OUTPUT=""
CODEX_BIN=""
AUTH_FILE=""
ALLOW_LIVE=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --output)
      [ "$#" -ge 2 ] || die "--output requires a value"
      OUTPUT=$2
      shift 2
      ;;
    --codex-bin)
      [ "$#" -ge 2 ] || die "--codex-bin requires a value"
      CODEX_BIN=$2
      shift 2
      ;;
    --allow-live-model-probe)
      ALLOW_LIVE=1
      shift
      ;;
    --auth-file)
      [ "$#" -ge 2 ] || die "--auth-file requires a value"
      AUTH_FILE=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *) die "unknown argument: $1" ;;
  esac
done

[ -n "$OUTPUT" ] || die "--output is required"
[ -n "$CODEX_BIN" ] || die "--codex-bin is required"
command -v python3 >/dev/null 2>&1 || die "python3 is required"
case "$CODEX_BIN" in
  */*) [ -x "$CODEX_BIN" ] || die "Codex executable not found: $CODEX_BIN" ;;
  *)
    _resolved=$(command -v "$CODEX_BIN" 2>/dev/null) || die "Codex executable not found: $CODEX_BIN"
    CODEX_BIN=$_resolved
    ;;
esac

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd) || die "cannot resolve repository root"
FIXTURES="$REPO_ROOT/tests/fixtures/codex-packaging"
for _fixture in marketplace.json plugin.json agents.toml; do
  [ -f "$FIXTURES/$_fixture" ] || die "missing fixture: $_fixture"
done

WORK=$(mktemp -d "${TMPDIR:-/tmp}/codex-packaging.XXXXXX") || die "cannot create temporary directory"
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
ISOLATED_HOME="$WORK/home"
ISOLATED_CODEX_HOME="$WORK/codex-home"
MARKET_ROOT="$WORK/marketplace"
HYBRID_PROJECT="$WORK/hybrid-project"
DIRECT_PROJECT="$WORK/direct-project"
RAW="$WORK/raw"
STAGED="$WORK/staged"
mkdir -p "$ISOLATED_HOME" "$ISOLATED_CODEX_HOME" "$MARKET_ROOT" \
  "$HYBRID_PROJECT" "$DIRECT_PROJECT" "$RAW" "$STAGED" || die "cannot initialize probe"

python3 - "$WORK" "$ISOLATED_HOME" "$ISOLATED_CODEX_HOME" <<'PY' \
  || die "isolated state roots are not fresh and distinct"
import pathlib
import sys

work, home, codex_home = (pathlib.Path(value).resolve() for value in sys.argv[1:])
if home == codex_home or home.parent != work or codex_home.parent != work:
    raise SystemExit(1)
if any(home.iterdir()) or any(codex_home.iterdir()):
    raise SystemExit(1)
PY
: >"$RAW/isolated-state-roots.present"
if [ -n "$AUTH_FILE" ]; then
  [ -f "$AUTH_FILE" ] || die "auth file not found: $AUTH_FILE"
  cp "$AUTH_FILE" "$ISOLATED_CODEX_HOME/auth.json" || die "cannot seed disposable auth"
  chmod 600 "$ISOLATED_CODEX_HOME/auth.json" || die "cannot protect disposable auth"
fi

python3 - "$FIXTURES" "$MARKET_ROOT" "$HYBRID_PROJECT" "$DIRECT_PROJECT" <<'PY' \
  || die "cannot materialize packaging candidates"
import json
import pathlib
import shutil
import sys

fixtures, market, hybrid, direct = map(pathlib.Path, sys.argv[1:])
marketplace = json.loads((fixtures / "marketplace.json").read_text())
plugin = json.loads((fixtures / "plugin.json").read_text())
if marketplace.get("name") != "harness-probe":
    raise SystemExit("unexpected marketplace name")
entries = marketplace.get("plugins")
if not isinstance(entries, list) or len(entries) != 1:
    raise SystemExit("marketplace must contain exactly one probe plugin")
source_path = entries[0].get("source", {}).get("path")
if source_path != "./plugins/harness-hybrid":
    raise SystemExit("unsafe or unexpected local source path")
if plugin.get("name") != "harness-hybrid":
    raise SystemExit("plugin and marketplace names disagree")
for field in ("skills", "hooks"):
    value = plugin.get(field)
    if not isinstance(value, str) or not value.startswith("./") or ".." in pathlib.PurePosixPath(value).parts:
        raise SystemExit(f"unsafe plugin path: {field}")

(market / ".agents/plugins").mkdir(parents=True)
(market / ".agents/plugins/marketplace.json").write_text(
    json.dumps(marketplace, indent=2, sort_keys=True) + "\n"
)
plugin_root = market / "plugins/harness-hybrid"
(plugin_root / ".codex-plugin").mkdir(parents=True)
(plugin_root / ".codex-plugin/plugin.json").write_text(
    json.dumps(plugin, indent=2, sort_keys=True) + "\n"
)
skill_text = "---\nname: harness-packaging-probe\ndescription: Disposable packaging discovery marker.\n---\n\nReturn HARNESS_PACKAGING_SKILL_OK.\n"
(plugin_root / "skills/harness-packaging-probe").mkdir(parents=True)
(plugin_root / "skills/harness-packaging-probe/SKILL.md").write_text(skill_text)
(plugin_root / "hooks").mkdir()
(plugin_root / "hooks/hooks.json").write_text(
    json.dumps(
        {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "python3 -c \"import os,pathlib; pathlib.Path(os.environ['HARNESS_PACKAGING_HOOK_LOG']).write_text('HARNESS_PACKAGING_HOOK_OK')\"",
                            }
                        ]
                    }
                ]
            }
        },
        indent=2,
        sort_keys=True,
    )
    + "\n"
)
(hybrid / ".codex/agents").mkdir(parents=True)
shutil.copy2(fixtures / "agents.toml", hybrid / ".codex/agents/harness-probe.toml")
(hybrid / "AGENTS.md").write_text("# Disposable hybrid project\n")

(direct / ".agents/skills/harness-packaging-probe").mkdir(parents=True)
(direct / ".agents/skills/harness-packaging-probe/SKILL.md").write_text(skill_text)
(direct / ".codex/agents").mkdir(parents=True)
shutil.copy2(fixtures / "agents.toml", direct / ".codex/agents/harness-probe.toml")
(direct / ".codex").mkdir(exist_ok=True)
shutil.copy2(plugin_root / "hooks/hooks.json", direct / ".codex/hooks.json")
(direct / "AGENTS.md").write_text("# Disposable direct project\n")
PY

VERSION_TEXT=$(HOME="$ISOLATED_HOME" CODEX_HOME="$ISOLATED_CODEX_HOME" \
  "$CODEX_BIN" --version 2>/dev/null) || die "codex --version failed"
CLI_VERSION=$(python3 -c 'import re,sys; m=re.search(r"\b(\d+\.\d+\.\d+)\b",sys.argv[1]); print(m.group(1) if m else "")' "$VERSION_TEXT")
[ -n "$CLI_VERSION" ] || die "could not parse Codex CLI version"
_os=$(uname -s 2>/dev/null || printf unknown)
_arch=$(uname -m 2>/dev/null || printf unknown)
case "$_arch" in
  x86_64|amd64) _arch=x86_64 ;;
  arm64|aarch64) _arch=arm64 ;;
esac
case "$_os" in
  Darwin) PLATFORM_LABEL="macos-$_arch" ;;
  Linux)
    if grep -qi microsoft /proc/version 2>/dev/null; then
      PLATFORM_LABEL="wsl-$_arch"
    else
      PLATFORM_LABEL="linux-$_arch"
    fi
    ;;
  *) PLATFORM_LABEL="unknown-$_arch" ;;
esac
CAPTURE_DATE=${CODEX_CAPTURE_DATE:-$(date -u +%Y-%m-%d 2>/dev/null)}
python3 -c 'import datetime,sys; datetime.date.fromisoformat(sys.argv[1])' "$CAPTURE_DATE" \
  >/dev/null 2>&1 || die "capture date must be YYYY-MM-DD"
LIVE_RC=125
RUNTIME_STDOUT="$RAW/runtime.stdout"
RUNTIME_HOOK_LOG="$RAW/runtime-hook.log"
: >"$RUNTIME_STDOUT"
printf 'definitely_unknown_packaging_probe_key = true\n' >"$ISOLATED_CODEX_HOME/config.toml"
if HOME="$ISOLATED_HOME" CODEX_HOME="$ISOLATED_CODEX_HOME" \
  "$CODEX_BIN" --strict-config --no-alt-screen </dev/null \
  >"$RAW/strict-invalid.stdout" 2>"$RAW/strict-invalid.stderr"; then
  printf '%s\n' strict-invalid-accepted >"$RAW/failure-step.txt"
elif grep -q 'unknown configuration field' "$RAW/strict-invalid.stderr"; then
  : >"$RAW/strict-invalid-rejected.present"
else
  printf '%s\n' strict-invalid-diagnostic >"$RAW/failure-step.txt"
fi
: >"$ISOLATED_CODEX_HOME/config.toml"
if HOME="$ISOLATED_HOME" CODEX_HOME="$ISOLATED_CODEX_HOME" \
  "$CODEX_BIN" --strict-config --no-alt-screen </dev/null \
  >"$RAW/strict-valid.stdout" 2>"$RAW/strict-valid.stderr"; then
  printf '%s\n' strict-valid-launched >"$RAW/failure-step.txt"
elif grep -q 'stdin is not a terminal' "$RAW/strict-valid.stderr" \
  && ! grep -q 'Error loading config.toml' "$RAW/strict-valid.stderr"; then
  : >"$RAW/strict-valid-accepted.present"
else
  printf '%s\n' strict-valid-parse >"$RAW/failure-step.txt"
fi

run_cli() {
  _name=$1
  shift
  if ! HOME="$ISOLATED_HOME" CODEX_HOME="$ISOLATED_CODEX_HOME" \
    "$CODEX_BIN" plugin "$@" >"$RAW/$_name.stdout" 2>"$RAW/$_name.stderr"; then
    python3 - "$RAW/$_name.stderr" "$WORK" <<'PY' >&2
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(errors="replace").replace(sys.argv[2], "<probe-tmp>")
print(text[:2000].rstrip())
PY
    printf '%s\n' "$_name" >"$RAW/failure-step.txt"
    return 1
  fi
}

cache_fingerprint() {
  python3 - "$1" <<'PY'
import hashlib
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
versions = sorted(path for path in root.iterdir() if path.is_dir()) if root.is_dir() else []
if len(versions) != 1:
    raise SystemExit(1)
version = versions[0]
digest = hashlib.sha256()
for path in sorted(version.rglob("*")):
    relative = path.relative_to(version).as_posix()
    digest.update(relative.encode())
    digest.update(b"\0")
    if path.is_file():
        digest.update(path.read_bytes())
    digest.update(b"\0")
print(f"{version.name} {digest.hexdigest()}")
PY
}

run_hybrid_lifecycle() {
  run_cli marketplace-add marketplace add "$MARKET_ROOT" --json || return 1
  run_cli marketplace-list marketplace list --json || return 1
  run_cli plugin-available list --marketplace harness-probe --available --json || return 1
  run_cli plugin-add add harness-hybrid@harness-probe --json || return 1
  run_cli plugin-installed list --marketplace harness-probe --json || return 1

  CACHE_BASE="$ISOLATED_CODEX_HOME/plugins/cache/harness-probe/harness-hybrid"
  _fingerprint_before=$(cache_fingerprint "$CACHE_BASE") || {
    printf '%s\n' cache-first-install >"$RAW/failure-step.txt"
    return 1
  }
  _cache_version=${_fingerprint_before%% *}
  CACHE="$CACHE_BASE/$_cache_version"
  if [ ! -f "$CACHE/skills/harness-packaging-probe/SKILL.md" ]; then
    python3 - "$ISOLATED_CODEX_HOME" <<'PY' >&2
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
for path in sorted(root.rglob("*")):
    if path.is_file():
        print("<isolated-codex-home>/" + path.relative_to(root).as_posix())
PY
    printf '%s\n' cache-skill >"$RAW/failure-step.txt"
    return 1
  fi
  [ -f "$CACHE/hooks/hooks.json" ] || {
    printf '%s\n' cache-hooks >"$RAW/failure-step.txt"
    return 1
  }
  [ -f "$HYBRID_PROJECT/.codex/agents/harness-probe.toml" ] || {
    printf '%s\n' project-agent >"$RAW/failure-step.txt"
    return 1
  }
  : >"$RAW/cache-skill.present"
  : >"$RAW/cache-hooks.present"
  printf '%s\n' "$_cache_version" >"$RAW/cache-version.txt"

  if [ "$ALLOW_LIVE" -eq 1 ]; then
    git -C "$HYBRID_PROJECT" init -q >/dev/null 2>&1 || {
      printf '%s\n' runtime-git-init >"$RAW/runtime-failure-step.txt"
      LIVE_RC=2
    }
    if [ "$LIVE_RC" -ne 2 ]; then
      python3 - "$ISOLATED_CODEX_HOME/config.toml" "$HYBRID_PROJECT" <<'PY' || return 1
import pathlib
import sys

config = pathlib.Path(sys.argv[1])
project = sys.argv[2].replace("\\", "\\\\").replace('"', '\\"')
with config.open("a") as handle:
    handle.write(f'\n[projects."{project}"]\ntrust_level = "trusted"\n')
PY
      HOME="$ISOLATED_HOME" CODEX_HOME="$ISOLATED_CODEX_HOME" \
        HARNESS_PACKAGING_HOOK_LOG="$RUNTIME_HOOK_LOG" \
        "$CODEX_BIN" exec --json --approve-for-me \
        --dangerously-bypass-hook-trust --ephemeral --enable multi_agent \
        --skip-git-repo-check \
        -C "$HYBRID_PROJECT" \
        'This is a runtime contract probe. You MUST invoke the installed $harness-packaging-probe skill, then MUST call spawn_agent with agent_type harness_probe_reviewer for one fresh read-only task and wait for it. Report the exact response from both; do not synthesize either marker yourself.' \
        >"$RUNTIME_STDOUT" 2>"$RAW/runtime.stderr"
      LIVE_RC=$?
    fi
  fi

  run_cli plugin-reinstall add harness-hybrid@harness-probe --json || return 1
  _fingerprint_after=$(cache_fingerprint "$CACHE_BASE") || {
    printf '%s\n' cache-reinstall >"$RAW/failure-step.txt"
    return 1
  }
  [ "$_fingerprint_before" = "$_fingerprint_after" ] || {
    printf '%s\n' reinstall-mutated-cache >"$RAW/failure-step.txt"
    return 1
  }
  : >"$RAW/reinstall-idempotent.present"
  run_cli plugin-remove remove harness-hybrid@harness-probe --json || return 1
  [ ! -e "$CACHE_BASE" ] || {
    printf '%s\n' plugin-remove-cache >"$RAW/failure-step.txt"
    return 1
  }
  run_cli marketplace-remove marketplace remove harness-probe --json || return 1

  python3 - "$MARKET_ROOT/plugins/harness-hybrid/skills/harness-packaging-probe/SKILL.md" <<'PY' \
    || return 1
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace("HARNESS_PACKAGING_SKILL_OK", "HARNESS_PACKAGING_SKILL_V2"))
PY
  run_cli marketplace-readd marketplace add "$MARKET_ROOT" --json || return 1
  run_cli plugin-update-add add harness-hybrid@harness-probe --json || return 1
  _updated_fingerprint=$(cache_fingerprint "$CACHE_BASE") || {
    printf '%s\n' updated-cache >"$RAW/failure-step.txt"
    return 1
  }
  UPDATED_CACHE="$CACHE_BASE/${_updated_fingerprint%% *}"
  grep -q HARNESS_PACKAGING_SKILL_V2 \
    "$UPDATED_CACHE/skills/harness-packaging-probe/SKILL.md" || {
    printf '%s\n' local-source-refresh >"$RAW/failure-step.txt"
    return 1
  }
  : >"$RAW/local-source-refresh.present"
  run_cli plugin-update-remove remove harness-hybrid@harness-probe --json || return 1
  [ ! -e "$CACHE_BASE" ] || {
    printf '%s\n' plugin-update-remove-cache >"$RAW/failure-step.txt"
    return 1
  }
  run_cli marketplace-final-remove marketplace remove harness-probe --json || return 1
  : >"$RAW/cleanup.present"
}

if run_hybrid_lifecycle; then
  : >"$RAW/hybrid-lifecycle-passed.present"
fi

export CLI_VERSION PLATFORM_LABEL CAPTURE_DATE STAGED DIRECT_PROJECT LIVE_RC
python3 - <<'PY' || die "failed to describe direct-project candidate"
import json
import os
import pathlib

staged = pathlib.Path(os.environ["STAGED"])
direct = pathlib.Path(os.environ["DIRECT_PROJECT"])
skill = direct / ".agents/skills/harness-packaging-probe/SKILL.md"
hook = direct / ".codex/hooks.json"
agent = direct / ".codex/agents/harness-probe.toml"
checks = {
    "project_files_materialized": all(path.is_file() for path in (skill, hook, agent)),
    "runtime_discovery_observed": False,
    "real_conflict_installer_observed": False,
}
payload = {
    "schema_version": 1,
    "runtime": "codex",
    "cli_version": os.environ["CLI_VERSION"],
    "platform": os.environ["PLATFORM_LABEL"],
    "captured_at": os.environ["CAPTURE_DATE"],
    "config_hash": "not-applicable",
    "capture": "isolated-local-packaging-probe",
    "candidate": "direct",
    "result": {
        "status": "unknown",
        "passed": False,
        "checks": checks,
        "runtime_execution_observed": False,
        "runtime_evidence_boundary": "representative files only; no Codex discovery, installer conflict, or runtime execution",
        "owner": "codex-support-phase-5",
        "exit_condition": "A disposable direct-adapter probe must prove Codex skill, agent, and hook discovery plus real installer conflict behavior.",
    },
}
(staged / "packaging-direct.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY

export RAW
python3 - <<'PY' || die "failed to normalize hybrid runtime evidence"
import json
import os
import pathlib

staged = pathlib.Path(os.environ["STAGED"])
raw = pathlib.Path(os.environ["RAW"])
stdout = (raw / "runtime.stdout").read_text(errors="replace")
checks = {
    "installed_plugin_skill_invoked": "HARNESS_PACKAGING_SKILL_OK" in stdout,
    "project_agent_dispatched": "HARNESS_PACKAGING_AGENT_OK" in stdout,
    "plugin_hook_executed": (
        (raw / "runtime-hook.log").is_file()
        and (raw / "runtime-hook.log").read_text(errors="replace").strip()
        == "HARNESS_PACKAGING_HOOK_OK"
    ),
}
passed = int(os.environ["LIVE_RC"]) == 0 and all(checks.values())
payload = {
    "schema_version": 1,
    "runtime": "codex",
    "cli_version": os.environ["CLI_VERSION"],
    "platform": os.environ["PLATFORM_LABEL"],
    "captured_at": os.environ["CAPTURE_DATE"],
    "config_hash": "not-applicable",
    "capture": "isolated-live-packaging-probe" if passed else "live-packaging-probe-not-observed",
    "candidate": "hybrid",
    "result": {
        "status": "observed" if passed else "unknown",
        "passed": passed,
        "checks": checks,
        "runtime_execution_observed": passed,
        "payload_values_redacted": True,
        "hook_trust_mode": "automation-vetted-bypass" if checks["plugin_hook_executed"] else "not-observed",
        "verifies": "Installed plugin skill invocation, automation-vetted plugin hook execution, and project-agent dispatch in one disposable session.",
        "does_not_verify": "Persisted user hook trust, interactive desktop behavior, network marketplace installation, or the direct-project fallback.",
    },
}
if not passed:
    payload["result"].update(
        {
            "owner": "codex-support-phase-5",
            "exit_condition": "Run the explicitly authorized hybrid runtime probe until skill, hook, and agent checks all pass.",
        }
    )
(staged / "packaging-hybrid-runtime.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n"
)
PY

export HYBRID_PROJECT RAW
python3 - <<'PY' || die "failed to normalize hybrid lifecycle"
import json
import os
import pathlib

staged = pathlib.Path(os.environ["STAGED"])
raw = pathlib.Path(os.environ["RAW"])
hybrid = pathlib.Path(os.environ["HYBRID_PROJECT"])
def contains(path, marker):
    try:
        return marker in path.read_text(errors="replace")
    except OSError:
        return False

checks = {
    "agent_discovery_surface": (hybrid / ".codex/agents/harness-probe.toml").is_file(),
    "cleanup": (raw / "cleanup.present").is_file(),
    "hook_registration_visible_in_installed_copy": (raw / "cache-hooks.present").is_file(),
    "isolated_state_roots": (raw / "isolated-state-roots.present").is_file(),
    "marketplace_discovery": contains(raw / "marketplace-list.stdout", "harness-probe"),
    "local_source_remove_readd_refresh": (raw / "local-source-refresh.present").is_file(),
    "no_op_reinstall": (raw / "reinstall-idempotent.present").is_file(),
    "plugin_discovery": contains(raw / "plugin-available.stdout", "harness-hybrid"),
    "plugin_install": contains(raw / "plugin-add.stdout", "harness-hybrid"),
    "plugin_removal": contains(raw / "plugin-remove.stdout", "harness-hybrid"),
    "skill_discovery_visible_in_installed_copy": (raw / "cache-skill.present").is_file(),
    "strict_config": (raw / "strict-invalid-rejected.present").is_file()
    and (raw / "strict-valid-accepted.present").is_file(),
}
passed = (raw / "hybrid-lifecycle-passed.present").is_file() and all(checks.values())
payload = {
    "schema_version": 1,
    "runtime": "codex",
    "cli_version": os.environ["CLI_VERSION"],
    "platform": os.environ["PLATFORM_LABEL"],
    "captured_at": os.environ["CAPTURE_DATE"],
    "config_hash": "not-applicable",
    "capture": "isolated-local-packaging-probe",
    "candidate": "hybrid",
    "result": {
        "status": "observed" if passed else "unknown",
        "passed": passed,
        "checks": checks,
        "runtime_execution_observed": False,
        "runtime_evidence_boundary": "installed-copy inspection only; no skill, hook, or agent execution",
        "hook_trust": "not-observed",
        "installed_cache_version": (raw / "cache-version.txt").read_text().strip()
        if (raw / "cache-version.txt").is_file()
        else "not-observed",
        "local_source_update": "remove-readd-refresh-observed"
        if (raw / "local-source-refresh.present").is_file()
        else "not-observed",
    },
}
if not passed:
    payload["result"].update(
        {
            "failure_step": (raw / "failure-step.txt").read_text().strip()
            if (raw / "failure-step.txt").is_file()
            else "normalization",
            "owner": "codex-support-phase-2",
            "exit_condition": "Re-run the isolated local packaging probe until the selected hybrid lifecycle passes every measured check.",
        }
    )
(staged / "packaging-hybrid.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
PY

python3 - "$STAGED" <<'PY' || die "unsafe packaging evidence"
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
windows_absolute = __import__("re").compile(r"^[A-Za-z]:[\\/]")

def unsafe(value):
    if isinstance(value, dict):
        return any(unsafe(child) for child in value.values())
    if isinstance(value, list):
        return any(unsafe(child) for child in value)
    return isinstance(value, str) and (
        value.startswith(("/", "file://")) or windows_absolute.match(value)
    )

for path in root.glob("*.json"):
    payload = json.loads(path.read_text())
    if unsafe(payload):
        raise SystemExit(f"private path remained in {path.name}")
PY

mkdir -p "$OUTPUT" || die "cannot create output directory"
for _result in packaging-hybrid.json packaging-hybrid-runtime.json packaging-direct.json; do
  cp "$STAGED/$_result" "$OUTPUT/$_result" || die "cannot publish $_result"
done
printf 'codex-packaging-probe: wrote 3 sanitized fixtures for Codex %s\n' "$CLI_VERSION"
