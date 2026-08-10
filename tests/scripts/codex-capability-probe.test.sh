#!/usr/bin/env bash
# Contract tests for scripts/capture_codex_capabilities.sh.

set -u

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SCRIPT="$ROOT/scripts/capture_codex_capabilities.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0
FAIL=0

ok() {
  PASS=$((PASS + 1))
  printf '  ok    %s\n' "$1"
}

not_ok() {
  FAIL=$((FAIL + 1))
  printf '  FAIL  %s\n' "$1"
}

assert() {
  _label=$1
  shift
  if "$@"; then ok "$_label"; else not_ok "$_label"; fi
}

FAKE="$TMP/fake-codex"
FAKE_LOG="$TMP/fake.log"
export FAKE_LOG

cat > "$FAKE" <<'FAKE'
#!/usr/bin/env bash
set -u
printf '%s\n' "$*" >> "$FAKE_LOG"

case "${1:-}" in
  --version)
    printf 'codex-cli %s\n' "${FAKE_VERSION:-0.147.0}"
    ;;
  features)
    printf '%-36s %-18s %s\n' hooks stable true
    printf '%-36s %-18s %s\n' multi_agent stable true
    printf '%-36s %-18s %s\n' plugins stable true
    printf '%-36s %-18s %s\n' unified_exec stable true
    ;;
  doctor)
    if [ "${FAKE_DOCTOR_FAIL:-0}" = 1 ]; then
      exit 9
    fi
    printf '%s\n' '{"schemaVersion":1,"overallStatus":"ok","codexVersion":"0.147.0","checks":{"config.load":{"id":"config.load","category":"config","status":"ok","details":{"cwd":"/Users/private/repo","auth file":"/Users/private/.codex/auth.json"}}}}'
    ;;
  --strict-config)
    printf '%s\n' 'Codex CLI --strict-config'
    ;;
  plugin)
    printf '%s\n' 'Manage Codex plugins'
    ;;
  exec)
    _previous=""
    _repo=""
    for _arg in "$@"; do
      if [ "$_previous" = "-C" ]; then _repo=$_arg; fi
      _previous=$_arg
    done
    printf 'PROBE_REPO=%s\n' "$_repo" >> "$FAKE_LOG"
    if [ -n "${HARNESS_PROBE_EVENT_LOG:-}" ]; then
      cat > "$HARNESS_PROBE_EVENT_LOG" <<'EVENTS'
{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"printf redacted"}}
{"hook_event_name":"PostToolUse","tool_name":"Bash","tool_input":{"command":"printf redacted"}}
{"hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** End Patch"}}
{"hook_event_name":"PostToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** End Patch"}}
EVENTS
    fi
    printf '%s\n' '{"type":"harness_agent_probe","fresh_bounded":true,"full_history_override_rejected":true}'
    ;;
  *)
    exit 2
    ;;
esac
FAKE
chmod +x "$FAKE"

if "$SCRIPT" --codex-bin "$FAKE" >/dev/null 2>&1; then
  not_ok "--output is mandatory"
else
  ok "--output is mandatory"
fi

OUT="$TMP/evidence"
: > "$FAKE_LOG"
if CODEX_CAPTURE_DATE=2026-08-10 "$SCRIPT" \
  --output "$OUT" --codex-bin "$FAKE" --platform-label macos-arm64 >/dev/null; then
  ok "default deterministic capture succeeds"
else
  not_ok "default deterministic capture succeeds"
fi

EXPECTED="doctor.json hooks-shell.json hooks-apply-patch.json agents-fresh-bounded.json agents-full-history-rejection.json session-end-timing.json platform.json trust-config.json"
for _name in $EXPECTED; do
  assert "writes $_name" test -s "$OUT/$_name"
done

assert "default capture never invokes a model" sh -c "! grep -q '^exec ' '$FAKE_LOG'"
assert "checker unit tests are registered in the CI-equivalent suite" grep -q \
  'scripts/test_check_codex_capabilities.py' "$ROOT/scripts/run-tests.sh"
assert "doctor output is sanitized" sh -c "! grep -R -q '/Users/private' '$OUT'"
assert "default shell result is explicit unknown" python3 -c \
  'import json,sys; assert json.load(open(sys.argv[1]))["result"]["status"] == "unknown"' \
  "$OUT/hooks-shell.json"
assert "SessionEnd benchmark uses at least 20 samples" python3 -c \
  'import json,sys; d=json.load(open(sys.argv[1]))["result"]; assert d["samples"] >= 20 and d["max_ms"] < d["support_threshold_ms"]' \
  "$OUT/session-end-timing.json"

LIVE="$TMP/live-evidence"
: > "$FAKE_LOG"
if CODEX_CAPTURE_DATE=2026-08-10 "$SCRIPT" \
  --output "$LIVE" --codex-bin "$FAKE" --platform-label macos-arm64 \
  --allow-live-model-probe >/dev/null; then
  ok "paid/model-backed probe requires and accepts explicit opt-in"
else
  not_ok "paid/model-backed probe requires and accepts explicit opt-in"
fi
assert "opted-in capture invokes exec" grep -q '^exec ' "$FAKE_LOG"
assert "live hook result is observed when all events arrive" python3 -c \
  'import json,sys; assert json.load(open(sys.argv[1]))["result"]["status"] == "observed"' \
  "$LIVE/hooks-apply-patch.json"

PROBE_REPO=$(sed -n 's/^PROBE_REPO=//p' "$FAKE_LOG" | tail -1)
assert "temporary live-probe repository is cleaned up" test ! -e "$PROBE_REPO"

if FAKE_VERSION=0.148.0 CODEX_CAPTURE_DATE=2026-08-10 "$SCRIPT" \
  --output "$OUT" --codex-bin "$FAKE" --platform-label macos-arm64 >/dev/null 2>&1; then
  not_ok "refuses to overwrite evidence from another CLI version"
else
  ok "refuses to overwrite evidence from another CLI version"
fi

if CODEX_CAPTURE_DATE=2026-08-10 "$SCRIPT" \
  --output "$OUT" --codex-bin "$FAKE" --platform-label linux-x86_64 >/dev/null 2>&1; then
  not_ok "refuses to overwrite evidence from another platform"
else
  ok "refuses to overwrite evidence from another platform"
fi

if CODEX_CAPTURE_DATE=2026-08-10 "$SCRIPT" \
  --output "$TMP/unsafe" --codex-bin "$FAKE" --platform-label /Users/private >/dev/null 2>&1; then
  not_ok "rejects unsafe platform labels before writing"
else
  ok "rejects unsafe platform labels before writing"
fi

TOOL_PATH="$TMP/tool-path"
mkdir -p "$TOOL_PATH"
for _tool in bash basename cat cp date dirname git grep mkdir mktemp mv python3 rm sed sh tail uname; do
  _tool_path=$(command -v "$_tool")
  ln -s "$_tool_path" "$TOOL_PATH/$_tool"
done
MISSING_TOOLS="$TMP/missing-tools"
if PATH="$TOOL_PATH" CODEX_CAPTURE_DATE=2026-08-10 "$SCRIPT" \
  --output "$MISSING_TOOLS" --codex-bin "$FAKE" --platform-label macos-arm64 >/dev/null; then
  assert "missing jq is recorded without touching real config" python3 -c \
    'import json,sys; d=json.load(open(sys.argv[1]))["result"]; assert d["dependencies"]["jq"] is False' \
    "$MISSING_TOOLS/platform.json"
  assert "missing benchmark dependency stays explicit unknown" python3 -c \
    'import json,sys; assert json.load(open(sys.argv[1]))["result"]["status"] == "unknown"' \
    "$MISSING_TOOLS/session-end-timing.json"
else
  not_ok "missing tools degrade to explicit unknown"
fi

FALLBACK="$TMP/doctor-fallback"
if FAKE_DOCTOR_FAIL=1 CODEX_CAPTURE_DATE=2026-08-10 "$SCRIPT" \
  --output "$FALLBACK" --codex-bin "$FAKE" --platform-label macos-arm64 >/dev/null; then
  assert "doctor failure becomes explicit unknown" python3 -c \
    'import json,sys; assert json.load(open(sys.argv[1]))["result"]["doctor_overall_status"] == "unknown"' \
    "$FALLBACK/doctor.json"
else
  not_ok "doctor failure becomes explicit unknown"
fi

printf '\n  codex-capability-probe.test.sh: %d passed' "$PASS"
if [ "$FAIL" -ne 0 ]; then
  printf ', %d failed\n' "$FAIL"
  exit 1
fi
printf '\n'
