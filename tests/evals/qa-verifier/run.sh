#!/usr/bin/env bash
# Run the qa-verifier eval cases with `claude plugin eval`. Same method as tests/evals/own/run.sh.
# The plugin, the cases and the fixtures are copied to a temp directory; the repo is not written to.
#
# Usage, from anywhere:
#   bash tests/evals/qa-verifier/run.sh --runs 1
#   bash tests/evals/qa-verifier/run.sh --case 'fails-*'
# Extra arguments go to `claude plugin eval` as is. These are real, billed model runs.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/qa-verifier-evals.XXXXXX")"

cp -R "$ROOT/plugins/harness" "$WORK/harness"
mkdir -p "$WORK/harness/evals/fixtures"
cp -R "$ROOT/tests/fixtures/qa-verifier" "$WORK/harness/evals/fixtures/qa-verifier"
for case_dir in "$HERE"/*/; do
  [ -f "$case_dir/case.yaml" ] && cp -R "$case_dir" "$WORK/harness/evals/"
done
# place-files.sh finds the fixtures at ../fixtures/qa-verifier from a copied case folder.

echo "plugin copy and results: $WORK/harness/evals/results/"
claude plugin eval "$WORK/harness" \
  --trust-plugin \
  --scaffold \
  --no-publish \
  --allow-tools Write,Edit,Bash \
  --disallow-tools AskUserQuestion \
  "$@"
