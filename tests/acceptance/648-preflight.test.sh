#!/bin/bash
# Acceptance tests for #648: autopilot preflight, drafted Verify: row, worktree setup.
# preflight.sh runs with a private fake PATH (git symlink, stubs for gh/jq/python3), so the cases do
# not depend on the host's gh login or on jq. The ship.js cases drive the script with a stub agent().
# The ship.js cases pf1-pf3 and tests/scripts/preflight.test.sh are written by the implementer (AC8).
source "$(dirname "$0")/../lib.sh"

PRE="$ROOT/plugins/harness/skills/pd-autopilot/scripts/preflight.sh"
SKILL="$ROOT/plugins/harness/skills/pd-autopilot/SKILL.md"
SHIP="$ROOT/plugins/harness/workflows/ship.js"
BASH_BIN=$(command -v bash)
GIT_BIN=$(command -v git)

W=$(mktemp -d); _CLEANUP_DIRS+=("$W")

# mkenv <name> <with_jq 0|1> <gh_auth_rc> <specs_ignored 0|1> -> sets BIN and REPO
mkenv() {
  local d="$W/$1"; mkdir -p "$d/bin" "$d/repo"
  BIN="$d/bin"; REPO="$d/repo"
  ln -s "$GIT_BIN" "$BIN/git"
  printf '#!%s\nexit 0\n' "$BASH_BIN" > "$BIN/python3"
  printf '#!%s\n[ "$1 $2" = "auth status" ] && exit %s\nexit 0\n' "$BASH_BIN" "$3" > "$BIN/gh"
  [ "$2" = 1 ] && printf '#!%s\nexit 0\n' "$BASH_BIN" > "$BIN/jq"
  chmod +x "$BIN"/* 2>/dev/null
  git -C "$REPO" init -q
  [ "$4" = 1 ] && printf '/specs/\n' > "$REPO/.gitignore"
  return 0
}
runpre() { OUT=$(PATH="$BIN" "$BASH_BIN" "$PRE" "$@" 2>&1); RC=$?; }

t "AC1: jq missing from PATH -> exit 1 and 'missing: jq'"
mkenv nojq 0 0 1; runpre --repo-dir "$REPO"
[ "$RC" = 1 ] && echo "$OUT" | grep -qF 'missing: jq' && pass || fail "rc=$RC out=$OUT"

t "AC2: all checks pass -> exit 0 and 'preflight: ok'"
mkenv allok 1 0 1; runpre --repo-dir "$REPO"
[ "$RC" = 0 ] && echo "$OUT" | grep -qF 'preflight: ok' && pass || fail "rc=$RC out=$OUT"

t "AC9: gh auth failing -> exit 1 and 'missing: gh auth'"
mkenv noauth 1 1 1; runpre --repo-dir "$REPO"
[ "$RC" = 1 ] && echo "$OUT" | grep -qF 'missing: gh auth' && pass || fail "rc=$RC out=$OUT"

t "AC9: specs/ not ignored -> exit 1 and 'missing: specs/ ignore'"
mkenv noign 1 0 0; runpre --repo-dir "$REPO"
[ "$RC" = 1 ] && echo "$OUT" | grep -qF 'missing: specs/ ignore' && pass || fail "rc=$RC out=$OUT"

t "AC9: preflight without --repo-dir exits 2"
mkenv nodir 1 0 1; runpre
[ "$RC" = 2 ] && pass || fail "rc=$RC out=$OUT"

t "AC9: preflight writes nothing into the repo"
mkenv ro 1 0 0; before=$(git -C "$REPO" status --porcelain; ls -A "$REPO"); runpre --repo-dir "$REPO"
after=$(git -C "$REPO" status --porcelain; ls -A "$REPO")
[ "$RC" = 1 ] && [ "$before" = "$after" ] && pass || fail "rc=$RC (want 1) or repo changed"

t "AC9: SKILL.md allowed-tools has the preflight Bash rule"
grep -qF 'Bash(bash ${CLAUDE_SKILL_DIR}/scripts/preflight.sh*)' "$SKILL" && pass || fail "rule missing"

t "AC9: SKILL.md step 1 runs preflight.sh --repo-dir"
grep -qE 'preflight\.sh --repo-dir' "$SKILL" && pass || fail "no run line"

t "AC6: 'Verify: row drafted' occurs once in autopilot SKILL.md"
n=$(grep -c 'Verify: row drafted' "$SKILL")
[ "$n" = 1 ] && pass || fail "grep -c printed: $n"

# ---- ship.js cases: a stub agent records every prompt -------------------------------------------
cat > "$W/driver.js" <<'JS'
const fs = require('fs')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta =', 'const meta =')
const extra = process.argv[3] ? JSON.parse(process.argv[3]) : {}
const args = { repo: 'o/r', repoDir: '/repo', pluginDir: '/plug', remote: 'origin', base: 'v5.0.0', slug: 'ms',
  tickets: [{ n: 1, title: 'Add the thing', depth: 'S', group: 1, deps: [], confirmed: '' }],
  testCmd: 'run-related', lintCmd: 'lint-it', fullTestCmd: 'run-all', advisorModel: 'opus', noAsk: false, local: false, ...extra }
const prompts = []
const answer = { status: 'ok', summary: 'did it', decisions: [], goal: 'g', acceptance: [], files: [], commits: [], verify: [],
  plan_steps: [{ title: 'step', files: [], done_when: 'true' }], plan_md: 'P', worktree: '/wt/1', branch: 'b1', passed: true,
  kind: 'BE', failedStep: '', consoleErrors: [], stills: [], report: 'R', pr: 101, url: 'https://x/pull/101' }
const agent = async (prompt, opts = {}) => { prompts.push({ label: opts.label || '', prompt }); return { ...answer } }
const parallel = th => Promise.all(th.map(async f => { try { return await f() } catch (e) { return null } }))
let err = null
;(async () => {
  try {
    await new AsyncFunction('agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget', 'workflow', src)(
      agent, parallel, async () => { throw new Error('x') }, () => {}, () => {}, args,
      { total: null, spent: () => 0, remaining: () => Infinity }, async () => { throw new Error('no nested') })
  } catch (e) { err = String(e && e.message) }
  process.stdout.write(JSON.stringify({ err, prompts }))
})()
JS

drive() { node "$W/driver.js" "$SHIP" "$1" 2>/dev/null; }

if ! command -v node >/dev/null 2>&1; then
  t "AC3/AC4/AC5: ship.js cases"; skip "no node"
else

t "AC3: worktreeSetup ['npm ci'] puts 'npm ci' after 'worktree add' in every worktree-creating prompt"
drive '{"worktreeSetup":["npm ci"]}' | node -e '
const d = JSON.parse(require("fs").readFileSync(0, "utf8"))
const wt = d.prompts.filter(p => p.prompt.includes("worktree add"))
if (!wt.length) { console.log("no worktree-creating prompt (err=" + d.err + ")"); process.exit(1) }
const bad = wt.filter(p => p.prompt.indexOf("npm ci", p.prompt.indexOf("worktree add")) < 0)
if (bad.length) { console.log("missing npm ci in: " + bad.map(p => p.label).join(", ")); process.exit(1) }
' && pass || fail "npm ci not after worktree add"

t "AC4: worktreeSetup as a string throws 'ship: args.worktreeSetup...'"
drive '{"worktreeSetup":"npm ci"}' | node -e '
const d = JSON.parse(require("fs").readFileSync(0, "utf8"))
if (!d.err || !d.err.startsWith("ship: args.worktreeSetup")) { console.log("err=" + d.err); process.exit(1) }
' && pass || fail "error text did not start with ship: args.worktreeSetup"

t "AC5: an implement prompt contains 'never run sudo'"
drive '{}' | node -e '
const d = JSON.parse(require("fs").readFileSync(0, "utf8"))
const imp = d.prompts.filter(p => /implement/.test(p.label))
if (!imp.length) { console.log("no implement prompt (err=" + d.err + ")"); process.exit(1) }
if (!imp.every(p => p.prompt.includes("never run sudo"))) process.exit(1)
' && pass || fail "implement prompt lacks 'never run sudo'"

fi

t "AC8: tests/scripts/preflight.test.sh exits 0"
(cd "$ROOT" && bash tests/scripts/preflight.test.sh >/dev/null 2>&1) && pass || fail "missing or failing"

t "AC8: harness.js prints PASS for pf1, pf2 and pf3"
n=$(cd "$ROOT" && node tests/workflows/harness.js 2>/dev/null | grep -cE '^PASS pf[1-3]:')
[ "$n" = 3 ] && pass || fail "grep -c printed: $n"

finish
