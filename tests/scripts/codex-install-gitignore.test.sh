#!/usr/bin/env bash
# Contract tests for the Codex installer's append-only .gitignore step.
source "$(dirname "$0")/../lib.sh"

INSTALL="$ROOT/scripts/install-codex-harness.sh"
LINE='.codex/.agent-harness/'

new_dir() {
  local directory
  directory=$(mktemp -d)
  _CLEANUP_DIRS+=("$directory")
  printf '%s\n' "$directory"
}

new_git_target() {
  local directory
  directory=$(new_dir)
  git -C "$directory" init -q
  git -C "$directory" config user.email test@test
  git -C "$directory" config user.name test
  printf '%s\n' "$directory"
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

run_install() {
  local target=$1 fake=$2
  shift 2
  OUT=$(FAKE_CODEX_LOG="$fake/codex.log" \
    PATH="$fake/bin:$PATH" \
    bash "$INSTALL" --source "$ROOT" --directory "$target" \
      --codex-bin "$fake/bin/codex" --codex-home "$fake/home" "$@" 2>&1)
  RC=$?
}

line_count() { # line_count <file> <exact line>
  if [ -f "$1" ]; then grep -cxF -- "$2" "$1"; else printf '0\n'; fi
}

FAKE=$(new_dir)
make_fake_codex "$FAKE"

# 1. Fresh repo: appended once, still once after a reinstall.
TARGET=$(new_git_target)
run_install "$TARGET" "$FAKE" --yes
t "fresh install appends .codex/.agent-harness/ to .gitignore"
if [ "$RC" -eq 0 ] && [ "$(line_count "$TARGET/.gitignore" "$LINE")" = "1" ]; then pass
else fail "rc=$RC count=$(line_count "$TARGET/.gitignore" "$LINE"): $OUT"; fi

run_install "$TARGET" "$FAKE" --yes
t "reinstall keeps exactly one .codex/.agent-harness/ line"
if [ "$RC" -eq 0 ] && [ "$(line_count "$TARGET/.gitignore" "$LINE")" = "1" ]; then pass
else fail "rc=$RC count=$(line_count "$TARGET/.gitignore" "$LINE"): $OUT"; fi

# 2. An existing scoping line is left as is.
for existing in '.codex/' '/.codex/.agent-harness' '.codex/.agent-harness/' '.codex' '!.codex/.agent-harness/'; do
  TARGET=$(new_git_target)
  printf 'node_modules/\n%s\n' "$existing" > "$TARGET/.gitignore"
  BEFORE=$(cat "$TARGET/.gitignore")
  run_install "$TARGET" "$FAKE" --yes
  t "existing '$existing' line is left as is and nothing is appended"
  if [ "$RC" -eq 0 ] && [ "$(cat "$TARGET/.gitignore")" = "$BEFORE" ]; then pass
  else fail "rc=$RC .gitignore now: $(cat "$TARGET/.gitignore"): $OUT"; fi
done

# 2b. A negated PARENT (`!/.codex/`, used to keep .codex/config.toml tracked) is not a decision
# about .agent-harness: the line is still appended, so payload .py files end up ignored.
TARGET=$(new_git_target)
printf '/.*\n!/.codex/\n' > "$TARGET/.gitignore"
run_install "$TARGET" "$FAKE" --yes
t "negated parent '!/.codex/' still gets .codex/.agent-harness/ appended and ignored"
mkdir -p "$TARGET/.codex/.agent-harness/payload/scripts"
: > "$TARGET/.codex/.agent-harness/payload/scripts/probe.py"
if [ "$RC" -eq 0 ] && [ "$(line_count "$TARGET/.gitignore" "$LINE")" = "1" ] \
   && [ -z "$(git -C "$TARGET" ls-files --others --exclude-standard -- .codex/.agent-harness)" ]; then pass
else fail "rc=$RC .gitignore now: $(cat "$TARGET/.gitignore"): $OUT"; fi

# 2c. Rule order matters: `.codex/` then `!.codex/` leaves the parent re-included, so the line
# must still be appended (last matching rule wins; a regex over lines cannot see this).
TARGET=$(new_git_target)
printf '.codex/\n!.codex/\n' > "$TARGET/.gitignore"
run_install "$TARGET" "$FAKE" --yes
t "'.codex/' then '!.codex/' still gets .codex/.agent-harness/ appended"
if [ "$RC" -eq 0 ] && [ "$(line_count "$TARGET/.gitignore" "$LINE")" = "1" ] \
   && git -C "$TARGET" check-ignore -q .codex/.agent-harness/payload/scripts/probe.py; then pass
else fail "rc=$RC .gitignore now: $(cat "$TARGET/.gitignore"): $OUT"; fi

# 3. --dry-run writes no .gitignore.
TARGET=$(new_git_target)
run_install "$TARGET" "$FAKE" --dry-run
t "--dry-run leaves .gitignore absent"
if [ "$RC" -eq 0 ] && [ ! -e "$TARGET/.gitignore" ]; then pass
else fail "rc=$RC: $OUT"; fi

# 4. An already-tracked directory gets a warning and no edit.
TARGET=$(new_git_target)
mkdir -p "$TARGET/.codex/.agent-harness"
printf 'tracked\n' > "$TARGET/.codex/.agent-harness/committed.txt"
git -C "$TARGET" add -f .codex/.agent-harness/committed.txt
git -C "$TARGET" commit -q -m 'track agent-harness state'
run_install "$TARGET" "$FAKE" --yes --overwrite-conflicts
t "tracked .codex/.agent-harness/ warns and leaves .gitignore unedited"
if [ ! -e "$TARGET/.gitignore" ] && printf '%s' "$OUT" | grep -qF '.codex/.agent-harness/ is tracked'; then pass
else fail "rc=$RC .gitignore exists=$([ -e "$TARGET/.gitignore" ] && echo yes || echo no): $OUT"; fi

# 5. --remove leaves the line in place.
TARGET=$(new_git_target)
run_install "$TARGET" "$FAKE" --yes
run_install "$TARGET" "$FAKE" --remove --yes
t "--remove leaves the .codex/.agent-harness/ line in place"
if [ "$RC" -eq 0 ] && [ "$(line_count "$TARGET/.gitignore" "$LINE")" = "1" ]; then pass
else fail "rc=$RC count=$(line_count "$TARGET/.gitignore" "$LINE"): $OUT"; fi

finish
