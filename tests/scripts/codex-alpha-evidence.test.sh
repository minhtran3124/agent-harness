#!/usr/bin/env bash
# Verify committed Phase-5 alpha evidence and the selected packaging runtime.

set -u

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT" || exit 1

python3 scripts/check_codex_capabilities.py --require-evidence \
  specs/codex-support/capability-matrix.json || exit 1
python3 scripts/check_codex_packaging.py \
  specs/codex-support/packaging-decision.md || exit 1

python3 - <<'PY'
import json
import pathlib

root = pathlib.Path("specs/codex-support/evidence/codex-0.147.0")
unified = json.loads((root / "hooks-unified-exec.json").read_text())["result"]
prompt = json.loads((root / "hooks-user-prompt-submit.json").read_text())["result"]
runtime = json.loads((root / "packaging-hybrid-runtime.json").read_text())["result"]
direct = json.loads((root / "packaging-direct.json").read_text())["result"]

assert unified["status"] == "observed"
assert unified["hook_tool_name"] == "Bash"
assert unified["tool_input_keys"] == ["command"]
assert unified["payload_values_redacted"] is True
assert prompt["status"] == "observed"
assert "prompt" in prompt["envelope_keys"]
assert prompt["prompt_redacted"] is True
assert runtime["status"] == "observed"
assert runtime["runtime_execution_observed"] is True
assert runtime["hook_trust_mode"] == "automation-vetted-bypass"
assert all(runtime["checks"].values())
assert direct["status"] == "unknown"
assert direct["passed"] is False
assert direct["owner"] == "codex-support-phase-5"
PY
