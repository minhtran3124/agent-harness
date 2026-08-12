#!/usr/bin/env bash
# Contract tests for the non-clobber Codex hybrid adapter lifecycle.
source "$(dirname "$0")/../lib.sh"

INSTALL="$ROOT/scripts/install-codex-harness.sh"
FIXTURES="$ROOT/tests/fixtures/codex-install"

new_dir() {
  local directory
  directory=$(mktemp -d)
  _CLEANUP_DIRS+=("$directory")
  printf '%s\n' "$directory"
}

make_fake_codex() {
  local directory=$1
  mkdir -p "$directory/bin" "$directory/home"
  cat > "$directory/bin/codex" <<'EOF'
#!/bin/bash
printf '%s\n' "$*" >> "$FAKE_CODEX_LOG"
if [ -n "${FAKE_CODEX_FAIL_MATCH:-}" ]; then
  case "$*" in
    *"$FAKE_CODEX_FAIL_MATCH"*)
      if [ ! -e "$FAKE_CODEX_FAIL_MARKER" ]; then
        : > "$FAKE_CODEX_FAIL_MARKER"
        exit 19
      fi
      ;;
  esac
fi
printf '{"ok":true}\n'
EOF
  chmod +x "$directory/bin/codex"
  : > "$directory/codex.log"
}

run_install() {
  local target=$1 fake=$2
  shift 2
  OUT=$(FAKE_CODEX_LOG="$fake/codex.log" \
    FAKE_CODEX_FAIL_MARKER="$fake/fail-once" \
    PATH="$fake/bin:$PATH" \
    bash "$INSTALL" --source "$ROOT" --directory "$target" \
      --codex-bin "$fake/bin/codex" --codex-home "$fake/home" "$@" 2>&1)
  RC=$?
}

snapshot() {
  python3 - "$1" <<'PY'
import hashlib
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
digest = hashlib.sha256()
for path in sorted(item for item in root.rglob("*") if item.is_file()):
    digest.update(path.relative_to(root).as_posix().encode())
    digest.update(b"\0")
    digest.update(path.read_bytes())
    digest.update(b"\0")
print(digest.hexdigest())
PY
}

TARGET=$(new_dir)
TARGET_REAL=$(cd "$TARGET" && pwd -P)
FAKE=$(new_dir)
make_fake_codex "$FAKE"
cp "$FIXTURES/custom-AGENTS.md" "$TARGET/AGENTS.md"
mkdir -p "$TARGET/.codex/agents" "$TARGET/.agents/plugins"
cp "$FIXTURES/custom-config.toml" "$TARGET/.codex/config.toml"
printf 'name = "custom"\n' > "$TARGET/.codex/agents/custom.toml"
printf '{"custom":true}\n' > "$TARGET/.codex/hooks.json"
printf '{"name":"user-marketplace"}\n' > "$TARGET/.agents/plugins/marketplace.json"
CONFIG_BEFORE=$(shasum -a 256 "$TARGET/.codex/config.toml")
AGENTS_PREFIX=$(cat "$TARGET/AGENTS.md")

run_install "$TARGET" "$FAKE" --yes
t "fresh install succeeds through the isolated Codex CLI"
assert_rc 0

t "fresh install creates all four project agents and the instruction fragment"
count=$(find "$TARGET/.codex/agents" -name '*.toml' | wc -l | tr -d ' ')
if [ "$count" = "5" ] && [ -f "$TARGET/.codex/harness-instructions.md" ]; then pass
else fail "agent count=$count or instructions missing"; fi

t "plugin source and marketplace are materialized under the owned state root"
if [ -f "$TARGET/.codex/.agent-harness/marketplace/.agents/plugins/marketplace.json" ] \
   && [ -f "$TARGET/.codex/.agent-harness/marketplace/plugins/agent-harness/.codex-plugin/plugin.json" ]; then pass
else fail "persistent marketplace/plugin source missing"; fi

t "Codex lifecycle uses marketplace add and plugin add"
if grep -qF "plugin marketplace add $TARGET_REAL/.codex/.agent-harness/marketplace --json" "$FAKE/codex.log" \
   && grep -qF "plugin add agent-harness@agent-harness-local --json" "$FAKE/codex.log"; then pass
else fail "unexpected CLI log: $(tr '\n' ' ' < "$FAKE/codex.log")"; fi

t "fresh install never preemptively removes a same-named external registration"
if ! grep -qE '^plugin (remove|marketplace remove) ' "$FAKE/codex.log"; then pass
else fail "fresh lifecycle removed state before proving ownership"; fi

t "root AGENTS.md keeps user prose and adds exactly one bounded pointer"
if grep -qF "$AGENTS_PREFIX" "$TARGET/AGENTS.md" \
   && [ "$(grep -c '<!-- agent-harness:begin -->' "$TARGET/AGENTS.md")" = "1" ] \
   && [ "$(grep -c '<!-- agent-harness:end -->' "$TARGET/AGENTS.md")" = "1" ]; then pass
else fail "AGENTS.md was clobbered or block count is wrong"; fi

t "config, trust, custom agent, hooks, and unrelated marketplace canaries survive"
if [ "$(shasum -a 256 "$TARGET/.codex/config.toml")" = "$CONFIG_BEFORE" ] \
   && [ -f "$TARGET/.codex/agents/custom.toml" ] \
   && grep -q custom "$TARGET/.codex/hooks.json" \
   && grep -q user-marketplace "$TARGET/.agents/plugins/marketplace.json"; then pass
else fail "one or more user-owned canaries changed"; fi

t "deployment manifest lists exact project ownership and no user canaries"
if python3 - "$TARGET/.codex/.agent-harness/deployment-manifest.json" <<'PY'
import json, pathlib, sys
data = json.loads(pathlib.Path(sys.argv[1]).read_text())
paths = set(data["project_files"])
assert paths == {
    ".codex/agents/coding.toml",
    ".codex/agents/reviewer.toml",
    ".codex/agents/task-reviewer.toml",
    ".codex/agents/test-runner.toml",
    ".codex/harness-instructions.md",
}
assert ".codex/config.toml" not in paths
PY
then pass; else fail "manifest inventory is not exact"; fi

FIRST_SNAPSHOT=$(snapshot "$TARGET")
run_install "$TARGET" "$FAKE" --yes
t "reinstall is byte-idempotent"
if [ "$RC" -eq 0 ] && [ "$(snapshot "$TARGET")" = "$FIRST_SNAPSHOT" ]; then pass
else fail "reinstall changed the target tree: $OUT"; fi

UPDATED_SOURCE=$(new_dir)
cp -R "$ROOT/." "$UPDATED_SOURCE/"
printf '\nSuccessful update marker.\n' >> "$UPDATED_SOURCE/adapters/codex/project/harness-instructions.md"
OUT=$(FAKE_CODEX_LOG="$FAKE/codex.log" \
  FAKE_CODEX_FAIL_MARKER="$FAKE/fail-once" \
  PATH="$FAKE/bin:$PATH" \
  bash "$INSTALL" --source "$UPDATED_SOURCE" --directory "$TARGET" \
    --codex-bin "$FAKE/bin/codex" --codex-home "$FAKE/home" --yes 2>&1)
RC=$?
t "source update refreshes owned artifacts without changing user configuration"
if [ "$RC" -eq 0 ] \
   && grep -qF 'Successful update marker.' "$TARGET/.codex/harness-instructions.md" \
   && [ "$(shasum -a 256 "$TARGET/.codex/config.toml")" = "$CONFIG_BEFORE" ]; then pass
else fail "source update failed: $OUT"; fi

# Return to the canonical source before conflict assertions below.
run_install "$TARGET" "$FAKE" --yes

printf 'LOCAL REVIEWER CUSTOMIZATION\n' > "$TARGET/.codex/agents/reviewer.toml"
python3 - "$TARGET/AGENTS.md" <<'PY'
import pathlib, sys
path = pathlib.Path(sys.argv[1])
path.write_text(path.read_text().replace(
    "Read `.codex/harness-instructions.md` before using the Agent Harness.",
    "LOCAL MANAGED BLOCK EDIT",
))
PY
run_install "$TARGET" "$FAKE" --yes
t "edited generated agent is preserved with a reviewable incoming sidecar"
if [ "$RC" -eq 0 ] \
   && grep -qF 'LOCAL REVIEWER CUSTOMIZATION' "$TARGET/.codex/agents/reviewer.toml" \
   && grep -qF 'sandbox_mode = "read-only"' "$TARGET/.codex/agents/reviewer.toml.harness-incoming"; then pass
else fail "agent conflict policy failed: $OUT"; fi

t "edited AGENTS.md block is preserved with a full incoming sidecar"
if grep -qF 'LOCAL MANAGED BLOCK EDIT' "$TARGET/AGENTS.md" \
   && grep -qF 'Read `.codex/harness-instructions.md`' "$TARGET/AGENTS.md.harness-incoming"; then pass
else fail "AGENTS.md conflict policy failed"; fi

run_install "$TARGET" "$FAKE" --overwrite-conflicts
t "explicit overwrite resolves managed conflicts and removes sidecars"
if [ "$RC" -eq 0 ] \
   && grep -qF 'sandbox_mode = "read-only"' "$TARGET/.codex/agents/reviewer.toml" \
   && grep -qF 'Read `.codex/harness-instructions.md`' "$TARGET/AGENTS.md" \
   && [ ! -e "$TARGET/.codex/agents/reviewer.toml.harness-incoming" ] \
   && [ ! -e "$TARGET/AGENTS.md.harness-incoming" ]; then pass
else fail "overwrite did not resolve conflicts: $OUT"; fi

printf 'retired generated content\n' > "$TARGET/.codex/agents/retired.toml"
python3 - "$TARGET/.codex/.agent-harness/deployment-manifest.json" "$TARGET/.codex/agents/retired.toml" <<'PY'
import hashlib, json, pathlib, sys
manifest, retired = map(pathlib.Path, sys.argv[1:])
data = json.loads(manifest.read_text())
data["project_files"][".codex/agents/retired.toml"] = hashlib.sha256(retired.read_bytes()).hexdigest()
manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY
run_install "$TARGET" "$FAKE" --yes
t "reinstall prunes a source-removed path only when its recorded hash still matches"
if [ "$RC" -eq 0 ] && [ ! -e "$TARGET/.codex/agents/retired.toml" ]; then pass
else fail "stale owned path survived: $OUT"; fi

DRY_TARGET=$(new_dir)
DRY_FAKE=$(new_dir)
make_fake_codex "$DRY_FAKE"
run_install "$DRY_TARGET" "$DRY_FAKE" --dry-run
t "dry-run writes nothing and never invokes Codex"
if [ "$RC" -eq 0 ] && [ -z "$(find "$DRY_TARGET" -mindepth 1 -print -quit)" ] \
   && [ ! -s "$DRY_FAKE/codex.log" ]; then pass
else fail "dry-run mutated state: $OUT"; fi

LINK_TARGET=$(new_dir)
LINK_EXTERNAL=$(new_dir)
ln -s "$LINK_EXTERNAL" "$LINK_TARGET/.codex"
run_install "$LINK_TARGET" "$DRY_FAKE" --dry-run
t "managed Codex paths cannot escape the target through a symlink"
if [ "$RC" -ne 0 ] && [ -z "$(find "$LINK_EXTERNAL" -mindepth 1 -print -quit)" ]; then pass
else fail "symlink escape was accepted: $OUT"; fi

TTY_TARGET=$(new_dir)
TTY_FAKE=$(new_dir)
make_fake_codex "$TTY_FAKE"
TTY_OUT=$(python3 - "$INSTALL" "$ROOT" "$TTY_TARGET" "$TTY_FAKE" <<'PY'
import os
import subprocess
import sys

install, source, target, fake = sys.argv[1:]
environment = dict(os.environ)
environment.update(
    FAKE_CODEX_LOG=f"{fake}/codex.log",
    FAKE_CODEX_FAIL_MARKER=f"{fake}/fail-once",
    PATH=f"{fake}/bin:{environment['PATH']}",
)
result = subprocess.run(
    [
        "bash", install, "--source", source, "--directory", target,
        "--codex-bin", f"{fake}/bin/codex", "--codex-home", f"{fake}/home",
    ],
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    start_new_session=True,
    text=True,
    timeout=30,
    env=environment,
)
print(f"RC={result.returncode}")
print(result.stdout)
PY
)
t "tty-less install is deterministic and never attempts to prompt"
if printf '%s\n' "$TTY_OUT" | grep -qF 'RC=0' \
   && [ -f "$TTY_TARGET/.codex/.agent-harness/deployment-manifest.json" ]; then pass
else fail "tty-less install failed: $TTY_OUT"; fi

MINIMAL_TARGET=$(new_dir)
MINIMAL_FAKE=$(new_dir)
make_fake_codex "$MINIMAL_FAKE"
OUT=$(FAKE_CODEX_LOG="$MINIMAL_FAKE/codex.log" \
  FAKE_CODEX_FAIL_MARKER="$MINIMAL_FAKE/fail-once" \
  PATH="$MINIMAL_FAKE/bin:$PATH" \
  CODEX_HOME="$MINIMAL_FAKE/home" \
  /bin/bash "$INSTALL" --source "$ROOT" --directory "$MINIMAL_TARGET" 2>&1)
RC=$?
t "minimal invocation with no forwarded flags works on stock /bin/bash (3.2 on macOS)"
if [ "$RC" -eq 0 ] \
   && [ -f "$MINIMAL_TARGET/.codex/.agent-harness/deployment-manifest.json" ]; then pass
else fail "minimal invocation failed: $OUT"; fi

FAIL_TARGET=$(new_dir)
FAIL_FAKE=$(new_dir)
make_fake_codex "$FAIL_FAKE"
OUT=$(FAKE_CODEX_LOG="$FAIL_FAKE/codex.log" \
  FAKE_CODEX_FAIL_MARKER="$FAIL_FAKE/fail-once" \
  FAKE_CODEX_FAIL_MATCH="add agent-harness@agent-harness-local" \
  PATH="$FAIL_FAKE/bin:$PATH" \
  bash "$INSTALL" --source "$ROOT" --directory "$FAIL_TARGET" \
    --codex-bin "$FAIL_FAKE/bin/codex" --codex-home "$FAIL_FAKE/home" --yes 2>&1)
RC=$?
t "failed plugin installation rolls back before project files are installed"
if [ "$RC" -ne 0 ] && [ -z "$(find "$FAIL_TARGET" -mindepth 1 -print -quit)" ]; then pass
else fail "rc=$RC target not empty after rollback: $OUT"; fi

NOOP_TARGET=$(new_dir)
NOOP_FAKE=$(new_dir)
make_fake_codex "$NOOP_FAKE"
run_install "$NOOP_TARGET" "$NOOP_FAKE" --remove --yes
t "removal with no deployment does not remove a same-named user plugin or marketplace"
if [ "$RC" -eq 0 ] && [ ! -s "$NOOP_FAKE/codex.log" ]; then pass
else fail "no-op removal invoked Codex: $(tr '\n' ' ' < "$NOOP_FAKE/codex.log")"; fi

BEFORE_FAILED_UPDATE=$(snapshot "$TARGET")
: > "$FAKE/fail-once"
rm "$FAKE/fail-once"
OUT=$(FAKE_CODEX_LOG="$FAKE/codex.log" \
  FAKE_CODEX_FAIL_MARKER="$FAKE/fail-once" \
  FAKE_CODEX_FAIL_MATCH="add agent-harness@agent-harness-local" \
  PATH="$FAKE/bin:$PATH" \
  bash "$INSTALL" --source "$ROOT" --directory "$TARGET" \
    --codex-bin "$FAKE/bin/codex" --codex-home "$FAKE/home" --yes 2>&1)
RC=$?
t "interrupted update restores the previous marketplace and project tree"
if [ "$RC" -ne 0 ] && [ "$(snapshot "$TARGET")" = "$BEFORE_FAILED_UPDATE" ]; then pass
else fail "failed update was not rolled back: $OUT"; fi

run_install "$TARGET" "$FAKE" --remove --yes
t "removal deletes unchanged manifest-owned files and the bounded AGENTS.md section"
if [ "$RC" -eq 0 ] \
   && [ ! -e "$TARGET/.codex/.agent-harness" ] \
   && [ ! -e "$TARGET/.codex/harness-instructions.md" ] \
   && [ ! -e "$TARGET/.codex/agents/reviewer.toml" ] \
   && ! grep -q 'agent-harness:' "$TARGET/AGENTS.md"; then pass
else fail "managed cleanup incomplete: $OUT"; fi

t "removal preserves every user-owned canary and original AGENTS.md prose"
if [ "$(shasum -a 256 "$TARGET/.codex/config.toml")" = "$CONFIG_BEFORE" ] \
   && [ -f "$TARGET/.codex/agents/custom.toml" ] \
   && grep -q custom "$TARGET/.codex/hooks.json" \
   && grep -q user-marketplace "$TARGET/.agents/plugins/marketplace.json" \
   && grep -qF "$AGENTS_PREFIX" "$TARGET/AGENTS.md"; then pass
else fail "removal damaged user state"; fi

t "removal invokes only the harness plugin and marketplace removal commands"
if grep -qF 'plugin remove agent-harness@agent-harness-local --json' "$FAKE/codex.log" \
   && grep -qF 'plugin marketplace remove agent-harness-local --json' "$FAKE/codex.log"; then pass
else fail "removal lifecycle missing from CLI log"; fi

finish
