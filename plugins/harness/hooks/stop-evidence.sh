#!/bin/bash
# Stop hook: "Done needs real command output".
# Blocks the end of a main session when code changed and the transcript holds no Bash tool output.
# A model judge picks the severity; a small bash risk floor decides only when the judge fails.
# Design: specs/stop-hook-evidence (decisions D1-D4). Fails open, except on the risk floor.
#
# Input   Stop JSON on stdin: transcript_path, stop_hook_active, last_assistant_message.
# Output  block = {"decision":"block","reason":"..."} on stdout, exit 0. Pass = no output, exit 0.
# Judge   $STOP_EVIDENCE_JUDGE_CMD <model> (prompt on stdin) prints {"severity":"pass|light|severe","reason":"..."}.
#         Default: claude -p --model <model>. STOP_EVIDENCE_GUARD stops the judge from re-entering this hook.
# Tuning  STOP_EVIDENCE_JUDGE_TIMEOUT seconds (default 90).
set -u

# The judge runs claude -p, which loads this hook again. The guard ends that second run at once.
[ -n "${STOP_EVIDENCE_GUARD:-}" ] && exit 0
command -v python3 >/dev/null 2>&1 || exit 0

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
PROMPT_FILE="$HOOK_DIR/stop-evidence-judge.md"

REPO_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$REPO_DIR" ] || exit 0

# --- Stop input -------------------------------------------------------------------------------
read -r TRANSCRIPT ACTIVE < <(printf '%s' "$INPUT" | python3 -I -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
print((d.get("transcript_path") or "-"), "true" if d.get("stop_hook_active") else "false")
')
[ -n "${TRANSCRIPT:-}" ] || exit 0
LAST_MSG=$(printf '%s' "$INPUT" | python3 -I -c '
import json, sys
try:
    print((json.load(sys.stdin).get("last_assistant_message") or "")[:2000])
except Exception:
    pass
')

# --- Code diff: changed files, minus docs and specs ---------------------------------------------
CODE_FILES=$(git -C "$REPO_DIR" status --porcelain 2>/dev/null | sed -E 's/^.{3}//; s/^.* -> //; s/^"(.*)"$/\1/' \
  | grep -vE '(^|/)(docs|specs)/|\.(md|txt)$' || true)
[ -n "$CODE_FILES" ] || exit 0

# --- Transcript: main model and Bash evidence ---------------------------------------------------
# The transcript format is not documented by Claude Code; read it defensively.
if [ -r "$TRANSCRIPT" ]; then
  read -r MODEL EVIDENCE < <(python3 -I - "$TRANSCRIPT" <<'PY'
import json, sys
model, bash_ids, evidence = "unknown", set(), 0
try:
    with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                o = json.loads(line)
            except Exception:
                continue
            m = o.get("message")
            if not isinstance(m, dict):
                continue
            if o.get("type") == "assistant" and m.get("model"):
                model = m["model"]
            c = m.get("content")
            if not isinstance(c, list):
                continue
            for b in c:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use" and b.get("name") == "Bash":
                    bash_ids.add(b.get("id"))
                elif b.get("type") == "tool_result" and b.get("tool_use_id") in bash_ids:
                    evidence = 1
except Exception:
    pass
print(model.replace(" ", "_") or "unknown", evidence)
PY
)
  READABLE=1
else
  MODEL=unknown; EVIDENCE=0; READABLE=0
fi
[ "$EVIDENCE" = 1 ] && exit 0

# --- Risk floor: hooks/ and scripts/ paths, or auth/secret words in added lines ----------------------
FLOOR=0
if printf '%s\n' "$CODE_FILES" | grep -qE '(^|/)(hooks|scripts)/'; then FLOOR=1; fi
if [ "$FLOOR" = 0 ]; then
  ADDED=$(git -C "$REPO_DIR" diff HEAD 2>/dev/null | grep -E '^\+[^+]' || true)
  if printf '%s\n%s\n' "$CODE_FILES" "$ADDED" | grep -qiE '\b(password|passwd|secret|api[_-]?key|credential|jwt|oauth|auth[a-z]*|login|sign[ -]?in)\b'; then FLOOR=1; fi
fi

block() { # block <reason>
  python3 -I -c 'import json,sys; print(json.dumps({"decision":"block","reason":sys.argv[1]}, separators=(",",":")))' "$1"
  exit 0
}
LIGHT_REASON="Code changed but no command output is in this session. Run the check that proves it works (tests, build or the app) and show its output, or say plainly that you could not run it and why. \"Done\" needs real command output."

# Unreadable transcript: the model and the evidence are unknown. Only the risk floor goes on.
if [ "$READABLE" = 0 ] && [ "$FLOOR" = 0 ]; then exit 0; fi

# Opus main without the risk floor: no judge. One light block, then let it end.
case "$MODEL" in
  *opus*)
    if [ "$FLOOR" = 0 ]; then
      [ "$ACTIVE" = true ] && exit 0
      block "$LIGHT_REASON"
    fi ;;
esac

# --- Judge ---------------------------------------------------------------------------------------
JUDGE_MODEL=opus
BUILD_PROMPT() {
  cat "$PROMPT_FILE" 2>/dev/null
  printf '\n\n## Session facts\n- Main model: %s\n- Risk floor matched: %s\n- Command output (Bash tool results) in the transcript: none\n' "$MODEL" "$([ "$FLOOR" = 1 ] && echo yes || echo no)"
  printf -- '- Changed code files:\n%s\n' "$(printf '%s\n' "$CODE_FILES" | sed 's/^/  - /')"
  printf '\n## Diff summary\n%s\n' "$(git -C "$REPO_DIR" diff HEAD --stat 2>/dev/null | tail -20)"
  printf '\n## Last assistant message\n%s\n' "$LAST_MSG"
}
default_judge() { STOP_EVIDENCE_GUARD=1 claude -p --model "$1"; }

OUTFILE=$(mktemp 2>/dev/null) || exit 0
trap 'rm -f "$OUTFILE"' EXIT
(
  if [ -n "${STOP_EVIDENCE_JUDGE_CMD:-}" ]; then
    BUILD_PROMPT | STOP_EVIDENCE_GUARD=1 "$STOP_EVIDENCE_JUDGE_CMD" "$JUDGE_MODEL"
  else
    BUILD_PROMPT | default_judge "$JUDGE_MODEL"
  fi
) >"$OUTFILE" 2>/dev/null &
JPID=$!
WAITED=0; LIMIT="${STOP_EVIDENCE_JUDGE_TIMEOUT:-90}"
while kill -0 "$JPID" 2>/dev/null; do
  if [ "$WAITED" -ge "$LIMIT" ]; then pkill -P "$JPID" 2>/dev/null; kill "$JPID" 2>/dev/null; break; fi
  sleep 1; WAITED=$((WAITED + 1))
done
wait "$JPID" 2>/dev/null
JRC=$?

SEVERITY=""; REASON=""
if [ "$JRC" = 0 ] && [ "$WAITED" -lt "$LIMIT" ]; then
  PARSED=$(python3 -I - "$OUTFILE" <<'PY'
import json, sys
sev = reason = ""
try:
    lines = [l for l in open(sys.argv[1], encoding="utf-8", errors="replace").read().splitlines() if l.strip()]
    o = json.loads(lines[-1])
    if o.get("severity") in ("pass", "light", "severe"):
        sev, reason = o["severity"], str(o.get("reason", ""))[:500]
except Exception:
    pass
print(sev + "\t" + reason.replace("\t", " ").replace("\n", " "))
PY
)
  SEVERITY="${PARSED%%$'\t'*}"; REASON="${PARSED#*$'\t'}"
fi

case "$SEVERITY" in
  pass)   exit 0 ;;
  light)  [ "$ACTIVE" = true ] && exit 0
          block "$LIGHT_REASON Judge: ${REASON:-no reason given}" ;;
  severe) block "Code changed on a risky area and no command output is in this session. Run the check that proves it works and show its output before you finish. Judge: ${REASON:-no reason given}" ;;
  *)      # judge failed or printed junk: fail closed on the risk floor, otherwise open
          [ "$FLOOR" = 1 ] && block "Code changed under hooks/, scripts/ or an auth/secret area, and no command output is in this session. The severity judge failed, so this gate blocks. Run the check that proves it works and show its output."
          exit 0 ;;
esac
