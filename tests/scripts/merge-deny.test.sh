#!/bin/bash
# Contract tests for plugins/harness/skills/setup/scripts/merge-deny.sh.
source "$(dirname "$0")/../lib.sh"

SCRIPT="$ROOT/plugins/harness/skills/setup/scripts/merge-deny.sh"

if ! command -v jq >/dev/null 2>&1; then
  t "merge-deny tests (need jq)"; skip "jq is not installed; install jq to run these cases"
  finish
fi

RULE_COUNT=34
work() { local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); echo "$d"; }
deny_len() { jq '.permissions.deny | length' "$1"; }

t "existing deny entries and other keys are preserved, with the overlap not duplicated"
d=$(work)
printf '%s' '{"model":"opus","permissions":{"allow":["Bash(ls *)"],"deny":["Read(./secrets/**)","Bash(git push -f*)"]},"hooks":{"Stop":[]}}' > "$d/s.json"
bash "$SCRIPT" "$d/s.json" >/dev/null; rc=$?
if [ "$rc" -eq 0 ] && jq -e '.model == "opus" and .permissions.allow == ["Bash(ls *)"] and .hooks == {"Stop":[]} and .permissions.deny[0] == "Read(./secrets/**)" and .permissions.deny[1] == "Bash(git push -f*)" and (.permissions.deny | length) == 35' "$d/s.json" >/dev/null; then pass
else fail "rc=$rc file: $(cat "$d/s.json")"; fi

t "no duplicate entries after the merge"
if [ "$(jq '.permissions.deny | length' "$d/s.json")" = "$(jq '.permissions.deny | unique | length' "$d/s.json")" ]; then pass; else fail "duplicates: $(jq -c .permissions.deny "$d/s.json")"; fi

t "a second run is a no-op: the file is byte-identical and the message says already present"
cp "$d/s.json" "$d/before.json"
out=$(bash "$SCRIPT" "$d/s.json"); rc=$?
if [ "$rc" -eq 0 ] && cmp -s "$d/s.json" "$d/before.json" && printf '%s' "$out" | grep -q 'already present'; then pass
else fail "rc=$rc out=$out"; fi

t "a missing file (and its folder) is created with all the rules"
d=$(work)
bash "$SCRIPT" "$d/.claude/settings.json" >/dev/null; rc=$?
if [ "$rc" -eq 0 ] && [ "$(deny_len "$d/.claude/settings.json")" = "$RULE_COUNT" ]; then pass
else fail "rc=$rc"; fi

t "a file with no permissions key keeps its keys and gains the rules"
d=$(work)
printf '%s' '{"model":"sonnet"}' > "$d/s.json"
bash "$SCRIPT" "$d/s.json" >/dev/null
if jq -e --argjson n "$RULE_COUNT" '.model == "sonnet" and (.permissions.deny | length) == $n' "$d/s.json" >/dev/null; then pass
else fail "file: $(cat "$d/s.json")"; fi

t "a permissions key without deny keeps the other permission keys"
d=$(work)
printf '%s' '{"permissions":{"allow":["Read"]}}' > "$d/s.json"
bash "$SCRIPT" "$d/s.json" >/dev/null
if jq -e '.permissions.allow == ["Read"] and (.permissions.deny | length) == 34' "$d/s.json" >/dev/null; then pass
else fail "file: $(cat "$d/s.json")"; fi

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

t "wrong-typed permissions or deny exit 2 and leave the file untouched"
d=$(work); ok=1
for body in '{"permissions":[]}' '{"permissions":"x"}' '{"permissions":{"deny":"x"}}' '{"permissions":{"deny":{}}}'; do
  printf '%s' "$body" > "$d/s.json"
  bash "$SCRIPT" "$d/s.json" >/dev/null 2>&1; rc=$?
  if [ "$rc" -ne 2 ] || [ "$(cat "$d/s.json")" != "$body" ]; then ok=0; echo "body=$body rc=$rc"; fi
done
if [ "$ok" -eq 1 ]; then pass; else fail "wrong exit or file changed"; fi

t "--dry-run prints a diff and leaves an existing file unchanged"
d=$(work)
printf '%s' '{"model":"sonnet"}' > "$d/s.json"
cp "$d/s.json" "$d/before.json"
out=$(bash "$SCRIPT" --dry-run "$d/s.json"); rc=$?
if [ "$rc" -eq 0 ] && cmp -s "$d/s.json" "$d/before.json" && printf '%s' "$out" | grep -q 'Read(./.env)'; then pass
else fail "rc=$rc out=$out"; fi

t "--dry-run does not create a missing file"
d=$(work)
bash "$SCRIPT" --dry-run "$d/.claude/settings.json" >/dev/null; rc=$?
if [ "$rc" -eq 0 ] && [ ! -e "$d/.claude" ]; then pass; else fail "rc=$rc, exists: $(ls -a "$d")"; fi

t "no argument prints usage and exits 1"
bash "$SCRIPT" >/dev/null 2>&1; rc=$?
if [ "$rc" -eq 1 ]; then pass; else fail "rc=$rc"; fi

t "the rule list equals the deny list in the repo's settings.json"
d=$(work)
bash "$SCRIPT" "$d/s.json" >/dev/null
if [ "$(jq -S '.permissions.deny | sort' "$d/s.json")" = "$(jq -S '.permissions.deny | sort' "$ROOT/settings.json")" ]; then pass
else fail "script rules differ from settings.json"; fi

t "the script uses no bash 4 feature"
if grep -nE 'declare -A|mapfile|readarray|\$\{[A-Za-z_]+(,,|\^\^)\}|&>>|\|&' "$SCRIPT"; then fail "bash 4 feature found"; else pass; fi

finish
