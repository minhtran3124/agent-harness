#!/bin/bash
# Find text that must not reach a GitHub issue. Prints file:line for each match, never the
# matched text, so a secret does not enter the session transcript.
# Exit 0: no match. Exit 1: match found. Exit 2: bad usage or an unreadable file.
# Usage: publish-check.sh <file> [<file> ...]
set -u
[ "$#" -gt 0 ] || { echo "usage: publish-check.sh <file> [<file> ...]" >&2; exit 2; }

KEYS='password|passwd|api[_-]?key|client[_-]?secret|secret|token'
# A keyword needs a quoted value, or a long bare value, so that "token: JWT" does not stop a run.
PATTERN="(sk-[a-z0-9]{20,}|AKIA[0-9A-Z]{16}|gh[pousr]_[a-z0-9]{20,}|github_pat_|xox[baprs]-|-----BEGIN [A-Z ]*PRIVATE KEY|($KEYS)[[:space:]]*[:=][[:space:]]*([\"'][^\"']+|[^[:space:]\"']{12,}))"

found=0
for f in "$@"; do
  [ -r "$f" ] || { echo "cannot read: $f" >&2; exit 2; }
  hits=$(grep -nEi -e "$PATTERN" -- "$f" | cut -d: -f1)
  for n in $hits; do echo "$f:$n"; found=1; done
done
[ "$found" = 0 ] && echo "publish-check: clean" || echo "publish-check: MATCH, stop"
exit "$found"
