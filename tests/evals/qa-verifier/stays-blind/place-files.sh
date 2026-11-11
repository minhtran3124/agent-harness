#!/usr/bin/env bash
set -eu
here="$(dirname "$0")"
cp -R "$here/files/." .
for f in "$here/../fixtures/qa-verifier/clean" "$here/../../../fixtures/qa-verifier/clean"; do [ -f "$f/tally.sh" ] && cp "$f/tally.sh" . && break; done
