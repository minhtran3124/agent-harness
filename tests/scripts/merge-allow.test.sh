#!/bin/bash
# Contract tests for plugins/harness/skills/setup/scripts/merge-allow.sh.
source "$(dirname "$0")/../lib.sh"

SCRIPT="$ROOT/plugins/harness/skills/setup/scripts/merge-allow.sh"
RULE='Bash(gh pr merge *)'

if ! command -v jq >/dev/null 2>&1; then
  t "merge-allow tests (need jq)"; skip "jq is not installed; install jq to run these cases"
  finish
fi

work() { local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); echo "$d"; }

t "a missing file (and its folder) is created with exactly the one rule"
d=$(work)
bash "$SCRIPT" "$d/.claude/settings.local.json" >/dev/null; rc=$?
if [ "$rc" -eq 0 ] && [ "$(jq -c .permissions.allow "$d/.claude/settings.local.json")" = "[\"$RULE\"]" ]; then pass
else fail "rc=$rc"; fi

t "existing allow entries keep their order first; deny and other keys are kept"
d=$(work)
printf '%s' '{"model":"opus","permissions":{"allow":["Bash(ls *)"],"deny":["Read(./.env)"]},"hooks":{"Stop":[]}}' > "$d/s.json"
bash "$SCRIPT" "$d/s.json" >/dev/null; rc=$?
if [ "$rc" -eq 0 ] && jq -e --arg r "$RULE" '.model == "opus" and .hooks == {"Stop":[]} and .permissions.deny[0] == "Read(./.env)" and .permissions.allow == ["Bash(ls *)", $r]' "$d/s.json" >/dev/null; then pass
else fail "rc=$rc file: $(cat "$d/s.json")"; fi

t "deny rules keep --admin, --auto and --delete-branch out of the wildcard allow rule"
d=$(work)
bash "$SCRIPT" "$d/s.json" >/dev/null
if jq -e '[.permissions.deny[] | select(startswith("Bash(gh pr merge"))] as $x
  | all(("--admin","--auto","--delete-branch"); . as $f | any($x[]; contains($f)))
  and (.permissions.deny | length == (unique | length))' "$d/s.json" >/dev/null; then pass
else fail "file: $(cat "$d/s.json")"; fi

t "a rule that is already present is not added twice"
d=$(work)
printf '%s' '{"permissions":{"allow":["Bash(gh pr merge *)","Bash(ls *)"]}}' > "$d/s.json"
bash "$SCRIPT" "$d/s.json" >/dev/null
if jq -e '.permissions.allow == ["Bash(gh pr merge *)","Bash(ls *)"]' "$d/s.json" >/dev/null; then pass
else fail "file: $(cat "$d/s.json")"; fi

t "a second run is a no-op: byte-identical file and the message says already present"
d=$(work)
bash "$SCRIPT" "$d/s.json" >/dev/null
cp "$d/s.json" "$d/before.json"
out=$(bash "$SCRIPT" "$d/s.json"); rc=$?
if [ "$rc" -eq 0 ] && cmp -s "$d/s.json" "$d/before.json" && printf '%s' "$out" | grep -q 'already present'; then pass
else fail "rc=$rc out=$out"; fi

t "invalid JSON exits 2 and leaves the file untouched"
d=$(work)
printf '%s' '{"permissions": {oops' > "$d/s.json"
cp "$d/s.json" "$d/before.json"
bash "$SCRIPT" "$d/s.json" >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 2 ] && cmp -s "$d/s.json" "$d/before.json"; then pass; else fail "rc=$rc"; fi

t "valid JSON that is not an object exits 2"
d=$(work)
printf '%s' '[1,2]' > "$d/s.json"
bash "$SCRIPT" "$d/s.json" >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 2 ]; then pass; else fail "rc=$rc"; fi

t "wrong-typed permissions, allow or deny exit 2 and leave the file untouched"
d=$(work); ok=1
for body in '{"permissions":[]}' '{"permissions":"x"}' '{"permissions":{"allow":"x"}}' '{"permissions":{"deny":{}}}' '{"permissions":false}' '{"permissions":{"allow":false}}' '{"permissions":{"deny":false}}'; do
  printf '%s' "$body" > "$d/s.json"
  bash "$SCRIPT" "$d/s.json" >/dev/null 2>&1; rc=$?
  if [ "$rc" -ne 2 ] || [ "$(cat "$d/s.json")" != "$body" ]; then ok=0; echo "body=$body rc=$rc"; fi
done
if [ "$ok" -eq 1 ]; then pass; else fail "wrong exit or file changed"; fi

t "a write keeps the file mode and a symlink, and leaves no temp file"
d=$(work)
printf '%s' '{"model":"sonnet"}' > "$d/real.json"
chmod 0640 "$d/real.json"
ln -s real.json "$d/link.json"
bash "$SCRIPT" "$d/link.json" >/dev/null; rc=$?
mode=$(ls -l "$d/real.json" | cut -c1-10)
if [ "$rc" -eq 0 ] && [ -L "$d/link.json" ] && [ "$mode" = "-rw-r-----" ] \
   && jq -e --arg r "$RULE" '.permissions.allow == [$r]' "$d/real.json" >/dev/null \
   && [ "$(ls -A "$d" | wc -l | tr -d ' ')" = "2" ]; then pass
else fail "rc=$rc mode=$mode files=$(ls -A "$d" | tr '\n' ' ')"; fi

t "--dry-run prints a diff naming the rule and leaves an existing file unchanged"
d=$(work)
printf '%s' '{"model":"sonnet"}' > "$d/s.json"
cp "$d/s.json" "$d/before.json"
out=$(bash "$SCRIPT" --dry-run "$d/s.json"); rc=$?
if [ "$rc" -eq 0 ] && cmp -s "$d/s.json" "$d/before.json" && printf '%s' "$out" | grep -qF "$RULE"; then pass
else fail "rc=$rc out=$out"; fi

t "--dry-run does not create a missing file"
d=$(work)
out=$(bash "$SCRIPT" --dry-run "$d/.claude/settings.local.json"); rc=$?
if [ "$rc" -eq 0 ] && [ ! -e "$d/.claude" ] && printf '%s' "$out" | grep -qF "$RULE"; then pass
else fail "rc=$rc, exists: $(ls -a "$d")"; fi

t "no argument prints usage and exits 1"
bash "$SCRIPT" >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 1 ]; then pass; else fail "rc=$rc"; fi

t "exit 3 when jq is missing"
skip "needs a PATH without jq; not simulated here (same as merge-deny.test.sh)"

t "the script uses no bash 4 feature"
if grep -nE 'declare -A|mapfile|readarray|\$\{[A-Za-z_]+(,,|\^\^)\}|&>>|\|&' "$SCRIPT"; then fail "bash 4 feature found"; else pass; fi

finish
