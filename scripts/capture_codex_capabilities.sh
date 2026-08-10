#!/usr/bin/env bash
# Capture sanitized, version-pinned Codex capability evidence.

set -u

usage() {
  cat <<'EOF'
Usage: capture_codex_capabilities.sh --output DIR --codex-bin PATH [options]

Options:
  --output DIR                    Required evidence output directory.
  --codex-bin PATH                Required Codex CLI executable.
  --platform-label LABEL          Override detected platform (for CI fixtures).
  --allow-live-model-probe        Explicitly allow the model-backed hook/agent probe.
  -h, --help                      Show this help.

The default path captures only CLI, doctor, dependency, config-hash, and local
SessionEnd timing facts.  Hook and custom-agent behavior stays explicit unknown
unless --allow-live-model-probe is supplied and the expected events are observed.
EOF
}

die() {
  printf 'codex-capability-capture: %s\n' "$1" >&2
  exit 2
}

OUTPUT=""
CODEX_BIN=""
PLATFORM_LABEL=""
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
    --platform-label)
      [ "$#" -ge 2 ] || die "--platform-label requires a value"
      PLATFORM_LABEL=$2
      shift 2
      ;;
    --allow-live-model-probe)
      ALLOW_LIVE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
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

detect_platform() {
  _os=$(uname -s 2>/dev/null || printf unknown)
  _arch=$(uname -m 2>/dev/null || printf unknown)
  case "$_arch" in
    x86_64|amd64) _arch=x86_64 ;;
    arm64|aarch64) _arch=arm64 ;;
  esac
  case "$_os" in
    Darwin) printf 'macos-%s\n' "$_arch" ;;
    Linux)
      if grep -qi microsoft /proc/version 2>/dev/null; then
        printf 'wsl-%s\n' "$_arch"
      else
        printf 'linux-%s\n' "$_arch"
      fi
      ;;
    *) printf 'unknown-%s\n' "$_arch" ;;
  esac
}

if [ -z "$PLATFORM_LABEL" ]; then
  PLATFORM_LABEL=$(detect_platform)
fi
case "$PLATFORM_LABEL" in
  *[!a-zA-Z0-9._-]*|"") die "unsafe platform label: $PLATFORM_LABEL" ;;
esac

CAPTURE_DATE=${CODEX_CAPTURE_DATE:-$(date -u +%Y-%m-%d 2>/dev/null)}
python3 -c 'import datetime,sys; datetime.date.fromisoformat(sys.argv[1])' "$CAPTURE_DATE" \
  >/dev/null 2>&1 || die "capture date must be YYYY-MM-DD"

WORK=$(mktemp -d "${TMPDIR:-/tmp}/codex-capabilities.XXXXXX") || die "cannot create temporary directory"
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
RAW="$WORK/raw"
STAGED="$WORK/staged"
mkdir -p "$RAW" "$STAGED" || die "cannot initialize temporary capture"

VERSION_TEXT=$("$CODEX_BIN" --version 2>/dev/null) || die "codex --version failed"
CLI_VERSION=$(python3 -c 'import re,sys; m=re.search(r"\b(\d+\.\d+\.\d+)\b",sys.argv[1]); print(m.group(1) if m else "")' "$VERSION_TEXT")
[ -n "$CLI_VERSION" ] || die "could not parse Codex CLI version"

# Refuse mixed-version/platform evidence before invoking any optional live probe.
if [ -d "$OUTPUT" ]; then
  python3 - "$OUTPUT" "$CLI_VERSION" "$PLATFORM_LABEL" <<'PY' || exit 2
import json
import pathlib
import sys

output = pathlib.Path(sys.argv[1])
version = sys.argv[2]
platform = sys.argv[3]
for path in sorted(output.glob("*.json")):
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"codex-capability-capture: refusing unreadable existing evidence {path.name}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    old_version = payload.get("cli_version")
    old_platform = payload.get("platform")
    if old_version not in (None, version):
        print(f"codex-capability-capture: refusing version overwrite {old_version} -> {version}", file=sys.stderr)
        raise SystemExit(1)
    if old_platform not in (None, platform):
        print(f"codex-capability-capture: refusing platform overwrite {old_platform} -> {platform}", file=sys.stderr)
        raise SystemExit(1)
PY
fi

"$CODEX_BIN" features list >"$RAW/features.txt" 2>"$RAW/features.err"
FEATURES_RC=$?
"$CODEX_BIN" doctor --json >"$RAW/doctor.json" 2>"$RAW/doctor.err"
DOCTOR_RC=$?
"$CODEX_BIN" --strict-config --help >"$RAW/strict.txt" 2>"$RAW/strict.err"
STRICT_RC=$?
"$CODEX_BIN" plugin --help >"$RAW/plugin.txt" 2>"$RAW/plugin.err"
PLUGIN_RC=$?

CONFIG_HASH=$(python3 - <<'PY'
import hashlib
canonical = b'{"features":{"hooks":true},"hooks":{"PostToolUse":["Bash","apply_patch"],"PreToolUse":["Bash","apply_patch"],"SessionEnd":["other"]}}'
print(hashlib.sha256(canonical).hexdigest())
PY
)

EVENT_LOG="$RAW/events.jsonl"
LIVE_STDOUT="$RAW/live.stdout"
AGENT_NONCE=""
: > "$EVENT_LOG"
: > "$LIVE_STDOUT"

if [ "$ALLOW_LIVE" -eq 1 ]; then
  PROBE_REPO="$WORK/probe-repo"
  mkdir -p "$PROBE_REPO/.codex/agents" || die "cannot create live-probe repository"
  git -C "$PROBE_REPO" init -q >/dev/null 2>&1 || die "cannot initialize live-probe repository"
  AGENT_NONCE=$(python3 -c 'import secrets; print(secrets.token_hex(12))')

  RECORDER="$WORK/record-hook.py"
  cat > "$RECORDER" <<'PY'
import json
import os
import sys

target = os.environ.get("HARNESS_PROBE_EVENT_LOG")
if target:
    try:
        payload = json.load(sys.stdin)
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    except Exception:
        pass
PY

  python3 - "$PROBE_REPO/.codex/hooks.json" "$RECORDER" <<'PY'
import json
import pathlib
import shlex
import sys

target = pathlib.Path(sys.argv[1])
command = "python3 " + shlex.quote(sys.argv[2])
entry = {"matcher": "Bash|apply_patch|Edit|Write", "hooks": [{"type": "command", "command": command}]}
target.write_text(json.dumps({"hooks": {"PreToolUse": [entry], "PostToolUse": [entry]}}, indent=2) + "\n")
PY

  python3 - "$PROBE_REPO/.codex/agents/harness-probe.toml" "$AGENT_NONCE" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
nonce = sys.argv[2]
path.write_text(
    'name = "harness_probe"\n'
    'description = "Disposable read-only capability probe."\n'
    'sandbox_mode = "read-only"\n'
    'developer_instructions = "Return exactly HARNESS_AGENT_OK:' + nonce + '."\n'
)
PY

  HARNESS_PROBE_EVENT_LOG="$EVENT_LOG" "$CODEX_BIN" exec --json \
    --skip-git-repo-check -C "$PROBE_REPO" \
    "Use one shell command and apply_patch once. Delegate one fresh task to the harness_probe custom agent and report its exact response. Then attempt a full-history fork with an agent-type override and state whether the runtime rejects that override." \
    >"$LIVE_STDOUT" 2>"$RAW/live.stderr"
  LIVE_RC=$?
else
  LIVE_RC=125
fi

export CAPTURE_DATE CLI_VERSION PLATFORM_LABEL CONFIG_HASH AGENT_NONCE
export RAW STAGED WORK FEATURES_RC DOCTOR_RC STRICT_RC PLUGIN_RC LIVE_RC
STATE_BREADCRUMB_HOOK=$(cd "$(dirname "$0")/.." && pwd)/hooks/state-breadcrumb.sh
export STATE_BREADCRUMB_HOOK
python3 - <<'PY' || die "failed to normalize captured evidence"
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import time

raw = pathlib.Path(os.environ["RAW"])
staged = pathlib.Path(os.environ["STAGED"])
work = pathlib.Path(os.environ["WORK"])
version = os.environ["CLI_VERSION"]
platform = os.environ["PLATFORM_LABEL"]
captured_at = os.environ["CAPTURE_DATE"]
config_digest = os.environ["CONFIG_HASH"]


def base(capture, result, config_hash="not-applicable"):
    return {
        "schema_version": 1,
        "runtime": "codex",
        "cli_version": version,
        "platform": platform,
        "captured_at": captured_at,
        "config_hash": config_hash,
        "capture": capture,
        "result": result,
    }


def write(name, payload):
    (staged / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


selected = {"hooks", "multi_agent", "plugins", "unified_exec"}
features = {}
if int(os.environ["FEATURES_RC"]) == 0:
    for line in (raw / "features.txt").read_text(errors="replace").splitlines():
        match = re.match(r"^(\S+)\s+(.+?)\s+(true|false)\s*$", line)
        if match and match.group(1) in selected:
            features[match.group(1)] = {
                "maturity": match.group(2).strip(),
                "enabled": match.group(3) == "true",
            }

doctor_overall = "unknown"
doctor_schema = None
doctor_checks = []
if int(os.environ["DOCTOR_RC"]) == 0:
    try:
        doctor = json.loads((raw / "doctor.json").read_text())
        doctor_overall = doctor.get("overallStatus", "unknown")
        doctor_schema = doctor.get("schemaVersion")
        checks = doctor.get("checks", {})
        if isinstance(checks, dict):
            for check in checks.values():
                if isinstance(check, dict):
                    doctor_checks.append(
                        {
                            "id": check.get("id"),
                            "category": check.get("category"),
                            "status": check.get("status"),
                        }
                    )
    except (OSError, json.JSONDecodeError):
        doctor_overall = "unknown"

doctor_status = "observed" if int(os.environ["DOCTOR_RC"]) == 0 and features and int(os.environ["STRICT_RC"]) == 0 and int(os.environ["PLUGIN_RC"]) == 0 else "unknown"
write(
    "doctor.json",
    base(
        "local-cli-non-model",
        {
            "status": doctor_status,
            "doctor_schema_version": doctor_schema,
            "doctor_overall_status": doctor_overall,
            "checks": sorted(doctor_checks, key=lambda item: str(item.get("id"))),
            "features": features,
            "strict_config_flag": int(os.environ["STRICT_RC"]) == 0,
            "plugin_command": int(os.environ["PLUGIN_RC"]) == 0,
        },
    ),
)

dependencies = {name: shutil.which(name) is not None for name in ("bash", "git", "jq", "python3")}
platform_status = "observed" if all(dependencies.values()) else "unknown"
os_family, _, architecture = platform.partition("-")
write(
    "platform.json",
    base(
        "local-dependency-probe",
        {
            "status": platform_status,
            "os_family": os_family,
            "architecture": architecture or "unknown",
            "dependencies": dependencies,
            "native_windows_claimed": False,
        },
    ),
)

write(
    "trust-config.json",
    base(
        "controlled-project-config",
        {
            "status": "observed",
            "hooks_feature": features.get("hooks", {}).get("maturity", "unknown"),
            "canonical_config_hashed": True,
            "project_trust_status": "unknown",
            "trust_evidence_boundary": "requires disposable-account probe",
        },
        f"sha256:{config_digest}",
    ),
)

events = []
for line in (raw / "events.jsonl").read_text(errors="replace").splitlines():
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        continue
    if isinstance(event, dict):
        events.append(event)


def event_pair(tool_name):
    names = {
        event.get("hook_event_name")
        for event in events
        if event.get("tool_name") == tool_name
    }
    return {"PreToolUse", "PostToolUse"}.issubset(names)


shell_observed = event_pair("Bash")
patch_observed = event_pair("apply_patch")
write(
    "hooks-shell.json",
    base(
        "isolated-live-model-probe" if shell_observed else "live-model-probe-not-observed",
        {
            "status": "observed" if shell_observed else "unknown",
            "tool_name": "Bash",
            "events": ["PreToolUse", "PostToolUse"] if shell_observed else [],
            "tool_input_keys": ["command"] if shell_observed else [],
            "command_redacted": True,
            "exit_condition": None if shell_observed else "Run the explicit live probe in a trusted disposable project.",
        },
        f"sha256:{config_digest}",
    ),
)
write(
    "hooks-apply-patch.json",
    base(
        "isolated-live-model-probe" if patch_observed else "live-model-probe-not-observed",
        {
            "status": "observed" if patch_observed else "unknown",
            "tool_name": "apply_patch",
            "events": ["PreToolUse", "PostToolUse"] if patch_observed else [],
            "matcher_aliases": ["Edit", "Write"],
            "tool_input_keys": ["command"] if patch_observed else [],
            "patch_redacted": True,
            "exit_condition": None if patch_observed else "Run the explicit live probe in a trusted disposable project.",
        },
        f"sha256:{config_digest}",
    ),
)

agent_marker = None
live_text = (raw / "live.stdout").read_text(errors="replace")
for line in live_text.splitlines():
    try:
        candidate = json.loads(line)
    except json.JSONDecodeError:
        continue
    if isinstance(candidate, dict) and candidate.get("type") == "harness_agent_probe":
        agent_marker = candidate
        break

agent_hash = hashlib.sha256(
    b'{"context":"fresh-bounded","delegation":false,"filesystem":"read-only","profile":"reviewer"}'
).hexdigest()
nonce = os.environ.get("AGENT_NONCE", "")
fresh_observed = bool(
    (agent_marker and agent_marker.get("fresh_bounded") is True)
    or (nonce and f"HARNESS_AGENT_OK:{nonce}" in live_text)
)
rejection_observed = bool(
    agent_marker and agent_marker.get("full_history_override_rejected") is True
)
write(
    "agents-fresh-bounded.json",
    base(
        "isolated-live-model-probe" if fresh_observed else "live-model-probe-not-observed",
        {
            "status": "observed" if fresh_observed else "unknown",
            "fork_context": "fresh-bounded",
            "requested_agent_profile_selected": fresh_observed,
            "instructions_redacted": True,
            "exit_condition": None if fresh_observed else "Capture a structured custom-agent dispatch trace.",
        },
        f"sha256:{agent_hash}",
    ),
)
write(
    "agents-full-history-rejection.json",
    base(
        "isolated-live-model-probe" if rejection_observed else "live-model-probe-not-observed",
        {
            "status": "observed" if rejection_observed else "unknown",
            "fork_context": "full-history",
            "override_rejected": rejection_observed,
            "error_text_redacted": True,
            "exit_condition": None if rejection_observed else "Capture a structured full-history override rejection.",
        },
        f"sha256:{agent_hash}",
    ),
)

samples = []
benchmark_ok = dependencies.get("jq", False)
benchmark_root = work / "session-end-benchmark"
(benchmark_root / "specs").mkdir(parents=True, exist_ok=True)
(benchmark_root / "specs/STATE.md").write_text("# State\n\n## Session End Log\n")
hook = pathlib.Path(__file__).resolve() if False else pathlib.Path.cwd() / "hooks/state-breadcrumb.sh"
# The capture script is run from any directory, so use the exported repository hook path.
hook = pathlib.Path(os.environ.get("STATE_BREADCRUMB_HOOK", str(hook)))
for index in range(20):
    if not hook.is_file():
        benchmark_ok = False
        break
    payload = json.dumps(
        {
            "session_id": f"benchmark-{index}",
            "cwd": str(benchmark_root),
            "hook_event_name": "SessionEnd",
            "reason": "other",
        }
    )
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(benchmark_root)
    started = time.perf_counter()
    completed = subprocess.run(
        ["bash", str(hook)],
        input=payload,
        text=True,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    samples.append((time.perf_counter() - started) * 1000)
    if completed.returncode != 0:
        benchmark_ok = False

ordered = sorted(samples)
minimum = min(ordered) if ordered else None
maximum = max(ordered) if ordered else None
p95_index = max(0, int(len(ordered) * 0.95 + 0.999999) - 1) if ordered else 0
p95 = ordered[p95_index] if ordered else None
within = bool(benchmark_ok and len(samples) >= 20 and maximum is not None and maximum < 800)
write(
    "session-end-timing.json",
    base(
        "isolated-local-benchmark",
        {
            "status": "observed" if within else "unknown",
            "hook": "hooks/state-breadcrumb.sh",
            "samples": len(samples),
            "min_ms": round(minimum, 3) if minimum is not None else None,
            "p95_ms": round(p95, 3) if p95 is not None else None,
            "max_ms": round(maximum, 3) if maximum is not None else None,
            "documented_default_timeout_ms": 1000,
            "documented_max_timeout_ms": 3000,
            "support_threshold_ms": 800,
            "within_threshold": within,
            "exit_condition": None if within else "Install dependencies and keep max runtime below 800 ms.",
        },
    ),
)


def unsafe_strings(value, prefix="fixture"):
    problems = []
    if isinstance(value, dict):
        for key, child in value.items():
            problems.extend(unsafe_strings(child, f"{prefix}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            problems.extend(unsafe_strings(child, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        if value.startswith(("/Users/", "/home/", "/root/", "file://")) or re.match(r"^[A-Za-z]:[\\/]Users[\\/]", value):
            problems.append(prefix)
    return problems


for path in sorted(staged.glob("*.json")):
    payload = json.loads(path.read_text())
    problems = unsafe_strings(payload)
    if problems:
        raise SystemExit(f"unsafe private data remained in {path.name}: {', '.join(problems)}")
PY

if [ ! -f "$STAGED/session-end-timing.json" ] || \
   ! python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["result"]["samples"] >= 20' "$STAGED/session-end-timing.json" 2>/dev/null; then
  die "SessionEnd benchmark did not complete"
fi

# Never silently replace an observed fixture with an unknown result.
if [ -d "$OUTPUT" ]; then
  python3 - "$OUTPUT" "$STAGED" <<'PY' || exit 2
import json
import pathlib
import sys

old_dir = pathlib.Path(sys.argv[1])
new_dir = pathlib.Path(sys.argv[2])
for new_path in new_dir.glob("*.json"):
    old_path = old_dir / new_path.name
    if not old_path.is_file():
        continue
    old = json.loads(old_path.read_text())
    new = json.loads(new_path.read_text())
    old_status = old.get("result", {}).get("status")
    new_status = new.get("result", {}).get("status")
    if old_status == "observed" and new_status == "unknown":
        print(f"codex-capability-capture: refusing evidence downgrade for {new_path.name}", file=sys.stderr)
        raise SystemExit(1)
PY
fi

mkdir -p "$OUTPUT" || die "cannot create output directory"
for _fixture in "$STAGED"/*.json; do
  _name=$(basename "$_fixture")
  cp "$_fixture" "$OUTPUT/.$_name.tmp" || die "cannot stage $_name"
  mv "$OUTPUT/.$_name.tmp" "$OUTPUT/$_name" || die "cannot publish $_name"
done

printf 'codex-capability-capture: wrote sanitized Codex %s evidence for %s\n' \
  "$CLI_VERSION" "$PLATFORM_LABEL"
