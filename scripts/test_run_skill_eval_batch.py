from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("run_skill_eval_batch.py")
SPEC = importlib.util.spec_from_file_location("run_skill_eval_batch", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_cases_reads_behavior_prompts_and_falls_back_to_expectation(tmp_path):
    base = tmp_path / "evals/skills/prompt-refactor"
    (base / "behavior").mkdir(parents=True)
    (base / "behavior/alpha.json").write_text(json.dumps({"cases": [
        {"id": "alpha-a", "skill": "alpha", "prompt": "scenario"},
        {"id": "alpha-b", "skill": "alpha", "expectation": "fallback"},
    ]}))
    (base / "corpus-manifest.json").write_text(json.dumps({"skills": [{
        "name": "alpha", "behavior": "evals/skills/prompt-refactor/behavior/alpha.json"
    }]}))
    found = MODULE.cases(tmp_path, "behavior")
    assert found == [
        {"id": "alpha-a", "skill": "alpha", "prompt": "scenario"},
        {"id": "alpha-b", "skill": "alpha", "prompt": "fallback"},
    ]


def test_evaluation_prompt_does_not_force_activation():
    case = {"id": "near-miss", "skill": "alpha", "prompt": "explain a poem"}
    prompt = MODULE.evaluation_prompt(case, "activation")
    assert not prompt.startswith("/alpha")
    assert "TRIGGER or NO-TRIGGER" in prompt


def test_evaluation_prompt_forces_behavior_dispatch():
    case = {"id": "golden", "skill": "alpha", "prompt": "plan this change"}
    prompt = MODULE.evaluation_prompt(case, "behavior")
    assert prompt.startswith("/alpha")
    assert "key safety gate" in prompt
