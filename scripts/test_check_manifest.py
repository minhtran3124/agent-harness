"""Tests for scripts/check_manifest.py — run via pytest (wired into run-tests.sh)."""

import json
import subprocess
import sys
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_manifest.py"

# A minimal risk-corroboration.sh stub exposing add_cat for two gates.
# Gate modes are manifest-owned (read by the hook at runtime) — not mirrored here.
RC_STUB = """#!/bin/bash
add_cat "auth"
add_cat "high-blast"
"""

MANIFEST_OK = {
    "hard_gates": {
        "detectable": [
            {"slug": "auth", "mode": "block", "desc": "x"},
            {"slug": "high-blast", "mode": "block", "desc": "y"},
        ],
        "judgment": [{"slug": "remove-functionality", "desc": "z"}],
    },
    "hooks": [
        {"name": "risk-corroboration.sh", "wired": True},
        {"name": "dormant.sh", "wired": False},
    ],
    "skills": ["alpha"],
    "agents": ["reviewer"],
    "contracts": {
        "c1": {"surface": ["settings.json"], "consumers": ["CLAUDE.md"]},
    },
}


def build(root: Path, manifest: dict) -> None:
    """Write a minimal but self-consistent harness layout under root."""
    (root / "hooks").mkdir(parents=True, exist_ok=True)
    (root / "hooks" / "risk-corroboration.sh").write_text(RC_STUB)
    (root / "hooks" / "dormant.sh").write_text("#!/bin/bash\n")
    (root / "skills" / "alpha").mkdir(parents=True, exist_ok=True)
    (root / "skills" / "alpha" / "SKILL.md").write_text("# alpha\n")
    (root / "agents").mkdir(parents=True, exist_ok=True)
    (root / "agents" / "reviewer.md").write_text("# reviewer\n")
    (root / "agents" / "README.md").write_text("# readme (excluded)\n")
    (root / "CLAUDE.md").write_text("# claude\n")
    # settings.json wires only risk-corroboration.sh (dormant.sh is unwired).
    (root / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {"hooks": [{"command": "hooks/risk-corroboration.sh"}]}
                    ]
                }
            }
        )
    )
    (root / "harness-manifest.json").write_text(json.dumps(manifest))


def run(root: Path):
    return subprocess.run(
        [sys.executable, str(CHECKER), "--root", str(root)],
        capture_output=True,
        text=True,
    )


def test_clean_fixture_passes(tmp_path):
    build(tmp_path, MANIFEST_OK)
    r = run(tmp_path)
    assert r.returncode == 0, r.stderr


def test_real_repo_passes():
    # The actual repo manifest must be consistent (guards live drift).
    repo = CHECKER.parent.parent
    r = run(repo)
    assert r.returncode == 0, r.stderr


def test_disk_hook_missing_from_manifest(tmp_path):
    build(tmp_path, MANIFEST_OK)
    (tmp_path / "hooks" / "surprise.sh").write_text("#!/bin/bash\n")
    r = run(tmp_path)
    assert r.returncode == 1
    assert "surprise.sh" in r.stderr and "missing from manifest" in r.stderr


def test_wired_flag_mismatch(tmp_path):
    m = json.loads(json.dumps(MANIFEST_OK))
    m["hooks"][1]["wired"] = True  # claim dormant.sh is wired; settings.json says no
    build(tmp_path, m)
    r = run(tmp_path)
    assert r.returncode == 1
    assert "dormant.sh" in r.stderr and "wired" in r.stderr


def test_detectable_gate_absent_from_hook(tmp_path):
    m = json.loads(json.dumps(MANIFEST_OK))
    m["hard_gates"]["detectable"].append(
        {"slug": "authorization", "mode": "block", "desc": "q"}
    )
    build(tmp_path, m)  # RC_STUB has no authorization add_cat
    r = run(tmp_path)
    assert r.returncode == 1
    assert "authorization" in r.stderr


def test_hook_add_cat_absent_from_manifest(tmp_path):
    build(tmp_path, MANIFEST_OK)
    # Add a gate the hook detects but the manifest doesn't declare.
    rc = tmp_path / "hooks" / "risk-corroboration.sh"
    rc.write_text(rc.read_text() + '\nadd_cat "public-contract"\n')
    r = run(tmp_path)
    assert r.returncode == 1
    assert "public-contract" in r.stderr


def test_contract_surface_missing(tmp_path):
    m = json.loads(json.dumps(MANIFEST_OK))
    m["contracts"]["c1"]["surface"] = ["no/such/file.txt"]
    build(tmp_path, m)
    r = run(tmp_path)
    assert r.returncode == 1
    assert "contracts" in r.stderr and "no/such/file.txt" in r.stderr


def test_contract_consumer_missing(tmp_path):
    m = json.loads(json.dumps(MANIFEST_OK))
    m["contracts"]["c1"]["consumers"] = ["no/such/consumer.txt"]
    build(tmp_path, m)
    r = run(tmp_path)
    assert r.returncode == 1
    assert "contracts" in r.stderr and "no/such/consumer.txt" in r.stderr


def test_contract_value_not_dict(tmp_path):
    m = json.loads(json.dumps(MANIFEST_OK))
    m["contracts"]["c1"] = "settings.json"
    build(tmp_path, m)
    r = run(tmp_path)
    assert r.returncode == 1
    assert "contracts" in r.stderr
    assert "Traceback" not in r.stderr


def test_contract_surface_not_list(tmp_path):
    m = json.loads(json.dumps(MANIFEST_OK))
    m["contracts"]["c1"]["surface"] = "settings.json"
    build(tmp_path, m)
    r = run(tmp_path)
    assert r.returncode == 1
    assert "contracts" in r.stderr
    assert "Traceback" not in r.stderr


def test_skill_missing_from_disk(tmp_path):
    m = json.loads(json.dumps(MANIFEST_OK))
    m["skills"].append("ghost")
    build(tmp_path, m)
    r = run(tmp_path)
    assert r.returncode == 1
    assert "ghost" in r.stderr


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))
