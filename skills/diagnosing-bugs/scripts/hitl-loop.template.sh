#!/usr/bin/env bash
# Human-in-the-loop feedback loop for skills/diagnosing-bugs (Phase 1).
# Use it only when a human must act to show the bug.
# Copy this file. Replace the example steps under "Loop steps" with the steps for your bug.
# Run the copy with: bash <copy>.sh
# Do not capture a secret. Write <REDACTED> in its place.
#
# Exit code contract:
#   0  green: the human answered SYMPTOM_SEEN=no.
#   1  red: the human answered SYMPTOM_SEEN=yes.
#   2  no human at a terminal, end of input, or a bad answer.
# Keep the "Verdict" block in your copy. It sets the exit code.
# Keep one capture into SYMPTOM_SEEN that asks for yes or no.
set -u

# The answers come from the controlling terminal, not from stdin.
# Open it to test it. A test of the /dev/tty mode bits passes with no terminal.
if ! (exec </dev/tty) 2>/dev/null; then
  printf 'hitl-loop: needs a human at a terminal (cannot open /dev/tty).\n' >&2
  exit 2
fi

__hitl_keys=()

# step "<instruction>": print one instruction, then wait for Enter.
step() {
  local __hitl_line=""
  printf '\n>> %s\n   Press Enter when done. ' "$1"
  if ! IFS= read -r __hitl_line </dev/tty; then
    printf '\nhitl-loop: end of input before the step was done.\n' >&2
    exit 2
  fi
}

# capture VAR "<question>": print one question, then read one answer into VAR.
capture() {
  local __hitl_name=$1 __hitl_question=$2 __hitl_answer=""
  case "$__hitl_name" in
    '' | [0-9]* | *[!A-Za-z0-9_]* | __hitl_*)
      printf 'capture: invalid variable name: %s\n' "$__hitl_name" >&2
      exit 2
      ;;
  esac
  printf '\n?? %s\n   > ' "$__hitl_question"
  if ! IFS= read -r __hitl_answer </dev/tty; then
    printf '\nhitl-loop: end of input before an answer to: %s\n' "$__hitl_question" >&2
    exit 2
  fi
  printf -v "$__hitl_name" '%s' "$__hitl_answer"
  __hitl_keys+=("$__hitl_name")
}

# --- Loop steps (example: replace these) ---
step "Start the application with the configuration that shows the bug."
step "Do the action that the user reported."
capture SYMPTOM_SEEN "Did the reported symptom appear? (yes/no)"
capture SYMPTOM_TEXT "Copy the exact error text, if any."

# --- Report ---
printf '\n--- Captured ---\n'
for __hitl_key in ${__hitl_keys[@]+"${__hitl_keys[@]}"}; do
  printf '%s=%s\n' "$__hitl_key" "${!__hitl_key}"
done

# --- Verdict (keep this block: it sets the exit code) ---
case "${SYMPTOM_SEEN-}" in
  yes) exit 1 ;;
  no) exit 0 ;;
  *)
    printf 'hitl-loop: SYMPTOM_SEEN must be yes or no, got: %s\n' "${SYMPTOM_SEEN-}" >&2
    exit 2
    ;;
esac
