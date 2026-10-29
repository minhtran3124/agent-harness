#!/bin/bash
# Contract test: /harness:setup proposes a .harness-sandbox from the audit and asks before writing.
source "$(dirname "$0")/../lib.sh"

SKILL="$ROOT/plugins/harness/skills/setup/SKILL.md"
SCRIPT="$ROOT/plugins/harness/scripts/provision-sandbox.sh"
flat=$(tr '\n' ' ' < "$SKILL" | tr -s ' ')

t "audit exits 1 and lists ignored paths nobody decided as unknown"
d=$(new_repo)
printf 'stray/\nout/\n' > "$d/.gitignore"
printf 'tracked\n' > "$d/app.txt"
git -C "$d" add .gitignore app.txt
git -C "$d" commit -qm seed
mkdir -p "$d/stray" "$d/out"; printf 'x\n' > "$d/stray/a"; printf 'y\n' > "$d/out/b"
OUT=$(bash "$SCRIPT" --audit "$d" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && printf '%s\n' "$OUT" | grep 'unknown' | grep -q 'stray' \
   && printf '%s\n' "$OUT" | grep 'unknown' | grep -q 'out'; then pass; else fail "rc=$RC out: $OUT"; fi

t "SKILL.md runs the audit on the project and names the manifest"
if printf '%s' "$flat" | grep -qF 'provision-sandbox.sh --audit' && printf '%s' "$flat" | grep -qF '.harness-sandbox'; then pass
else fail "the audit step is missing"; fi

t "SKILL.md writes the manifest only after the owner agrees (AskUserQuestion)"
if printf '%s' "$flat" | grep -qF 'AskUserQuestion' && printf '%s' "$flat" | grep -qiF 'only after the owner agrees'; then pass
else fail "the agreement gate is missing"; fi

t "SKILL.md never overwrites an existing manifest: appends only the missing lines"
if printf '%s' "$flat" | grep -qiF 'never overwrite' && printf '%s' "$flat" | grep -qF 'append' \
   && printf '%s' "$flat" | grep -qF 'only the missing lines'; then pass
else fail "the no-overwrite rule is missing"; fi

t "SKILL.md leaves unknown paths to the owner and says the owner commits the file"
if printf '%s' "$flat" | grep -qF 'unknown' && printf '%s' "$flat" | grep -qF 'commits'; then pass
else fail "unknown handling or commit note is missing"; fi

finish
