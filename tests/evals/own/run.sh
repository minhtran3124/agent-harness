#!/usr/bin/env bash
# Run the /harness:own eval cases with `claude plugin eval`.
#
# `claude plugin eval` reads cases only from a directory below the plugin. The cases live here,
# outside plugins/harness, so they do not ship with the plugin. This script copies the plugin and
# the cases into a temp directory and runs the CLI there. The repo is not written to.
#
# Usage, from anywhere:
#   bash tests/evals/own/run.sh                    # every case, CLI defaults (3 runs + baseline)
#   bash tests/evals/own/run.sh --runs 1           # one run per case
#   bash tests/evals/own/run.sh --case 'grill-*'   # some cases
# Extra arguments go to `claude plugin eval` as is.
#
# These are real, billed model runs. --trust-plugin is passed because the copy is this repo's
# own plugin, which you already run.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/own-evals.XXXXXX")"

cp -R "$ROOT/plugins/harness" "$WORK/harness"
mkdir -p "$WORK/harness/evals"
for case_dir in "$HERE"/*/; do
  [ -f "$case_dir/case.yaml" ] && cp -R "$case_dir" "$WORK/harness/evals/"
done

echo "plugin copy and results: $WORK/harness/evals/results/"
claude plugin eval "$WORK/harness" \
  --trust-plugin \
  --scaffold \
  --no-publish \
  --allow-tools Write,Edit \
  --disallow-tools AskUserQuestion \
  "$@"
