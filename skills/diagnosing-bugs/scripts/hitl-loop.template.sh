#!/usr/bin/env bash
# Human-in-the-loop feedback loop for skills/diagnosing-bugs (Phase 1).
# Use it only when a human must act to show the bug.
# Copy this file. Replace the example steps under "Loop steps" with the steps for your bug.
# Run the copy with: bash <copy>.sh
# Do not capture a secret. Write <REDACTED> in its place.
set -u

captured_keys=()

# step "<instruction>": print one instruction, then wait for Enter.
step() {
  printf '\n>> %s\n   Press Enter when done. ' "$1"
  IFS= read -r _ || true
}

# capture VAR "<question>": print one question, then read one answer into VAR.
capture() {
  local name=$1 question=$2 answer=""
  case "$name" in
    '' | [0-9]* | *[!A-Za-z0-9_]*)
      printf 'capture: invalid variable name: %s\n' "$name" >&2
      exit 2
      ;;
  esac
  printf '\n?? %s\n   > ' "$question"
  IFS= read -r answer || true
  printf -v "$name" '%s' "$answer"
  captured_keys+=("$name")
}

# --- Loop steps (example: replace these) ---
step "Start the application with the configuration that shows the bug."
step "Do the action that the user reported."
capture SYMPTOM_SEEN "Did the reported symptom appear? (yes/no)"
capture SYMPTOM_TEXT "Copy the exact error text, if any."

# --- Report ---
printf '\n--- Captured ---\n'
for key in ${captured_keys[@]+"${captured_keys[@]}"}; do
  printf '%s=%s\n' "$key" "${!key}"
done
