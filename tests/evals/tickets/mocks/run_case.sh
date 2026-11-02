#!/bin/bash
# Run one tickets eval case with `claude -p` in a throwaway directory. Use this, not `claude plugin eval`:
# that command has no stub, so prompt.md grants it no Bash.
# Score a run with: python3 mocks/score.py <out-dir> <case-name>
# The stub gh is first on PATH and GH_TOKEN is fake, so a run cannot reach GitHub.
# Usage: run_case.sh <case-name> <plugin-dir> <out-dir> [model]
# Output in <out-dir>: gh-calls.jsonl, questions.md, stream.jsonl, final.md, timing.json.
set -eu
CASE="$1"; PLUGIN="$(cd "$2" && pwd)"; OUT="$3"; MODEL="${4:-sonnet}"
EVALS="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
# The fixture and the stub stay outside the run's directory, so the run stays blind to them.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
BOX="$TMP/repo"; STUB="$TMP/stub"
mkdir "$BOX" "$STUB"
cp -R "$EVALS/$CASE/files/." "$BOX/"
mv "$BOX/gh-state.json" "$STUB/state.json"
cp "$STUB/state.json" "$OUT/gh-state-before.json"
cp "$EVALS/mocks/gh" "$STUB/gh"
: >"$OUT/gh-calls.jsonl"
git -C "$BOX" init -q
COMMAND=$(sed -n '/^\/harness:tickets/p' "$EVALS/$CASE/prompt.md")
OWNER=$(sed -n '/^Owner script: /p' "$EVALS/$CASE/prompt.md")
SYS="You run inside an eval. In this eval the AskUserQuestion dialog works through a file, so the dialog is available. Each time the skill says to ask the owner, use the Write tool to save the full question text and its options to a new file q1.md, q2.md and so on, then take the reply from the owner script and go on. If the owner script has no reply for a question, end the run there. $OWNER"
start=$(date +%s)
( cd "$BOX" && PATH="$STUB:$PATH" GH_TOKEN=stub-not-real GH_STUB_LOG="$OUT/gh-calls.jsonl" GH_STUB_STATE="$STUB/state.json" \
  claude -p --model "$MODEL" --plugin-dir "$PLUGIN" --strict-mcp-config --setting-sources local \
    --no-session-persistence --permission-mode default --max-turns 40 \
    --allowedTools Write --disallowedTools AskUserQuestion Agent \
    --append-system-prompt "$SYS" --output-format stream-json --verbose \
    "$COMMAND" </dev/null >"$OUT/stream.jsonl" 2>"$OUT/stderr.log" ) && rc=0 || rc=$?
cp "$STUB/state.json" "$OUT/gh-state-after.json"
: >"$OUT/questions.md"
for q in "$BOX"/q[0-9]*.md; do [ -f "$q" ] && cat "$q" >>"$OUT/questions.md"; done
ls -A "$BOX" >"$OUT/repo-files.txt"
jq -r 'select(.type=="result")|.result // ""' "$OUT/stream.jsonl" >"$OUT/final.md" || true
jq -c --argjson s "$(( $(date +%s) - start ))" 'select(.type=="result")|{total_tokens:((.usage.input_tokens//0)+(.usage.output_tokens//0)+(.usage.cache_read_input_tokens//0)+(.usage.cache_creation_input_tokens//0)),duration_ms,total_duration_seconds:$s,denials:(.permission_denials|length)}' "$OUT/stream.jsonl" >"$OUT/timing.json" || true
if [ "$rc" != 0 ] || ! grep -q '"type":"result"' "$OUT/stream.jsonl"; then
  rm -f "$OUT/timing.json"
  echo "$CASE: claude failed (exit $rc), see $OUT/stderr.log" >&2
  exit 1
fi
