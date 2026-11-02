#!/bin/bash
# Find text that must not reach a GitHub issue. Prints file:line for each match, never the
# matched text, so a secret does not enter the session transcript.
# Run it BEFORE you read a file: reading the file puts the secret in the transcript.
# Exit 0: no match. Exit 1: match found. Exit 2: bad usage, or a file it cannot scan.
# Usage: publish-check.sh <file> [<file> ...]
set -u
[ "$#" -gt 0 ] || { echo "usage: publish-check.sh <file> [<file> ...]" >&2; exit 2; }

KEYS='[a-z0-9_-]*(password|passwd|pwd|api[_-]?key|secret|token)[a-z0-9_-]*'
# A keyword needs a quoted value, or a long bare value, so that "token: JWT" does not stop a run.
VALUE="[\"']?[[:space:]]*[:=][[:space:]]*([\"'][^\"']+|[^[:space:]\"']{12,})"
PATTERN="(sk-[a-z0-9_-]{20,}|[rs]k_(live|test)_[a-z0-9]{16,}|AKIA[0-9A-Z]{16}|gh[pousr]_[a-z0-9]{20,}|github_pat_|xox[baprs]-|-----BEGIN [A-Z ]*PRIVATE KEY|bearer[[:space:]]+[a-z0-9._~+/-]{16,}|[a-z][a-z0-9+.-]*://[^[:space:]:/@]+:[^[:space:]/@]+@|$KEYS$VALUE)"

found=0
for f in "$@"; do
  [ -f "$f" ] && [ -r "$f" ] || { echo "publish-check: cannot read $f, stop" >&2; exit 2; }
  # A NUL byte means binary or UTF-16 text. A line match is not reliable there, so do not pass it.
  if [ "$(LC_ALL=C tr -d '\000' <"$f" | wc -c)" -ne "$(wc -c <"$f")" ]; then
    echo "publish-check: $f is binary or UTF-16, stop" >&2
    exit 2
  fi
  hits=$(LC_ALL=C grep -anEi -e "$PATTERN" -- "$f")
  status=$?
  [ "$status" -le 1 ] || { echo "publish-check: grep failed on $f, stop" >&2; exit 2; }
  for n in $(printf '%s\n' "$hits" | cut -d: -f1); do echo "$f:$n"; found=1; done
done
[ "$found" = 0 ] && echo "publish-check: clean" || echo "publish-check: MATCH, stop"
exit "$found"
