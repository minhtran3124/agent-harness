#!/bin/bash
# Contract tests for hooks/model-config.sh — SessionStart applies harness-models.json to the
# deployed agent and skill frontmatter on `startup`/`clear` only, and never blocks a session.
# Every case runs the consumer layout: .claude/hooks/model-config.sh beside
# .claude/scripts/apply_model_config.py, inside an isolated temp git repo.
source "$(dirname "$0")/../lib.sh"

H=model-config.sh
AGENT=.claude/agents/coding.md
SKILL=.claude/skills/correctness-review/SKILL.md

# consumer_repo [--no-snapshot] [--no-applier] — echoes a temp repo with a deployed .claude/.
consumer_repo() {
  local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d")
  git -C "$d" init -q 2>/dev/null
  mkdir -p "$d/.claude/hooks" "$d/.claude/scripts" "$d/.claude/agents" \
    "$d/.claude/skills/correctness-review"
  cp "$ROOT/hooks/$H" "$d/.claude/hooks/"
  case " $* " in *" --no-applier "*) ;; *)
    cp "$ROOT/scripts/apply_model_config.py" "$d/.claude/scripts/" ;; esac
  printf '%s\n' '---' 'name: coding' 'description: Write code.' 'model: sonnet' '---' '' 'Body.' \
    > "$d/$AGENT"
  printf '%s\n' '---' 'name: correctness-review' 'description: Review a diff.' '---' '' 'Body.' \
    > "$d/$SKILL"
  case " $* " in *" --no-snapshot "*) ;; *)
    printf '%s\n' '{"agents": {"coding": {"model": "sonnet"}}, "skills": {"correctness-review": {}}}' \
      > "$d/.claude/harness-models.defaults.json" ;; esac
  echo "$d"
}

# Valid user file: one agent effort and one skill effort (spec SC-1/SC-11 shape).
user_valid() {
  printf '%s\n' '{"agents": {"coding": {"effort": "high"}}, "skills": {"correctness-review": {"effort": "high"}}}' \
    > "$1/harness-models.json"
}

# snap <repo> / unchanged <repo> — save, then compare, every target file byte for byte.
snap() { cp "$1/$AGENT" "$1/agent.before"; cp "$1/$SKILL" "$1/skill.before"; }
unchanged() { cmp -s "$1/$AGENT" "$1/agent.before" && cmp -s "$1/$SKILL" "$1/skill.before"; }

# run_consumer <repo> <source> [cwd] — runs the deployed hook copy with CLAUDE_PROJECT_DIR set.
run_consumer() {
  local repo="$1" src="$2" cwd="${3:-$1}"
  OUT=$(cd "$cwd" && printf '{"session_id":"s1","hook_event_name":"SessionStart","source":"%s"}' "$src" \
    | CLAUDE_PROJECT_DIR="$repo" bash "$repo/.claude/hooks/$H" 2>&1); RC=$?
}

# --- SC-11: startup and clear apply ---------------------------------------------------

for src in startup clear; do
  t "source=$src applies the user file to agent and skill frontmatter"
  repo=$(consumer_repo); user_valid "$repo"
  run_consumer "$repo" "$src"
  if [ "$RC" -ne 0 ]; then fail "rc=$RC (want 0) out: $OUT"
  elif ! grep -qx 'effort: high' "$repo/$AGENT"; then fail "agent lacks effort: high: $(cat "$repo/$AGENT")"
  elif ! grep -qx 'model: sonnet' "$repo/$AGENT"; then fail "agent lost model: sonnet"
  elif ! grep -qx 'effort: high' "$repo/$SKILL"; then fail "skill lacks effort: high: $(cat "$repo/$SKILL")"
  elif ! printf '%s' "$OUT" | jq -e '.hookSpecificOutput.hookEventName == "SessionStart"' >/dev/null 2>&1; then
    fail "output is not SessionStart hook JSON: $OUT"
  elif ! printf '%s' "$OUT" | jq -e '.hookSpecificOutput.reloadSkills == true' >/dev/null 2>&1; then
    fail "a skill file changed but reloadSkills is not true: $OUT"
  else pass; fi
done

# --- SC-11: resume, compact and fork leave every target byte-identical ------------------

for src in resume compact fork; do
  t "source=$src leaves every target byte-identical, silent exit 0"
  repo=$(consumer_repo); user_valid "$repo"; snap "$repo"
  run_consumer "$repo" "$src"
  if [ "$RC" -ne 0 ] || [ -n "$OUT" ]; then fail "want silent rc=0; rc=$RC out: $OUT"
  elif ! unchanged "$repo"; then fail "a target file changed on $src"
  else pass; fi
done

# --- SC-11: invalid file warns, exits 0, writes nothing --------------------------------

t "invalid user file → exit 0, warning in additionalContext, no target written"
repo=$(consumer_repo)
printf '%s\n' '{"agents": {"coding": {"effort": "ultra"}}}' > "$repo/harness-models.json"
snap "$repo"
run_consumer "$repo" startup
if [ "$RC" -ne 0 ]; then fail "rc=$RC (want 0) out: $OUT"
elif ! unchanged "$repo"; then fail "a target file changed despite the invalid file"
elif ! printf '%s' "$OUT" | jq -r '.hookSpecificOutput.additionalContext' 2>/dev/null \
    | grep -q 'last applied values stay'; then fail "expected the invalid-file warning: $OUT"
else pass; fi

# --- SC-11: no snapshot → silent exit 0 -------------------------------------------------

t "defaults snapshot missing → silent exit 0, no target written"
repo=$(consumer_repo --no-snapshot); user_valid "$repo"; snap "$repo"
run_consumer "$repo" startup
if [ "$RC" -ne 0 ] || [ -n "$OUT" ]; then fail "want silent rc=0; rc=$RC out: $OUT"
elif ! unchanged "$repo"; then fail "a target file changed with no snapshot"
else pass; fi

t "applier absent from the deployed tree → silent exit 0"
repo=$(consumer_repo --no-applier); user_valid "$repo"; snap "$repo"
run_consumer "$repo" startup
if [ "$RC" -ne 0 ] || [ -n "$OUT" ]; then fail "want silent rc=0; rc=$RC out: $OUT"
elif ! unchanged "$repo"; then fail "a target file changed with no applier"
else pass; fi

t "unparseable stdin → silent exit 0"
repo=$(consumer_repo); user_valid "$repo"; snap "$repo"
OUT=$(cd "$repo" && printf 'not json' | CLAUDE_PROJECT_DIR="$repo" bash ".claude/hooks/$H" 2>&1); RC=$?
if [ "$RC" -ne 0 ] || [ -n "$OUT" ]; then fail "want silent rc=0; rc=$RC out: $OUT"
elif ! unchanged "$repo"; then fail "a target file changed on bad stdin"
else pass; fi

# --- Root resolution --------------------------------------------------------------------

t "root comes from CLAUDE_PROJECT_DIR, not the working directory"
repo=$(consumer_repo); user_valid "$repo"
elsewhere=$(mktemp -d); _CLEANUP_DIRS+=("$elsewhere")
run_consumer "$repo" startup "$elsewhere"
if [ "$RC" -eq 0 ] && grep -qx 'effort: high' "$repo/$AGENT"; then pass
else fail "CLAUDE_PROJECT_DIR not honoured — rc=$RC out: $OUT"; fi

t "no CLAUDE_PROJECT_DIR → root from git rev-parse of the working directory"
repo=$(consumer_repo); user_valid "$repo"
OUT=$(cd "$repo" && printf '{"source":"startup"}' | env -u CLAUDE_PROJECT_DIR bash ".claude/hooks/$H" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && grep -qx 'effort: high' "$repo/$AGENT"; then pass
else fail "git fallback root not used — rc=$RC out: $OUT"; fi

# --- SC-11 / A7: one startup run under the 1 s budget -----------------------------------

t "one startup run completes in under 1 s (budget)"
repo=$(consumer_repo); user_valid "$repo"
_t0=$(python3 -c 'import time; print(time.time())')
run_consumer "$repo" startup
_t1=$(python3 -c 'import time; print(time.time())')
_elapsed=$(python3 -c "print(round($_t1 - $_t0, 3))")
if [ "$RC" -eq 0 ] && python3 -c "import sys; sys.exit(0 if $_t1 - $_t0 < 1.0 else 1)"; then pass
else fail "rc=$RC elapsed=${_elapsed}s (budget 1 s)"; fi

finish
