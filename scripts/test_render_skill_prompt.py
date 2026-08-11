import json
import subprocess
import sys
from pathlib import Path

import render_skill_prompt as module


SCRIPT = Path(__file__).with_name("render_skill_prompt.py")


def run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True
    )


def test_composes_provenance_and_values(tmp_path):
    first = tmp_path / "shared.md"
    second = tmp_path / "role.md"
    values = tmp_path / "values.json"
    first.write_text("shared {{NAME}}")
    second.write_text("role")
    values.write_text(json.dumps({"NAME": "Ada"}))
    result = run("--fragment", first, "--fragment", second, "--values", values)
    assert result.returncode == 0
    assert "source:" in result.stdout and "shared Ada" in result.stdout


def test_rejects_unresolved_or_missing_fragment(tmp_path):
    fragment = tmp_path / "fragment.md"
    fragment.write_text("{{MISSING}}")
    assert run("--fragment", fragment).returncode == 1
    assert run("--fragment", tmp_path / "missing.md").returncode == 1


def test_live_required_policy_delivery_passes():
    root = SCRIPT.parent.parent
    result = run("--root", root, "--check-all")
    assert result.returncode == 0, result.stderr


def test_context_matrix_enumerates_every_isolated_context():
    assert set(module.CONTEXT_MATRIX) == {
        "main.plan-author",
        "main.plan-executor",
        "implementer",
        "task-reviewer",
        "plan-document-reviewer",
        "correctness-controller",
        "correctness-reviewer",
        "correctness-scorer",
        "intent-controller",
        "resume",
    }


def test_every_empty_delivery_has_a_rationale():
    for context, spec in module.CONTEXT_MATRIX.items():
        if not spec["required"]:
            assert spec.get("rationale"), context


def test_each_policy_delivery_edge_is_load_bearing(tmp_path):
    source_root = SCRIPT.parent.parent
    for context, spec in module.CONTEXT_MATRIX.items():
        for token in spec["required"]:
            target = tmp_path / spec["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                (source_root / spec["path"]).read_text().replace(token, "REMOVED")
            )
            errors = module.check_all(tmp_path)
            assert any(context in error and token in error for error in errors), (
                context,
                token,
                errors,
            )
            target.unlink()


def test_check_all_rejects_invalid_correctness_config(tmp_path):
    for spec in module.CONTEXT_MATRIX.values():
        path = tmp_path / spec["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(spec["required"]))
    config = tmp_path / "skills/correctness-review/review-config.json"
    config.write_text(
        json.dumps(
            {
                "finder_angles": ["one"],
                "default_threshold": 75,
                "minimum_threshold": 60,
            }
        )
    )
    result = run("--root", tmp_path, "--check-all")
    assert result.returncode == 1
    assert "finder-angle" in result.stderr
