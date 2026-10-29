#!/bin/bash
# Serve the verify fixture app with python3 -m http.server.
# Reads APP_USER and APP_PASSWORD (the app's own names, set from verify.config.json env) and writes them to
# credentials.json in a temp copy of the app. The tracked tree never holds a value.
# PORT (default 8765) sets the port.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
: "${APP_USER:?APP_USER is not set}"
: "${APP_PASSWORD:?APP_PASSWORD is not set}"
PORT="${PORT:-8765}"

SERVE_DIR="$(mktemp -d)"
CHILD=""
trap 'rm -rf "$SERVE_DIR"' EXIT
trap '[ -z "$CHILD" ] || kill "$CHILD" 2>/dev/null; exit 143' TERM
trap '[ -z "$CHILD" ] || kill "$CHILD" 2>/dev/null; exit 130' INT
cp "$HERE/index.html" "$HERE/login.html" "$SERVE_DIR/"
python3 - "$SERVE_DIR/credentials.json" <<'PY'
import json, os, sys
with open(sys.argv[1], "w") as f:
    json.dump({"user": os.environ["APP_USER"], "password": os.environ["APP_PASSWORD"]}, f)
PY

echo "verify fixture on http://127.0.0.1:$PORT" >&2
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$SERVE_DIR" &
CHILD=$!
wait "$CHILD"
