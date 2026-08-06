#!/bin/bash
# GENERATED from harness-manifest.json hard_gates.detectable — do not hand-edit.
# Regenerate: python3 scripts/generate_gate_modes_default.py
# Sourced by risk-corroboration when no index/root/.claude manifest is available.
hook_lib_default_gate_modes() {
  cat <<'EOF'
auth=block
authorization=block
data-loss/migration=block
audit/security=block
external-provider=block
public-contract=block
weakening-validation=warn
high-blast=block
workflow-engine=warn
EOF
}
