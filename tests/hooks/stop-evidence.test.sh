#!/bin/bash
# Contract tests for hooks/stop-evidence.sh (Stop hook: "Done needs real command output").
#
# Contract under test (design: specs/stop-hook-evidence/design.md, decisions D1-D4):
#   stdin   Stop JSON {transcript_path, cwd, stop_hook_active, ...}; CWD = the repo.
#   trigger a code diff (git status; docs and specs files ignored) AND no Bash tool_result in the transcript.
#   judge   `$STOP_EVIDENCE_JUDGE_CMD <model>` (prompt on stdin) prints one JSON line
#           {"severity":"pass|light|severe","reason":"..."}. The test sets it to a stub.
#           Main model from the transcript: sonnet -> judge model "opus"; opus -> no judge unless the risk floor matches.
#   floor   changed path under hooks/ or scripts/ (or a secret/auth word in the diff) = severe floor.
#   output  block = exit 0 + stdout {"decision":"block","reason":"..."}; pass = exit 0, empty stdout.
#   light   blocks once: passes when stop_hook_active is true.   severe: blocks even when active.
#   errors  judge fails or prints junk: light diff passes (fail open); floor diff blocks (fail closed).
#   guard   STOP_EVIDENCE_GUARD set = exit 0 at once (the judge subprocess must not recurse).
source "$(dirname "$0")/../lib.sh"

H=stop-evidence.sh
J=stop-evidence-judge.md
FX="$ROOT/tests/fixtures/stop-evidence"
STUBLOG=$(mktemp); _CLEANUP_DIRS+=("$STUBLOG")

# stub <name> <json-or-FAIL> -> path of a judge stub that logs its model argument
stub() {
  local s; s=$(mktemp); _CLEANUP_DIRS+=("$s")
  if [ "$2" = FAIL ]; then
    printf '#!/bin/bash\necho "$1" >> "%s"\ncat >/dev/null\nexit 1\n' "$STUBLOG" > "$s"
  else
    printf '#!/bin/bash\necho "$1" >> "%s"\ncat >/dev/null\necho '"'%s'"'\n' "$STUBLOG" "$2" > "$s"
  fi
  chmod +x "$s"; echo "$s"
}
# repo_with <relpath> -> repo with a base commit and an unstaged edit to that path
repo_with() {
  local r; r=$(new_repo $H $J)
  stage "$r" "$1" 'v1'; git -C "$r" commit -qm base
  printf 'v2\n' > "$r/$1"
  echo "$r"
}
stop_json() { # stop_json <transcript-file> <active true|false>
  printf '{"session_id":"s","transcript_path":"%s","cwd":".","hook_event_name":"Stop","stop_hook_active":%s}' "$1" "$2"
}
run_stop() { # run_stop <repo> <transcript> <active> <stub> [VAR=val ...]
  local r="$1" tr="$2" act="$3" st="$4"; shift 4
  : > "$STUBLOG"
  run_hook "$r" $H "$(stop_json "$tr" "$act")" STOP_EVIDENCE_JUDGE_CMD="$st" "$@"
}
judge_calls() { wc -l < "$STUBLOG" | tr -d ' '; }
assert_pass()  { if [ "$RC" = 0 ] && [ -z "$OUT" ]; then pass; else fail "want exit 0 and no output; rc=$RC out=$(echo "$OUT" | head -3 | tr '\n' ' ')"; fi; }
assert_block() { if [ "$RC" = 0 ] && printf '%s' "$OUT" | grep -qF '"decision":"block"'; then pass; else fail "want exit 0 and a block; rc=$RC out=$(echo "$OUT" | head -3 | tr '\n' ' ')"; fi; }
assert_pass_no_judge() { if [ "$RC" = 0 ] && [ -z "$OUT" ] && [ "$(judge_calls)" = 0 ]; then pass; else fail "rc=$RC out=$OUT judge calls=$(judge_calls)"; fi; }

LIGHT=$(stub light '{"severity":"light","reason":"no test output"}')
SEVERE=$(stub severe '{"severity":"severe","reason":"auth change, nothing ran"}')
PASSV=$(stub pass '{"severity":"pass","reason":"evidence fits"}')
BAD=$(stub bad FAIL)
JUNK=$(stub junk 'not json')

R=$(new_repo $H $J); stage "$R" src/app.py 'v1'; git -C "$R" commit -qm base
t "no diff: passes silently"
run_stop "$R" "$FX/sonnet-no-evidence.jsonl" false "$LIGHT"; assert_pass

R=$(repo_with README.md)
t "docs-only diff: passes silently, judge not called"
run_stop "$R" "$FX/sonnet-no-evidence.jsonl" false "$LIGHT"; assert_pass_no_judge

R=$(repo_with src/app.py)
t "code diff, no output, judge says light: blocks once"
run_stop "$R" "$FX/sonnet-no-evidence.jsonl" false "$LIGHT"; assert_block

t "sonnet main: the judge runs with model opus"
if [ "$(cat "$STUBLOG")" = opus ]; then pass; else fail "judge calls: $(cat "$STUBLOG")"; fi

t "light verdict with stop_hook_active true: passes (blocks only once)"
run_stop "$R" "$FX/sonnet-no-evidence.jsonl" true "$LIGHT"; assert_pass

t "severe verdict blocks even when stop_hook_active is true"
run_stop "$R" "$FX/sonnet-no-evidence.jsonl" true "$SEVERE"; assert_block

t "judge says pass: passes"
run_stop "$R" "$FX/sonnet-no-evidence.jsonl" false "$PASSV"; assert_pass

t "a Bash tool_result in the transcript counts as evidence: passes, judge not called"
run_stop "$R" "$FX/sonnet-with-evidence.jsonl" false "$SEVERE"; assert_pass_no_judge

t "judge exits non-zero on a light diff: fails open"
run_stop "$R" "$FX/sonnet-no-evidence.jsonl" false "$BAD"; assert_pass

t "judge prints junk on a light diff: fails open"
run_stop "$R" "$FX/sonnet-no-evidence.jsonl" false "$JUNK"; assert_pass

t "unreadable transcript on a light diff: fails open"
run_stop "$R" "/nonexistent/t.jsonl" false "$LIGHT"; assert_pass

t "guard env set: exits 0 at once, judge not called"
run_stop "$R" "$FX/sonnet-no-evidence.jsonl" false "$SEVERE" STOP_EVIDENCE_GUARD=1; assert_pass_no_judge

t "opus main, no risk floor: one light block, judge not called"
run_stop "$R" "$FX/opus-no-evidence.jsonl" false "$SEVERE"
if [ "$RC" = 0 ] && printf '%s' "$OUT" | grep -qF '"decision":"block"' && [ "$(judge_calls)" = 0 ]; then pass; else fail "rc=$RC out=$OUT calls=$(judge_calls)"; fi

t "opus main, light block already given (active true): passes"
run_stop "$R" "$FX/opus-no-evidence.jsonl" true "$SEVERE"; assert_pass

F=$(repo_with scripts/deploy.sh)
t "risk floor (scripts/), judge fails: fails closed (blocks)"
run_stop "$F" "$FX/sonnet-no-evidence.jsonl" false "$BAD"; assert_block

t "risk floor (scripts/), judge fails, stop_hook_active true: still blocks"
run_stop "$F" "$FX/sonnet-no-evidence.jsonl" true "$BAD"; assert_block

t "risk floor, opus main: the judge is called with model opus"
run_stop "$F" "$FX/opus-no-evidence.jsonl" false "$PASSV"
if [ "$RC" = 0 ] && [ "$(cat "$STUBLOG")" = opus ]; then pass; else fail "rc=$RC calls: $(cat "$STUBLOG")"; fi

A=$(repo_with src/login.py)
printf 'password = request.get("password")\n' > "$A/src/login.py"
t "auth word in the diff counts as the risk floor: judge fails, blocks"
run_stop "$A" "$FX/sonnet-no-evidence.jsonl" false "$BAD"; assert_block

finish
