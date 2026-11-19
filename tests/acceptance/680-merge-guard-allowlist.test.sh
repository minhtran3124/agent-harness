#!/bin/bash
# Acceptance tests for #680: merge-guard denies merge-like quoted text unless the command is on a
# short allow list of commands that never run their arguments; backslash-newline is joined first.
# AC1 "Each command above is denied, as a test."
# AC2 (replay of session transcripts, PR states the number) is not testable from outside.
# AC3 "Every existing case in tests/hooks/merge-guard.test.sh still passes." (run that suite; not repeated here)
source "$(dirname "$0")/../lib.sh"

R=$(new_repo merge-guard.sh)
D=$(mktemp -d); _CLEANUP_DIRS+=("$D")
STUB="$D/bin"; mkdir -p "$STUB"
LOG="$D/gh.log"
cat > "$STUB/gh" <<'STUBEOF'
#!/bin/sh
d=$(dirname "$0")/..
echo "$*" >> "$d/gh.log"
case "$1 $2" in
  "pr view")
    case "$*" in
      *headRefOid*) printf '%s 0123456789abcdef0123456789abcdef01234567\n' "$(cat "$d/base")" ;;
      *) cat "$d/base" ;;
    esac ;;
  "repo view") echo main ;;
  *) exit 1 ;;
esac
STUBEOF
chmod +x "$STUB/gh"

setbase() { rm -f "$LOG"; printf '%s\n' "$1" > "$D/base"; }
g() {
  local json; json=$(jq -n --arg c "$1" '{tool_input:{command:$c},permission_mode:"default"}')
  OUT=$(cd "$R" && printf '%s' "$json" | env PATH="$STUB:$PATH" bash hooks/merge-guard.sh 2>&1); RC=$?
}
nocall() { [ ! -s "$LOG" ]; }

NL=$'\n'
MT='gh pr merge 7 --repo o/r'
HIDDEN_NAMES=(python3-c perl-e awk-system find-exec git-alias python3-bsnl-in-quotes)
HIDDEN_CMDS=(
  "python3 -c \"import os; os.system('$MT')\""
  "perl -e \"system('$MT')\""
  "awk 'BEGIN{system(\"$MT\")}'"
  "find . -exec sh -c \"$MT\" \\;"
  "git -c alias.x='!$MT' x"
  "python3 -c \"import os; os.system('gh pr mer\\${NL}ge 7 --repo o/r')\""
)

for base in main feat/x; do
  for i in "${!HIDDEN_CMDS[@]}"; do
    setbase "$base"
    t "AC1: hidden merge via ${HIDDEN_NAMES[$i]} is denied (PR base $base)"
    g "${HIDDEN_CMDS[$i]}"; assert_rc 2
  done
done

# Backslash-newline inside the word: joined, it is a plain merge. Into main (no pinned head) it is denied.
setbase main
t "AC1: backslash-newline inside 'merge' is joined and denied (PR base main)"
g "gh pr mer\\${NL}ge 7 --repo o/r --merge"; assert_rc 2

# Benign controls: merge text in quotes, command never runs it -> allowed, no gh call.
BENIGN=(
  "echo \"$MT\""
  "printf '%s\\n' \"$MT\""
  "grep -n \"$MT\" README.md"
  "rg \"$MT\" docs"
  "git commit -m \"docs: mention $MT\""
  "gh pr create --title x --body \"run $MT after review\""
  "gh issue comment 5 --body \"do not run $MT\""
)
for i in "${!BENIGN[@]}"; do
  setbase main
  t "AC1 (allow list): benign command $((i+1)) with merge text in quotes is allowed, no gh call"
  g "${BENIGN[$i]}"
  if [ "$RC" -eq 0 ] && nocall; then pass; else fail "rc=$RC gh-log: $(head -1 "$LOG" 2>/dev/null) out: $(echo "$OUT" | head -2 | tr '\n' ' ')"; fi
done

# A plain merge into feat/x stays allowed.
setbase feat/x
t "AC3: a plain gh pr merge into feat/x is still allowed"
g "$MT --merge"; assert_rc 0

finish
