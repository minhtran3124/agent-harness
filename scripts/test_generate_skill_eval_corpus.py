"""Tests for checked-in prompt-eval corpus generation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("generate_skill_eval_corpus.py")


def test_generator_emits_complete_balanced_catalog(tmp_path):
    subprocess.run([sys.executable, str(SCRIPT), "--root", str(tmp_path)], check=True)
    root = tmp_path / "evals/skills/prompt-refactor"
    manifest = json.loads((root / "corpus-manifest.json").read_text())
    assert len(manifest["skills"]) == 12
    for entry in manifest["skills"]:
        activation = json.loads((tmp_path / entry["activation"]).read_text())["cases"]
        behavior = json.loads((tmp_path / entry["behavior"]).read_text())["cases"]
        assert len([case for case in activation if case["should_trigger"]]) == 8
        assert len([case for case in activation if not case["should_trigger"]]) == 8
        assert {case["kind"] for case in behavior} == {"golden", "boundary", "handoff"}
    end_to_end = json.loads((tmp_path / manifest["end_to_end"]).read_text())["cases"]
    assert {case["id"] for case in end_to_end} == {
        "e2e-tiny", "e2e-normal", "e2e-high-risk", "e2e-resume", "e2e-workflow-engine"
    }
