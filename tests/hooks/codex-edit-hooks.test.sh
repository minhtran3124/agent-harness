#!/usr/bin/env bash
# Cross-hook Codex edit-path integration: one patch envelope, three advisory consumers.
source "$(dirname "$0")/../lib.sh"

HOOKS="ruff-on-edit.sh blast-radius-check.sh render-plan-on-write.sh"

patch_payload() {
  jq -cn --arg command "$1" '{turn_id:"turn-redacted",hook_event_name:"PostToolUse",tool_name:"apply_patch",tool_input:{command:$command}}'
}

make_repo() {
  local repo
  repo=$(new_repo $HOOKS)
  mkdir -p "$repo/app" "$repo/specs/demo" "$repo/skills/visual-planner" "$repo/bin"
  printf -- '%s\n' '---' 'status: active' '---' '```xml' '<task id="1.1"><files>app/in.py, specs/demo/PLAN.md</files><action>x</action></task>' '```' > "$repo/specs/demo/PLAN.md"
  printf '#!/bin/bash\nprintf "%%s\\n" "$*" >> "$RUFF_LOG"\n' > "$repo/bin/ruff"
  chmod +x "$repo/bin/ruff"
  printf '#!/usr/bin/env python3\nimport pathlib,sys\np=pathlib.Path(sys.argv[1]); (p.parent / "PLAN.html").write_text("ok")\nprint(f"Wrote {p.parent / '\''PLAN.html'\''}")\n' > "$repo/skills/visual-planner/render_plan.py"
  chmod +x "$repo/skills/visual-planner/render_plan.py"
  printf '%s\n' "$repo"
}

t "multi-file Codex patch formats every existing Python path"
repo=$(make_repo); log="$repo/ruff.log"; : > "$log"
printf 'x=1\n' > "$repo/app/in.py"; printf 'y=2\n' > "$repo/app/other.py"
payload=$(patch_payload $'*** Begin Patch\n*** Update File: app/in.py\n*** Add File: app/other.py\n*** Update File: notes.md\n*** End Patch')
run_hook "$repo" ruff-on-edit.sh "$payload" PATH="$repo/bin:$PATH" RUFF_LOG="$log"
if [ "$RC" -eq 0 ] && [ "$(grep -c 'app/in.py' "$log")" = 2 ] && [ "$(grep -c 'app/other.py' "$log")" = 2 ]; then pass
else fail "ruff did not process both paths exactly twice (check+format): $(cat "$log")"; fi

t "multi-file Codex patch reports all out-of-plan paths in one blast-radius result"
repo=$(make_repo)
payload=$(patch_payload $'*** Begin Patch\n*** Update File: app/in.py\n*** Add File: app/out-a.py\n*** Delete File: app/out-b.py\n*** End Patch')
run_hook "$repo" blast-radius-check.sh "$payload"
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q 'app/out-a.py' && printf '%s' "$OUT" | grep -q 'app/out-b.py'; then pass
else fail "blast-radius did not report the complete path set: $OUT"; fi

t "plan renderer processes every touched PLAN.md once"
repo=$(make_repo)
mkdir -p "$repo/specs/other"; cp "$repo/specs/demo/PLAN.md" "$repo/specs/other/PLAN.md"
payload=$(patch_payload $'*** Begin Patch\n*** Update File: specs/demo/PLAN.md\n*** Update File: specs/other/PLAN.md\n*** Update File: specs/demo/PLAN.md\n*** End Patch')
run_hook "$repo" render-plan-on-write.sh "$payload"
if [ "$RC" -eq 0 ] && [ -f "$repo/specs/demo/PLAN.html" ] && [ -f "$repo/specs/other/PLAN.html" ] && [ "$(printf '%s' "$OUT" | grep -o 'auto-rendered' | wc -l | tr -d ' ')" = 2 ]; then pass
else fail "renderer did not process two deduplicated plans: $OUT"; fi

t "move/delete paths remain visible while nonexistent deleted Python files are skipped"
repo=$(make_repo); log="$repo/ruff.log"; : > "$log"; printf 'x=1\n' > "$repo/app/current.py"
payload=$(patch_payload $'*** Begin Patch\n*** Update File: app/legacy.py\n*** Move to: app/current.py\n*** Delete File: app/unused.py\n*** End Patch')
run_hook "$repo" ruff-on-edit.sh "$payload" PATH="$repo/bin:$PATH" RUFF_LOG="$log"
if [ "$RC" -eq 0 ] && grep -q 'app/current.py' "$log" && ! grep -q 'app/unused.py' "$log"; then pass
else fail "move/delete handling wrong: $(cat "$log")"; fi

for hook in $HOOKS; do
  t "$hook exposes malformed input and stays non-blocking"
  repo=$(make_repo)
  run_hook "$repo" "$hook" '{not-json'
  if [ "$RC" -eq 0 ] && [ -n "$OUT" ]; then pass
  else fail "rc=$RC output=[$OUT]"; fi
done

t "known patch with no applicable advisory path stays silent"
repo=$(make_repo)
payload=$(patch_payload $'*** Begin Patch\n*** Update File: docs/readme.md\n*** End Patch')
run_hook "$repo" ruff-on-edit.sh "$payload"
assert_silent_ok

finish
