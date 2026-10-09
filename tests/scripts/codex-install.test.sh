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

# The managed AGENTS.md section, begin marker through end marker.
agents_block() {
  sed -n '/<!-- agent-harness:begin -->/,/<!-- agent-harness:end -->/p' "$1"
}

# Same test as rule-loading-tiers.test.sh: always-on unless line 1 is --- and a
# paths: line appears before the closing ---.
always_on_rules() {
  local rule
  for rule in "$ROOT"/rules/*.md; do
    if [ "$(head -n 1 "$rule")" = "---" ] \
       && sed -n '2,/^---$/p' "$rule" | grep -q '^paths:'; then
      continue
    fi
    printf '%s\n' "$rule"
  done
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

t "fresh install creates all four project agents and no retired instruction fragment"
count=$(find "$TARGET/.codex/agents" -name '*.toml' | wc -l | tr -d ' ')
if [ "$count" = "5" ] && [ ! -e "$TARGET/.codex/harness-instructions.md" ]; then pass
else fail "agent count=$count or retired instructions file written"; fi

t "fresh install puts every always-on rule's first heading inside the AGENTS.md markers"
BLOCK=$(agents_block "$TARGET/AGENTS.md")
missing=""
for rule in $(always_on_rules); do
  heading=$(grep -m 1 '^#' "$rule")
  printf '%s\n' "$BLOCK" | grep -qxF "$heading" || missing="$missing $(basename "$rule")"
done
if [ -n "$(always_on_rules)" ] && [ -z "$missing" ]; then pass
else fail "always-on rules missing from the block:$missing"; fi

t "a plain fresh install prints neither AGENTS.md warning"
if ! printf '%s\n' "$OUT" | grep -qE 'AGENTS\.override\.md|32 KiB'; then pass
else fail "unexpected warning: $OUT"; fi

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

RENDERED=$(new_dir)
python3 "$ROOT/scripts/render_codex_adapter.py" --root "$ROOT" --output "$RENDERED/out" >/dev/null
t "deployment manifest lists exact project ownership and no user canaries"
if python3 - "$TARGET/.codex/.agent-harness/deployment-manifest.json" "$RENDERED/out/render-manifest.json" <<'PY'
import json, pathlib, sys
data = json.loads(pathlib.Path(sys.argv[1]).read_text())
payload = json.loads(pathlib.Path(sys.argv[2]).read_text())["payload"]
assert payload
paths = set(data["project_files"])
assert paths == {
    ".codex/agents/coding.toml",
    ".codex/agents/reviewer.toml",
    ".codex/agents/task-reviewer.toml",
    ".codex/agents/test-runner.toml",
} | {".codex/.agent-harness/payload/" + item for item in payload}
assert ".codex/config.toml" not in paths
PY
then pass; else fail "manifest inventory is not exact"; fi

t "install writes the payload and records it in project_files"
if [ -f "$TARGET/.codex/.agent-harness/payload/scripts/verify_summary.py" ] \
   && grep -qF '".codex/.agent-harness/payload/scripts/verify_summary.py"' \
     "$TARGET/.codex/.agent-harness/deployment-manifest.json"; then pass
else fail "payload helper missing or not manifest-owned"; fi

FIRST_SNAPSHOT=$(snapshot "$TARGET")
run_install "$TARGET" "$FAKE" --yes
t "reinstall is byte-idempotent"
if [ "$RC" -eq 0 ] && [ "$(snapshot "$TARGET")" = "$FIRST_SNAPSHOT" ]; then pass
else fail "reinstall changed the target tree: $OUT"; fi

UPDATED_SOURCE=$(new_dir)
cp -R "$ROOT/." "$UPDATED_SOURCE/"
printf '\nSuccessful update marker.\n' >> "$UPDATED_SOURCE/rules/behavior.md"
OUT=$(FAKE_CODEX_LOG="$FAKE/codex.log" \
  FAKE_CODEX_FAIL_MARKER="$FAKE/fail-once" \
  PATH="$FAKE/bin:$PATH" \
  bash "$INSTALL" --source "$UPDATED_SOURCE" --directory "$TARGET" \
    --codex-bin "$FAKE/bin/codex" --codex-home "$FAKE/home" --yes 2>&1)
RC=$?
t "source update refreshes owned artifacts without changing user configuration"
if [ "$RC" -eq 0 ] \
   && agents_block "$TARGET/AGENTS.md" | grep -qF 'Successful update marker.' \
   && [ "$(shasum -a 256 "$TARGET/.codex/config.toml")" = "$CONFIG_BEFORE" ]; then pass
else fail "source update failed: $OUT"; fi

# Return to the canonical source before conflict assertions below.
run_install "$TARGET" "$FAKE" --yes

printf 'LOCAL REVIEWER CUSTOMIZATION\n' > "$TARGET/.codex/agents/reviewer.toml"
python3 - "$TARGET/AGENTS.md" <<'PY'
import pathlib, sys
path = pathlib.Path(sys.argv[1])
path.write_text(path.read_text(encoding="utf-8").replace(
    "# Behavioral Guidelines",
    "LOCAL MANAGED BLOCK EDIT",
), encoding="utf-8")
PY
run_install "$TARGET" "$FAKE" --yes
t "edited generated agent is preserved with a reviewable incoming sidecar"
if [ "$RC" -eq 0 ] \
   && grep -qF 'LOCAL REVIEWER CUSTOMIZATION' "$TARGET/.codex/agents/reviewer.toml" \
   && grep -qF 'sandbox_mode = "read-only"' "$TARGET/.codex/agents/reviewer.toml.harness-incoming"; then pass
else fail "agent conflict policy failed: $OUT"; fi

t "edited AGENTS.md block is preserved with a full incoming sidecar"
if grep -qF 'LOCAL MANAGED BLOCK EDIT' "$TARGET/AGENTS.md" \
   && grep -qxF '# Behavioral Guidelines' "$TARGET/AGENTS.md.harness-incoming"; then pass
else fail "AGENTS.md conflict policy failed"; fi

run_install "$TARGET" "$FAKE" --overwrite-conflicts
t "explicit overwrite resolves managed conflicts and removes sidecars"
if [ "$RC" -eq 0 ] \
   && grep -qF 'sandbox_mode = "read-only"' "$TARGET/.codex/agents/reviewer.toml" \
   && grep -qxF '# Behavioral Guidelines' "$TARGET/AGENTS.md" \
   && ! grep -qF 'LOCAL MANAGED BLOCK EDIT' "$TARGET/AGENTS.md" \
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

t "removal leaves no empty directory under .codex"
EMPTY_DIRS=$(find "$TARGET/.codex" -type d -empty)
if [ -z "$EMPTY_DIRS" ]; then pass
else fail "empty directories remain: $EMPTY_DIRS"; fi

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

PAYLOAD_TARGET=$(new_dir)
PAYLOAD_FAKE=$(new_dir)
make_fake_codex "$PAYLOAD_FAKE"
PAYLOAD="$PAYLOAD_TARGET/.codex/.agent-harness/payload"
run_install "$PAYLOAD_TARGET" "$PAYLOAD_FAKE" --yes
printf 'LOCAL PAYLOAD EDIT\n' > "$PAYLOAD/rules/behavior.md"
run_install "$PAYLOAD_TARGET" "$PAYLOAD_FAKE" --yes
t "edited payload file is preserved with a reviewable incoming sidecar"
if [ "$RC" -eq 0 ] \
   && grep -qF 'LOCAL PAYLOAD EDIT' "$PAYLOAD/rules/behavior.md" \
   && [ -s "$PAYLOAD/rules/behavior.md.harness-incoming" ] \
   && ! grep -qF 'LOCAL PAYLOAD EDIT' "$PAYLOAD/rules/behavior.md.harness-incoming"; then pass
else fail "payload conflict policy failed: $OUT"; fi

RETIRED_SOURCE=$(new_dir)
cp -R "$ROOT/." "$RETIRED_SOURCE/"
rm "$RETIRED_SOURCE/skills/using-git-worktrees/scripts/detect-isolation.sh"
OUT=$(FAKE_CODEX_LOG="$PAYLOAD_FAKE/codex.log" \
  FAKE_CODEX_FAIL_MARKER="$PAYLOAD_FAKE/fail-once" \
  PATH="$PAYLOAD_FAKE/bin:$PATH" \
  bash "$INSTALL" --source "$RETIRED_SOURCE" --directory "$PAYLOAD_TARGET" \
    --codex-bin "$PAYLOAD_FAKE/bin/codex" --codex-home "$PAYLOAD_FAKE/home" --yes 2>&1)
RC=$?
t "retired payload file is pruned along with its empty directory"
if [ "$RC" -eq 0 ] \
   && [ ! -e "$PAYLOAD/skills/using-git-worktrees" ] \
   && [ -f "$PAYLOAD/scripts/verify_summary.py" ] \
   && ! grep -qF 'detect-isolation.sh' "$PAYLOAD_TARGET/.codex/.agent-harness/deployment-manifest.json"; then pass
else fail "retired payload path survived: $OUT"; fi

run_install "$PAYLOAD_TARGET" "$PAYLOAD_FAKE" --remove --yes
t "removal keeps an edited payload file and deletes unchanged payload files"
if [ "$RC" -eq 0 ] \
   && grep -qF 'LOCAL PAYLOAD EDIT' "$PAYLOAD/rules/behavior.md" \
   && [ ! -e "$PAYLOAD/rules/behavior.md.harness-incoming" ] \
   && [ ! -e "$PAYLOAD/scripts" ] \
   && [ -z "$(find "$PAYLOAD_TARGET/.codex" -type d -empty)" ]; then pass
else fail "edited payload removal policy failed: $OUT"; fi

# Seed the pre-#254 deployed state into an installed target: the one-line pointer block
# (hash recorded as agents_block_hash) and a manifest-owned .codex/harness-instructions.md.
# $2 is the content written; the manifest records the hash of the pre-#254 original.
seed_pre_254() {
  python3 - "$1" "$2" <<'PY'
import hashlib, json, pathlib, sys
target = pathlib.Path(sys.argv[1])
written = sys.argv[2]
begin, end = "<!-- agent-harness:begin -->", "<!-- agent-harness:end -->"
old_block = begin + "\nRead `.codex/harness-instructions.md` before using the Agent Harness.\n" + end
agents = target / "AGENTS.md"
text = agents.read_text(encoding="utf-8")
start, finish = text.index(begin), text.index(end) + len(end)
agents.write_text(text[:start] + old_block + text[finish:], encoding="utf-8")
original = "# Agent Harness for Codex\n\nPre-#254 instruction fragment.\n"
(target / ".codex/harness-instructions.md").write_text(written, encoding="utf-8")
manifest = target / ".codex/.agent-harness/deployment-manifest.json"
data = json.loads(manifest.read_text())
data["agents_block_hash"] = hashlib.sha256(old_block.encode()).hexdigest()
data["project_files"][".codex/harness-instructions.md"] = hashlib.sha256(original.encode()).hexdigest()
manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
PY
}
PRE_254_TEXT=$(printf '# Agent Harness for Codex\n\nPre-#254 instruction fragment.\n')

UPGRADE_TARGET=$(new_dir)
UPGRADE_FAKE=$(new_dir)
make_fake_codex "$UPGRADE_FAKE"
cp "$FIXTURES/custom-AGENTS.md" "$UPGRADE_TARGET/AGENTS.md"
run_install "$UPGRADE_TARGET" "$UPGRADE_FAKE" --yes
seed_pre_254 "$UPGRADE_TARGET" "$PRE_254_TEXT
"

STUB_SOURCE=$(new_dir)
mkdir -p "$STUB_SOURCE/scripts"
cp "$ROOT/scripts/deploy-codex-adapter.sh" "$STUB_SOURCE/scripts/"
cat > "$STUB_SOURCE/scripts/render_codex_adapter.py" <<EOF
import pathlib, subprocess, sys
output = sys.argv[sys.argv.index("--output") + 1]
subprocess.run([sys.executable, "$ROOT/scripts/render_codex_adapter.py",
                "--root", "$ROOT", "--output", output], check=True)
pathlib.Path(output, "agents-block.md").unlink()
EOF
BEFORE_STUB=$(snapshot "$UPGRADE_TARGET")
AGENTS_BEFORE_STUB=$(shasum -a 256 "$UPGRADE_TARGET/AGENTS.md")
OUT=$(FAKE_CODEX_LOG="$UPGRADE_FAKE/codex.log" \
  FAKE_CODEX_FAIL_MARKER="$UPGRADE_FAKE/fail-once" \
  PATH="$UPGRADE_FAKE/bin:$PATH" \
  bash "$INSTALL" --source "$STUB_SOURCE" --directory "$UPGRADE_TARGET" \
    --codex-bin "$UPGRADE_FAKE/bin/codex" --codex-home "$UPGRADE_FAKE/home" --yes 2>&1)
RC=$?
t "a missing rendered block file fails closed before any project write"
if [ "$RC" -ne 0 ] \
   && printf '%s\n' "$OUT" | grep -qF 'rendered AGENTS.md block is missing' \
   && [ "$(snapshot "$UPGRADE_TARGET")" = "$BEFORE_STUB" ] \
   && [ "$(shasum -a 256 "$UPGRADE_TARGET/AGENTS.md")" = "$AGENTS_BEFORE_STUB" ]; then pass
else fail "rc=$RC or target changed: $OUT"; fi

run_install "$UPGRADE_TARGET" "$UPGRADE_FAKE" --yes
t "upgrade from the pre-#254 one-line block replaces it and prunes the unchanged retired file"
if [ "$RC" -eq 0 ] \
   && ! grep -qF 'Read `.codex/harness-instructions.md`' "$UPGRADE_TARGET/AGENTS.md" \
   && agents_block "$UPGRADE_TARGET/AGENTS.md" | grep -qxF '# Behavioral Guidelines' \
   && [ ! -e "$UPGRADE_TARGET/AGENTS.md.harness-incoming" ] \
   && [ ! -e "$UPGRADE_TARGET/.codex/harness-instructions.md" ] \
   && ! grep -qF 'harness-instructions.md' "$UPGRADE_TARGET/.codex/.agent-harness/deployment-manifest.json"; then pass
else fail "pre-#254 upgrade failed: $OUT"; fi

EDITED_TARGET=$(new_dir)
EDITED_FAKE=$(new_dir)
make_fake_codex "$EDITED_FAKE"
run_install "$EDITED_TARGET" "$EDITED_FAKE" --yes
seed_pre_254 "$EDITED_TARGET" "LOCAL RETIRED EDIT
"
run_install "$EDITED_TARGET" "$EDITED_FAKE" --yes
t "upgrade keeps an edited retired harness-instructions.md and still replaces the block"
if [ "$RC" -eq 0 ] \
   && grep -qF 'LOCAL RETIRED EDIT' "$EDITED_TARGET/.codex/harness-instructions.md" \
   && printf '%s\n' "$OUT" | grep -qF 'preserved edited retired file .codex/harness-instructions.md' \
   && agents_block "$EDITED_TARGET/AGENTS.md" | grep -qxF '# Behavioral Guidelines'; then pass
else fail "edited retired file policy failed: $OUT"; fi

OVERRIDE_TARGET=$(new_dir)
OVERRIDE_FAKE=$(new_dir)
make_fake_codex "$OVERRIDE_FAKE"
printf '# Local override\n' > "$OVERRIDE_TARGET/AGENTS.override.md"
run_install "$OVERRIDE_TARGET" "$OVERRIDE_FAKE" --yes
t "a root AGENTS.override.md prints a non-fatal warning and the block is still written"
if [ "$RC" -eq 0 ] \
   && printf '%s\n' "$OUT" | grep -qF 'AGENTS.override.md' \
   && grep -qF '<!-- agent-harness:begin -->' "$OVERRIDE_TARGET/AGENTS.md"; then pass
else fail "override warning missing: $OUT"; fi

LARGE_TARGET=$(new_dir)
LARGE_FAKE=$(new_dir)
make_fake_codex "$LARGE_FAKE"
python3 -c 'import sys; open(sys.argv[1], "w").write("# Large\n" + "x" * 79 + "\n" + ("y" * 79 + "\n") * 400)' \
  "$LARGE_TARGET/AGENTS.md"
run_install "$LARGE_TARGET" "$LARGE_FAKE" --yes
t "an AGENTS.md over 32 KiB after the write prints a non-fatal warning"
if [ "$RC" -eq 0 ] \
   && printf '%s\n' "$OUT" | grep -qF '32 KiB' \
   && grep -qF '<!-- agent-harness:end -->' "$LARGE_TARGET/AGENTS.md"; then pass
else fail "size warning missing: $OUT"; fi

finish
