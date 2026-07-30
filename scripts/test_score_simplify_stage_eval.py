from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("score_simplify_stage_eval.py")
SPEC = importlib.util.spec_from_file_location("score_simplify_stage_eval", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def record(
    case_id: str,
    *,
    outcome: str,
    changed_files: list[str] | None = None,
    verify_exit: int = 0,
    review_exit: int = 0,
    removed_lines: int = 0,
) -> dict:
    changed_files = changed_files or []
    changed = outcome == "changed"
    return {
        "case_id": case_id,
        "fixture_digest": "",
        "worktree": f"/discarded/{case_id}",
        "base_sha": "1" * 40,
        "pre_sha": "2" * 40,
        "post_sha": "3" * 40 if changed else "2" * 40,
        "outcome": outcome,
        "changed_files": changed_files,
        "diff_stats": {
            "simplify_added_lines": 0,
            "simplify_removed_lines": removed_lines,
        },
        "claude": {
            "returncode": 0,
            "invocations": 1,
            "observed_skill_invocations": ["simplify"],
            "skill_tool_evidence": {
                "tool_use_id": "skill-0",
                "skill": "simplify",
                "result_count": 1,
                "result_status": "success",
            },
            "command": ["claude"],
            "elapsed_seconds": 0.1,
            "result": "done",
            "usage": {},
        },
        "verification": [{
            "command": ["/usr/bin/true"],
            "returncode": verify_exit,
            "elapsed_seconds": 0.1,
            "stdout": "",
            "stderr": "",
        }],
        "final_review": [{
            "command": ["/usr/bin/true"],
            "returncode": review_exit,
            "elapsed_seconds": 0.1,
            "stdout": "",
            "stderr": "",
        }],
        "artifacts": {
            name: {"path": f"{case_id}/{name}", "sha256": "f" * 64}
            for name in (
                "pre_diff",
                "simplify_diff",
                "post_diff",
                "transcript",
                "checks",
                "history_bundle",
            )
        },
    }


def collection(mode: str, records: list[dict], fixtures: Path) -> dict:
    for item in records:
        item["fixture_digest"] = MODULE.RUNNER._fixture_digest(
            fixtures / item["case_id"]
        )
        if mode == "advisory":
            item["claude"].update(
                {
                    "invocations": 0,
                    "observed_skill_invocations": [],
                    "skill_tool_evidence": None,
                    "command": [],
                }
            )
    return {
        "schema_version": 1,
        "mode": mode,
        "collected_at": "2026-07-30T00:00:00+00:00",
        "source_commit_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=SCRIPT.parent.parent,
            text=True,
        ).strip(),
        "input_digest": MODULE.RUNNER.evaluation_input_digest(fixtures),
        "environment": {
            "client_version": "2.1.220",
            "expected_client_version": "2.1.220",
            "model": "sonnet",
        },
        "records": records,
    }


def write_truth(
    root: Path,
    case_id: str,
    *,
    safe_outcomes: list[str],
    value_opportunity: bool,
    allowed_changed_paths: list[str] | None = None,
) -> None:
    fixture = root / case_id
    fixture.mkdir(parents=True)
    (fixture / "base").mkdir()
    (fixture / "candidate").mkdir()
    (fixture / "base" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (fixture / "candidate" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (fixture / "fixture.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "case_id": case_id,
                "verification_commands": [["/usr/bin/true"]],
                "final_review_commands": [["/usr/bin/true"]],
            }
        ),
        encoding="utf-8",
    )
    (fixture / "truth.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "safe_outcomes": safe_outcomes,
                "allowed_changed_paths": allowed_changed_paths or [],
                "value_opportunity": value_opportunity,
                "minimum_removed_lines": 1 if value_opportunity else 0,
            }
        ),
        encoding="utf-8",
    )


def test_quality_gate_rejects_behavior_and_contract_mutations(tmp_path):
    write_truth(
        tmp_path,
        "required-behavior",
        safe_outcomes=["no_op"],
        value_opportunity=False,
    )
    write_truth(
        tmp_path,
        "public-contract",
        safe_outcomes=["no_op"],
        value_opportunity=False,
    )
    baseline = collection(
        "advisory",
        [
            record("required-behavior", outcome="no_op"),
            record("public-contract", outcome="no_op"),
        ],
        tmp_path,
    )
    candidate = collection(
        "candidate",
        [
            record(
                "required-behavior",
                outcome="changed",
                changed_files=["app.py"],
                removed_lines=8,
            ),
            record(
                "public-contract",
                outcome="changed",
                changed_files=["api.py"],
                review_exit=1,
                removed_lines=9,
            ),
        ],
        tmp_path,
    )

    report = MODULE.score_collections(baseline, candidate, tmp_path)

    assert not report.quality_pass
    assert not report.value_evaluated
    assert any("required-behavior: unsafe outcome changed" in item for item in report.errors)
    assert any("public-contract: final review failed" in item for item in report.errors)


def test_quality_gate_rejects_failed_verification_even_when_diff_is_smaller(tmp_path):
    write_truth(
        tmp_path,
        "efficiency",
        safe_outcomes=["changed", "no_op"],
        value_opportunity=True,
        allowed_changed_paths=["app.py"],
    )
    baseline = collection(
        "advisory",
        [record("efficiency", outcome="no_op")],
        tmp_path,
    )
    candidate = collection(
        "candidate",
        [
            record(
                "efficiency",
                outcome="changed",
                changed_files=["app.py"],
                verify_exit=1,
                removed_lines=100,
            )
        ],
        tmp_path,
    )

    report = MODULE.score_collections(baseline, candidate, tmp_path)

    assert not report.quality_pass
    assert not report.value_evaluated
    assert report.value_score is None
    assert "efficiency: verification failed" in report.errors


def test_value_gate_requires_safe_improvement_over_advisory(tmp_path):
    for case_id in ("reuse", "duplication"):
        write_truth(
            tmp_path,
            case_id,
            safe_outcomes=["changed", "no_op"],
            value_opportunity=True,
            allowed_changed_paths=["app.py"],
        )
    baseline = collection(
        "advisory",
        [
            record("reuse", outcome="no_op"),
            record("duplication", outcome="no_op"),
        ],
        tmp_path,
    )
    candidate = collection(
        "candidate",
        [
            record(
                "reuse",
                outcome="changed",
                changed_files=["app.py"],
                removed_lines=3,
            ),
            record(
                "duplication",
                outcome="changed",
                changed_files=["app.py"],
                removed_lines=5,
            ),
        ],
        tmp_path,
    )

    report = MODULE.score_collections(baseline, candidate, tmp_path)

    assert report.quality_pass
    assert report.value_evaluated
    assert report.value_pass
    assert report.value_score == 2
    assert report.baseline_value_score == 0


def test_quality_rejects_changes_outside_fixture_allowlist(tmp_path):
    write_truth(
        tmp_path,
        "reuse",
        safe_outcomes=["changed", "no_op"],
        value_opportunity=True,
        allowed_changed_paths=["app.py"],
    )
    baseline = collection("advisory", [record("reuse", outcome="no_op")], tmp_path)
    candidate = collection(
        "candidate",
        [
            record(
                "reuse",
                outcome="changed",
                changed_files=["app.py", "public_api.py"],
                removed_lines=2,
            )
        ],
        tmp_path,
    )

    report = MODULE.score_collections(baseline, candidate, tmp_path)

    assert not report.quality_pass
    assert any("changed path is not allowed: public_api.py" in item for item in report.errors)


def test_collections_must_cover_exactly_the_truth_corpus(tmp_path):
    write_truth(
        tmp_path,
        "reuse",
        safe_outcomes=["changed", "no_op"],
        value_opportunity=True,
    )
    baseline = collection("advisory", [record("reuse", outcome="no_op")], tmp_path)
    candidate = collection("candidate", [], tmp_path)

    report = MODULE.score_collections(baseline, candidate, tmp_path)

    assert not report.quality_pass
    assert any("case collections differ" in item for item in report.errors)


def test_rejects_schema_source_and_public_fixture_digest_tampering(tmp_path):
    write_truth(
        tmp_path,
        "reuse",
        safe_outcomes=["changed", "no_op"],
        value_opportunity=True,
        allowed_changed_paths=["app.py"],
    )
    baseline = collection("advisory", [record("reuse", outcome="no_op")], tmp_path)
    candidate = collection(
        "candidate",
        [
            record(
                "reuse",
                outcome="changed",
                changed_files=["app.py"],
                removed_lines=2,
            )
        ],
        tmp_path,
    )
    candidate["source_commit_sha"] = "b" * 40
    candidate["input_digest"] = "0" * 64
    candidate["records"][0]["fixture_digest"] = "0" * 64
    candidate["records"][0]["claude"]["observed_skill_invocations"] = []

    report = MODULE.score_collections(baseline, candidate, tmp_path)

    assert not report.quality_pass
    assert any("collection schema invalid" in item for item in report.errors)
    assert "source commit mismatch" in report.errors
    assert any("evaluation input digest" in item for item in report.errors)
    assert any("public fixture digest mismatch" in item for item in report.errors)


def test_artifact_crosscheck_rejects_rehashed_patch_and_metadata_tampering(tmp_path):
    fixtures = tmp_path / "fixtures"
    write_truth(
        fixtures,
        "reuse",
        safe_outcomes=["changed", "no_op"],
        value_opportunity=True,
        allowed_changed_paths=["app.py"],
    )
    fake = tmp_path / "claude"
    fake.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--version\" ]; then\n"
        "  echo '2.1.220 (Claude Code)'\n"
        "  exit 0\n"
        "fi\n"
        "exit 99\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    output = tmp_path / "results" / "baseline.json"
    collection_result = MODULE.RUNNER.collect(
        mode="advisory",
        fixtures=fixtures,
        output=output,
        claude=str(fake),
        expected_client_version="2.1.220",
        model="sonnet",
        source_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=SCRIPT.parent.parent,
            text=True,
        ).strip(),
    )
    assert MODULE.artifact_errors(collection_result, output) == []

    record_result = collection_result["records"][0]
    record_result["diff_stats"]["simplify_added_lines"] = 7
    record_result["verification"][0]["returncode"] = 9
    simplify_path = output.parent / record_result["artifacts"]["simplify_diff"]["path"]
    simplify_path.write_text("forged patch\n", encoding="utf-8")
    record_result["artifacts"]["simplify_diff"]["sha256"] = MODULE._sha256(
        simplify_path
    )
    transcript_path = output.parent / record_result["artifacts"]["transcript"]["path"]
    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    transcript["stdout"] = json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "forged",
                        "name": "Skill",
                        "input": {"skill": "simplify"},
                    }
                ]
            },
        }
    )
    transcript_path.write_text(json.dumps(transcript), encoding="utf-8")
    record_result["artifacts"]["transcript"]["sha256"] = MODULE._sha256(
        transcript_path
    )

    errors = MODULE.artifact_errors(collection_result, output)

    assert any("simplify_diff contradicts history bundle" in item for item in errors)
    assert any("diff_stats contradict history bundle" in item for item in errors)
    assert any("checks artifact contradicts verification" in item for item in errors)
    assert any("advisory transcript contains Claude stream output" in item for item in errors)
