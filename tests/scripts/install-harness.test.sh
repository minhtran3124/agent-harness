#!/bin/bash
# Integration tests for scripts/install-harness.sh — installs from this checkout
# (--source) into throwaway target dirs. Frozen from the 6-case suite that shipped
# the MCP wiring (commit ea3182f).
source "$(dirname "$0")/../lib.sh"

INSTALL="$ROOT/scripts/install-harness.sh"
MEMORY_DIR="agent""-memory"

target() { local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); echo "$d"; }
run_install() { # run_install <target> [extra args/env...]
  local tgt="$1"; shift
  OUT=$(bash "$INSTALL" --source "$ROOT" --yes -d "$tgt" "$@" 2>&1); RC=$?
}

t "dry-run on a fresh target writes nothing"
tgt=$(target)
OUT=$(bash "$INSTALL" --source "$ROOT" --dry-run -d "$tgt" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF "would create  .mcp.json" && ! echo "$OUT" | grep -qiF "$MEMORY_DIR" && [ ! -e "$tgt/.claude" ] && [ ! -e "$tgt/.mcp.json" ] && [ -z "$(find "$tgt" -mindepth 1 -print -quit)" ]; then
  pass
else
  fail "rc=$RC, .claude exists: $([ -e "$tgt/.claude" ] && echo yes || echo no)"
fi

t "fresh install creates valid .mcp.json, builds .claude/, prunes root sources"
tgt=$(target)
run_install "$tgt"
if [ "$RC" -eq 0 ] \
   && jq -e '.mcpServers["code-review-graph"]' "$tgt/.mcp.json" >/dev/null 2>&1 \
   && [ -d "$tgt/.claude/skills" ] && [ ! -e "$tgt/skills" ]; then
  pass
else
  fail "rc=$RC — mcp/.claude/prune state wrong: $(ls -a "$tgt" | tr '\n' ' ')"
fi

t "fresh install scaffolds six structural files and memory-free agents"
tgt=$(target)
run_install "$tgt"
if [ "$RC" -eq 0 ] \
   && [ -f "$tgt/specs/README.md" ] && [ -f "$tgt/specs/STATE.md" ] \
   && [ -f "$tgt/docs/solutions/README.md" ] && [ -f "$tgt/docs/solutions/INDEX.md" ] \
   && [ -f "$tgt/docs/solutions/critical-patterns.md" ] && [ -f "$tgt/techstacks/README.md" ] \
   && [ ! -e "$tgt/$MEMORY_DIR" ] \
   && ! grep -q '^memory:' "$tgt/.claude/agents/coding.md" \
   && ! grep -q '^memory:' "$tgt/.claude/agents/reviewer.md" \
   && ! grep -q '^memory:' "$tgt/.claude/agents/test-runner.md"; then
  pass
else
  fail "rc=$RC — structural scaffolding missing: $(ls -a "$tgt" | tr '\n' ' ')"
fi

t "fresh install emits Claude-bound agents, not source-time binding metadata"
tgt=$(target)
run_install "$tgt"
if [ "$RC" -eq 0 ] \
   && grep -q '^model: claude-opus-5-5$' "$tgt/.claude/agents/reviewer.md" \
   && grep -q '^tools: Glob, Grep, Read, Bash$' "$tgt/.claude/agents/reviewer.md" \
   && [ ! -e "$tgt/.claude/agents/agent-contracts.json" ] \
   && [ ! -e "$tgt/.claude/agents/runtime-bindings.json" ]; then
  pass
else
  fail "rc=$RC — agent renderer output/boundary is wrong"
fi

t "reinstall does not recreate the removed directory"
tgt=$(target)
run_install "$tgt"
run_install "$tgt"
if [ "$RC" -eq 0 ] && [ ! -e "$tgt/$MEMORY_DIR" ]; then pass; else fail "rc=$RC"; fi

t "pre-existing consumer directory is untouched"
tgt=$(target)
mkdir -p "$tgt/$MEMORY_DIR/nested"
printf 'KEEP ME\n' > "$tgt/$MEMORY_DIR/KEEP.md"
printf 'NESTED\n' > "$tgt/$MEMORY_DIR/nested/value.txt"
manifest_before=$(find "$tgt/$MEMORY_DIR" -type f -print | sed "s#^$tgt/$MEMORY_DIR/##" | sort)
content_before=$(cat "$tgt/$MEMORY_DIR/KEEP.md")
run_install "$tgt"
manifest_after=$(find "$tgt/$MEMORY_DIR" -type f -print | sed "s#^$tgt/$MEMORY_DIR/##" | sort)
content_after=$(cat "$tgt/$MEMORY_DIR/KEEP.md")
if [ "$RC" -eq 0 ] && [ "$manifest_before" = "$manifest_after" ] && [ "$content_before" = "$content_after" ]; then pass; else fail "rc=$RC manifest/content changed"; fi

t "install never clobbers a pre-existing structural file"
tgt=$(target)
mkdir -p "$tgt/docs/solutions"
printf 'MY REAL INDEX\n' > "$tgt/docs/solutions/INDEX.md"
run_install "$tgt"
if [ "$RC" -eq 0 ] && [ "$(cat "$tgt/docs/solutions/INDEX.md")" = "MY REAL INDEX" ]; then
  pass
else
  fail "rc=$RC — pre-existing INDEX.md was clobbered: [$(cat "$tgt/docs/solutions/INDEX.md" 2>&1)]"
fi

t "existing .mcp.json with other servers is merged, not replaced (backup taken)"
tgt=$(target)
echo '{"mcpServers":{"context7":{"type":"http","url":"https://example.com"}}}' > "$tgt/.mcp.json"
run_install "$tgt"
keys=$(jq -r '.mcpServers | keys | join(",")' "$tgt/.mcp.json" 2>/dev/null)
if [ "$RC" -eq 0 ] && [ "$keys" = "code-review-graph,context7" ] && ls "$tgt"/.harness-backup-*/.mcp.json >/dev/null 2>&1; then
  pass
else
  fail "rc=$RC keys=[$keys] backup=$(ls "$tgt"/.harness-backup-* 2>/dev/null | head -1)"
fi

t "re-install on an already-wired target is idempotent"
run_install "$tgt"
assert_rc_contains 0 "already wires code-review-graph"

t "invalid existing .mcp.json is left untouched with a warning"
tgt=$(target)
printf 'NOT JSON {' > "$tgt/.mcp.json"
run_install "$tgt"
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF "not valid JSON" && [ "$(cat "$tgt/.mcp.json")" = "NOT JSON {" ]; then
  pass
else
  fail "rc=$RC content=[$(cat "$tgt/.mcp.json")]"
fi

t "missing uvx warns at preflight but does not fail the install"
tgt=$(target)
OUT=$(env PATH=/usr/bin:/bin bash "$INSTALL" --source "$ROOT" --dry-run -d "$tgt" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF "uvx not found"; then pass; else
  command -v uvx >/dev/null 2>&1 && [ "$RC" -eq 0 ] && skip "uvx reachable even at /usr/bin:/bin" || fail "rc=$RC"
fi

# ---------- uv auto-install (no network: fake curl, stub uvx, temp HOME, restricted PATH) ----------
POLL_TRIES=20   # 0.1 s each — the 2 s budget for observing the detached pre-fetch
SYS_UVX=$(env PATH=/usr/bin:/bin sh -c 'command -v uvx' || true)
UV_LINE="uvx not found — installing uv from astral.sh for the code-review-graph MCP server (skip with --no-uv)"
POST_WARN="Install uv before that restart"
PREFETCH_LINE="Pre-fetching code-review-graph from PyPI in the background (skip with --no-uv)"

# uv_home → fresh tmphome + fakebin (fakebin empty; rows add fakes)
uv_home() { tmphome=$(target); fakebin=$(target); }
# fake_curl <body> — a curl that logs each call to $HOME/curl.log, then runs <body>
fake_curl() {
  printf '#!/bin/sh\necho "$*" >> "$HOME/curl.log"\n%s\n' "$1" > "$fakebin/curl"
  chmod +x "$fakebin/curl"
}
# stub_uvx <dir> — a no-op uvx that logs its args to $HOME/uvx.log
stub_uvx() {
  mkdir -p "$1"
  printf '#!/bin/sh\necho "$*" >> "$HOME/uvx.log"\n' > "$1/uvx"
  chmod +x "$1/uvx"
}
# run_uv <PATH> [VAR=val | --flag]... — install into a fresh target with uv env scrubbed
run_uv() {
  local p="$1"; shift
  local tgt a; tgt=$(target)
  local -a envs=() args=()
  for a in "$@"; do case "$a" in -*) args+=("$a") ;; *) envs+=("$a") ;; esac; done
  OUT=$(env -u CS_NO_UV -u XDG_BIN_HOME -u XDG_DATA_HOME -u UV_INSTALL_DIR \
          -u CARGO_DIST_FORCE_INSTALL_DIR -u UV_UNMANAGED_INSTALL \
          HOME="$tmphome" PATH="$p" ${envs[@]+"${envs[@]}"} \
          bash "$INSTALL" --source "$ROOT" --yes -d "$tgt" ${args[@]+"${args[@]}"} 2>&1); RC=$?
}
# poll_log <file> — wait up to POLL_TRIES × 0.1 s for <file> to be non-empty
poll_log() { local i=0; while [ "$i" -lt "$POLL_TRIES" ] && [ ! -s "$1" ]; do sleep 0.1; i=$((i+1)); done; }

t "auto-install success"
if [ -n "$SYS_UVX" ]; then skip "system uvx at $SYS_UVX"; else
  uv_home
  # The detached pre-fetch stub may still append to $tmphome/uvx.log after cleanup removes
  # tmphome; that write fails silently and is harmless.
  fake_curl "cat <<'EOS'
mkdir -p \"\$HOME/.local/bin\"
printf '#!/bin/sh\necho \"\$*\" >> \"\$HOME/uvx.log\"\n' > \"\$HOME/.local/bin/uvx\"
chmod +x \"\$HOME/.local/bin/uvx\"
EOS"
  run_uv "$fakebin:/usr/bin:/bin"
  n=$(printf '%s\n' "$OUT" | grep -c "uvx not found" || true)
  if [ "$RC" -eq 0 ] && [ "$n" -eq 1 ] && echo "$OUT" | grep -qF "$UV_LINE" \
     && echo "$OUT" | grep -qF "Installed uv" && [ -s "$tmphome/curl.log" ] \
     && ! echo "$OUT" | grep -qF "$POST_WARN"; then pass
  else fail "rc=$RC uvx-not-found lines=$n — out: $(echo "$OUT" | grep -iE 'uv|curl' | tr '\n' ' ')"; fi
fi

t "pre-fetch runs by default"
uv_home; fake_curl "exit 0"; stub_uvx "$fakebin"
run_uv "$fakebin:/usr/bin:/bin"
poll_log "$tmphome/uvx.log"
if [ "$RC" -eq 0 ] && grep -qF "code-review-graph --version" "$tmphome/uvx.log" 2>/dev/null \
   && echo "$OUT" | grep -qF "$PREFETCH_LINE" && [ ! -e "$tmphome/curl.log" ]; then pass
else fail "rc=$RC uvx.log=[$(cat "$tmphome/uvx.log" 2>&1)] curl.log exists: $([ -e "$tmphome/curl.log" ] && echo yes || echo no)"; fi

t "auto-install failure"
if [ -n "$SYS_UVX" ]; then skip "system uvx at $SYS_UVX"; else
  uv_home; fake_curl "exit 22"
  run_uv "$fakebin:/usr/bin:/bin"
  if [ "$RC" -eq 0 ] && [ -s "$tmphome/curl.log" ] && echo "$OUT" | grep -qF "uv install failed" \
     && echo "$OUT" | grep -qF "$POST_WARN"; then pass
  else fail "rc=$RC — out: $(echo "$OUT" | grep -iE 'uv|curl' | tr '\n' ' ')"; fi
fi

t "no curl"
if [ -n "$SYS_UVX" ]; then skip "system uvx at $SYS_UVX"; else
  uv_home; nocurlbin=$(target)
  for f in /usr/bin/* /bin/*; do
    case "${f##*/}" in curl|uvx) continue ;; esac
    ln -sfn "$f" "$nocurlbin/${f##*/}"   # -n: never descend into an earlier dir symlink (X11)
  done
  run_uv "$nocurlbin"
  if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF "curl not found"; then pass
  else fail "rc=$RC — out: $(echo "$OUT" | grep -iE 'uv|curl' | tr '\n' ' ')"; fi
fi

t "--no-uv"
if [ -n "$SYS_UVX" ]; then skip "system uvx at $SYS_UVX"; else
  uv_home; fake_curl "exit 0"
  run_uv "$fakebin:/usr/bin:/bin" --no-uv
  if [ "$RC" -eq 0 ] && [ ! -e "$tmphome/curl.log" ] \
     && echo "$OUT" | grep -qF "uvx not found — the code-review-graph MCP server launches through it."; then pass
  else fail "rc=$RC curl.log exists: $([ -e "$tmphome/curl.log" ] && echo yes || echo no)"; fi
fi

t "CS_NO_UV=1"
if [ -n "$SYS_UVX" ]; then skip "system uvx at $SYS_UVX"; else
  uv_home; fake_curl "exit 0"
  run_uv "$fakebin:/usr/bin:/bin" CS_NO_UV=1
  if [ "$RC" -eq 0 ] && [ ! -e "$tmphome/curl.log" ]; then pass
  else fail "rc=$RC curl.log exists: $([ -e "$tmphome/curl.log" ] && echo yes || echo no)"; fi
fi

t "--dry-run"
if [ -n "$SYS_UVX" ]; then skip "system uvx at $SYS_UVX"; else
  uv_home; fake_curl "exit 0"
  run_uv "$fakebin:/usr/bin:/bin" --dry-run
  if [ "$RC" -eq 0 ] && [ ! -e "$tmphome/curl.log" ] && echo "$OUT" | grep -qF "would install uv"; then pass
  else fail "rc=$RC curl.log exists: $([ -e "$tmphome/curl.log" ] && echo yes || echo no)"; fi
fi

t "pre-fetch opt-out"
uv_home; fake_curl "exit 0"; stub_uvx "$fakebin"
run_uv "$fakebin:/usr/bin:/bin" CS_NO_UV=1
i=0; while [ "$i" -lt "$POLL_TRIES" ]; do sleep 0.1; i=$((i+1)); done   # full window
if [ "$RC" -eq 0 ] && [ ! -s "$tmphome/uvx.log" ] && [ ! -e "$tmphome/curl.log" ]; then pass
else fail "rc=$RC uvx.log=[$(cat "$tmphome/uvx.log" 2>&1)]"; fi

t "declined re-sync installs nothing"
if [ -n "$SYS_UVX" ]; then skip "system uvx at $SYS_UVX"
elif ! command -v python3 >/dev/null 2>&1; then skip "python3 needed to sever the controlling terminal"
else
  uv_home; fake_curl "exit 0"; tgt=$(target)
  bash "$INSTALL" --source "$ROOT" --yes -d "$tgt" </dev/null >/dev/null 2>&1   # existing harness (CS_NO_UV=1)
  # Re-run without --yes and with no controlling terminal (as install-tty-gate.test.sh does),
  # so the existing-harness gate aborts; uv must not have been installed by then.
  OUT=$(python3 - "$tmphome" "$fakebin:/usr/bin:/bin" "$INSTALL" "$ROOT" "$tgt" <<'PYEOF'
import subprocess, sys
home, path, install, root, tgt = sys.argv[1:]
p = subprocess.run(["env", "-u", "CS_NO_UV", "HOME=" + home, "PATH=" + path,
                    "bash", install, "--source", root, "-d", tgt],
                   start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT, timeout=120, text=True)
print(p.stdout, end="")
print("INSTALL_RC=%d" % p.returncode)
PYEOF
)
  RC=$(printf '%s\n' "$OUT" | sed -n 's/^INSTALL_RC=\([0-9]*\)$/\1/p' | tail -1)
  if [ "${RC:-0}" -ne 0 ] && echo "$OUT" | grep -qF "Re-run with --yes" \
     && [ ! -e "$tmphome/curl.log" ]; then pass
  else fail "rc=$RC curl.log exists: $([ -e "$tmphome/curl.log" ] && echo yes || echo no)"; fi
fi

t "--help documents --no-uv"
OUT=$(bash "$INSTALL" --help 2>&1); RC=$?
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF -- "--no-uv"; then pass; else fail "rc=$RC — --no-uv missing from --help"; fi

finish
