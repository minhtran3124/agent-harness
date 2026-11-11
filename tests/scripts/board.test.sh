#!/usr/bin/env bash
# The live run board (plugins/harness/board/): label map, run-dir tailing and the SSE server. The cases are
# in tests/board/board.test.js; this wrapper puts them in the L3 suite.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
if ! command -v node >/dev/null 2>&1; then
  echo 'board: skip — no node'
  exit 0
fi
node "$root/tests/board/board.test.js"
