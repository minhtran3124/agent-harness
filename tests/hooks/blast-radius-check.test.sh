#!/bin/bash
# Contract tests for hooks/blast-radius-check.sh — flag edits outside the active PLAN <files>.
source "$(dirname "$0")/../lib.sh"

H=blast-radius-check.sh

# make_plan <repo> <status> <files-csv>
make_plan() {
  mkdir -p "$1/specs/demo"
  cat > "$1/specs/demo/PLAN.md" <<EOF
---
status: $2
---
\`\`\`xml
<task id="1.1"><files>$3</files><action>x</action></task>
\`\`\`
EOF
}

t "no PLAN.md present → silent (not in plan-execution mode)"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_file "$repo/app/foo.py")"
assert_silent_ok

t "PLAN.md exists but is SHIPPED (none active) → silent, even out-of-scope (no stale-plan fallback)"
repo=$(new_repo $H)
make_plan "$repo" shipped "app/foo.py"
run_hook "$repo" $H "$(json_file "$repo/app/rogue.py")"
assert_silent_ok

t "PLAN.md exists but is PROPOSED (not yet active) → silent, even out-of-scope"
repo=$(new_repo $H)
make_plan "$repo" proposed "app/foo.py"
run_hook "$repo" $H "$(json_file "$repo/app/rogue.py")"
assert_silent_ok

t "edited file is in the active plan's <files> → silent"
repo=$(new_repo $H)
make_plan "$repo" active "app/foo.py, app/bar.py"
run_hook "$repo" $H "$(json_file "$repo/app/foo.py")"
assert_silent_ok

t "edited file outside <files> → warn (additionalContext, exit 0)"
repo=$(new_repo $H)
make_plan "$repo" active "app/foo.py"
run_hook "$repo" $H "$(json_file "$repo/app/rogue.py")"
assert_rc_contains 0 "blast-radius"

t "same out-of-scope edit with BLAST_RADIUS_STRICT=1 → exit 2"
repo=$(new_repo $H)
make_plan "$repo" active "app/foo.py"
run_hook "$repo" $H "$(json_file "$repo/app/rogue.py")" BLAST_RADIUS_STRICT=1
assert_rc_contains 2 "outside the active plan"

t "bookkeeping file (.md) is never flagged"
repo=$(new_repo $H)
make_plan "$repo" active "app/foo.py"
run_hook "$repo" $H "$(json_file "$repo/notes.md")"
assert_silent_ok

t "basename match counts as in-scope (lenient/advisory)"
repo=$(new_repo $H)
make_plan "$repo" active "app/services/foo.py"
run_hook "$repo" $H "$(json_file "$repo/app/other/foo.py")"
assert_silent_ok

# make_md_plan <repo> <status> <files-csv> — markdown task syntax (plan-format.md two-syntaxes)
make_md_plan() {
  mkdir -p "$1/specs/mddemo"
  cat > "$1/specs/mddemo/PLAN.md" <<EOF
---
status: $2
---
### Task 1.1 — demo (wave 1)

- **Files:** $3
- **Action:** x
- **Verify:** \`true\`
- **Done:** ok
EOF
}

t "markdown plan: edited file in the - **Files:** set → silent"
repo=$(new_repo $H)
make_md_plan "$repo" active "app/foo.py, app/bar.py"
run_hook "$repo" $H "$(json_file "$repo/app/foo.py")"
assert_silent_ok

t "markdown plan: edited file outside the - **Files:** set → warn"
repo=$(new_repo $H)
make_md_plan "$repo" active "app/foo.py"
run_hook "$repo" $H "$(json_file "$repo/app/rogue.py")"
assert_rc_contains 0 "blast-radius"

t "mixed plan: XML <files> and markdown - **Files:** sets are unioned"
repo=$(new_repo $H)
mkdir -p "$repo/specs/mixed"
cat > "$repo/specs/mixed/PLAN.md" <<'EOF'
---
status: active
---
```xml
<task id="1.1"><files>app/xml_task.py</files><action>x</action></task>
```

### Task 2.1 — md task (wave 2)

- **Files:** app/md_task.py
- **Action:** y
- **Verify:** `true`
- **Done:** ok
EOF
run_hook "$repo" $H "$(json_file "$repo/app/xml_task.py")"
assert_silent_ok
run_hook "$repo" $H "$(json_file "$repo/app/md_task.py")"
assert_silent_ok

finish
