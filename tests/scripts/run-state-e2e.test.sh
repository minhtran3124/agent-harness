#!/bin/bash
# End-to-end lifecycle test for runtime/run_state.py (GitHub issue #129).
#
# Scope, and why this is not a duplicate of runtime/test_run_state.py: the pytest suite
# covers each function and each rule in isolation. This one drives the REAL CLI through a
# whole realistic run — intake -> plan -> implement -> CI failure -> review round -> ship —
# and then asserts on the DURABLE ARTIFACTS the harness checkpoints actually leave behind:
# the shape of events.jsonl, seq contiguity across the full run, and the invariant that a
# refused transition appends nothing. A per-function test cannot catch a defect that only
# appears after a long chain of states.
#
# Hermetic: the engine resolves `specs/<slug>` relative to CWD (there is no --specs-root
# flag), so each case runs inside its own mktemp dir. Nothing in the real repo is touched.
source "$(dirname "$0")/../lib.sh"

ENGINE="$ROOT/runtime/run_state.py"
SLUG="gh-207-checkout-rate-limit"

# rs <args...> — run the CLI inside $SANDBOX; sets OUT (stdout+stderr) and RC.
rs() { OUT=$(cd "$SANDBOX" && python3 "$ENGINE" "$@" 2>&1); RC=$?; }

new_sandbox() {
  SANDBOX=$(mktemp -d); _CLEANUP_DIRS+=("$SANDBOX")
  mkdir -p "$SANDBOX/specs/$SLUG"
}

LOG() { echo "$SANDBOX/specs/$1/events.jsonl"; }
lines() { [ -f "$1" ] && wc -l < "$1" | tr -d ' ' || echo 0; }

# Drive the full lifecycle. Echoes nothing; leaves the run at `shipped`.
run_full_lifecycle() {
  rs init --slug "$SLUG"
  rs transition --slug "$SLUG" --to investigating     --event "feature-intake classified: normal lane"
  rs transition --slug "$SLUG" --to planning          --event "writing-plans drafted PLAN.md"
  rs transition --slug "$SLUG" --to implementing      --event "wave 1 dispatched" --sha 1a2b3c4
  rs transition --slug "$SLUG" --to verifying         --event "wave 1 green" --sha 5d6e7f8
  rs transition --slug "$SLUG" --to awaiting_ci       --event "PR opened" --waiting-on "github-actions/harness-ci"
  rs transition --slug "$SLUG" --to fixing_ci         --event "harness-ci failed on ubuntu"
  rs transition --slug "$SLUG" --to awaiting_ci       --event "pushed fix" --sha 9a0b1c2 --waiting-on "github-actions/harness-ci"
  rs transition --slug "$SLUG" --to awaiting_review   --event "CI green" --waiting-on "reviewer:someone"
  rs transition --slug "$SLUG" --to addressing_review --event "2 review comments"
  rs transition --slug "$SLUG" --to verifying         --event "re-ran suite" --sha 3d4e5f6
  rs transition --slug "$SLUG" --to awaiting_ci       --event "re-push" --waiting-on "github-actions/harness-ci"
  rs transition --slug "$SLUG" --to awaiting_review   --event "CI green again" --waiting-on "reviewer:someone"
  rs transition --slug "$SLUG" --to ready_to_merge    --event "approved"
  rs transition --slug "$SLUG" --to shipped           --event "merged" --sha f00dcafe
}

# --------------------------------------------------------------------------- #
# Happy path: a realistic run with a CI-failure loop and a review loop.
# --------------------------------------------------------------------------- #
new_sandbox
run_full_lifecycle
LOGF=$(LOG "$SLUG")

t "the full lifecycle (15 checkpoints) leaves the run shipped"
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -q "ready_to_merge -> shipped"; then pass
else fail "last transition rc=$RC out: $OUT"; fi

t "every checkpoint appended exactly one event (15 lines)"
n=$(lines "$LOGF")
if [ "$n" -eq 15 ]; then pass; else fail "events.jsonl has $n lines, want 15"; fi

t "seq is contiguous 1..15 with no gaps or reuse"
seqs=$(python3 -c "
import json,sys
s=[json.loads(l)['seq'] for l in open(sys.argv[1]) if l.strip()]
print('ok' if s==list(range(1,len(s)+1)) else s)" "$LOGF")
if [ "$seqs" = "ok" ]; then pass; else fail "seq sequence was $seqs"; fi

t "every event carries the full required key set"
missing=$(python3 -c "
import json,sys
need={'event','event_id','from_state','to_state','run_id','seq','slug','ts','sha','waiting_on','metadata'}
bad=[]
for i,l in enumerate(open(sys.argv[1]),1):
    if l.strip() and not need <= set(json.loads(l)): bad.append(i)
print(','.join(map(str,bad)) or 'ok')" "$LOGF")
if [ "$missing" = "ok" ]; then pass; else fail "lines missing required keys: $missing"; fi

t "from_state of each event chains to the previous to_state"
chain=$(python3 -c "
import json,sys
ev=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]
bad=[e['seq'] for a,e in zip(ev,ev[1:]) if e['from_state']!=a['to_state']]
print(','.join(map(str,bad)) or 'ok')" "$LOGF")
if [ "$chain" = "ok" ]; then pass; else fail "broken from_state chain at seq: $chain"; fi

t "keys are serialized sorted, so the log stays diff-stable"
unsorted=$(python3 -c "
import json,sys
bad=[i for i,l in enumerate(open(sys.argv[1]),1)
     if l.strip() and list(json.loads(l))!=sorted(json.loads(l))]
print(','.join(map(str,bad)) or 'ok')" "$LOGF")
if [ "$unsorted" = "ok" ]; then pass; else fail "unsorted keys on lines: $unsorted"; fi

t "the CI-failure loop is recorded, not smoothed over"
if grep -q '"to_state": "fixing_ci"' "$LOGF"; then pass
else fail "no fixing_ci event — the CI failure left no trace"; fi

t "waiting_on is carried on the events that entered a waiting state"
w=$(python3 -c "
import json,sys
ev=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]
wait={'awaiting_ci','awaiting_review','awaiting_confirmation'}
print('ok' if all(e['waiting_on'] for e in ev if e['to_state'] in wait) else 'missing')" "$LOGF")
if [ "$w" = "ok" ]; then pass; else fail "a waiting-state event has an empty waiting_on"; fi

t "RUN.json projects the final state and the last seq"
rs status --slug "$SLUG" --json
if echo "$OUT" | grep -q '"state": "shipped"' && echo "$OUT" | grep -q '"seq": 15'; then pass
else fail "status: $OUT"; fi

t "rebuild --check confirms RUN.json matches the replayed log"
rs rebuild --slug "$SLUG" --check
assert_rc 0

# --------------------------------------------------------------------------- #
# The append-nothing invariant — the property that makes the log trustworthy.
# --------------------------------------------------------------------------- #
t "a post-terminal transition is refused (exit 2) and appends nothing"
before=$(lines "$LOGF")
rs transition --slug "$SLUG" --to implementing --event "reopen after ship"
after=$(lines "$LOGF")
if [ "$RC" -eq 2 ] && [ "$before" -eq "$after" ]; then pass
else fail "rc=$RC (want 2), lines $before -> $after"; fi

t "entering a waiting state without --waiting-on is refused and appends nothing"
new_sandbox
rs init --slug "$SLUG"
rs transition --slug "$SLUG" --to investigating --event i
rs transition --slug "$SLUG" --to planning --event p
rs transition --slug "$SLUG" --to implementing --event im
rs transition --slug "$SLUG" --to verifying --event v
L2=$(LOG "$SLUG"); before=$(lines "$L2")
rs transition --slug "$SLUG" --to awaiting_ci --event "no waiting-on"
after=$(lines "$L2")
if [ "$RC" -eq 2 ] && [ "$before" -eq "$after" ]; then pass
else fail "rc=$RC (want 2), lines $before -> $after"; fi

t "a run that only ever gets refused transitions keeps a 1-line log"
new_sandbox
SLUG2="gh-208-skip-check"; mkdir -p "$SANDBOX/specs/$SLUG2"
rs init --slug "$SLUG2"
rs transition --slug "$SLUG2" --to shipped   --event "skip the whole FSM"
rs transition --slug "$SLUG2" --to queued    --event "self transition"
rs transition --slug "$SLUG2" --to verifying --event "jump ahead"
n=$(lines "$(LOG "$SLUG2")")
if [ "$n" -eq 1 ]; then pass; else fail "log grew to $n lines from refused transitions alone"; fi

t "an idempotent replay returns 0 without appending or bumping seq"
rs transition --slug "$SLUG2" --to investigating --event "intake" --event-id evt-fixed-001
before=$(lines "$(LOG "$SLUG2")")
rs transition --slug "$SLUG2" --to investigating --event "intake" --event-id evt-fixed-001
after=$(lines "$(LOG "$SLUG2")")
seq=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['seq'])" "$SANDBOX/specs/$SLUG2/RUN.json")
if [ "$RC" -eq 0 ] && [ "$before" -eq "$after" ] && [ "$seq" -eq 2 ]; then pass
else fail "rc=$RC, lines $before -> $after, seq=$seq (want rc=0, no growth, seq=2)"; fi

t "list --active shows the unfinished run and omits the shipped one"
rs list --active
if echo "$OUT" | grep -q "$SLUG2" && ! echo "$OUT" | grep -q "shipped"; then pass
else fail "list --active: $OUT"; fi

finish
