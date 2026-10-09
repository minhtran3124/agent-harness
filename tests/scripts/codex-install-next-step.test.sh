#!/usr/bin/env bash
# Contract tests for the Codex installer's tail: workflow structure, doctor mode, trust next step.
source "$(dirname "$0")/../lib.sh"

INSTALL="$ROOT/scripts/install-codex-harness.sh"
ROOT_P=$(cd "$ROOT" && pwd -P)

new_dir() {
  local directory
  directory=$(mktemp -d)
  _CLEANUP_DIRS+=("$directory")
  (cd "$directory" && pwd -P)
}

make_fake_codex() {
  local directory=$1
  mkdir -p "$directory/bin" "$directory/home"
  cat > "$directory/bin/codex" <<'EOF'
#!/bin/bash
printf '%s\n' "$*" >> "$FAKE_CODEX_LOG"
printf '{"ok":true}\n'
EOF
  chmod +x "$directory/bin/codex"
  : > "$directory/codex.log"
}

run_install() { # run_install <source> <target> <fake> [args...]
  local source=$1 target=$2 fake=$3
  shift 3
  OUT=$(FAKE_CODEX_LOG="$fake/codex.log" \
    PATH="$fake/bin:$PATH" \
    bash "$INSTALL" --source "$source" --directory "$target" \
      --codex-bin "$fake/bin/codex" --codex-home "$fake/home" "$@" 2>&1)
  RC=$?
}

has_line() { printf '%s\n' "$OUT" | grep -qF -- "$1"; }

FAKE=$(new_dir)
make_fake_codex "$FAKE"
NEXT_LINE='codex-install: next: start Codex in'

# 1. Fresh install: structure created, existing file kept, mode line and next step printed.
TARGET=$(new_dir)
mkdir -p "$TARGET/techstacks"
printf 'my own stack notes\n' > "$TARGET/techstacks/README.md"
TECH_BEFORE=$(shasum -a 256 "$TARGET/techstacks/README.md")
run_install "$ROOT" "$TARGET" "$FAKE" --yes
t "fresh install creates the workflow structure files"
if [ "$RC" -eq 0 ] && [ -f "$TARGET/specs/README.md" ] \
   && [ -f "$TARGET/docs/solutions/critical-patterns.md" ]; then pass
else fail "rc=$RC: $OUT"; fi

t "fresh install keeps a pre-existing techstacks/README.md byte-identical"
if [ "$(shasum -a 256 "$TARGET/techstacks/README.md")" = "$TECH_BEFORE" ]; then pass
else fail "techstacks/README.md changed"; fi

t "fresh install prints the doctor mode line"
if printf '%s\n' "$OUT" | grep -qE '^codex-install: doctor mode: [a-z]+'; then pass
else fail "no mode line: $OUT"; fi

t "fresh install prints the trust next step and the --source doctor command"
if has_line "$NEXT_LINE $TARGET, choose \"Review hooks\"" \
   && has_line "hooks do not run until trusted." \
   && has_line "codex-install: then run: python3 $ROOT_P/scripts/codex_harness_doctor.py --root $TARGET"; then pass
else fail "next-step lines missing: $OUT"; fi

t "fresh install creates agents/PROJECT.md from the template"
if [ "$RC" -eq 0 ] && cmp -s "$ROOT/agents/PROJECT.template.md" "$TARGET/agents/PROJECT.md" \
   && has_line 'codex-install: created agents/PROJECT.md from the template; fill in its Test execution section.'; then pass
else fail "rc=$RC: $OUT"; fi

# 1b. A target with a Claude copy gets a root copy seeded from it.
TARGET=$(new_dir)
mkdir -p "$TARGET/.claude/agents"
printf 'claude-side project notes\n' > "$TARGET/.claude/agents/PROJECT.md"
run_install "$ROOT" "$TARGET" "$FAKE" --yes
t "install seeds agents/PROJECT.md from .claude/agents/PROJECT.md"
if [ "$RC" -eq 0 ] && cmp -s "$TARGET/.claude/agents/PROJECT.md" "$TARGET/agents/PROJECT.md" \
   && has_line 'codex-install: created agents/PROJECT.md from .claude/agents/PROJECT.md; Codex agents read the root copy, so keep the two in step.'; then pass
else fail "rc=$RC: $OUT"; fi

# 1c. An existing agents/PROJECT.md is left byte-identical.
TARGET=$(new_dir)
mkdir -p "$TARGET/agents" "$TARGET/.claude/agents"
printf 'my filled-in project index\n' > "$TARGET/agents/PROJECT.md"
printf 'a different claude copy\n' > "$TARGET/.claude/agents/PROJECT.md"
PROJECT_BEFORE=$(shasum -a 256 "$TARGET/agents/PROJECT.md")
run_install "$ROOT" "$TARGET" "$FAKE" --yes
t "install leaves an existing agents/PROJECT.md byte-identical"
if [ "$RC" -eq 0 ] && [ "$(shasum -a 256 "$TARGET/agents/PROJECT.md")" = "$PROJECT_BEFORE" ] \
   && has_line 'codex-install: agents/PROJECT.md exists; left as is.' \
   && ! has_line 'codex-install: created agents/PROJECT.md'; then pass
else fail "rc=$RC: $OUT"; fi

# 2. Stub source: a doctor that exits 2 and no init-structure.sh — install still succeeds.
STUB_SOURCE=$(new_dir)
mkdir -p "$STUB_SOURCE/scripts"
cp "$ROOT/scripts/deploy-codex-adapter.sh" "$STUB_SOURCE/scripts/"
cat > "$STUB_SOURCE/scripts/render_codex_adapter.py" <<EOF
import subprocess, sys
output = sys.argv[sys.argv.index("--output") + 1]
subprocess.run([sys.executable, "$ROOT/scripts/render_codex_adapter.py",
                "--root", "$ROOT", "--output", output], check=True)
EOF
printf 'import sys\nsys.exit(2)\n' > "$STUB_SOURCE/scripts/codex_harness_doctor.py"
TARGET=$(new_dir)
run_install "$STUB_SOURCE" "$TARGET" "$FAKE" --yes
t "a failing doctor still installs with rc 0 and says it could not run"
if [ "$RC" -eq 0 ] && has_line 'codex-install: doctor could not run (exit 2)' \
   && ! has_line 'doctor mode:'; then pass
else fail "rc=$RC: $OUT"; fi

t "a source without init-structure.sh prints a skip line and still exits 0"
if [ "$RC" -eq 0 ] && has_line 'codex-install: init-structure.sh not in this source checkout; skipping the workflow structure.' \
   && [ ! -e "$TARGET/specs" ]; then pass
else fail "rc=$RC: $OUT"; fi

t "a source without agents/PROJECT.template.md prints a skip line and creates no agents/"
if [ "$RC" -eq 0 ] && has_line 'codex-install: agents/PROJECT.template.md not in this source checkout; skipping agents/PROJECT.md.' \
   && [ ! -e "$TARGET/agents" ]; then pass
else fail "rc=$RC: $OUT"; fi

printf 'print("{}")\n' > "$STUB_SOURCE/scripts/codex_harness_doctor.py"
TARGET=$(new_dir)
run_install "$STUB_SOURCE" "$TARGET" "$FAKE" --yes
t "a doctor that exits 0 without a mode record gets its own message"
if [ "$RC" -eq 0 ] && has_line 'codex-install: doctor output was not a mode record' \
   && ! has_line 'could not run (exit 0)'; then pass
else fail "rc=$RC: $OUT"; fi

# 3. --dry-run and --remove run neither step.
TARGET=$(new_dir)
run_install "$ROOT" "$TARGET" "$FAKE" --dry-run
t "--dry-run creates no specs/ and prints no doctor mode"
if [ "$RC" -eq 0 ] && [ ! -e "$TARGET/specs" ] && ! has_line 'doctor mode:' \
   && ! has_line "$NEXT_LINE"; then pass
else fail "rc=$RC: $OUT"; fi

t "--dry-run creates no agents/PROJECT.md"
if [ ! -e "$TARGET/agents/PROJECT.md" ] && ! has_line 'agents/PROJECT.md'; then pass
else fail "rc=$RC: $OUT"; fi

run_install "$ROOT" "$TARGET" "$FAKE" --yes
PROJECT_BEFORE=$(shasum -a 256 "$TARGET/agents/PROJECT.md" 2>/dev/null)
run_install "$ROOT" "$TARGET" "$FAKE" --remove --yes
t "--remove prints no doctor mode"
if [ "$RC" -eq 0 ] && ! has_line 'doctor mode:' && ! has_line "$NEXT_LINE"; then pass
else fail "rc=$RC: $OUT"; fi

t "--remove leaves agents/PROJECT.md in place"
if [ -n "$PROJECT_BEFORE" ] && [ "$(shasum -a 256 "$TARGET/agents/PROJECT.md")" = "$PROJECT_BEFORE" ] \
   && ! has_line 'agents/PROJECT.md'; then pass
else fail "rc=$RC: $OUT"; fi

# 4. Clone mode prints a clone-then-doctor command (the clone is deleted on exit).
BARE=$(new_dir)/harness.git
git init -q --bare "$BARE"
git -C "$ROOT" push -q "$BARE" HEAD:refs/heads/next-step-test
TARGET=$(new_dir)
OUT=$(FAKE_CODEX_LOG="$FAKE/codex.log" PATH="$FAKE/bin:$PATH" \
  CS_REPO_URL="file://$BARE" CS_BRANCH=next-step-test \
  bash "$INSTALL" --directory "$TARGET" \
    --codex-bin "$FAKE/bin/codex" --codex-home "$FAKE/home" --yes 2>&1)
RC=$?
t "clone mode prints the git clone && doctor command"
if [ "$RC" -eq 0 ] && has_line "codex-install: then run: git clone --depth 1 --branch next-step-test file://$BARE agent-harness && python3 agent-harness/scripts/codex_harness_doctor.py --root $TARGET"; then pass
else fail "rc=$RC: $OUT"; fi

# 5. An exported CODEX_BIN (no --codex-bin) still reaches the deploy and the doctor.
TARGET=$(new_dir)
: > "$FAKE/codex.log"
OUT=$(FAKE_CODEX_LOG="$FAKE/codex.log" CODEX_BIN="$FAKE/bin/codex" \
  bash "$INSTALL" --source "$ROOT" --directory "$TARGET" --codex-home "$FAKE/home" --yes 2>&1)
RC=$?
t "an exported CODEX_BIN is honoured when --codex-bin is not given"
if [ "$RC" -eq 0 ] && grep -qF 'doctor --json' "$FAKE/codex.log" && has_line 'codex-install: doctor mode: '; then pass
else fail "rc=$RC: $OUT"; fi

# 6. A target with a space: the printed command is shell-quoted and carries the Codex flags.
SPACED=$(new_dir)/"my project"
mkdir -p "$SPACED"
run_install "$ROOT" "$SPACED" "$FAKE" --yes
SPACED_P=$(cd "$SPACED" && pwd -P)
t "the printed doctor command is shell-quoted and keeps --codex-bin/--codex-home"
if [ "$RC" -eq 0 ] \
   && has_line "--root $(printf '%q' "$SPACED_P") --codex-bin $(printf '%q' "$FAKE/bin/codex") --codex-home $(printf '%q' "$FAKE/home")"; then pass
else fail "rc=$RC: $OUT"; fi

# 7. A relative --codex-bin still reaches Codex from the doctor (which runs with cwd=<target>).
TARGET=$(new_dir)
: > "$FAKE/codex.log"
OUT=$(cd "$FAKE" && FAKE_CODEX_LOG="$FAKE/codex.log" \
  bash "$INSTALL" --source "$ROOT" --directory "$TARGET" \
    --codex-bin ./bin/codex --codex-home "$FAKE/home" --yes 2>&1)
RC=$?
t "a relative --codex-bin is made absolute for the doctor"
if [ "$RC" -eq 0 ] && grep -qF 'doctor --json' "$FAKE/codex.log"; then pass
else fail "rc=$RC log=$(cat "$FAKE/codex.log"): $OUT"; fi

# agents exists as a regular file: the copy fails, the install still exits 0 and says so.
TARGET=$(new_dir)
: > "$TARGET/agents"
run_install "$ROOT" "$TARGET" "$FAKE" --yes
t "a failed agents/PROJECT.md copy is reported and does not fail the install"
if [ "$RC" -eq 0 ] && has_line 'codex-install: could not create agents/PROJECT.md' \
   && [ -f "$TARGET/agents" ]; then pass
else fail "rc=$RC: $OUT"; fi

# An untouched Claude copy (the harness's own PROJECT.md) is not used as the seed.
TARGET=$(new_dir)
mkdir -p "$TARGET/.claude/agents"
cp "$ROOT/agents/PROJECT.md" "$TARGET/.claude/agents/PROJECT.md"
run_install "$ROOT" "$TARGET" "$FAKE" --yes
t "an uncustomized .claude/agents/PROJECT.md falls back to the template"
if [ "$RC" -eq 0 ] && cmp -s "$ROOT/agents/PROJECT.template.md" "$TARGET/agents/PROJECT.md" \
   && has_line 'codex-install: created agents/PROJECT.md from the template; fill in its Test execution section.'; then pass
else fail "rc=$RC: $OUT"; fi

# An untouched copy from an older harness version (differs, but keeps the marker line) is not used.
TARGET=$(new_dir)
mkdir -p "$TARGET/.claude/agents"
{ cat "$ROOT/agents/PROJECT.md"; printf '\nolder-version line\n'; } > "$TARGET/.claude/agents/PROJECT.md"
run_install "$ROOT" "$TARGET" "$FAKE" --yes
t "an untouched older-version .claude/agents/PROJECT.md falls back to the template"
if [ "$RC" -eq 0 ] && cmp -s "$ROOT/agents/PROJECT.template.md" "$TARGET/agents/PROJECT.md" \
   && [ -z "$(find "$TARGET/agents" -name 'PROJECT.md.*')" ]; then pass
else fail "rc=$RC: $OUT"; fi

# A dangling agents/PROJECT.md symlink counts as existing; nothing is written through it.
TARGET=$(new_dir)
mkdir -p "$TARGET/agents"
ln -s ../missing-project.md "$TARGET/agents/PROJECT.md"
run_install "$ROOT" "$TARGET" "$FAKE" --yes
t "a dangling agents/PROJECT.md symlink is left alone and not written through"
if [ "$RC" -eq 0 ] && [ -L "$TARGET/agents/PROJECT.md" ] && [ ! -e "$TARGET/missing-project.md" ] \
   && has_line 'codex-install: agents/PROJECT.md exists; left as is.'; then pass
else fail "rc=$RC: $OUT"; fi

# Checked last, so every install above (stub, dry-run, remove, clone) is covered.
t "the installer makes no trust-changing Codex call and writes no Codex config"
if ! grep -qE '(^| )(trust|--trust[^ ]*)( |$)|trust_level' "$FAKE/codex.log" \
   && [ ! -e "$FAKE/home/config.toml" ]; then pass
else fail "codex log: $(cat "$FAKE/codex.log"); home: $(ls -A "$FAKE/home")"; fi

finish
