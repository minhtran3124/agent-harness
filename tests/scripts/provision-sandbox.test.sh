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

finish
