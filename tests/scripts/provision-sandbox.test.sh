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

t "a passing check runs in the sandbox with the port variables and the run is ready"
repo=$(mk_repo)
printf 'setup echo set > setup.out\ncheck test "$SANDBOX_PORT" = 4010 && test -f setup.out && pwd > check.out\n' > "$repo/.harness-sandbox"
prov "$repo" r 1 s
dir="$(dirname "$repo")/.ship-$(basename "$repo")/r-t1-s"
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q '"status":"ready"' && [ "$(cat "$dir/check.out")" = "$(cd "$dir" && pwd)" ]; then pass; else fail "rc=$RC $OUT"; fi

t "a failing check fails the run, names the command and prints no ready line"
printf 'check exit 3\n' > "$repo/.harness-sandbox"
prov "$repo" r 2 s
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'check failed: exit 3' && ! echo "$OUT" | grep -q '"status":"ready"'; then pass; else fail "rc=$RC $OUT"; fi

t "a missing require-env variable fails first, names it, and leaves no sandbox or setup effect"
repo=$(mk_repo)
printf 'copy .env\nsetup touch setup.ran\nrequire-env HARNESS_T476_UNSET\n' > "$repo/.harness-sandbox"
prov "$repo" r 1 s
dir="$(dirname "$repo")/.ship-$(basename "$repo")/r-t1-s"
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'HARNESS_T476_UNSET' && [ ! -e "$dir" ]; then pass; else fail "rc=$RC $OUT"; fi

t "a set require-env variable lets the run continue"
OUT=$(HARNESS_T476_UNSET=1 bash "$SCRIPT" "$repo" r 1 s 2>&1); RC=$?
if [ "$RC" -eq 0 ] && [ -e "$dir/setup.ran" ]; then pass; else fail "rc=$RC $OUT"; fi

t "a check past the timeout fails and its background child is killed"
repo=$(mk_repo)
printf 'check sleep 30 & echo $! > "$PWD/child.pid"; wait\n' > "$repo/.harness-sandbox"
OUT=$(HARNESS_CHECK_TIMEOUT=1 bash "$SCRIPT" "$repo" r 1 s 2>&1); RC=$?
dir="$(dirname "$repo")/.ship-$(basename "$repo")/r-t1-s"
sleep 0.5
child=$(cat "$dir/child.pid" 2>/dev/null)
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'timed out' && [ -n "$child" ] && ! kill -0 "$child" 2>/dev/null; then pass; else fail "rc=$RC child=$child $OUT"; fi

t "a check that leaves a background server behind does not leak it"
printf 'check sleep 30 & echo $! > "$PWD/bg.pid"\n' > "$repo/.harness-sandbox"
prov "$repo" r 2 s
dir="$(dirname "$repo")/.ship-$(basename "$repo")/r-t2-s"
sleep 0.5
child=$(cat "$dir/bg.pid" 2>/dev/null)
if [ "$RC" -eq 0 ] && [ -n "$child" ] && ! kill -0 "$child" 2>/dev/null; then pass; else fail "rc=$RC child=$child $OUT"; fi

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

# ---- --mode clone ----
sbdir() { echo "$(dirname "$1")/.ship-$(basename "$1")/$2"; }
state_hash() { { git -C "$1" status --porcelain --ignored; git -C "$1" rev-parse HEAD; git -C "$1" branch --list; } | md5sum 2>/dev/null || { git -C "$1" status --porcelain --ignored; git -C "$1" rev-parse HEAD; git -C "$1" branch --list; } | md5 -q; }

t "clone mode makes a standalone clone with its own .git and one worktree entry in main"
repo=$(mk_repo)
prov "$repo" c 1 one --mode clone --branch feat/c1
dir=$(sbdir "$repo" c-t1-one)
if [ "$RC" -eq 0 ] && [ -d "$dir/.git" ] && echo "$OUT" | grep -q '"status":"ready"' && echo "$OUT" | grep -q '"mode":"clone"' \
  && [ "$(git -C "$repo" worktree list | wc -l | tr -d ' ')" = 1 ]; then pass; else fail "rc=$RC $OUT"; fi

t "clone carries committed content only: dirty main does not leak in"
repo=$(mk_repo)
printf 'edited\n' > "$repo/app.txt"; printf 'new\n' > "$repo/untracked.txt"
prov "$repo" c 1 dirty --mode clone --branch feat/d
dir=$(sbdir "$repo" c-t1-dirty)
if [ "$RC" -eq 0 ] && [ -z "$(git -C "$dir" status --porcelain)" ] && [ "$(cat "$dir/app.txt")" = tracked ] && [ ! -e "$dir/untracked.txt" ]; then pass
else fail "rc=$RC $(git -C "$dir" status --porcelain | head -3)"; fi

t "clone origin is the main repo's remote URL, --remote picks another, a missing remote warns and exits 0"
repo=$(mk_repo)
git -C "$repo" remote add origin https://example.com/o.git
git -C "$repo" remote add up https://example.com/up.git
prov "$repo" c 1 a --mode clone
o1=$(git -C "$(sbdir "$repo" c-t1-a)" remote get-url origin)
prov "$repo" c 2 b --mode clone --remote up
o2=$(git -C "$(sbdir "$repo" c-t2-b)" remote get-url origin)
repo2=$(mk_repo)
prov "$repo2" c 1 n --mode clone
if [ "$o1" = https://example.com/o.git ] && [ "$o2" = https://example.com/up.git ] && [ "$RC" -eq 0 ] && echo "$OUT" | grep -qi 'warn'; then pass
else fail "o1=$o1 o2=$o2 rc=$RC $OUT"; fi

t "clone origin/* refs mirror the main repo's remote-tracking refs, not its local branches"
repo=$(mk_repo)
git -C "$repo" remote add origin https://example.com/o.git
git -C "$repo" branch localonly
old=$(git -C "$repo" rev-parse HEAD)
git -C "$repo" update-ref refs/remotes/origin/main "$old"
prov "$repo" c 1 refs --mode clone
dir=$(sbdir "$repo" c-t1-refs)
if [ "$RC" -eq 0 ] && [ "$(git -C "$dir" rev-parse origin/main)" = "$old" ] && ! git -C "$dir" rev-parse -q --verify origin/localonly >/dev/null; then pass
else fail "rc=$RC $(git -C "$dir" for-each-ref refs/remotes)"; fi

t "clone mode runs the manifest, ports and setup like worktree mode"
repo=$(mk_repo)
printf 'copy .env\ncopy CLAUDE.local.md\nlink node_modules\nrequire .env\nsetup echo "$SANDBOX_PORT" > port.out\n' > "$repo/.harness-sandbox"
prov "$repo" c 3 m --mode clone
dir=$(sbdir "$repo" c-t3-m)
if [ "$RC" -eq 0 ] && [ "$(cat "$dir/.env")" = SECRET=1 ] && [ -f "$dir/CLAUDE.local.md" ] && [ -L "$dir/node_modules" ] \
  && [ "$(cat "$dir/port.out")" = 4030 ] && grep -q '^SANDBOX_DB_NAME=' "$dir/.sandbox.env"; then pass; else fail "rc=$RC $OUT"; fi

t "clone branch and --from: branch B at REF, detached without --branch, unknown ref exits 1 and creates nothing"
repo=$(mk_repo)
first=$(git -C "$repo" rev-parse HEAD)
printf 'more\n' >> "$repo/app.txt"; git -C "$repo" commit -qam second
prov "$repo" c 1 b --mode clone --branch feat/b --from "$first"
dir=$(sbdir "$repo" c-t1-b)
ok1=0; [ "$RC" -eq 0 ] && [ "$(git -C "$dir" symbolic-ref --short HEAD)" = feat/b ] && [ "$(git -C "$dir" rev-parse HEAD)" = "$first" ] && ok1=1
prov "$repo" c 2 d --mode clone --from "$first"
dird=$(sbdir "$repo" c-t2-d)
ok2=0; [ "$RC" -eq 0 ] && echo "$OUT" | grep -q '"branch":"detached"' && [ "$(git -C "$dird" rev-parse HEAD)" = "$first" ] && ok2=1
prov "$repo" c 3 x --mode clone --from nosuchref
if [ "$ok1" = 1 ] && [ "$ok2" = 1 ] && [ "$RC" -eq 1 ] && [ ! -e "$(sbdir "$repo" c-t3-x)" ]; then pass; else fail "ok1=$ok1 ok2=$ok2 rc=$RC $OUT"; fi

t "clone mode is idempotent, re-syncs the manifest, and refuses a foreign folder or a worktree"
repo=$(mk_repo)
printf 'copy .env\n' > "$repo/.harness-sandbox"
prov "$repo" c 1 r --mode clone --branch feat/r
dir=$(sbdir "$repo" c-t1-r)
head1=$(git -C "$dir" rev-parse HEAD); ino1=$(ls -di "$dir/.git" | cut -d' ' -f1)
printf 'copy CLAUDE.local.md\n' >> "$repo/.harness-sandbox"
prov "$repo" c 1 r --mode clone --branch feat/r
rc_again=$RC
ino2=$(ls -di "$dir/.git" | cut -d' ' -f1)
mkdir -p "$(sbdir "$repo" c-t2-plain)"
prov "$repo" c 2 plain --mode clone; rc_plain=$RC
prov "$repo" c 3 wt --branch feat/wt
prov "$repo" c 3 wt --mode clone; rc_wt=$RC
if [ "$rc_again" -eq 0 ] && [ -f "$dir/CLAUDE.local.md" ] && [ "$head1" = "$(git -C "$dir" rev-parse HEAD)" ] && [ "$ino1" = "$ino2" ] \
  && [ "$rc_plain" -eq 1 ] && [ "$rc_wt" -eq 1 ]; then pass; else fail "again=$rc_again plain=$rc_plain wt=$rc_wt"; fi

t "clone mode leaves the main repo untouched"
repo=$(mk_repo)
printf 'copy .env\n' > "$repo/.harness-sandbox"
before=$(state_hash "$repo")
prov "$repo" c 1 u --mode clone --branch feat/u
after=$(state_hash "$repo")
if [ "$RC" -eq 0 ] && [ "$before" = "$after" ]; then pass; else fail "rc=$RC state changed"; fi

t "an unknown --mode exits 2"
prov "$repo" c 1 z --mode bogus
if [ "$RC" -eq 2 ]; then pass; else fail "rc=$RC $OUT"; fi

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

# ---- provisioning uses the same classification ----
snap() { git -C "$1" status --porcelain --ignored | sort | md5sum 2>/dev/null || git -C "$1" status --porcelain --ignored | sort | md5 -q; }
hash_of() { md5sum "$1" 2>/dev/null || md5 -q "$1"; }
# mk_auto_repo → small config and state only, none of it in a manifest; plus a regenerable dir.
mk_auto_repo() {
  local d; d=$(new_repo)
  _CLEANUP_DIRS+=("$(dirname "$d")/.ship-$(basename "$d")")
  printf '.env*\n*.db\n.auth/\nCLAUDE.local.md\nnode_modules/\nstray/\n' > "$d/.gitignore"
  printf 'x\n' > "$d/app.txt"; git -C "$d" add .gitignore app.txt; git -C "$d" commit -qm seed
  printf 'A=1\n' > "$d/.env"; printf 'db\n' > "$d/data.db"; printf 'local\n' > "$d/CLAUDE.local.md"
  mkdir -p "$d/.auth" "$d/node_modules/p"; printf 'tok\n' > "$d/.auth/x"; printf 'x\n' > "$d/node_modules/p/i.js"
  echo "$d"
}
sbx() { echo "$(dirname "$1")/.ship-$(basename "$1")/$2"; }

t "small unlisted config and state files are copied with no manifest"
repo=$(mk_auto_repo)
prov "$repo" a 1 s
dir=$(sbx "$repo" a-t1-s)
if [ "$RC" -eq 0 ] && [ "$(cat "$dir/.env")" = A=1 ] && [ -f "$dir/data.db" ] && [ -f "$dir/.auth/x" ] \
  && [ -f "$dir/CLAUDE.local.md" ] && [ ! -e "$dir/node_modules" ]; then pass; else fail "rc=$RC $OUT"; fi

t "two unknown paths block the run, list both hints, and create nothing"
repo=$(mk_auto_repo)
printf 'P=1\n' > "$repo/.env.prod"; mkdir -p "$repo/stray"; printf 'u\n' > "$repo/stray/n.txt"
before=$(snap "$repo"); envh=$(hash_of "$repo/.env")
prov "$repo" b 1 s
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'copy \.env\.prod' && echo "$OUT" | grep -q 'copy stray' \
  && [ ! -e "$(dirname "$repo")/.ship-$(basename "$repo")" ] && [ "$(snap "$repo")" = "$before" ] \
  && [ "$(hash_of "$repo/.env")" = "$envh" ]; then pass; else fail "rc=$RC $OUT"; fi

t "a config file over --max-kb fails and prints its manifest line"
rm -rf "$repo/stray" "$repo/.env.prod"; head -c 102400 /dev/zero | tr "\0" x > "$repo/big.db"
prov "$repo" c 1 s --max-kb 50
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'copy big\.db' && [ ! -e "$(dirname "$repo")/.ship-$(basename "$repo")" ]; then pass
else fail "rc=$RC $OUT"; fi

t "a prod-named file is never copied by default"
printf 'P=1\n' > "$repo/.env.prod"; rm -f "$repo/big.db"
prov "$repo" d 1 s
if [ "$RC" -eq 1 ] && [ ! -e "$(sbx "$repo" d-t1-s)/.env.prod" ]; then pass; else fail "rc=$RC $OUT"; fi

t "manifest copy lines win over the rules, and skip settles an unknown"
head -c 102400 /dev/zero | tr "\0" x > "$repo/big.db"; mkdir -p "$repo/stray"; printf 'u\n' > "$repo/stray/n.txt"
printf 'copy .env.prod\ncopy big.db\nskip stray\n' > "$repo/.harness-sandbox"
before=$(snap "$repo"); envh=$(hash_of "$repo/.env")
prov "$repo" e 1 s --max-kb 50
dir=$(sbx "$repo" e-t1-s)
if [ "$RC" -eq 0 ] && [ -f "$dir/.env.prod" ] && [ -f "$dir/big.db" ] && [ ! -e "$dir/stray" ] \
  && [ "$(snap "$repo")" = "$before" ] && [ "$(hash_of "$repo/.env")" = "$envh" ]; then pass; else fail "rc=$RC $OUT"; fi

t "running again for an existing sandbox still succeeds"
prov "$repo" e 1 s --max-kb 50
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q '"status":"ready"'; then pass; else fail "rc=$RC $OUT"; fi

t "a bad --max-kb exits 2"
prov "$repo" f 1 s --max-kb abc
rc1=$RC
OUT=$(timeout 10 bash "$SCRIPT" "$repo" f 1 s --max-kb 2>&1); RC=$?
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

# ---- teardown ----
trepo=$(mk_repo); troot="$(dirname "$trepo")/.ship-$(basename "$trepo")"
tlog="$(dirname "$trepo")/teardown.log"
printf 'teardown echo first:$SANDBOX_DB_NAME >> %s\nteardown echo second:$SANDBOX_DB_NAME >> %s\n' "$tlog" "$tlog" > "$trepo/.harness-sandbox"
prov "$trepo" td 1 ok --branch br/td-ok
tdb=$(sed -n 's/^SANDBOX_DB_NAME=//p' "$troot/td-t1-ok/.sandbox.env")

t "a manifest with teardown lines provisions without running them"
if [ "$RC" -eq 0 ] && [ ! -e "$tlog" ]; then pass; else fail "rc=$RC $OUT"; fi

t "a dry run runs no teardown"
cln "$trepo" --run td
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q 'would remove td-t1-ok' && [ ! -e "$tlog" ] && [ -d "$troot/td-t1-ok" ]; then pass; else fail "rc=$RC $OUT"; fi

t "clean --yes runs each teardown once, in reverse order, with SANDBOX_DB_NAME, then removes the sandbox"
cln "$trepo" --run td --yes
if [ "$RC" -eq 0 ] && [ ! -d "$troot/td-t1-ok" ] && [ "$(cat "$tlog")" = "$(printf 'second:%s\nfirst:%s' "$tdb" "$tdb")" ]; then pass; else fail "rc=$RC $OUT log=$(cat "$tlog" 2>&1)"; fi

t "a failing teardown keeps the sandbox, skips the lines after it, names the command and exits 1"
rm -f "$tlog"
printf 'teardown echo early >> %s\nteardown false-teardown-cmd\nteardown echo late >> %s\n' "$tlog" "$tlog" > "$trepo/.harness-sandbox"
prov "$trepo" tf 2 bad --branch br/td-bad
cln "$trepo" --run tf --yes
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'refused tf-t2-bad.*teardown failed: false-teardown-cmd' && [ -d "$troot/tf-t2-bad" ] \
  && [ "$(cat "$tlog")" = late ]; then pass; else fail "rc=$RC $OUT log=$(cat "$tlog" 2>&1)"; fi

t "a dirty sandbox is refused before any teardown runs"
rm -f "$tlog"
printf 'teardown echo ran >> %s\n' "$tlog" > "$trepo/.harness-sandbox"
prov "$trepo" td 3 dirty --branch br/td-dirty
printf 'u\n' > "$troot/td-t3-dirty/new.txt"
cln "$trepo" --run td --yes
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'refused td-t3-dirty' && [ ! -e "$tlog" ] && [ -d "$troot/td-t3-dirty" ]; then pass; else fail "rc=$RC $OUT"; fi

t "an empty teardown line fails the manifest"
printf 'teardown\n' > "$trepo/.harness-sandbox"
prov "$trepo" td 4 empty --branch br/td-empty
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'empty teardown command'; then pass; else fail "rc=$RC $OUT"; fi

t "a sandbox without .sandbox.env is refused when the manifest has teardown lines: no teardown runs"
rm -f "$tlog"
printf 'teardown echo noenv >> %s\n' "$tlog" > "$trepo/.harness-sandbox"
prov "$trepo" te 5 noenv --branch br/td-noenv
rm -f "$troot/te-t5-noenv/.sandbox.env"
cln "$trepo" --run te --yes
if [ "$RC" -eq 1 ] && echo "$OUT" | grep -q 'refused te-t5-noenv.*sandbox.env is missing' && [ ! -e "$tlog" ] && [ -d "$troot/te-t5-noenv" ]; then pass; else fail "rc=$RC $OUT"; fi

t "a sandbox without .sandbox.env is still cleaned when the manifest has no teardown lines"
printf 'copy .env\n' > "$trepo/.harness-sandbox"
prov "$trepo" tf 6 noenv2 --branch br/td-noenv2
rm -f "$troot/tf-t6-noenv2/.sandbox.env"
cln "$trepo" --run tf --yes
if [ "$RC" -eq 0 ] && [ ! -d "$troot/tf-t6-noenv2" ]; then pass; else fail "rc=$RC $OUT"; fi

# ---- clean --branch ----
prov "$repo" d 1 bra --branch br/sel-a
prov "$repo" d 2 brb --branch br/sel-b
prov "$repo" d 3 brr --branch br/sel-run
sleep 30 & SLEEPER2=$!
printf '%s\n' "$SLEEPER2" > "$root/d-t3-brr/.sandbox.pid"

t "clean --branch without --yes prints would remove and changes nothing"
before=$(snap)
cln "$repo" --branch br/sel-a
after=$(snap)
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q 'would remove d-t1-bra' && ! echo "$OUT" | grep -q 'd-t2-brb' && [ "$before" = "$after" ]; then pass; else fail "rc=$RC $OUT"; fi

t "clean --branch B --yes removes only the sandbox on B"
cln "$repo" --branch br/sel-a --yes
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q 'removed d-t1-bra' && [ ! -d "$root/d-t1-bra" ] && [ -d "$root/d-t2-brb" ]; then pass; else fail "rc=$RC $OUT"; fi

t "clean --branch with another selector, or without a value, exits 2"
cln "$repo" --branch br/sel-b --merged; rc1=$RC
cln "$repo" --merged --branch br/sel-b; rc2=$RC
cln "$repo" --branch; rc3=$RC
if [ "$rc1" -eq 2 ] && [ "$rc2" -eq 2 ] && [ "$rc3" -eq 2 ] && [ -d "$root/d-t2-brb" ]; then pass; else fail "rc=$rc1/$rc2/$rc3"; fi

t "clean --branch skips a running sandbox on that branch"
cln "$repo" --branch br/sel-run --yes
if echo "$OUT" | grep -q 'skip d-t3-brr (running)' && [ -d "$root/d-t3-brr" ]; then pass; else fail "rc=$RC $OUT"; fi
kill "$SLEEPER2" 2>/dev/null; wait "$SLEEPER2" 2>/dev/null

t "clean removes a clone-mode sandbox and runs its teardown"
crepo=$(mk_repo); croot="$(dirname "$crepo")/.ship-$(basename "$crepo")"
clog="$(dirname "$crepo")/clone-teardown.log"
printf 'teardown echo gone >> %s\n' "$clog" > "$crepo/.harness-sandbox"
prov "$crepo" cl 1 cc --mode clone --branch br/clone-clean
cln "$crepo" --branch br/clone-clean --yes
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q 'removed cl-t1-cc' && [ ! -d "$croot/cl-t1-cc" ] && grep -q gone "$clog"; then pass; else fail "rc=$RC $OUT"; fi

t "clean refuses a clone-mode sandbox with unpushed commits"
urepo=$(mk_repo); uroot="$(dirname "$urepo")/.ship-$(basename "$urepo")"
prov "$urepo" ul 1 up --mode clone --branch br/clone-unpushed
udir="$uroot/ul-t1-up"
git -C "$udir" -c user.name=t -c user.email=t@t commit -q --allow-empty -m local-only
cln "$urepo" --branch br/clone-unpushed --yes
if [ "$RC" -ne 0 ] && echo "$OUT" | grep -q 'refused ul-t1-up.*unpushed' && [ -d "$udir" ]; then pass; else fail "rc=$RC $OUT"; fi

t "a re-run on a detached HEAD keeps the recorded branch"
repo=$(mk_repo)
prov "$repo" r 1 keep --branch feat/keep
dir=$(sbdir "$repo" r-t1-keep)
git -C "$dir" checkout -q --detach
prov "$repo" r 1 keep --branch feat/keep
if [ "$RC" -eq 0 ] && grep -q '"branch":"feat/keep"' "$dir/.sandbox.json" && echo "$OUT" | grep -q '"branch":"feat/keep"'; then pass; else fail "rc=$RC $OUT $(cat "$dir/.sandbox.json")"; fi

t "clean --branch classifies only matching sandboxes and prints no skip lines for the rest"
repo=$(mk_repo); root="$(dirname "$repo")/.ship-$(basename "$repo")"
prov "$repo" g 1 aa --branch br/open
prov "$repo" g 2 bb --branch br/merged
mkdir -p "$root/stray"
GHLOG="$FAKEBIN/gh.log"; : > "$GHLOG"
cat > "$FAKEBIN/gh-counting" <<GH
#!/bin/bash
echo "\$3" >> "$GHLOG"
exec "$FAKEBIN/gh" "\$@"
GH
chmod +x "$FAKEBIN/gh-counting"
CBIN=$(mktemp -d); _CLEANUP_DIRS+=("$CBIN"); cp "$FAKEBIN/gh-counting" "$CBIN/gh"
OUT=$(PATH="$CBIN:$FAKEBIN:$PATH" bash "$SCRIPT" clean "$repo" --branch br/merged 2>&1); RC=$?
if [ "$RC" -eq 0 ] && [ "$(wc -l < "$GHLOG" | tr -d ' ')" -eq 1 ] && ! echo "$OUT" | grep -q 'skip' && echo "$OUT" | grep -q 'would remove g-t2-bb'; then pass; else fail "rc=$RC calls=$(cat "$GHLOG") $OUT"; fi

finish
