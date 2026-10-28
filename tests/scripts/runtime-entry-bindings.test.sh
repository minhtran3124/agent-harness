#!/usr/bin/env bash
# Contract tests for Task 5.5's Claude runtime-entry binding.
source "$(dirname "$0")/../lib.sh"

RENDERER="scripts/render_runtime_entry.py"

# Resolve an interpreter that actually has pytest; a bare `python3` is whatever
# the runner ships, which on a fresh CI runner lacks it. Missing pytest is a
# failure here, not a skip — the focused tests are part of the contract.
PY=python3
if ensure_pyenv; then
  PY="$PYENV_DIR/bin/python"
fi

t "runtime entry binding validates and focused Python tests pass"
if python3 "$ROOT/$RENDERER" --root "$ROOT" --check >/dev/null \
  && "$PY" -m pytest "$ROOT/scripts/test_render_runtime_entry.py" -q >/dev/null; then
  pass
else
  fail "runtime entry binding or focused tests failed"
fi

t "Claude renders the official skill-entry syntax"
claude_out=$(python3 "$ROOT/$RENDERER" --root "$ROOT" --runtime claude --skill feature-intake --prompt '<case prompt>')
if [ "$claude_out" = "claude -p '/feature-intake <case prompt>' --output-format text" ]; then
  pass
else
  fail "unexpected output — claude=[$claude_out]"
fi

t "Claude model stages resolve through the agent bindings"
claude_model=$(python3 "$ROOT/$RENDERER" --root "$ROOT" --runtime claude --model-stage task_reviewer)
if [ "$claude_model" = "claude-opus-5-5" ]; then
  pass
else
  fail "unexpected task-reviewer model — claude=[$claude_model]"
fi

t "semantic prompts retain explicit model-stage selection without vendor labels"
if grep -q 'model_stage: correctness_scorer' "$ROOT/skills/correctness-review/correctness-scorer-prompt.md" \
  && grep -q '"intent_reviewer": "intent-reviewer"' "$ROOT/adapters/runtime-entry-bindings.json" \
  && grep -q 'model_stage: implementer' "$ROOT/skills/implement/implementer-prompt.md"; then
  pass
else
  fail "one or more semantic model stages are missing"
fi

finish
