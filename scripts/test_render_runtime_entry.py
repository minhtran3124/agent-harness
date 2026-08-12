import json
from pathlib import Path

import pytest

import render_runtime_entry as entry


ROOT = Path(__file__).resolve().parents[1]


def clone_inputs(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "adapters").mkdir(parents=True)
    (root / "agents").mkdir()
    for relative in (
        "adapters/runtime-entry-bindings.json",
        "agents/runtime-bindings.json",
    ):
        destination = root / relative
        destination.write_bytes((ROOT / relative).read_bytes())
    return root


def test_live_binding_is_total_and_preserves_model_diversity():
    binding, agents = entry.validate(ROOT)
    for runtime in entry.RUNTIMES:
        assert entry.model_label(
            binding, agents, runtime, "correctness_finder"
        ) != entry.model_label(binding, agents, runtime, "correctness_scorer")
        assert entry.model_label(
            binding, agents, runtime, "implementer"
        ) != entry.model_label(binding, agents, runtime, "intent_reviewer")


def test_paired_skill_cli_golden_output():
    binding, _ = entry.validate(ROOT)
    assert entry.cli_command(
        binding, "claude", "feature-intake", "<case prompt>"
    ) == "claude -p '/feature-intake <case prompt>' --output-format text"
    assert entry.cli_command(
        binding, "codex", "feature-intake", "<case prompt>"
    ) == "codex exec '$feature-intake <case prompt>'"


def test_paired_model_label_golden_output():
    binding, agents = entry.validate(ROOT)
    assert entry.model_label(
        binding, agents, "claude", "task_reviewer"
    ) == "claude-opus-5"
    assert entry.model_label(
        binding, agents, "codex", "task_reviewer"
    ) == "gpt-5.6-terra"
    assert entry.model_label(
        binding, agents, "claude", "correctness_scorer"
    ) == "claude-opus-4-8"
    assert entry.model_label(
        binding, agents, "codex", "correctness_scorer"
    ) == "gpt-5.6-sol"


def test_missing_runtime_or_model_stage_is_rejected(tmp_path):
    root = clone_inputs(tmp_path)
    path = root / "adapters/runtime-entry-bindings.json"
    value = json.loads(path.read_text())
    del value["runtimes"]["codex"]
    path.write_text(json.dumps(value))
    with pytest.raises(entry.BindingError, match="claude and codex"):
        entry.validate(root)

    root = clone_inputs(tmp_path / "stage")
    path = root / "adapters/runtime-entry-bindings.json"
    value = json.loads(path.read_text())
    del value["model_stages"]["intent_reviewer"]
    path.write_text(json.dumps(value))
    with pytest.raises(entry.BindingError, match="model stages"):
        entry.validate(root)


def test_collapsed_model_diversity_is_rejected(tmp_path):
    root = clone_inputs(tmp_path)
    path = root / "adapters/runtime-entry-bindings.json"
    value = json.loads(path.read_text())
    value["model_stages"]["correctness_scorer"] = "reviewer"
    path.write_text(json.dumps(value))
    with pytest.raises(entry.BindingError, match="scorer must differ"):
        entry.validate(root)


def test_unknown_field_or_embedded_prompt_placeholder_is_rejected(tmp_path):
    root = clone_inputs(tmp_path)
    path = root / "adapters/runtime-entry-bindings.json"
    value = json.loads(path.read_text())
    value["extra"] = True
    path.write_text(json.dumps(value))
    with pytest.raises(entry.BindingError, match="unknown top-level"):
        entry.validate(root)

    root = clone_inputs(tmp_path / "prompt")
    path = root / "adapters/runtime-entry-bindings.json"
    value = json.loads(path.read_text())
    value["runtimes"]["codex"]["cli"]["arguments"] = ["--prompt={prompt}"]
    path.write_text(json.dumps(value))
    with pytest.raises(entry.BindingError, match="prompt placeholder"):
        entry.validate(root)


def test_skill_names_are_strict_and_shell_output_is_quoted():
    binding, _ = entry.validate(ROOT)
    with pytest.raises(entry.BindingError, match="kebab-case"):
        entry.cli_command(binding, "codex", "../../unsafe", "prompt")
    command = entry.cli_command(binding, "codex", "feature-intake", "has ' quote")
    assert command == "codex exec '$feature-intake has '\"'\"' quote'"
