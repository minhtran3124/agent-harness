#!/usr/bin/env bash

set -u

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SCRIPT="$ROOT/scripts/probe_codex_packaging.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/codex-packaging-test.XXXXXX")
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
PASS=0
FAIL=0

ok() {
  PASS=$((PASS + 1))
  printf '  ok    %s\n' "$1"
}

not_ok() {
  FAIL=$((FAIL + 1))
  printf '  not ok %s\n' "$1"
}

assert() {
  _label=$1
  shift
  if "$@"; then ok "$_label"; else not_ok "$_label"; fi
}

FAKE="$TMP/codex"
cat >"$FAKE" <<'SH'
#!/usr/bin/env bash
set -u

printf '%s|%s|%s\n' "$HOME" "$CODEX_HOME" "$*" >>"$FAKE_CODEX_LOG"

if [ "${1:-}" = "--version" ]; then
  printf 'codex-cli 0.147.0\n'
  exit 0
fi
if [ "${1:-}" = "--strict-config" ] && [ "${2:-}" = "--no-alt-screen" ]; then
  if grep -q definitely_unknown_packaging_probe_key "$CODEX_HOME/config.toml"; then
    if [ "${FAKE_STRICT_ACCEPT_INVALID:-0}" = 1 ]; then
      exit 0
    fi
    printf 'unknown configuration field\n' >&2
    exit 19
  fi
  printf 'Error: stdin is not a terminal\n' >&2
  exit 20
fi

[ "${1:-}" = "plugin" ] || exit 92
shift

case "${1:-}:${2:-}" in
  marketplace:add)
    [ "${FAKE_MARKETPLACE_FAIL:-0}" = 0 ] || exit 17
    source=$3
    mkdir -p "$CODEX_HOME/probe-marketplace"
    cp -R "$source/." "$CODEX_HOME/probe-marketplace/"
    printf '{"name":"harness-probe","status":"added"}\n'
    ;;
  marketplace:list)
    printf '[{"name":"harness-probe"}]\n'
    ;;
  marketplace:remove)
    rm -rf "$CODEX_HOME/probe-marketplace"
    printf '{"name":"harness-probe","status":"removed"}\n'
    ;;
  list:--marketplace)
    if [ -d "$CODEX_HOME/plugins/cache/harness-probe/harness-hybrid/local" ]; then
      printf '[{"name":"harness-hybrid","enabled":true,"installed":true}]\n'
    else
      printf '[{"name":"harness-hybrid","enabled":false,"installed":false}]\n'
    fi
    ;;
  add:harness-hybrid@harness-probe)
    target="$CODEX_HOME/plugins/cache/harness-probe/harness-hybrid/local"
    count_file="$CODEX_HOME/add-count"
    count=0
    [ ! -f "$count_file" ] || count=$(cat "$count_file")
    count=$((count + 1))
    printf '%s\n' "$count" >"$count_file"
    mkdir -p "$(dirname "$target")"
    rm -rf "$target"
    cp -R "$CODEX_HOME/probe-marketplace/plugins/harness-hybrid" "$target"
    if [ "${FAKE_REINSTALL_MUTATE:-0}" = 1 ] && [ "$count" -eq 2 ]; then
      printf 'reinstall mutation\n' >>"$target/skills/harness-packaging-probe/SKILL.md"
    fi
    printf '{"name":"harness-hybrid","status":"installed"}\n'
    ;;
  remove:harness-hybrid@harness-probe)
    rm -rf "$CODEX_HOME/plugins/cache/harness-probe/harness-hybrid"
    printf '{"name":"harness-hybrid","status":"removed"}\n'
    ;;
  *)
    exit 93
    ;;
esac
SH
chmod +x "$FAKE"

CALLER_HOME="$TMP/caller-home"
CALLER_CODEX="$TMP/caller-codex"
mkdir -p "$CALLER_HOME" "$CALLER_CODEX"
printf 'keep\n' >"$CALLER_CODEX/sentinel"
LOG="$TMP/calls.log"
: >"$LOG"

if HOME="$CALLER_HOME" CODEX_HOME="$CALLER_CODEX" FAKE_CODEX_LOG="$LOG" \
  "$SCRIPT" --output "$TMP/out" --codex-bin "$FAKE" >/dev/null; then
  ok "disposable hybrid-versus-direct probe succeeds"
else
  not_ok "disposable hybrid-versus-direct probe succeeds"
fi

assert "hybrid result is emitted" test -f "$TMP/out/packaging-hybrid.json"
assert "direct result is emitted" test -f "$TMP/out/packaging-direct.json"
assert "caller Codex state stays untouched" test "$(cat "$CALLER_CODEX/sentinel")" = keep
assert "probe does not leave a cache in caller state" test ! -e "$CALLER_CODEX/plugins"
assert "hybrid lifecycle passes without claiming runtime execution" python3 -c \
  'import json,sys; r=json.load(open(sys.argv[1]))["result"]; assert r["passed"] and not r["runtime_execution_observed"] and all(r["checks"].values())' \
  "$TMP/out/packaging-hybrid.json"
assert "direct candidate remains owned unknown until a real adapter probe" python3 -c \
  'import json,sys; r=json.load(open(sys.argv[1]))["result"]; assert not r["passed"] and r["status"]=="unknown" and not r["runtime_execution_observed"] and r["owner"]=="codex-support-phase-5" and not all(r["checks"].values())' \
  "$TMP/out/packaging-direct.json"
assert "all mutating CLI calls use isolated HOME and CODEX_HOME" python3 -c \
  'import pathlib,sys; caller_home,caller_codex,log=sys.argv[1:]; rows=pathlib.Path(log).read_text().splitlines(); assert rows; assert all(r.split("|",2)[0] != caller_home and r.split("|",2)[1] != caller_codex for r in rows)' \
  "$CALLER_HOME" "$CALLER_CODEX" "$LOG"
assert "exact supported CLI lifecycle is exercised" python3 -c \
  'import pathlib,re,sys; calls=[r.split("|",2)[2] for r in pathlib.Path(sys.argv[1]).read_text().splitlines()]; expected=[r"--version", r"--strict-config --no-alt-screen", r"--strict-config --no-alt-screen", r"plugin marketplace add .+ --json", r"plugin marketplace list --json", r"plugin list --marketplace harness-probe --available --json", r"plugin add harness-hybrid@harness-probe --json", r"plugin list --marketplace harness-probe --json", r"plugin add harness-hybrid@harness-probe --json", r"plugin remove harness-hybrid@harness-probe --json", r"plugin marketplace remove harness-probe --json", r"plugin marketplace add .+ --json", r"plugin add harness-hybrid@harness-probe --json", r"plugin remove harness-hybrid@harness-probe --json", r"plugin marketplace remove harness-probe --json"]; assert len(calls)==len(expected), calls; assert all(re.fullmatch(pattern,call) for call,pattern in zip(calls,expected)), calls' \
  "$LOG"
assert "fixtures contain no absolute repository path" python3 -c \
  'import pathlib,sys; root=str(pathlib.Path(sys.argv[1]).resolve()); assert root not in pathlib.Path(sys.argv[2]).read_text()' \
  "$ROOT" "$TMP/out/packaging-hybrid.json"

FAIL_OUT="$TMP/fail-out"
if HOME="$CALLER_HOME" CODEX_HOME="$CALLER_CODEX" FAKE_CODEX_LOG="$LOG" \
  FAKE_MARKETPLACE_FAIL=1 "$SCRIPT" --output "$FAIL_OUT" --codex-bin "$FAKE" >/dev/null 2>&1; then
  ok "CLI lifecycle failure is captured without aborting publication"
else
  not_ok "CLI lifecycle failure is captured without aborting publication"
fi
assert "failed hybrid is published as owned unknown" python3 -c \
  'import json,sys; r=json.load(open(sys.argv[1]))["result"]; assert r["status"]=="unknown" and not r["passed"] and r["failure_step"]=="marketplace-add" and r["owner"]' \
  "$FAIL_OUT/packaging-hybrid.json"
assert "failed capture still publishes the direct fallback state" test -f "$FAIL_OUT/packaging-direct.json"

MUTATE_OUT="$TMP/mutate-out"
if HOME="$CALLER_HOME" CODEX_HOME="$CALLER_CODEX" FAKE_CODEX_LOG="$LOG" \
  FAKE_REINSTALL_MUTATE=1 "$SCRIPT" --output "$MUTATE_OUT" --codex-bin "$FAKE" >/dev/null 2>&1; then
  ok "reinstall cache mutation is captured"
else
  not_ok "reinstall cache mutation is captured"
fi
assert "reinstall mutation fails the measured idempotence check" python3 -c \
  'import json,sys; r=json.load(open(sys.argv[1]))["result"]; assert not r["passed"] and not r["checks"]["no_op_reinstall"] and r["failure_step"]=="reinstall-mutated-cache"' \
  "$MUTATE_OUT/packaging-hybrid.json"

STRICT_OUT="$TMP/strict-out"
if HOME="$CALLER_HOME" CODEX_HOME="$CALLER_CODEX" FAKE_CODEX_LOG="$LOG" \
  FAKE_STRICT_ACCEPT_INVALID=1 "$SCRIPT" --output "$STRICT_OUT" --codex-bin "$FAKE" >/dev/null 2>&1; then
  ok "strict parsing failure is captured without aborting publication"
else
  not_ok "strict parsing failure is captured without aborting publication"
fi
assert "strict parsing failure makes selected hybrid unknown" python3 -c \
  'import json,sys; r=json.load(open(sys.argv[1]))["result"]; assert not r["passed"] and not r["checks"]["strict_config"] and r["failure_step"]=="strict-invalid-accepted"' \
  "$STRICT_OUT/packaging-hybrid.json"

printf '\n  codex-packaging-probe.test.sh: %d passed' "$PASS"
if [ "$FAIL" -gt 0 ]; then
  printf ', %d failed\n' "$FAIL"
  exit 1
fi
printf '\n'
