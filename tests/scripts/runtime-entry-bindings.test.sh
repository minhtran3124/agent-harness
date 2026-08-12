#!/usr/bin/env bash
# Contract tests for Task 5.5's single Claude/Codex runtime-entry binding.
source "$(dirname "$0")/../lib.sh"

RENDERER="scripts/render_runtime_entry.py"
CHECKER="scripts/check_runtime_neutral_sources.py"

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

t "Claude and Codex render distinct official skill-entry syntax"
claude_out=$(python3 "$ROOT/$RENDERER" --root "$ROOT" --runtime claude --skill feature-intake --prompt '<case prompt>')
codex_out=$(python3 "$ROOT/$RENDERER" --root "$ROOT" --runtime codex --skill feature-intake --prompt '<case prompt>')
if [ "$claude_out" = "claude -p '/feature-intake <case prompt>' --output-format text" ] \
  && [ "$codex_out" = "codex exec '\$feature-intake <case prompt>'" ]; then
  pass
else
  fail "unexpected paired output — claude=[$claude_out] codex=[$codex_out]"
fi

t "Claude and Codex model stages resolve through their agent bindings"
claude_model=$(python3 "$ROOT/$RENDERER" --root "$ROOT" --runtime claude --model-stage task_reviewer)
codex_model=$(python3 "$ROOT/$RENDERER" --root "$ROOT" --runtime codex --model-stage task_reviewer)
if [ "$claude_model" = "claude-opus-5" ] && [ "$codex_model" = "gpt-5.6-terra" ]; then
  pass
else
  fail "unexpected task-reviewer models — claude=[$claude_model] codex=[$codex_model]"
fi

t "live shared sources have zero owned runtime-entry exceptions"
if python3 "$ROOT/$CHECKER" --root "$ROOT" >/dev/null \
  && python3 -c 'import json,sys; assert json.load(open(sys.argv[1]))["findings"] == []' \
    "$ROOT/specs/codex-support/neutralization-inventory.json"; then
  pass
else
  fail "shared runtime-entry inventory is not closed"
fi

copy_scanner_fixture() {
  local destination="$1"
  mkdir -p "$destination/specs/codex-support" "$destination/skills/demo"
  cp "$ROOT/$CHECKER" "$destination/scripts-checker.py"
  python3 - "$ROOT/specs/codex-support/neutralization-inventory.json" "$destination/specs/codex-support/neutralization-inventory.json" <<'PY'
import json, sys
source, destination = sys.argv[1:]
value = json.load(open(source))
value["scan_roots"] = ["skills"]
value["skill_names"] = ["feature-intake"]
value["findings"] = []
open(destination, "w").write(json.dumps(value))
PY
}

t "mutation: a new raw slash-skill invocation fails the count-exact inventory"
fixture=$(mktemp -d); _CLEANUP_DIRS+=("$fixture")
copy_scanner_fixture "$fixture"
printf '%s\n' 'Run /feature-intake now.' > "$fixture/skills/demo/SKILL.md"
if python3 "$fixture/scripts-checker.py" --root "$fixture" >/dev/null 2>&1; then
  fail "slash-skill mutation passed"
else
  pass
fi

t "mutation: a new vendor model label in shared prose fails the inventory"
fixture=$(mktemp -d); _CLEANUP_DIRS+=("$fixture")
copy_scanner_fixture "$fixture"
printf '%s\n' 'Pin this shared stage to claude-opus-example.' > "$fixture/skills/demo/SKILL.md"
if python3 "$fixture/scripts-checker.py" --root "$fixture" >/dev/null 2>&1; then
  fail "vendor-model mutation passed"
else
  pass
fi

t "semantic prompts retain explicit model-stage selection without vendor labels"
if grep -q 'model_stage: correctness_scorer' "$ROOT/skills/correctness-review/correctness-scorer-prompt.md" \
  && grep -q 'model_stage: intent_reviewer' "$ROOT/skills/intent-review/intent-reviewer-prompt.md" \
  && grep -q 'model_stage: task_reviewer' "$ROOT/skills/subagent-driven-development/task-reviewer-prompt.md"; then
  pass
else
  fail "one or more semantic model stages are missing"
fi

finish
