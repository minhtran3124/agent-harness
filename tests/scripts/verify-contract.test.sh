#!/bin/bash
# Contract for the harness:verify skill and its fixture. CI cannot drive a browser (the
# Playwright plugin exists only in a Claude session), so this checks the text contract,
# the no-secrets rule for verify.config.json, and that the fixture server starts.
source "$(dirname "$0")/../lib.sh"
SKILL="$ROOT/plugins/harness/skills/verify/SKILL.md"
FIX="$ROOT/tests/fixtures/verify-app"

t "verify SKILL.md stays under 600 words"
[ "$(wc -w < "$SKILL")" -lt 600 ] && pass || fail "word ceiling exceeded"

t "verify description has a use/when cue"
desc=$(awk 'NR==1&&/^---$/{inb=1;next} inb&&/^---$/{exit} inb&&/^description:/' "$SKILL")
echo "$desc" | grep -qiE '\b(use|when)\b' && pass || fail "no use/when cue in: $desc"

t "name verify exists only under plugins/harness/skills, never as a project skill"
if [ -f "$ROOT/plugins/harness/skills/verify/SKILL.md" ] && [ ! -e "$ROOT/.claude/skills/verify" ] \
   && grep -q '^name: verify$' "$SKILL"; then pass; else fail "verify skill misplaced"; fi

t "SKILL.md names the five Playwright tools and the two login variables"
miss=""
for w in browser_navigate browser_snapshot browser_take_screenshot browser_console_messages \
         browser_run_code_unsafe VERIFY_USER VERIFY_PASSWORD; do
  grep -q "$w" "$SKILL" || miss="$miss $w"
done
[ -z "$miss" ] && pass || fail "missing:$miss"

t "allowed-tools lists the form and click tools that Login needs"
tools=$(grep '^allowed-tools:' "$SKILL")
miss=""
for w in browser_fill_form browser_click; do
  echo "$tools" | grep -q "$w" || miss="$miss $w"
done
[ -z "$miss" ] && pass || fail "allowed-tools missing:$miss"

# no_secrets <config>: pass when baseUrl and startCommand exist and loginEnv holds only
# upper-case variable names (a value such as "hunter2" fails).
no_secrets() {
  python3 - "$1" <<'PY'
import json, re, sys
c = json.load(open(sys.argv[1]))
names = c.get("loginEnv", [])
ok = (c.get("baseUrl") and c.get("startCommand") and isinstance(names, list)
      and all(isinstance(n, str) and re.fullmatch(r"[A-Z][A-Z0-9_]*", n) for n in names)
      and set(c) <= {"baseUrl", "startCommand", "loginEnv"})
sys.exit(0 if ok else 1)
PY
}

t "fixture verify.config.json holds env var names only"
no_secrets "$FIX/verify.config.json" && pass || fail "fixture config holds a non-name value"

t "a config that holds a value fails the no-secrets check"
bad=$(mktemp); _CLEANUP_DIRS+=("$bad")
printf '{"baseUrl":"http://x","startCommand":"y","loginEnv":["hunter2"]}' > "$bad"
no_secrets "$bad" && fail "secret value was accepted" || pass

t "fixture serve.sh is valid bash"
bash -n "$FIX/serve.sh" && pass || fail "bash -n failed"

t "fixture server starts, answers / and /login.html, then stops"
PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')
VERIFY_USER=dummy VERIFY_PASSWORD=dummy PORT="$PORT" bash "$FIX/serve.sh" >/dev/null 2>&1 &
SRV=$!
trap 'kill "$SRV" 2>/dev/null' EXIT
codes=""
for _ in $(seq 1 30); do
  c=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/" 2>/dev/null)
  [ "$c" = 200 ] && break
  sleep 0.2
done
codes="$c $(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/login.html")"
kill "$SRV" 2>/dev/null; wait "$SRV" 2>/dev/null
sleep 0.3
if [ "$codes" = "200 200" ] && ! curl -s -o /dev/null "http://127.0.0.1:$PORT/" 2>/dev/null; then pass
else fail "codes=[$codes] or server still up"; fi

finish
