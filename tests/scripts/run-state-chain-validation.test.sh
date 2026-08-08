#!/bin/bash
# Executable guard for subagent-driven-development's --check claim (GitHub issue #174).
#
# Scope, and why this is not a duplicate of runtime/test_run_state.py: the pytest suite
# calls validate_chain() and cmd_rebuild() as Python functions, in-process. This suite
# asserts the CLI CONTRACT AS THE SKILL INVOKES IT -- argv in, exit code and combined
# stdout+stderr text out (rs() merges the streams, and `matches events.jsonl` is on stdout
# while the warnings are on stderr) -- because that is what
# skills/subagent-driven-development/SKILL.md actually tells a
# resuming session to run. Per
# docs/solutions/harness/prose-encoded-state-logic-accrues-contradiction-chains.md ("assert
# executability, not wording"), a test that greps SKILL.md for a phrase would pass even if
# the engine did nothing; this one runs the real subprocess and checks what it does. The
# case list below reproduces the issue's forged log verbatim -- SKILL.md used to claim
# `rebuild --check` on it exits 0; it must exit 3.
#
# Hermetic: the engine resolves `specs/<slug>` relative to CWD (there is no --specs-root
# flag), so each case runs inside its own mktemp dir. Nothing in the real repo is touched.
source "$(dirname "$0")/../lib.sh"

ENGINE="$ROOT/runtime/run_state.py"
SLUG="gh-174-forged-chain"

# rs <args...> — run the CLI inside $SANDBOX; sets OUT (stdout+stderr) and RC.
rs() { OUT=$(cd "$SANDBOX" && python3 "$ENGINE" "$@" 2>&1); RC=$?; }

new_sandbox() {
  SANDBOX=$(mktemp -d); _CLEANUP_DIRS+=("$SANDBOX")
  mkdir -p "$SANDBOX/specs/$SLUG"
}

LOG() { echo "$SANDBOX/specs/$1/events.jsonl"; }
# Byte-level fingerprint (size + checksum). `wc -l` cannot see an in-place rewrite of an
# existing event, nor an append with no trailing newline — both would leave the line count
# unchanged while mutating the audit log. cksum is POSIX, present on macOS and Linux.
digest() { [ -f "$1" ] && cksum < "$1" || echo "absent"; }

# write_forged_log <slug> — the issue's exact forged log: two lines, both seq 1, the
# second event from a different run_id than the first. Written by hand directly into the
# sandbox (not via the CLI), simulating an externally-corrupted or hand-edited
# events.jsonl reaching the engine.
write_forged_log() {
  cat > "$(LOG "$1")" <<EOF
{"event":"run.init","event_id":"a","seq":1,"ts":"2026-01-01T00:00:00Z","slug":"$1","run_id":"r1","from_state":null,"to_state":"queued","waiting_on":null,"resume_event":null,"sha":null,"metadata":{}}
{"event":"ci.merged","event_id":"b","seq":1,"ts":"2026-01-02T00:00:00Z","slug":"$1","run_id":"r2","from_state":"verifying","to_state":"shipped","waiting_on":null,"resume_event":null,"sha":"deadbee","metadata":{}}
EOF
}

# --------------------------------------------------------------------------- #
# Case 1 — the issue's exact forged log: `rebuild --check` must refuse it. This is
# the case SKILL.md:82-90 used to claim exits 0.
# --------------------------------------------------------------------------- #
new_sandbox
write_forged_log "$SLUG"

t "rebuild --check on the forged (duplicate-seq) log exits 3 and reports invalid event chain"
rs rebuild --slug "$SLUG" --check
if [ "$RC" -eq 3 ] && echo "$OUT" | grep -qF "invalid event chain"; then pass
else fail "rc=$RC out: $OUT"; fi

# --------------------------------------------------------------------------- #
# Case 2 — same forged log: plain `rebuild` (no --check) must also refuse, and must
# leave RUN.json absent — a wrong or partial projection would be worse than none.
#
# MUST run before case 3, which seeds RUN.json into this same sandbox. The message grep is
# load-bearing: exit 3 alone also fires for `missing:` / `empty event log` / `corrupt event
# log`, so without it a sandbox with no events.jsonl at all would pass this case.
# --------------------------------------------------------------------------- #
runjson="$SANDBOX/specs/$SLUG/RUN.json"
t "rebuild (no --check) on the forged log exits 3 and writes no RUN.json"
rs rebuild --slug "$SLUG"
if [ "$RC" -eq 3 ] && [ ! -f "$runjson" ] && echo "$OUT" | grep -qF "invalid event chain"; then pass
else fail "rc=$RC, RUN.json exists=$([ -f "$runjson" ] && echo yes || echo no), out: $OUT"; fi

# --------------------------------------------------------------------------- #
# Case 3 — the --allow-invalid-chain opt-out, and drift detection layered on top of
# it. RUN.json must be SEEDED first via `rebuild --allow-invalid-chain`: without that
# seeding step the sandbox has no RUN.json, `read_json` raises `missing: …`, --check
# exits 3 for an unrelated reason, and the case would pass for the wrong cause. The
# assertions below key on the distinguishing message text (not just the exit code) so
# a `missing:` failure cannot masquerade as a pass.
# --------------------------------------------------------------------------- #
t "rebuild --allow-invalid-chain seeds RUN.json from the forged log (warns, exits 0)"
rs rebuild --slug "$SLUG" --allow-invalid-chain
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF "chain validation skipped"; then pass
else fail "rc=$RC out: $OUT"; fi

t "rebuild --check --allow-invalid-chain on the now-seeded RUN.json matches (exit 0, distinct UNVALIDATED verdict, warning present)"
rs rebuild --slug "$SLUG" --check --allow-invalid-chain
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF "matches an UNVALIDATED fold" \
   && ! echo "$OUT" | grep -qF "matches events.jsonl" \
   && echo "$OUT" | grep -qF "chain validation skipped"; then pass
else fail "rc=$RC out: $OUT"; fi

# stdout-only variant: a consumer capturing stdout alone (the `2>/dev/null` idiom used by
# hooks/session-knowledge.sh and scripts/harness-status.sh) must see the UNVALIDATED verdict,
# not the byte-identical "matches events.jsonl" a fully validated pass would print.
t "rebuild --check --allow-invalid-chain: stdout alone (2>/dev/null) is distinguishable from a validated pass"
stdout_only=$(cd "$SANDBOX" && python3 "$ENGINE" rebuild --slug "$SLUG" --check --allow-invalid-chain 2>/dev/null)
rc_only=$?
if [ "$rc_only" -eq 0 ] && echo "$stdout_only" | grep -qF "matches an UNVALIDATED fold" \
   && ! echo "$stdout_only" | grep -qF "matches events.jsonl"; then pass
else fail "rc=$rc_only stdout: $stdout_only"; fi

t "mutating RUN.json then rebuild --check --allow-invalid-chain detects drift (exit 3, DRIFT:)"
python3 -c "
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d['seq'] = 99
json.dump(d, open(p, 'w'))
" "$runjson"
rs rebuild --slug "$SLUG" --check --allow-invalid-chain
if [ "$RC" -eq 3 ] && echo "$OUT" | grep -qF "DRIFT:"; then pass
else fail "rc=$RC out: $OUT"; fi

# --------------------------------------------------------------------------- #
# Case 4 — a real, engine-generated 3-event log (init, then two legal hops) must be
# ACCEPTED. Guards against a validator that is simply too strict and rejects
# histories the engine itself produces.
# --------------------------------------------------------------------------- #
new_sandbox
SLUG4="gh-174-real-chain"; mkdir -p "$SANDBOX/specs/$SLUG4"
rs init --slug "$SLUG4"
rs transition --slug "$SLUG4" --to investigating --event "feature-intake classified"
rs transition --slug "$SLUG4" --to planning      --event "writing-plans drafted PLAN.md"

t "rebuild --check on an engine-generated, legally-chained log exits 0"
rs rebuild --slug "$SLUG4" --check
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF "matches events.jsonl"; then pass
else fail "rc=$RC out: $OUT"; fi

# --------------------------------------------------------------------------- #
# Case 5 — `transition` must refuse a forged log too (not just `rebuild`), and the
# refusal must leave the log byte-identical: cksum, since a rewrite-in-place or a
# trailing-newline change would not move the line count `wc -l` would see.
# --------------------------------------------------------------------------- #
new_sandbox
write_forged_log "$SLUG"
before=$(digest "$(LOG "$SLUG")")

t "transition against the forged log exits 3 and leaves the log byte-identical"
rs transition --slug "$SLUG" --to implementing --event x
after=$(digest "$(LOG "$SLUG")")
if [ "$RC" -eq 3 ] && echo "$OUT" | grep -qF "invalid event chain" && [ "$before" = "$after" ]; then pass
else fail "rc=$RC, cksum [$before] -> [$after], out: $OUT"; fi

# --------------------------------------------------------------------------- #
# Case 6 — the issue's exact THIRD repro line. Before Fix 1, `status` read
# RUN.json directly and never touched the event log, so even after
# `rebuild --allow-invalid-chain` seeded a RUN.json reporting the forged log's
# fold (state=shipped) `status` happily printed it and exited 0 — the repro this
# case exists to close. `status` must now validate the chain itself and refuse,
# regardless of what RUN.json already says.
# --------------------------------------------------------------------------- #
rs rebuild --slug "$SLUG" --allow-invalid-chain   # seeds RUN.json state=shipped, same forged log as case 5

t "status on the seeded RUN.json for the forged log exits 3, not the issue's old 'state: shipped ... exit 0'"
rs status --slug "$SLUG"
if [ "$RC" -eq 3 ] && echo "$OUT" | grep -qF "invalid event chain"; then pass
else fail "rc=$RC out: $OUT"; fi

# --------------------------------------------------------------------------- #
# Case 7 — Fix 2: a bricked run (this same forged log) must be closeable via a
# transition to a terminal, non-shipped target. Proves the CLI contract, not just
# the Python unit-level behavior already pinned in runtime/test_run_state.py.
# --------------------------------------------------------------------------- #
t "transition --to cancelled on the forged log closes it (exit 0, loud stderr warning)"
rs transition --slug "$SLUG" --to cancelled --event "operator.abandon"
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF "INVALID event chain" && echo "$OUT" | grep -qF "closed over invalid chain"; then pass
else fail "rc=$RC out: $OUT"; fi

t "after closing, RUN.json reports the closed state (so list --active stops advertising it)"
runjson="$SANDBOX/specs/$SLUG/RUN.json"
runjson_state=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['state'])" "$runjson" 2>/dev/null || true)
if [ "$runjson_state" = "cancelled" ]; then pass
else fail "RUN.json state=$runjson_state, want cancelled"; fi

t "status on the closed run still exits 3 — closing abandons the run, it does not repair its history"
rs status --slug "$SLUG"
if [ "$RC" -eq 3 ] && echo "$OUT" | grep -qF "invalid event chain"; then pass
else fail "rc=$RC out: $OUT"; fi

t "transition --to shipped on the same forged log stays hard-blocked (no bypass beyond cancelled/superseded)"
rs transition --slug "$SLUG" --to shipped --event x --sha abc1234
if [ "$RC" -eq 3 ] && echo "$OUT" | grep -qF "invalid event chain"; then pass
else fail "rc=$RC out: $OUT"; fi

finish
