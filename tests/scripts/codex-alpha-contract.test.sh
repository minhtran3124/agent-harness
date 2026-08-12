#!/usr/bin/env bash
# Deterministic release contract for the Phase-5 Codex advisory alpha.
# --quick runs only this file's unique assertions (platform boundary, docs/
# manifest phrases, binding check) and skips the nested component suites,
# which SC-1..SC-6 already re-run individually. ci-strict-gate re-executes
# each SUMMARY Verify row under a 60s cap, so the composed full run is CI's
# named-step form, not a Verify-row form.
source "$(dirname "$0")/../lib.sh"

QUICK=0
[ "${1:-}" = "--quick" ] && QUICK=1

# The pytest-backed rows below must run against an interpreter that HAS pytest.
# A bare `python3 -m pytest` inherits whatever the runner happens to ship, which
# on a fresh GitHub runner is an interpreter without it — that turned three real
# contract rows into failures unrelated to the contract. Provision the shared
# venv here instead of depending on another CI step having run first, and treat
# an unavailable interpreter as a contract failure, never as a silent skip.
PY=python3
if [ "$QUICK" -eq 0 ]; then
  if ensure_pyenv; then
    PY="$PYENV_DIR/bin/python"
  else
    t "python interpreter with pytest is available"
    fail "cannot provision pytest; the pytest-backed contract rows cannot run"
  fi
fi

if [ "$QUICK" -eq 0 ]; then
  t "committed evidence still selects the observed hybrid package"
  if bash "$ROOT/tests/scripts/codex-alpha-evidence.test.sh" >/dev/null; then
    pass
  else
    fail "capability or packaging evidence contract failed"
  fi

  t "adapter rendering is deterministic and capability mappings stay total"
  if "$PY" -m pytest "$ROOT/scripts/test_render_codex_adapter.py" \
    "$ROOT/scripts/test_render_agent_definitions.py" -q >/dev/null; then
    pass
  else
    fail "adapter or agent rendering contract failed"
  fi

  t "install, update, conflict, removal, and rollback preserve user state"
  if bash "$ROOT/tests/scripts/codex-install.test.sh" >/dev/null; then
    pass
  else
    fail "Codex install lifecycle contract failed"
  fi

  t "doctor and runtime-mode records fail closed without breaking legacy state"
  if "$PY" -m pytest "$ROOT/scripts/test_codex_harness_doctor.py" \
    "$ROOT/runtime/test_runtime_mode.py" "$ROOT/runtime/test_run_state.py" -q >/dev/null; then
    pass
  else
    fail "doctor or runtime-mode contract failed"
  fi
fi

t "Linux and unobserved WSL can never inherit macOS enforcement evidence"
if ROOT="$ROOT" python3 - <<'PY'
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

root = Path(os.environ["ROOT"])
sys.path.insert(0, str(root / "scripts"))
import codex_harness_doctor as doctor

report = {
    "cli_version": "0.147.0",
    "platform": "macos-arm64",
    "overallStatus": "ok",
    "checks": {"installation": {"status": "ok"}},
    "features": {
        name: {"enabled": True, "maturity": "stable"}
        for name in doctor.REQUIRED_FEATURES
    },
    "effective_trust": {"hooks": "trusted"},
}
dependencies = {name: True for name in doctor.REQUIRED_DEPENDENCIES}

# Other component contracts prove installation and evidence integrity. Isolate the
# platform decision here so an unobserved OS cannot be promoted by unrelated drift.
doctor._install_reasons = lambda _root, _repo_root: []
doctor._evidence_reasons = lambda _matrix, _platform, _trust, _today: ([], None)
with tempfile.TemporaryDirectory() as directory:
    for platform in ("linux-x86_64", "wsl-x86_64"):
        result = doctor.diagnose(
            root=Path(directory),
            repo_root=root,
            doctor_value=report,
            platform_override=platform,
            dependencies=dependencies,
            today=date(2026, 8, 12),
        )
        assert result["mode"] == "advisory", (platform, json.dumps(result))
        assert "PLATFORM_UNVERIFIED" in result["reason_codes"]
PY
then
  pass
else
  fail "Linux/WSL advisory boundary failed"
fi

if [ "$QUICK" -eq 0 ]; then
  t "runtime entry binding and Claude deployment regression remain green"
  if bash "$ROOT/tests/scripts/runtime-entry-bindings.test.sh" >/dev/null \
    && bash "$ROOT/tests/scripts/settings-wiring.test.sh" >/dev/null \
    && bash "$ROOT/tests/scripts/deploy-prune.test.sh" >/dev/null; then
    pass
  else
    fail "runtime entry or Claude regression contract failed"
  fi
else
  t "runtime entry binding validates (quick)"
  if python3 "$ROOT/scripts/render_runtime_entry.py" --root "$ROOT" --check >/dev/null; then
    pass
  else
    fail "runtime entry binding failed validation"
  fi
fi

t "public docs and manifest expose the advisory boundary without peer or GA claims"
if ROOT="$ROOT" python3 - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["ROOT"])
manifest = json.loads((root / "harness-manifest.json").read_text())
contract = manifest["contracts"].get("codex-advisory-alpha")
assert contract is not None
assert "tests/scripts/codex-alpha-contract.test.sh" in contract["surface"]

required = {
    "CLAUDE.md": ("Codex advisory alpha", "not GA", "PLATFORM_UNVERIFIED"),
    "HARNESS.md": ("Codex advisory alpha", "not peer enforcement"),
    "skills/README.md": ("Codex advisory alpha", "`$skill-name`"),
    "specs/codex-support/ROADMAP.md": ("advisory alpha", "WSL"),
}
for relative, phrases in required.items():
    text = (root / relative).read_text()
    for phrase in phrases:
        assert phrase in text, f"{relative} is missing {phrase!r}"
PY
then
  pass
else
  fail "advisory-alpha documentation or manifest contract failed"
fi

finish
