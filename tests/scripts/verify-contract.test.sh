#!/bin/bash
# Contract for the harness:verify skill and its fixture. CI cannot drive a browser (the
# Playwright plugin exists only in a Claude session), so this checks the text contract,
# the no-secrets rule for verify.config.json, and that the fixture server starts.
source "$(dirname "$0")/../lib.sh"
SKILL="$ROOT/plugins/harness/skills/verify/SKILL.md"
RUN="$ROOT/plugins/harness/skills/verify/references/run-app.md"
FIX="$ROOT/tests/fixtures/verify-app"

t "verify SKILL.md stays under 600 words"
[ "$(wc -w < "$SKILL")" -lt 600 ] && pass || fail "word ceiling exceeded"

t "verify description has a use/when cue"
desc=$(awk 'NR==1&&/^---$/{inb=1;next} inb&&/^---$/{exit} inb&&/^description:/' "$SKILL")
echo "$desc" | grep -qiE '\b(use|when)\b' && pass || fail "no use/when cue in: $desc"

t "name verify exists only under plugins/harness/skills, never as a project skill"
if [ -f "$ROOT/plugins/harness/skills/verify/SKILL.md" ] && [ ! -e "$ROOT/.claude/skills/verify" ] \
   && grep -q '^name: verify$' "$SKILL"; then pass; else fail "verify skill misplaced"; fi

t "SKILL.md names the Playwright tools; run-app.md names them and the two login variables"
miss=""
for w in browser_navigate browser_snapshot browser_take_screenshot browser_console_messages \
         browser_run_code_unsafe; do
  grep -q "$w" "$SKILL" || miss="$miss $w"
done
for w in browser_navigate browser_snapshot browser_take_screenshot browser_console_messages \
         browser_run_code_unsafe VERIFY_USER VERIFY_PASSWORD; do
  grep -q "$w" "$RUN" || miss="$miss run:$w"
done
[ -z "$miss" ] && pass || fail "missing:$miss"

t "SKILL.md pins the ToolSearch fallback and the seven tool name tails"
miss=""
for w in ToolSearch browser_navigate browser_snapshot browser_fill_form browser_click \
         browser_take_screenshot browser_console_messages browser_run_code_unsafe; do
  grep -q "$w" "$SKILL" || miss="$miss $w"
done
[ -z "$miss" ] && pass || fail "fallback rule missing:$miss"

t "allowed-tools lists the form and click tools that Login needs"
tools=$(grep '^allowed-tools:' "$SKILL")
miss=""
for w in browser_fill_form browser_click; do
  echo "$tools" | grep -q "$w" || miss="$miss $w"
done
[ -z "$miss" ] && pass || fail "allowed-tools missing:$miss"

t "allowed-tools stays unchanged: no ToolSearch added (owner decision #439)"
grep '^allowed-tools:' "$SKILL" | grep -q 'ToolSearch' && fail "ToolSearch added to allowed-tools" || pass

# no_secrets <config>: pass when baseUrl and startCommand exist, loginEnv holds only
# upper-case variable names (a value such as "hunter2" fails), and env, if present, maps
# app variable names to $VERIFY_* references only.
no_secrets() {
  python3 - "$1" <<'PY'
import json, re, sys
c = json.load(open(sys.argv[1]))
names = c.get("loginEnv", [])
env = c.get("env", {})
ok = (c.get("baseUrl") and c.get("startCommand") and isinstance(names, list)
      and all(isinstance(n, str) and re.fullmatch(r"[A-Z][A-Z0-9_]*", n) for n in names)
      and isinstance(env, dict)
      and all(re.fullmatch(r"[A-Z][A-Z0-9_]*", k) and isinstance(v, str)
              and re.fullmatch(r"\$VERIFY_[A-Z_]+", v) for k, v in env.items())
      and set(c) <= {"baseUrl", "startCommand", "loginEnv", "env"})
sys.exit(0 if ok else 1)
PY
}

t "fixture verify.config.json holds env var names only"
no_secrets "$FIX/verify.config.json" && pass || fail "fixture config holds a non-name value"

t "a config that holds a value fails the no-secrets check"
bad=$(mktemp); _CLEANUP_DIRS+=("$bad")
printf '{"baseUrl":"http://x","startCommand":"y","loginEnv":["hunter2"]}' > "$bad"
no_secrets "$bad" && fail "secret value was accepted" || pass

t "a config whose env map holds a value fails the no-secrets check"
bad2=$(mktemp); _CLEANUP_DIRS+=("$bad2")
printf '{"baseUrl":"http://x","startCommand":"y","loginEnv":["VERIFY_USER"],"env":{"APP_PASSWORD":"hunter2"}}' > "$bad2"
no_secrets "$bad2" && fail "env literal value was accepted" || pass

t "fixture serve.sh is valid bash"
bash -n "$FIX/serve.sh" && pass || fail "bash -n failed"

t "fixture server starts the way the stage does: startCommand and env from the config, free PORT"
PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')
cfg="$FIX/verify.config.json"
startcmd=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["startCommand"])' "$cfg")
baseurl=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["baseUrl"].replace("${PORT}", sys.argv[2]))' "$cfg" "$PORT")
exports=$(python3 - "$cfg" <<'PY'
import json, shlex, sys
for k, v in json.load(open(sys.argv[1])).get("env", {}).items():
    print("export %s=\"%s\"" % (k, v))
PY
)
(
  export VERIFY_USER=dummy VERIFY_PASSWORD=dummy PORT
  eval "$exports"
  cd "$ROOT" && exec bash -c "$startcmd"
) >/dev/null 2>&1 &
SRV=$!
trap 'kill "$SRV" 2>/dev/null' EXIT
c=""
for _ in $(seq 1 30); do
  c=$(curl -s -o /dev/null -w '%{http_code}' "$baseurl/" 2>/dev/null)
  [ "$c" = 200 ] && break
  sleep 0.2
done
codes="$c $(curl -s -o /dev/null -w '%{http_code}' "$baseurl/login.html") $(curl -s -o /dev/null -w '%{http_code}' "$baseurl/profile.html")"
kill "$SRV" 2>/dev/null; wait "$SRV" 2>/dev/null
sleep 0.3
if [ "$codes" = "200 200 200" ] && ! curl -s -o /dev/null "$baseurl/" 2>/dev/null; then pass
else fail "codes=[$codes] or server still up"; fi

t "fixture config uses a \${PORT} baseUrl and an env map"
grep -q 'baseUrl.*127.0.0.1:\${PORT}' "$FIX/verify.config.json" && grep -q '"env"' "$FIX/verify.config.json" && pass || fail "fixture config lacks PORT placeholder or env"

REF="$ROOT/plugins/harness/skills/verify/references/config.md"
t "references/config.md pins env, PORT, throwaway consent, fill_form rule, ship.js note"
miss=""
for w in 'env' '${PORT}' 'throwaway credentials OK' 'browser_fill_form' 'browser_run_code_unsafe' 'openssl rand' 'ship.js'; do
  grep -qF -- "$w" "$REF" || miss="$miss $w"
done
[ -z "$miss" ] && pass || fail "reference missing:$miss"

t "run-app.md points to its sibling config.md, not references/config.md"
grep -q '`config.md`' "$RUN" && ! grep -q 'references/config.md' "$RUN" && [ -f "$(dirname "$RUN")/config.md" ] && pass || fail "pointer missing or wrong relative path"

t "storageState path is named and gitignored"
grep -q 'storageState.*\.playwright-mcp/' "$RUN" && grep -qx '\.playwright-mcp/' "$ROOT/.gitignore" && pass || fail "storageState path missing or not gitignored"

t "docs or config tickets skip Start config and never touch verify.config.json"
grep -q 'never read, create or commit' "$RUN" && pass || fail "skip rule for docs or config tickets missing"

t "Start config forbids an empty baseUrl or startCommand and reports BLOCKED"
grep -qi 'empty' "$RUN" && grep -i 'empty' "$RUN" | grep -q 'baseUrl' \
  && grep -i 'empty' -A2 "$RUN" | grep -q 'BLOCKED' && pass || fail "empty-value rule or BLOCKED missing"

t "Start config step 5 and Base mode say to resolve PORT and export env"
grep -q '^5\..*PORT.*export' "$RUN" && grep -A1 '^5\.' "$RUN" | grep -q 'env' \
  && grep -q 'Base mode' "$SKILL" && grep -A6 '^## Base mode' "$SKILL" | grep -q 'PORT' && pass || fail "PORT or env export missing in step 5 or Base mode"

t "Base mode keeps 'Do not retry' and 'the workflow decides'; Report leaves the GIF to the workflow"
grep -A8 '^## Base mode' "$SKILL" | grep -q 'Do not retry' && grep -A8 '^## Base mode' "$SKILL" | grep -q 'workflow decides' \
  && grep -q 'workflow builds the GIF' "$SKILL" && pass || fail "retry or workflow rule missing"

t "Step 5 says to resolve \$VERIFY_* references in env, not export them literally"
grep '^5\.' "$RUN" | grep -qF 'resolve `$VERIFY_*`' && pass || fail "env reference resolution missing"

t "SKILL.md tells the agent to read references/run-app.md before Start config, Login or Browser steps"
grep -q 'read `references/run-app.md`' "$SKILL" && grep -q 'Start config, Login or Browser steps' "$SKILL" && pass || fail "run-app.md pointer missing"

t "verify SKILL.md is at most 450 words"
[ "$(wc -w < "$SKILL")" -le 450 ] && pass || fail "over 450 words"

finish
