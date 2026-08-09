#!/bin/bash
# SC-10: SDD resume behavior contract. Drives runtime/resume_decision.py over durable-run +
# PLAN fixtures for every public action, an evidence conflict, and the portable command path,
# asserting the structured action/reason_code/cursor OUTPUTS — never SKILL.md prose. Mirrors
# runtime/test_resume_decision.py's FSM fixtures at the shell boundary a resuming session uses.
source "$(dirname "$0")/../lib.sh"

RD="$ROOT/runtime/resume_decision.py"
RS="$ROOT/runtime/run_state.py"

# A declared base (VERIFY_ROWS_BASE / GITHUB_BASE_REF) is now validated even with no claimed
# commits (finding G); CI pull-request jobs export GITHUB_BASE_REF, which would turn these
# no-commit execute-plan fixtures into base-unresolved stops. Keep the shell contract hermetic.
unset VERIFY_ROWS_BASE GITHUB_BASE_REF

ws() { W=$(mktemp -d); _CLEANUP_DIRS+=("$W"); }

plan_body() { # <status> [status-log line]
  cat <<EOF
issue: 175
status: $1

# Plan

### Task 1.1 — first (wave 1)

- **Files:** a.py
- **Action:** do a
- **Verify:** \`pytest -k a\`
- **Done:** a done

### Task 1.2 — second (wave 1)

- **Files:** b.py
- **Action:** do b
- **Verify:** \`pytest -k b\`
- **Done:** b done
EOF
  [ -n "$2" ] && printf '\n## Status Log\n\n- %s\n' "$2"
}

write_plan() { # <dir> <slug> <status> [status-log line]
  mkdir -p "$1/specs/$2"
  plan_body "$3" "$4" > "$1/specs/$2/PLAN.md"
}

rs_step() { # <dir> <slug> <state>
  local d="$1" s="$2" st="$3"; local extra=()
  case "$st" in
    awaiting_ci|awaiting_review|awaiting_confirmation) extra=(--waiting-on "$st");;
    blocked|escalated) extra=(--waiting-on blocker --resume-event resolved);;
    shipped) extra=(--sha deadbeef1234);;
  esac
  ( cd "$d" && python3 "$RS" transition --slug "$s" --to "$st" --event "to.$st" "${extra[@]}" >/dev/null 2>&1 )
}

rs_run() { # <dir> <slug> <state...>
  local d="$1" s="$2"; shift 2
  ( cd "$d" && python3 "$RS" init --slug "$s" --run-id "run-$s" >/dev/null 2>&1 )
  local st; for st in "$@"; do rs_step "$d" "$s" "$st"; done
}

decide() { # <dir> <slug> [extra args...] -> sets JSON, RC
  local d="$1" s="$2"; shift 2
  JSON=$( cd "$d" && python3 "$RD" --slug "$s" "$@" ); RC=$?
}

# jq-free field read: prints eval('d'+<expr>) over the parsed JSON on stdin.
jf() { printf '%s' "$JSON" | python3 -c "import sys,json;d=json.load(sys.stdin);print(eval('d'+sys.argv[1]))" "$1" 2>/dev/null; }

assert_ar() { # <want-action> <want-reason_code>
  local a rc; a=$(jf "['action']"); rc=$(jf "['reason_code']")
  if [ "$RC" -eq 0 ] && [ "$a" = "$1" ] && [ "$rc" = "$2" ]; then pass
  else fail "rc=$RC action=$a reason_code=$rc, want $1/$2"; fi
}

# --- shipped plan: execute blocked, but post-PR repair states still route (SC-3 parity) ---

t "shipped plan + implementing -> stop/plan-shipped (plan-task execution is closed)"
ws; write_plan "$W" ship-impl shipped
rs_run "$W" ship-impl investigating planning implementing
decide "$W" ship-impl; assert_ar stop plan-shipped

t "shipped plan + fixing_ci -> resume-repair (repair loop outlives a shipped plan)"
ws; write_plan "$W" ship-ci shipped
rs_run "$W" ship-ci investigating planning implementing verifying awaiting_ci fixing_ci
decide "$W" ship-ci; assert_ar resume-repair post-pr-repair

# --- a repair state on an active plan ---

t "active plan + addressing_review -> resume-repair"
ws; write_plan "$W" rev-repair active
rs_run "$W" rev-repair investigating planning implementing verifying awaiting_ci awaiting_review addressing_review
decide "$W" rev-repair; assert_ar resume-repair post-pr-repair

# --- review chain ---

t "verifying -> resume-review-chain (tasks passed; do not re-sweep waves)"
ws; write_plan "$W" rc active
rs_run "$W" rc investigating planning implementing verifying
decide "$W" rc; assert_ar resume-review-chain review-chain

# --- wait ---

t "awaiting_ci -> wait/awaiting-external"
ws; write_plan "$W" wait-ci active
rs_run "$W" wait-ci investigating planning implementing verifying awaiting_ci
decide "$W" wait-ci; assert_ar wait awaiting-external

# --- rebuild (projection drift) ---

t "RUN.json drifted from events -> rebuild/projection-drift"
ws; write_plan "$W" drift active
rs_run "$W" drift investigating planning
python3 - "$W" <<'PY'
import sys, json, pathlib
p = pathlib.Path(sys.argv[1]) / "specs/drift/RUN.json"
d = json.loads(p.read_text()); d["state"] = "queued"; p.write_text(json.dumps(d))
PY
decide "$W" drift; assert_ar rebuild projection-drift

# --- execute-plan: claimed task surfaces checks_to_rerun; pending is NOT skipped ---

t "execute-plan reconstructs the cursor: claimed task -> checks_to_rerun, next_task stays pending"
ws; write_plan "$W" exec-cur active "2026-08-09 — Task 1.1 complete."
rs_run "$W" exec-cur investigating planning implementing
decide "$W" exec-cur
a=$(jf "['action']"); rc=$(jf "['reason_code']")
nxt=$(jf "['cursor']['next_task']")
chk=$(jf "['cursor']['checks_to_rerun'][0]['task_id']+' '+d['cursor']['checks_to_rerun'][0]['command']")
if [ "$RC" -eq 0 ] && [ "$a" = execute-plan ] && [ "$rc" = active-plan ] \
   && [ "$nxt" = 1.2 ] && [ "$chk" = "1.1 pytest -k a" ]; then pass
else fail "rc=$RC a=$a reason=$rc next=$nxt chk=[$chk] — pending must not dispatch before rerun"; fi

# --- evidence conflict: a claimed SHA outside BASE..HEAD fails closed with stop ---

t "claimed commit out of BASE..HEAD -> stop/git-evidence-conflict (fails closed)"
ws
( cd "$W" && git init -q -b main >/dev/null 2>&1 || git init -q >/dev/null 2>&1
  git -C "$W" config user.email t@t; git -C "$W" config user.name t
  git -C "$W" commit --allow-empty -q -m base )
gbase=$( git -C "$W" rev-parse HEAD )
git -C "$W" commit --allow-empty -q -m head
write_plan "$W" ev active "2026-08-09 — Task 1.1 complete (\`$gbase\`)."
rs_run "$W" ev investigating planning implementing
decide "$W" ev --base "$gbase"
a=$(jf "['action']"); rc=$(jf "['reason_code']"); ct=$(jf "['git']['conflicts'][0]['type']")
if [ "$RC" -eq 0 ] && [ "$a" = stop ] && [ "$rc" = git-evidence-conflict ] \
   && [ "$ct" = commit-out-of-range ]; then pass
else fail "rc=$RC a=$a reason=$rc conflict=$ct"; fi

# --- portable path: the exact deployed-fallback command emits valid structured JSON ---

t "portable command falls back to .claude/runtime ONLY when the source file is absent"
ws
mkdir -p "$W/.claude/runtime"; cp "$RD" "$RS" "$W/.claude/runtime/"
write_plan "$W" portable active
# The published form: source-tree first, deployed copy only when the source is ABSENT.
out=$( cd "$W" && if [ -f runtime/resume_decision.py ]; then python3 runtime/resume_decision.py --slug portable; else python3 .claude/runtime/resume_decision.py --slug portable; fi )
parsed=$( printf '%s' "$out" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['schema_version'],d['action'])" 2>/dev/null )
if [ "$parsed" = "1 execute-plan" ]; then pass
else fail "fallback command did not emit valid JSON: parsed=[$parsed] out=[$(printf '%s' "$out" | head -1)]"; fi

# --- fail-closed: a source-copy ERROR must NOT be re-answered from the stale deployed copy ---

t "portable command does NOT fall through to the deployed copy on a source-copy error (exit 3)"
ws
mkdir -p "$W/runtime" "$W/.claude/runtime"
# A stale/broken SOURCE copy that fails closed with exit 3.
printf '#!/usr/bin/env python3\nimport sys\nsys.stderr.write("SOURCE-EXIT-3\\n")\nsys.exit(3)\n' > "$W/runtime/resume_decision.py"
# The deployed copy WOULD answer execute-plan if wrongly consulted.
cp "$RD" "$RS" "$W/.claude/runtime/"
write_plan "$W" e3 active
out=$( cd "$W" && { if [ -f runtime/resume_decision.py ]; then python3 runtime/resume_decision.py --slug e3; else python3 .claude/runtime/resume_decision.py --slug e3; fi; } 2>/dev/null ); RC3=$?
if [ "$RC3" -eq 3 ] && ! printf '%s' "$out" | grep -q '"action"'; then pass
else fail "fell through to the stale deployed copy: rc=$RC3 out=[$(printf '%s' "$out" | head -1)]"; fi

finish
