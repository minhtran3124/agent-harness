#!/usr/bin/env bash
# tally: a tiny calculator CLI used by the qa-verifier eval.
set -u
usage() { echo "usage: tally.sh add|mul A B" >&2; exit 2; }
[ $# -eq 3 ] || usage
case "$1" in
  add) echo $(( $2 + $3 )) ;;
  mul) echo $(( $2 * $3 )) ;;
  *) usage ;;
esac
