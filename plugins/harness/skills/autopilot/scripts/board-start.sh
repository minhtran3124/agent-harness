#!/usr/bin/env bash
# Start the run board for /harness:autopilot and open it in a browser.
#
#   board-start.sh [--port <n>] [--no-open] [--stop]
#
# It works for the Claude Code project of the CURRENT directory (the board derives the project from it), so run it
# from the directory where Claude Code was started. It starts plugins/harness/board/board.js in the background and
# keeps a pid, a url and a log file per project under ${TMPDIR:-/tmp}. A board already running for this project is
# reused. If the port is held by something else, or by the board of another project, a free port is used.
# It opens a browser only when a desktop is there (macOS, or a display and no SSH session); otherwise it prints the
# URL. --stop ends the board of this project. The board is advisory: this script always exits 0. Its first line starts with "board:" and says what happened.
#
# Verifies: a board for this project answers on the printed URL (checked with its /state.json) when it prints a URL.
# Does not verify: that a browser opened, that the board outlives the Claude Code session, or that the project
# directory is the one Claude Code writes its runs under.

here=${BASH_SOURCE[0]%/*}
[ "$here" = "${BASH_SOURCE[0]}" ] && here=.
board=$(cd "$here/../../../board" 2>/dev/null && pwd)/board.js

port=4317 open=1 stop=0
while [ $# -gt 0 ]; do
  case "$1" in
    --port) port=${2:-4317}; [ $# -gt 1 ] && shift ;;
    --no-open) open=0 ;;
    --stop) stop=1 ;;
  esac
  shift
done

case "$port" in ""|*[!0-9]*) port=4317 ;; esac

if ! command -v node >/dev/null 2>&1; then
  echo 'board: skipped, node not found'
  exit 0
fi
if [ ! -f "$board" ]; then
  echo "board: skipped, $board not found"
  exit 0
fi

key=$(node -e 'console.log(require(process.argv[1]).projectKey(process.argv[2]))' "$board" "$PWD" 2>/dev/null)
if [ -z "$key" ]; then
  echo 'board: skipped, could not read board.js'
  exit 0
fi
tmp=${TMPDIR:-/tmp}
tmp=${tmp%/}
pidf="$tmp/harness-board-$key.pid"
urlf="$tmp/harness-board-$key.url"
logf="$tmp/harness-board-$key.log"

# project_dir that the board at <url> follows, or nothing when nothing answers or the answer is not a board.
probe() {
  node -e 'const h=require("http");h.get(process.argv[1]+"/state.json",{timeout:2000},r=>{let b="";r.on("data",c=>b+=c);r.on("end",()=>{try{console.log(JSON.parse(b).project_dir||"")}catch(e){console.log("")}})}).on("error",()=>console.log("")).on("timeout",function(){this.destroy()})' "$1" 2>/dev/null
}
is_mine() { case "$(probe "$1")" in */"$key") return 0 ;; esac; return 1; }

if [ "$stop" -eq 1 ]; then
  pid=$(cat "$pidf" 2>/dev/null)
  if [ -n "$pid" ] && ps -p "$pid" -o args= 2>/dev/null | grep -q 'board\.js'; then
    kill "$pid" 2>/dev/null
    rm -f "$pidf" "$urlf"
    echo 'board: stopped'
  elif [ -z "$pid" ] && [ -s "$urlf" ]; then
    echo "board: running at $(cat "$urlf"), but not started by this script; stop it yourself"
  else
    rm -f "$pidf" "$urlf"
    echo 'board: not running'
  fi
  exit 0
fi

# A board of this project is already running: reuse it.
url=$(cat "$urlf" 2>/dev/null)
if [ -n "$url" ] && is_mine "$url"; then
  echo "board: already running at $url"
  exit 0
fi
if is_mine "http://127.0.0.1:$port"; then
  echo "http://127.0.0.1:$port" > "$urlf"
  echo "board: already running at http://127.0.0.1:$port"
  exit 0
fi

# Use the wanted port when it is free; else any free port (0).
p=$port
if (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then p=0; fi

nohup node "$board" --project "$PWD" --port "$p" </dev/null >"$logf" 2>&1 &
echo $! > "$pidf"
disown 2>/dev/null
url=''
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  url=$(sed -n 's/^board: \(http:\/\/127\.0\.0\.1:[0-9]*\).*/\1/p' "$logf" 2>/dev/null | head -1)
  [ -n "$url" ] && break
  sleep 0.2
done
if [ -z "$url" ]; then
  echo "board: could not start; see $logf"
  exit 0
fi
echo "$url" > "$urlf"
echo "board: $url"

[ "$open" -eq 1 ] || exit 0
opener=''
if [ -n "${SSH_CONNECTION:-}" ]; then
  echo "board: remote session; on your own machine run: ssh -L ${url##*:}:127.0.0.1:${url##*:} <this host>, then open $url"
elif [ "$(uname 2>/dev/null)" = Darwin ]; then
  opener=open
elif [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
  if command -v wslview >/dev/null 2>&1; then opener=wslview
  elif command -v xdg-open >/dev/null 2>&1; then opener=xdg-open; fi
else
  echo "board: no display here; open $url yourself"
fi
if [ -n "$opener" ] && command -v "$opener" >/dev/null 2>&1; then
  "$opener" "$url" >/dev/null 2>&1 &
elif [ -n "$opener" ]; then
  echo "board: no browser opener found; open $url yourself"
fi
exit 0
