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

finish
