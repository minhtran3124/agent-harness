from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("check_skill_eval_readiness.py")
SPEC = importlib.util.spec_from_file_location("check_skill_eval_readiness", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_expected_and_observed_ids(tmp_path):
    base = tmp_path / "evals/skills/prompt-refactor"
    (base / "activation").mkdir(parents=True)
    (base / "behavior").mkdir()
    (base / "activation/alpha.json").write_text(json.dumps({"cases": [{"id": "a-1"}]}))
    (base / "behavior/alpha.json").write_text(json.dumps({"cases": [{"id": "b-1"}]}))
    (base / "end-to-end.json").write_text(json.dumps({"cases": [{"id": "e-1"}]}))
    (base / "corpus-manifest.json").write_text(json.dumps({
        "skills": [{"name": "alpha", "activation": "evals/skills/prompt-refactor/activation/alpha.json", "behavior": "evals/skills/prompt-refactor/behavior/alpha.json"}],
        "end_to_end": "evals/skills/prompt-refactor/end-to-end.json",
    }))
    result = tmp_path / "results.json"
    result.write_text(json.dumps({"records": [{"case_id": "a-1", "suite": "activation"}]}))
    assert MODULE.expected_ids(tmp_path, "activation") == {"a-1"}
    assert MODULE.observed_ids(result, "activation") == {"a-1"}
    assert MODULE.observed_ids(result, "behavior") == set()
