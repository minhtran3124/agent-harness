#!/bin/bash
# Contract tests for hooks/render-plan-on-write.sh — render PLAN.md → PLAN.html; never blocks.
source "$(dirname "$0")/../lib.sh"

H=render-plan-on-write.sh

t "non-PLAN file → silent exit 0"
repo=$(new_repo $H)
printf 'x\n' > "$repo/README.md"
run_hook "$repo" $H "$(json_file "$repo/README.md")"
assert_silent_ok

t "PLAN.md but no render engine present → silent exit 0 (no crash)"
repo=$(new_repo $H)
mkdir -p "$repo/specs/demo"; printf '# plan\n' > "$repo/specs/demo/PLAN.md"
run_hook "$repo" $H "$(json_file "$repo/specs/demo/PLAN.md")"
assert_rc 0

# Real render: copy the actual visual-planner engine into the throwaway repo
if command -v python3 >/dev/null 2>&1 && [ -f "$ROOT/skills/visual-planner/render_plan.py" ]; then
  t "PLAN.md with the engine present → renders PLAN.html + reports the path"
  repo=$(new_repo $H)
  mkdir -p "$repo/skills/visual-planner"
  cp "$ROOT/skills/visual-planner/render_plan.py" "$repo/skills/visual-planner/"
  [ -f "$ROOT/skills/visual-planner/template.html" ] && cp "$ROOT/skills/visual-planner/template.html" "$repo/skills/visual-planner/"
  mkdir -p "$repo/specs/demo"
  cat > "$repo/specs/demo/PLAN.md" <<'EOF'
---
slug: demo
status: active
---
# Demo
## 1. Motivation
x
## 4. Tasks
```xml
<task id="1.1" wave="1"><files>a.py</files><action>do</action><verify>true</verify><done>ok</done></task>
```
EOF
  run_hook "$repo" $H "$(json_file "$repo/specs/demo/PLAN.md")"
  if [ -f "$repo/specs/demo/PLAN.html" ] && echo "$OUT" | grep -q "PLAN.html"; then pass
  else fail "rc=$RC html=$([ -f "$repo/specs/demo/PLAN.html" ] && echo yes || echo no) out:$(echo "$OUT" | head -2 | tr '\n' ' ')"; fi
  t "PLAN.md with the engine present → injects At-a-glance block, idempotent on rerun"
  repo=$(new_repo $H)
  mkdir -p "$repo/skills/visual-planner"
  cp "$ROOT/skills/visual-planner/render_plan.py" "$repo/skills/visual-planner/"
  [ -f "$ROOT/skills/visual-planner/template.html" ] && cp "$ROOT/skills/visual-planner/template.html" "$repo/skills/visual-planner/"
  mkdir -p "$repo/specs/demo"
  cat > "$repo/specs/demo/PLAN.md" <<'EOF'
---
slug: demo
status: active
---
# Demo

## 1. Motivation

x

## 4. Tasks

```xml
<task id="1.1" wave="1"><files>a.py</files><action>do</action><verify>true</verify><done>ok</done></task>
```

## Status Log
EOF
  run_hook "$repo" $H "$(json_file "$repo/specs/demo/PLAN.md")"
  if [ "$RC" -eq 0 ] && grep -q "AT-A-GLANCE:BEGIN" "$repo/specs/demo/PLAN.md"; then pass
  else fail "rc=$RC AT-A-GLANCE not injected — out:$(echo "$OUT" | head -2 | tr '\n' ' ')"; fi

  t "second run on an already-summarized PLAN.md is byte-identical (idempotent)"
  snapshot=$(mktemp); _CLEANUP_DIRS+=("$snapshot")
  cp "$repo/specs/demo/PLAN.md" "$snapshot"
  run_hook "$repo" $H "$(json_file "$repo/specs/demo/PLAN.md")"
  if [ "$RC" -eq 0 ] && cmp -s "$snapshot" "$repo/specs/demo/PLAN.md"; then pass
  else fail "rc=$RC PLAN.md changed on rerun (not idempotent)"; fi
else
  t "real render case"; skip "python3 or render_plan.py unavailable"
  t "At-a-glance injection + idempotency"; skip "python3 or render_plan.py unavailable"
fi

finish
