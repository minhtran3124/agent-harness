#!/bin/bash
# Contract tests for hooks/state-breadcrumb.sh — SessionEnd appends to specs/STATE.md,
# idempotent per session_id, never blocks. (Hook silences stderr, so assert on the file.)
source "$(dirname "$0")/../lib.sh"

H=state-breadcrumb.sh

# session JSON with a given id; cwd points at the repo so git/last_commit resolve
sess() { printf '{"session_id":"%s","matcher_value":"clear","cwd":"%s","transcript_path":""}' "$1" "$2"; }

t "session_id + existing STATE.md → appends a Session End Log entry"
repo=$(new_repo $H)
mkdir -p "$repo/specs"; printf '# State\n' > "$repo/specs/STATE.md"
run_hook "$repo" $H "$(sess sess-aaa "$repo")" CLAUDE_PROJECT_DIR="$repo"
if grep -q "## Session End Log" "$repo/specs/STATE.md" && grep -q "session_id: sess-aaa" "$repo/specs/STATE.md"; then pass
else fail "STATE.md not updated: $(cat "$repo/specs/STATE.md" | tr '\n' '|')"; fi

t "idempotent — same session_id twice yields one entry"
run_hook "$repo" $H "$(sess sess-aaa "$repo")" CLAUDE_PROJECT_DIR="$repo"
n=$(grep -c "session_id: sess-aaa" "$repo/specs/STATE.md")
if [ "$n" -eq 1 ]; then pass; else fail "expected 1 entry, got $n"; fi

t "no session_id → no write, exit 0"
repo=$(new_repo $H)
mkdir -p "$repo/specs"; printf '# State\n' > "$repo/specs/STATE.md"
before=$(cat "$repo/specs/STATE.md")
run_hook "$repo" $H '{"matcher_value":"clear"}' CLAUDE_PROJECT_DIR="$repo"
if [ "$RC" -eq 0 ] && [ "$(cat "$repo/specs/STATE.md")" = "$before" ]; then pass; else fail "STATE.md changed or rc=$RC"; fi

t "no STATE.md present → silent exit 0, nothing created"
repo=$(new_repo $H)
run_hook "$repo" $H "$(sess sess-bbb "$repo")" CLAUDE_PROJECT_DIR="$repo"
if [ "$RC" -eq 0 ] && [ ! -f "$repo/specs/STATE.md" ]; then pass; else fail "rc=$RC or STATE.md was created"; fi

finish
