#!/usr/bin/env bash
# plugins/harness/skills/autopilot/scripts/board-start.sh starts the run board in the background for
# /harness:autopilot and opens it in a browser. It is advisory: it always exits 0. The cases use free
# ports, a fake browser opener on PATH and a private TMPDIR, and they stop every server they start.
set -uo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
start="$root/plugins/harness/skills/autopilot/scripts/board-start.sh"
if ! command -v node >/dev/null 2>&1; then
  echo 'board-start: skip — no node'
  exit 0
fi

work=$(mktemp -d)
other_pid=''
free_port() { node -e "const s=require('net').createServer().listen(0,'127.0.0.1',()=>{console.log(s.address().port);s.close()})"; }
cleanup() {
  [ -n "$other_pid" ] && kill "$other_pid" 2>/dev/null
  for f in "$work"/tmp/harness-board-*.pid; do [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null; done
  rm -rf "$work"
}
trap cleanup EXIT
mkdir -p "$work/tmp" "$work/bin" "$work/proj1" "$work/proj2" "$work/proj3" "$work/empty"
port=$(free_port)

# A fake browser opener: it records each call.
printf '#!/usr/bin/env bash\necho "$@" >> "%s/opened.log"\n' "$work" > "$work/bin/xdg-open"
chmod +x "$work/bin/xdg-open"
cp "$work/bin/xdg-open" "$work/bin/open"

fails=0
ok() { printf '  ok    %s\n' "$1"; }
bad() { printf '  FAIL  %s\n' "$1"; [ -n "${2:-}" ] && printf '        %s\n' "$2"; fails=$((fails + 1)); }
opens() { grep -c . "$work/opened.log" 2>/dev/null || echo 0; }
# run_in <project dir> <args...>: a display is set, SSH is not.
run_in() { local d=$1; shift; ( cd "$d" && env -u SSH_CONNECTION -u WAYLAND_DISPLAY TMPDIR="$work/tmp" DISPLAY=:0 PATH="$work/bin:$PATH" bash "$start" "$@" 2>&1 ); }
status() { curl -s -m 3 -o /dev/null -w '%{http_code}' "$1/state.json"; }

if [ ! -f "$start" ]; then
  bad "board-start.sh exists" "missing $start"
  echo; echo "board-start.test.sh: FAILED"; exit 1
fi

# 1. First call.
out=$(run_in "$work/proj1" --port "$port"); rc=$?
[ "$rc" -eq 0 ] && ok "first call exits 0" || bad "first call exits 0" "rc=$rc out=$out"
echo "$out" | grep -q "board: http://127.0.0.1:$port" && ok "first call prints the board URL" || bad "first call prints the board URL" "$out"
[ "$(status "http://127.0.0.1:$port")" = "200" ] && ok "the board answers /state.json with 200" || bad "the board answers /state.json with 200"
state=$(curl -s -m 3 "http://127.0.0.1:$port/state.json")
echo "$state" | grep -q 'proj1' && ok "the board follows the directory the script ran in (proj1)" || bad "the board follows the directory the script ran in" "$state"
[ "$(opens)" = "1" ] && grep -q "http://127.0.0.1:$port" "$work/opened.log" && ok "the opener was called once with the URL" || bad "the opener was called once with the URL" "$(cat "$work/opened.log" 2>/dev/null)"
pid1=$(cat "$work"/tmp/harness-board-*proj1*.pid 2>/dev/null)
[ -n "$pid1" ] && ok "a pid file for the project is written under TMPDIR" || bad "a pid file for the project is written under TMPDIR" "$(ls "$work/tmp")"

# 2. Second call, same project.
out=$(run_in "$work/proj1" --port "$port"); rc=$?
[ "$rc" -eq 0 ] && echo "$out" | grep -q 'already running' && ok "second call reports 'already running' and exits 0" || bad "second call reports 'already running' and exits 0" "rc=$rc out=$out"
[ "$(opens)" = "1" ] && ok "second call opens no browser" || bad "second call opens no browser" "opens=$(opens)"
[ "$(cat "$work"/tmp/harness-board-*proj1*.pid)" = "$pid1" ] && ok "second call starts no second server" || bad "second call starts no second server"

# 3. The default port is held by the board of ANOTHER project: a second board starts on another port.
out=$(run_in "$work/proj2" --port "$port"); rc=$?
url2=$(echo "$out" | grep -o 'http://127.0.0.1:[0-9]*' | head -1)
[ "$rc" -eq 0 ] && [ -n "$url2" ] && [ "$url2" != "http://127.0.0.1:$port" ] && ok "another project gets its own board on another port" || bad "another project gets its own board on another port" "rc=$rc out=$out"
[ -n "$url2" ] && curl -s -m 3 "$url2/state.json" | grep -q 'proj2' && ok "the second board follows proj2" || bad "the second board follows proj2" "url=$url2"

# 4. The port is taken by something that is not a board: the script moves to another port.
bport=$(free_port)
node -e "require('http').createServer((q,r)=>r.end('not a board')).listen($bport,'127.0.0.1')" &
other_pid=$!
sleep 1
out=$(run_in "$work/proj3" --port "$bport"); rc=$?
url3=$(echo "$out" | grep -o 'http://127.0.0.1:[0-9]*' | head -1)
[ "$rc" -eq 0 ] && [ -n "$url3" ] && [ "$url3" != "http://127.0.0.1:$bport" ] && curl -s -m 3 "$url3/state.json" | grep -q 'proj3' \
  && ok "a port held by a non-board server is not taken for the board" || bad "a port held by a non-board server is not taken for the board" "rc=$rc out=$out"
kill "$other_pid" 2>/dev/null; other_pid=''

# 5. --stop.
out=$(run_in "$work/proj1" --stop); rc=$?
sleep 1
[ "$rc" -eq 0 ] && echo "$out" | grep -qi 'stopped' && ok "--stop reports 'stopped' and exits 0" || bad "--stop reports 'stopped' and exits 0" "rc=$rc out=$out"
[ "$(status "http://127.0.0.1:$port")" != "200" ] && ok "--stop ends the board" || bad "--stop ends the board"
out=$(run_in "$work/proj1" --stop); rc=$?
[ "$rc" -eq 0 ] && echo "$out" | grep -qi 'not running' && ok "--stop with nothing running says 'not running' and exits 0" || bad "--stop with nothing running says 'not running' and exits 0" "rc=$rc out=$out"

# 6. --no-open still starts the board.
rm -f "$work/opened.log"
out=$(run_in "$work/proj1" --port "$port" --no-open); rc=$?
[ "$rc" -eq 0 ] && [ "$(opens)" = "0" ] && ok "--no-open makes no opener call" || bad "--no-open makes no opener call" "rc=$rc opens=$(opens)"
[ "$(status "http://127.0.0.1:$port")" = "200" ] && ok "--no-open still starts the board" || bad "--no-open still starts the board"
run_in "$work/proj1" --stop >/dev/null

# 7. No display (Linux): no opener call, the URL is printed. macOS uses `open` without X, so skip there.
if [ "$(uname)" != "Darwin" ]; then
  rm -f "$work/opened.log"
  out=$( cd "$work/proj1" && env -u DISPLAY -u WAYLAND_DISPLAY -u SSH_CONNECTION TMPDIR="$work/tmp" PATH="$work/bin:$PATH" bash "$start" --port "$port" 2>&1 ); rc=$?
  [ "$rc" -eq 0 ] && [ "$(opens)" = "0" ] && echo "$out" | grep -q "http://127.0.0.1:$port" && ok "no display: no opener call, URL printed" || bad "no display: no opener call, URL printed" "rc=$rc opens=$(opens) out=$out"
  run_in "$work/proj1" --stop >/dev/null
  rm -f "$work/opened.log"
  out=$( cd "$work/proj1" && env -u WAYLAND_DISPLAY TMPDIR="$work/tmp" DISPLAY=:0 SSH_CONNECTION='1.2.3.4 1 5.6.7.8 22' PATH="$work/bin:$PATH" bash "$start" --port "$port" 2>&1 ); rc=$?
  [ "$rc" -eq 0 ] && [ "$(opens)" = "0" ] && echo "$out" | grep -q 'ssh -L' && ok "over SSH: no opener call, an ssh -L hint is printed" || bad "over SSH: no opener call, an ssh -L hint is printed" "rc=$rc opens=$(opens) out=$out"
  run_in "$work/proj1" --stop >/dev/null
fi

# 7b. A relative path to the script works (the documented --stop command is relative).
out=$( cd "$work/proj1" && env TMPDIR="$work/tmp" bash "$(realpath --relative-to="$work/proj1" "$start" 2>/dev/null || echo "$start")" --stop 2>&1 ); rc=$?
[ "$rc" -eq 0 ] && ! echo "$out" | grep -qi 'skipped' && ok "a relative script path works (no 'skipped')" || bad "a relative script path works" "rc=$rc out=$out"

# 8. No node on PATH: a one-line note and exit 0 (the board never blocks a run).
out=$( cd "$work/proj1" && env TMPDIR="$work/tmp" PATH="$work/empty" /bin/bash "$start" --port "$port" 2>&1 ); rc=$?
[ "$rc" -eq 0 ] && echo "$out" | grep -qi 'node' && ok "no node: exits 0 with a note that names node" || bad "no node: exits 0 with a note that names node" "rc=$rc out=$out"

# 9. No opener at all: the URL is printed, exit 0.
mkdir -p "$work/min"
for c in node curl nohup sleep cat mkdir dirname rm ps uname grep sed tr head; do p=$(command -v "$c") && ln -sf "$p" "$work/min/$c"; done
out=$( cd "$work/proj1" && env TMPDIR="$work/tmp" DISPLAY=:0 PATH="$work/min" /bin/bash "$start" --port "$port" 2>&1 ); rc=$?
[ "$rc" -eq 0 ] && echo "$out" | grep -q "http://127.0.0.1:$port" && ok "no opener: exits 0 and prints the URL" || bad "no opener: exits 0 and prints the URL" "rc=$rc out=$out"
run_in "$work/proj1" --stop >/dev/null

echo
if [ "$fails" -eq 0 ]; then echo 'board-start.test.sh: passed'; else echo "board-start.test.sh: $fails FAILED"; exit 1; fi
