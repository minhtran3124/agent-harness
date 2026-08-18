import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("check_codex_packaging.py")
SPEC = importlib.util.spec_from_file_location("check_codex_packaging", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
validate_decision = MODULE.validate_decision


def build_contract(tmp_path):
    evidence_root = tmp_path / "specs/codex-support/evidence/codex-0.147.0"
    evidence_root.mkdir(parents=True)
    for candidate in ("hybrid", "direct"):
        selected = candidate == "hybrid"
        payload = {
            "schema_version": 1,
            "runtime": "codex",
            "cli_version": "0.147.0",
            "platform": "macos-arm64",
            "captured_at": "2026-08-10",
            "config_hash": "not-applicable",
            "capture": "isolated-local-packaging-probe",
            "candidate": candidate,
            "result": {
                "status": "observed" if selected else "unknown",
                "passed": selected,
                "checks": {"lifecycle": selected},
                "runtime_execution_observed": False,
            },
        }
        if not selected:
            payload["result"].update(
                {
                    "owner": "codex-support-phase-5",
                    "exit_condition": "Run the real direct adapter probe.",
                }
            )
        (evidence_root / f"packaging-{candidate}.json").write_text(json.dumps(payload))
    matrix = {
        "capabilities": [
            {
                "id": "packaging.plugins",
                "status": "advisory",
                "evidence_level": "observed",
                "evidence_path": "specs/codex-support/evidence/codex-0.147.0/packaging-hybrid.json",
            }
        ]
    }
    matrix_path = tmp_path / "specs/codex-support/capability-matrix.json"
    matrix_path.write_text(json.dumps(matrix))
    decision = tmp_path / "specs/codex-support/packaging-decision.md"
    decision.write_text(
        """---
decision: hybrid
fallback: direct
cli_version: 0.147.0
matrix: specs/codex-support/capability-matrix.json
hybrid_evidence: specs/codex-support/evidence/codex-0.147.0/packaging-hybrid.json
direct_evidence: specs/codex-support/evidence/codex-0.147.0/packaging-direct.json
runtime_execution: not-observed
fallback_trigger: Select direct when plugin lifecycle or trust fails the Phase-5 runtime probe.
---
# Decision
## Ownership boundary
Text.
## Executable evidence
Text.
## Unresolved gaps
Text.
## Fallback trigger
Text.
"""
    )
    return decision, evidence_root, matrix_path


def test_valid_decision_passes(tmp_path):
    decision, _, _ = build_contract(tmp_path)
    assert validate_decision(decision, root=tmp_path) == []


def test_missing_fallback_trigger_is_rejected(tmp_path):
    decision, _, _ = build_contract(tmp_path)
    decision.write_text(
        decision.read_text().replace(
            "fallback_trigger: Select direct when plugin lifecycle or trust fails the Phase-5 runtime probe.\n",
            "",
        )
    )
    assert any(
        "fallback_trigger" in error
        for error in validate_decision(decision, root=tmp_path)
    )


def test_failed_selected_evidence_is_rejected(tmp_path):
    decision, evidence_root, _ = build_contract(tmp_path)
    path = evidence_root / "packaging-hybrid.json"
    payload = json.loads(path.read_text())
    payload["result"]["checks"]["lifecycle"] = False
    payload["result"].update(
        {
            "status": "unknown",
            "passed": False,
            "owner": "codex-support-phase-2",
            "exit_condition": "Repair and rerun the hybrid probe.",
        }
    )
    path.write_text(json.dumps(payload))
    assert any(
        "selected packaging candidate" in error
        for error in validate_decision(decision, root=tmp_path)
    )


def test_unknown_unselected_fallback_is_accepted(tmp_path):
    decision, evidence_root, _ = build_contract(tmp_path)
    payload = json.loads((evidence_root / "packaging-direct.json").read_text())
    assert payload["result"]["status"] == "unknown"
    assert validate_decision(decision, root=tmp_path) == []


def test_failed_hybrid_can_select_proven_direct_fallback(tmp_path):
    decision, evidence_root, matrix_path = build_contract(tmp_path)
    hybrid_path = evidence_root / "packaging-hybrid.json"
    hybrid = json.loads(hybrid_path.read_text())
    hybrid["result"] = {
        "status": "unknown",
        "passed": False,
        "checks": {"lifecycle": False},
        "runtime_execution_observed": False,
        "owner": "codex-support-phase-2",
        "exit_condition": "Repair and rerun the hybrid probe.",
    }
    hybrid_path.write_text(json.dumps(hybrid))

    direct_path = evidence_root / "packaging-direct.json"
    direct = json.loads(direct_path.read_text())
    direct["result"] = {
        "status": "observed",
        "passed": True,
        "checks": {"lifecycle": True},
        "runtime_execution_observed": False,
    }
    direct_path.write_text(json.dumps(direct))

    decision.write_text(
        decision.read_text()
        .replace("decision: hybrid", "decision: direct")
        .replace("fallback: direct", "fallback: hybrid")
    )
    matrix = json.loads(matrix_path.read_text())
    matrix["capabilities"][0]["evidence_path"] = (
        "specs/codex-support/evidence/codex-0.147.0/packaging-direct.json"
    )
    matrix_path.write_text(json.dumps(matrix))
    assert validate_decision(decision, root=tmp_path) == []


def test_candidate_mismatch_is_rejected(tmp_path):
    decision, evidence_root, _ = build_contract(tmp_path)
    path = evidence_root / "packaging-hybrid.json"
    payload = json.loads(path.read_text())
    payload["candidate"] = "direct"
    path.write_text(json.dumps(payload))
    assert any(
        "candidate must be hybrid" in error
        for error in validate_decision(decision, root=tmp_path)
    )


def test_absolute_evidence_path_is_rejected(tmp_path):
    decision, _, _ = build_contract(tmp_path)
    decision.write_text(
        decision.read_text().replace(
            "specs/codex-support/evidence/codex-0.147.0/packaging-hybrid.json",
            "/Users/private/packaging-hybrid.json",
        )
    )
    assert any(
        "inside the repository" in error
        for error in validate_decision(decision, root=tmp_path)
    )


def test_matrix_must_point_to_selected_evidence(tmp_path):
    decision, _, matrix_path = build_contract(tmp_path)
    matrix = json.loads(matrix_path.read_text())
    matrix["capabilities"][0]["evidence_path"] = (
        "specs/codex-support/evidence/codex-0.147.0/packaging-direct.json"
    )
    matrix_path.write_text(json.dumps(matrix))
    assert any(
        "selected evidence" in error
        for error in validate_decision(decision, root=tmp_path)
    )


def test_runtime_execution_overclaim_is_rejected(tmp_path):
    decision, evidence_root, _ = build_contract(tmp_path)
    path = evidence_root / "packaging-hybrid.json"
    payload = json.loads(path.read_text())
    payload["result"]["runtime_execution_observed"] = True
    path.write_text(json.dumps(payload))
    assert any(
        "overclaim" in error for error in validate_decision(decision, root=tmp_path)
    )


def test_observed_runtime_requires_separate_passing_evidence(tmp_path):
    decision, evidence_root, _ = build_contract(tmp_path)
    runtime_path = evidence_root / "packaging-hybrid-runtime.json"
    runtime_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "runtime": "codex",
                "cli_version": "0.147.0",
                "platform": "macos-arm64",
                "captured_at": "2026-08-11",
                "config_hash": "not-applicable",
                "capture": "isolated-live-packaging-probe",
                "candidate": "hybrid",
                "result": {
                    "status": "observed",
                    "passed": True,
                    "checks": {
                        "installed_plugin_skill_invoked": True,
                        "plugin_hook_executed": True,
                        "project_agent_dispatched": True,
                    },
                    "runtime_execution_observed": True,
                    "hook_trust_mode": "automation-vetted-bypass",
                    "verifies": "All three disposable runtime boundaries.",
                    "does_not_verify": "The direct fallback.",
                },
            }
        )
    )
    decision.write_text(
        decision.read_text()
        .replace("runtime_execution: not-observed", "runtime_execution: observed")
        .replace(
            "fallback_trigger:",
            "runtime_evidence: specs/codex-support/evidence/codex-0.147.0/packaging-hybrid-runtime.json\nfallback_trigger:",
        )
    )
    assert validate_decision(decision, root=tmp_path) == []


def test_observed_runtime_rejects_a_failed_execution_check(tmp_path):
    decision, evidence_root, _ = build_contract(tmp_path)
    runtime_path = evidence_root / "packaging-hybrid-runtime.json"
    runtime_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "runtime": "codex",
                "cli_version": "0.147.0",
                "platform": "macos-arm64",
                "captured_at": "2026-08-11",
                "config_hash": "not-applicable",
                "capture": "isolated-live-packaging-probe",
                "candidate": "hybrid",
                "result": {
                    "status": "observed",
                    "passed": True,
                    "checks": {
                        "installed_plugin_skill_invoked": True,
                        "plugin_hook_executed": True,
                        "project_agent_dispatched": False,
                    },
                    "runtime_execution_observed": True,
                    "hook_trust_mode": "automation-vetted-bypass",
                    "verifies": "Attempted runtime boundaries.",
                    "does_not_verify": "The missing agent dispatch.",
                },
            }
        )
    )
    decision.write_text(
        decision.read_text()
        .replace("runtime_execution: not-observed", "runtime_execution: observed")
        .replace(
            "fallback_trigger:",
            "runtime_evidence: specs/codex-support/evidence/codex-0.147.0/packaging-hybrid-runtime.json\nfallback_trigger:",
        )
    )
    assert any(
        "runtime checks must all pass" in error
        for error in validate_decision(decision, root=tmp_path)
    )


def test_not_observed_runtime_cannot_point_at_evidence(tmp_path):
    decision, _, _ = build_contract(tmp_path)
    decision.write_text(
        decision.read_text().replace(
            "fallback_trigger:",
            "runtime_evidence: specs/codex-support/evidence/codex-0.147.0/runtime.json\nfallback_trigger:",
        )
    )
    assert any(
        "must be omitted" in error
        for error in validate_decision(decision, root=tmp_path)
    )


def test_required_section_is_enforced(tmp_path):
    decision, _, _ = build_contract(tmp_path)
    decision.write_text(decision.read_text().replace("## Unresolved gaps", "## Notes"))
    assert any(
        "Unresolved gaps" in error
        for error in validate_decision(decision, root=tmp_path)
    )


def test_private_path_in_unselected_evidence_is_rejected(tmp_path):
    decision, evidence_root, _ = build_contract(tmp_path)
    path = evidence_root / "packaging-direct.json"
    payload = json.loads(path.read_text())
    payload["result"]["debug"] = "/Users/private/.codex/config.toml"
    path.write_text(json.dumps(payload))
    assert any(
        "private or absolute path" in error
        for error in validate_decision(decision, root=tmp_path)
    )
