import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest


SCRIPT = Path(__file__).with_name("check_codex_capabilities.py")


def load_checker():
    spec = importlib.util.spec_from_file_location("check_codex_capabilities", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def valid_matrix(tmp_path):
    evidence_dir = tmp_path / "specs/codex-support/evidence/codex-0.147.0"
    evidence_dir.mkdir(parents=True)
    evidence_path = evidence_dir / "shell.json"
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "runtime": "codex",
                "cli_version": "0.147.0",
                "platform": "macos-arm64",
                "captured_at": "2026-08-10",
                "config_hash": "not-applicable",
                "capture": "isolated-live-model-probe",
                "result": {"status": "observed", "tool_name": "Bash"},
            }
        )
    )
    matrix = {
        "schema_version": 1,
        "runtime": "codex",
        "matrix_version": "2026-08-10",
        "cli_version": "0.147.0",
        "evidence_root": "specs/codex-support/evidence/codex-0.147.0",
        "supported_platforms": ["macos-arm64", "linux-x86_64", "wsl-x86_64"],
        "capabilities": [
            {
                "id": "hooks.pre_tool_use.shell",
                "area": "hooks",
                "support_target": "required",
                "load_bearing": True,
                "status": "supported",
                "evidence_level": "observed",
                "platforms": ["macos-arm64"],
                "source": {
                    "kind": "captured-fixture",
                    "reference": "local isolated probe",
                    "checked_at": "2026-08-10",
                    "expires_at": "2026-11-08",
                },
                "config": {"scope": "not-applicable", "sha256": None},
                "evidence_path": "specs/codex-support/evidence/codex-0.147.0/shell.json",
                "owner": "codex-adapter",
                "exit_condition": None,
            },
            {
                "id": "config.project_trust",
                "area": "config",
                "support_target": "required",
                "load_bearing": True,
                "status": "unknown",
                "evidence_level": "unknown",
                "platforms": ["macos-arm64", "linux-x86_64", "wsl-x86_64"],
                "source": {
                    "kind": "unavailable",
                    "reference": "no deterministic public trust-state query",
                    "checked_at": "2026-08-10",
                    "expires_at": "2026-11-08",
                },
                "config": {"scope": "unknown", "sha256": None},
                "evidence_path": None,
                "owner": "codex-adapter",
                "exit_condition": "Add a deterministic effective-trust query or isolated probe.",
            },
        ],
    }
    matrix_path = tmp_path / "specs/codex-support/capability-matrix.json"
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    matrix_path.write_text(json.dumps(matrix))
    return tmp_path, matrix_path, matrix


def validate(valid_matrix, *, require_evidence=False, today=date(2026, 8, 10)):
    root, matrix_path, _ = valid_matrix
    return load_checker().validate_matrix(
        matrix_path,
        root=root,
        today=today,
        require_evidence=require_evidence,
    )


def rewrite(valid_matrix, mutate):
    _, matrix_path, matrix = valid_matrix
    mutate(matrix)
    matrix_path.write_text(json.dumps(matrix))


def test_valid_matrix_and_explicit_unknown_pass(valid_matrix):
    assert validate(valid_matrix) == []
    assert validate(valid_matrix, require_evidence=True) == []


@pytest.mark.parametrize(
    "field",
    [
        "id",
        "area",
        "support_target",
        "load_bearing",
        "status",
        "evidence_level",
        "platforms",
        "source",
        "config",
        "evidence_path",
        "owner",
        "exit_condition",
    ],
)
def test_missing_capability_field_is_rejected(valid_matrix, field):
    rewrite(valid_matrix, lambda m: m["capabilities"][0].pop(field))
    assert any(field in error for error in validate(valid_matrix))


def test_duplicate_capability_id_is_rejected(valid_matrix):
    rewrite(
        valid_matrix, lambda m: m["capabilities"].append(m["capabilities"][0].copy())
    )
    assert any("duplicate" in error for error in validate(valid_matrix))


def test_unknown_cannot_claim_supported(valid_matrix):
    rewrite(valid_matrix, lambda m: m["capabilities"][1].update(status="supported"))
    assert any("unknown evidence" in error for error in validate(valid_matrix))


def test_unknown_requires_owner_and_exit_condition(valid_matrix):
    rewrite(
        valid_matrix,
        lambda m: m["capabilities"][1].update(owner="", exit_condition=""),
    )
    errors = validate(valid_matrix)
    assert any("owner" in error for error in errors)
    assert any("exit_condition" in error for error in errors)


def test_observed_requires_existing_relative_fixture(valid_matrix):
    rewrite(
        valid_matrix,
        lambda m: m["capabilities"][0].update(
            evidence_path="/Users/private/probe.json"
        ),
    )
    errors = validate(valid_matrix)
    assert any("relative" in error or "private" in error for error in errors)


def test_observed_fixture_version_must_match_directory(valid_matrix):
    rewrite(
        valid_matrix,
        lambda m: m["capabilities"][0].update(
            evidence_path="specs/codex-support/evidence/codex-0.148.0/shell.json"
        ),
    )
    assert any("0.147.0" in error for error in validate(valid_matrix))


def test_observed_fixture_identity_must_match_matrix(valid_matrix):
    root, _, _ = valid_matrix
    fixture = root / "specs/codex-support/evidence/codex-0.147.0/shell.json"
    payload = json.loads(fixture.read_text())
    payload["cli_version"] = "0.148.0"
    fixture.write_text(json.dumps(payload))
    assert any("cli_version" in error for error in validate(valid_matrix))


def test_stale_source_is_rejected(valid_matrix):
    assert any(
        "expired" in error for error in validate(valid_matrix, today=date(2026, 11, 9))
    )


def test_required_documented_claim_fails_require_evidence(valid_matrix):
    rewrite(
        valid_matrix,
        lambda m: m["capabilities"][0].update(
            evidence_level="documented",
            evidence_path=None,
            source={
                "kind": "official-documentation",
                "reference": "https://learn.chatgpt.com/docs/hooks",
                "checked_at": "2026-08-10",
                "expires_at": "2026-11-08",
            },
        ),
    )
    assert validate(valid_matrix) == []
    assert any(
        "load-bearing" in error
        for error in validate(valid_matrix, require_evidence=True)
    )


def test_effective_config_requires_sha256(valid_matrix):
    rewrite(
        valid_matrix,
        lambda m: m["capabilities"][0].update(
            config={"scope": "effective", "sha256": "not-a-hash"}
        ),
    )
    assert any("sha256" in error for error in validate(valid_matrix))


def test_fixture_with_private_path_is_rejected(valid_matrix):
    root, _, _ = valid_matrix
    fixture = root / "specs/codex-support/evidence/codex-0.147.0/shell.json"
    payload = json.loads(fixture.read_text())
    payload["result"]["cwd"] = "/Users/private/repository"
    fixture.write_text(json.dumps(payload))
    assert any("private or absolute path" in error for error in validate(valid_matrix))


def test_fixture_capture_label_must_be_in_the_closed_vocabulary(valid_matrix):
    """A hand-authored fixture must not be able to wear a captured provenance label."""
    root, _, _ = valid_matrix
    fixture = root / "specs/codex-support/evidence/codex-0.147.0/shell.json"
    payload = json.loads(fixture.read_text())
    payload["capture"] = "hand-written-by-an-agent"
    fixture.write_text(json.dumps(payload))
    assert any("capture unsupported" in error for error in validate(valid_matrix))


def test_transcribed_capture_label_is_accepted(valid_matrix):
    root, _, _ = valid_matrix
    fixture = root / "specs/codex-support/evidence/codex-0.147.0/shell.json"
    payload = json.loads(fixture.read_text())
    payload["capture"] = "transcribed-isolated-live-probe"
    fixture.write_text(json.dumps(payload))
    assert validate(valid_matrix) == []


def test_observed_claim_rejects_unknown_fixture_result(valid_matrix):
    root, _, _ = valid_matrix
    fixture = root / "specs/codex-support/evidence/codex-0.147.0/shell.json"
    payload = json.loads(fixture.read_text())
    payload["result"]["status"] = "unknown"
    fixture.write_text(json.dumps(payload))
    assert any("result.status" in error for error in validate(valid_matrix))
