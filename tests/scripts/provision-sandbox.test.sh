#!/bin/bash
# Contract test: provision-sandbox.sh builds a worktree that carries the untracked environment.
source "$(dirname "$0")/../lib.sh"
SCRIPT="$ROOT/plugins/harness/scripts/provision-sandbox.sh"

# mk_repo → a seeded repo whose ignored files (.env, node_modules) exist only in the main checkout.
mk_repo() {
  local d; d=$(new_repo)
  _CLEANUP_DIRS+=("$(dirname "$d")/.ship-$(basename "$d")")
  printf '.env\nnode_modules/\nCLAUDE.local.md\n' > "$d/.gitignore"
  printf 'tracked\n' > "$d/app.txt"
  git -C "$d" add .gitignore app.txt
  git -C "$d" commit -qm seed
  printf 'SECRET=1\n' > "$d/.env"
  printf 'local rules\n' > "$d/CLAUDE.local.md"
  mkdir -p "$d/node_modules/pkg"; printf 'x\n' > "$d/node_modules/pkg/index.js"
  echo "$d"
}
prov() { OUT=$(bash "$SCRIPT" "$@" 2>&1); RC=$?; }

t "manifest copy and link bring ignored files into the sandbox"
repo=$(mk_repo)
printf '# env\ncopy .env\ncopy CLAUDE.local.md\nlink node_modules\nrequire .env\n' > "$repo/.harness-sandbox"
prov "$repo" run1 3 "my ticket" --branch feat/t3
dir="$(dirname "$repo")/.ship-$(basename "$repo")/run1-t3-my-ticket"
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q '"status":"ready"' && [ "$(cat "$dir/.env")" = SECRET=1 ] \
  && [ -f "$dir/CLAUDE.local.md" ] && [ -L "$dir/node_modules" ] && [ -f "$dir/node_modules/pkg/index.js" ]; then pass; else fail "rc=$RC $OUT"; fi

t "the sandbox is on the requested branch and git status stays clean"
if [ "$(git -C "$dir" symbolic-ref --short HEAD)" = feat/t3 ] && [ -z "$(git -C "$dir" status --porcelain)" ]; then pass
else fail "branch/status: $(git -C "$dir" status --porcelain | head -3)"; fi

t ".sandbox.json records the run, ticket, branch, created_at and a null pr; git status stays clean"
js="$dir/.sandbox.json"
if grep -q '"runId":"run1"' "$js" && grep -q '"ticket":{"n":3,"slug":"my-ticket"}' "$js" && grep -q '"branch":"feat/t3"' "$js" \
  && grep -qE '"created_at":"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"' "$js" && grep -q '"pr":null' "$js" \
  && [ -z "$(git -C "$dir" status --porcelain)" ]; then pass; else fail "$(cat "$js")"; fi

t "a re-run keeps the original created_at"
sed -i.bak 's/"created_at":"[^"]*"/"created_at":"2020-01-02T03:04:05Z"/' "$js"; rm -f "$js.bak"
prov "$repo" run1 3 "my ticket" --branch feat/t3
if grep -q '"created_at":"2020-01-02T03:04:05Z"' "$js"; then pass; else fail "$(cat "$js")"; fi

t "each ticket gets its own port block and DB name"
prov "$repo" run1 4 other --branch feat/t4
dir4="$(dirname "$repo")/.ship-$(basename "$repo")/run1-t4-other"
p3=$(sed -n 's/^SANDBOX_PORT=//p' "$dir/.sandbox.env"); p4=$(sed -n 's/^SANDBOX_PORT=//p' "$dir4/.sandbox.env")
d3=$(sed -n 's/^SANDBOX_DB_NAME=//p' "$dir/.sandbox.env"); d4=$(sed -n 's/^SANDBOX_DB_NAME=//p' "$dir4/.sandbox.env")
if [ "$p3" = 4030 ] && [ "$p4" = 4040 ] && [ "$d3" != "$d4" ]; then pass; else fail "ports $p3 $p4 dbs $d3 $d4"; fi

t "setup commands run in the sandbox and see the port variables"
repo=$(mk_repo)
printf 'setup echo "$SANDBOX_PORT" > port.out && pwd > cwd.out\n' > "$repo/.harness-sandbox"
prov "$repo" r 1 s --port-base 5000
dir="$(dirname "$repo")/.ship-$(basename "$repo")/r-t1-s"
if [ "$RC" -eq 0 ] && [ "$(cat "$dir/port.out")" = 5010 ] && [ "$(cat "$dir/cwd.out")" = "$(cd "$dir" && pwd)" ]; then pass; else fail "rc=$RC $OUT"; fi

t "a required path that nothing provides fails the run"
printf 'require .env.missing\n' > "$repo/.harness-sandbox"
prov "$repo" r 2 s
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'required path missing'; then pass; else fail "rc=$RC $OUT"; fi

t "a failing setup command fails the run and names the command"
printf 'setup exit 7\n' > "$repo/.harness-sandbox"
prov "$repo" r 5 s
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'setup failed: exit 7'; then pass; else fail "rc=$RC $OUT"; fi

t "absolute and parent-relative manifest paths are rejected"
printf 'copy ../outside\n' > "$repo/.harness-sandbox"
prov "$repo" r 6 s
rc1=$RC
printf 'copy /etc/passwd\n' > "$repo/.harness-sandbox"
prov "$repo" r 7 s
if [ "$rc1" -eq 1 ] && [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'unsafe'; then pass; else fail "rc=$rc1/$RC $OUT"; fi

t "running it again reuses the worktree and re-syncs files"
repo=$(mk_repo)
printf 'copy .env\n' > "$repo/.harness-sandbox"
prov "$repo" r 1 s --branch feat/again
printf 'copy CLAUDE.local.md\n' >> "$repo/.harness-sandbox"
prov "$repo" r 1 s --branch feat/again
dir="$(dirname "$repo")/.ship-$(basename "$repo")/r-t1-s"
if [ "$RC" -eq 0 ] && [ -f "$dir/CLAUDE.local.md" ]; then pass; else fail "rc=$RC $OUT"; fi

t "without a manifest the sandbox is a plain worktree and still ready"
repo=$(mk_repo)
prov "$repo" r 1 s
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q '"branch":"detached"'; then pass; else fail "rc=$RC $OUT"; fi

t "a detached sandbox records branch detached"
if grep -q '"branch":"detached"' "$(dirname "$repo")/.ship-$(basename "$repo")/r-t1-s/.sandbox.json"; then pass; else fail "detached"; fi

t "bad usage exits 2"
prov "$repo" r notanumber s
rc1=$RC
prov
if [ "$rc1" -eq 2 ] && [ "$RC" -eq 2 ]; then pass; else fail "rc=$rc1/$RC"; fi

t "an option without a value exits 2 instead of looping"
repo=$(mk_repo)
OUT=$(timeout 10 bash "$SCRIPT" "$repo" r 1 s --branch 2>&1); rc1=$?
OUT=$(timeout 10 bash "$SCRIPT" --audit "$repo" --max-kb 2>&1); RC=$?
if [ "$rc1" -eq 2 ] && [ "$RC" -eq 2 ]; then pass; else fail "rc=$rc1/$RC"; fi

# ---- --audit ----
# mk_audit_repo → ignored paths of every class: config, state, prod secret, regenerable, unrecognised.
mk_audit_repo() {
  local d; d=$(new_repo)
  printf '.env*\n*.db\nnode_modules/\n.next/\nout/\n' > "$d/.gitignore"
  printf 'x\n' > "$d/app.txt"; git -C "$d" add .gitignore app.txt; git -C "$d" commit -qm seed
  printf 'A=1\n' > "$d/.env"; printf 'P=1\n' > "$d/.env.prod"; printf 'db\n' > "$d/data.db"
  mkdir -p "$d/node_modules/p" "$d/.next" "$d/out" "$d/stray"; printf 'x\n' > "$d/node_modules/p/i.js"
  printf 'x\n' > "$d/.next/b"; printf 'x\n' > "$d/out/report.html"; printf 'u\n' > "$d/stray/notes.txt"
  echo "$d"
}
audit() { OUT=$(bash "$SCRIPT" --audit "$@" 2>&1); RC=$?; }

t "audit copies small config and state, skips regenerable dirs, flags prod and unrecognised paths"
repo=$(mk_audit_repo)
audit "$repo"
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -qE '^copy .*\.env  ' && echo "$OUT" | grep -qE '^copy .*data\.db' \
  && echo "$OUT" | grep -qE '^unknown .*\.env\.prod' && echo "$OUT" | grep -qE '^unknown .*out' \
  && ! echo "$OUT" | grep -q 'node_modules'; then pass; else fail "rc=$RC $OUT"; fi

t "audit --all lists the skipped paths too"
audit "$repo" --all
if echo "$OUT" | grep -qE '^skip .*node_modules' && echo "$OUT" | grep -qE '^skip .*\.next'; then pass; else fail "$OUT"; fi

t "manifest copy, link and skip lines settle every unknown, so the audit exits 0"
printf 'copy .env.prod\nskip out\n' > "$repo/.harness-sandbox"
audit "$repo"
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qE '^covered .*\.env\.prod' && echo "$OUT" | grep -q 'unknown 0'; then pass; else fail "rc=$RC $OUT"; fi

t "a config file above --max-kb is unknown, not copied"
head -c 3000 /dev/zero | tr '\0' x > "$repo/big.db"
audit "$repo" --max-kb 1
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -qE '^unknown .*big\.db.*over 1K'; then pass; else fail "rc=$RC $OUT"; fi

t "audit does not descend into untracked directories"
mkdir -p "$repo/scratch/node_modules" "$repo/scratch/.env"; printf 'x\n' > "$repo/scratch/untracked.txt"
audit "$repo" --all
if ! echo "$OUT" | grep -q 'scratch/node_modules' && echo "$OUT" | grep -qE '^skip .*scratch '; then pass; else fail "$OUT"; fi

t "audit changes nothing in the repo"
before=$(git -C "$repo" status --porcelain --ignored | sort | md5sum 2>/dev/null || git -C "$repo" status --porcelain --ignored | sort | md5 -q)
audit "$repo" >/dev/null
after=$(git -C "$repo" status --porcelain --ignored | sort | md5sum 2>/dev/null || git -C "$repo" status --porcelain --ignored | sort | md5 -q)
if [ "$before" = "$after" ]; then pass; else fail "status changed"; fi

t "audit usage errors exit 2"
OUT=$(bash "$SCRIPT" --audit 2>&1); rc1=$?
audit "$repo" --max-kb abc
if [ "$rc1" -eq 2 ] && [ "$RC" -eq 2 ]; then pass; else fail "rc=$rc1/$RC"; fi

# ---- list and clean ----
# fake gh on PATH: the branch name picks the answer.
FAKEBIN=$(mktemp -d); _CLEANUP_DIRS+=("$FAKEBIN")
cat > "$FAKEBIN/gh" <<'GH'
#!/bin/bash
case "$3" in
  br/open) echo OPEN ;;
  br/merged) echo MERGED ;;
  br/fail) echo 'error connecting to api.github.com' >&2; exit 1 ;;
  *) echo 'no pull requests found for branch "x"' >&2; exit 1 ;;
esac
GH
chmod +x "$FAKEBIN/gh"
days_ago() { date -u -d "$1 days ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-"$1"d +%Y-%m-%dT%H:%M:%SZ; }
set_age() { sed -i.bak "s/\"created_at\":\"[^\"]*\"/\"created_at\":\"$(days_ago "$2")\"/" "$1/.sandbox.json"; rm -f "$1/.sandbox.json.bak"; }
lst() { OUT=$(PATH="$FAKEBIN:$PATH" bash "$SCRIPT" list "$@" 2>&1); RC=$?; }
cln() { OUT=$(PATH="$FAKEBIN:$PATH" bash "$SCRIPT" clean "$@" 2>&1); RC=$?; }
state_of() { echo "$OUT" | awk -v n="$1" '$1 ~ n {print}'; }

repo=$(mk_repo); root="$(dirname "$repo")/.ship-$(basename "$repo")"
lst "$repo"
t "list prints nothing and exits 0 when there are no sandboxes"
if [ "$RC" -eq 0 ] && [ -z "$OUT" ]; then pass; else fail "rc=$RC $OUT"; fi

printf 'link node_modules\n' > "$repo/.harness-sandbox"
prov "$repo" a 1 run --branch br/running
prov "$repo" c 2 open --branch br/open
prov "$repo" c 3 merged --branch br/merged
prov "$repo" c 4 old --branch br/old
prov "$repo" a 5 fail --branch br/fail
prov "$repo" c 6 stale --branch br/stale
prov "$repo" c 7 garbage --branch br/garbage
sleep 30 & SLEEPER=$!
printf '%s\n' "$SLEEPER" > "$root/a-t1-run/.sandbox.pid"
set_age "$root/c-t4-old" 10
printf '99999999\n' > "$root/c-t6-stale/.sandbox.pid"
printf 'not-a-pid\n' > "$root/c-t7-garbage/.sandbox.pid"
set_age "$root/c-t7-garbage" 10

t "list shows each state, with the header columns"
lst "$repo"
if [ "$RC" -eq 0 ] && echo "$OUT" | head -1 | grep -qE '^SANDBOX +BRANCH +STATE +SIZE +AGE' \
  && state_of a-t1-run | grep -q 'running' && state_of c-t2-open | grep -q 'PR open' \
  && state_of c-t3-merged | grep -q 'merged' && state_of c-t4-old | grep -q 'abandoned' \
  && state_of a-t5-fail | grep -q 'unknown'; then pass; else fail "rc=$RC $OUT"; fi

t "a stale or garbage pid file is not running"
if ! state_of c-t6-stale | grep -q running && ! state_of c-t7-garbage | grep -q running \
  && state_of c-t7-garbage | grep -q abandoned; then pass; else fail "$OUT"; fi

t "list with no gh at all shows unknown and changes nothing"
OUT=$(PATH="/usr/bin:/bin" bash -c 'command -v gh >/dev/null && exit 99; bash "$0" list "$1"' "$SCRIPT" "$repo" 2>&1); RC=$?
if [ "$RC" -eq 99 ] || { [ "$RC" -eq 0 ] && echo "$OUT" | grep -q 'c-t3-merged.*unknown'; }; then pass; else fail "rc=$RC $OUT"; fi

snap() { { git -C "$repo" worktree list; git -C "$repo" branch --list; find "$root" -maxdepth 1 | sort; } | md5sum 2>/dev/null || true; }
t "clean without a selector, or with a bad --older, exits 2"
cln "$repo"; rc1=$RC
cln "$repo" --older abc; rc2=$RC
cln "$repo" --older 7; rc3=$RC
if [ "$rc1" -eq 2 ] && [ "$rc2" -eq 2 ] && [ "$rc3" -eq 2 ]; then pass; else fail "rc=$rc1/$rc2/$rc3"; fi

t "dry run reports the plan and changes nothing"
before=$(snap)
cln "$repo" --older 7d
after=$(snap)
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q 'would remove c-t4-old (abandoned)' && [ "$before" = "$after" ]; then pass; else fail "rc=$RC $OUT"; fi

t "running and unknown sandboxes are skipped even when selected, with and without --yes"
cln "$repo" --run a --yes
if echo "$OUT" | grep -q 'skip a-t1-run (running)' && echo "$OUT" | grep -q 'skip a-t5-fail (unknown)' \
  && [ -d "$root/a-t1-run" ] && [ -d "$root/a-t5-fail" ]; then pass; else fail "rc=$RC $OUT"; fi

t "--yes removes a symlinked node_modules as a link and the original survives"
[ -L "$root/c-t3-merged/node_modules" ] || fail "setup: node_modules is not a link"
cln "$repo" --merged --yes
if [ ! -d "$root/c-t3-merged" ] && [ -f "$repo/node_modules/pkg/index.js" ] && [ "$(cat "$repo/node_modules/pkg/index.js")" = x ]; then pass; else fail "$OUT"; fi

t "the branch survives a clean"
if git -C "$repo" rev-parse --verify -q br/merged >/dev/null; then pass; else fail "branch gone"; fi

t "a dirty sandbox (tracked change or untracked file) is refused, left intact, and clean exits 1"
printf 'dirty\n' >> "$root/c-t4-old/app.txt"
printf 'u\n' > "$root/c-t7-garbage/new.txt"
cln "$repo" --older 7d --yes
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'refused c-t4-old' && echo "$OUT" | grep -q 'refused c-t7-garbage' \
  && grep -q dirty "$root/c-t4-old/app.txt" && [ -f "$root/c-t7-garbage/new.txt" ]; then pass; else fail "rc=$RC $OUT"; fi

t "--merged removes only merged sandboxes; PR open stays"
prov "$repo" b 1 m2 --branch br/merged
cln "$repo" --merged --yes
if [ "$RC" -eq 0 ] && [ ! -d "$root/b-t1-m2" ] && [ -d "$root/c-t2-open" ]; then pass; else fail "rc=$RC $OUT"; fi

t "--older skips a sandbox with an open PR"
set_age "$root/c-t2-open" 30
cln "$repo" --older 7d --yes
if ! echo "$OUT" | grep -q 'c-t2-open' && [ -d "$root/c-t2-open" ]; then pass; else fail "$OUT"; fi

t "a directory that is not a registered worktree is reported and kept"
mkdir -p "$root/stray"; printf 'x\n' > "$root/stray/f"
cln "$repo" --older 0d --yes
if echo "$OUT" | grep -q 'skip stray (not a registered' && [ -f "$root/stray/f" ]; then pass; else fail "$OUT"; fi
kill "$SLEEPER" 2>/dev/null; wait "$SLEEPER" 2>/dev/null

finish
