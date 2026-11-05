"""Tests for load_profile.py."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("load_profile.py")
DEFAULT = Path(__file__).resolve().parent.parent / "profile.json"


def run(repo_dir, *extra):
    return subprocess.run([sys.executable, str(SCRIPT), "--repo-dir", str(repo_dir), *extra],
                          capture_output=True, text=True)


def override(tmp_path, data):
    d = tmp_path / ".claude"
    d.mkdir()
    (d / "autopilot-profile.json").write_text(data if isinstance(data, str) else json.dumps(data))


def test_default_profile_without_override(tmp_path):
    r = run(tmp_path)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == json.loads(DEFAULT.read_text())


def test_default_keeps_sonnet_orchestrator():
    assert json.loads(DEFAULT.read_text())["orchestrator"] == "sonnet"


def test_override_replaces_keys_and_merges_stages(tmp_path):
    base = tmp_path / "base.json"
    base.write_text(json.dumps({"orchestrator": "sonnet", "advisor": "opus",
                                "stages": {"review": {"model": "sonnet"}, "qa": {"effort": "low"}}}))
    override(tmp_path, {"orchestrator": "opus", "stages": {"review": {"model": "opus"}}})
    r = run(tmp_path, "--default", str(base))
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["orchestrator"] == "opus" and out["advisor"] == "opus"
    assert out["stages"] == {"review": {"model": "opus"}, "qa": {"effort": "low"}}


def test_locked_stage_exits_2(tmp_path):
    override(tmp_path, {"stages": {"implement": {"model": "opus"}}})
    r = run(tmp_path)
    assert r.returncode == 2 and "implement is locked" in r.stderr


def test_bad_values_exit_2(tmp_path):
    for bad, msg in [({"orchestrator": "haiku"}, "orchestrator must be"),
                     ({"stages": {"review": {"model": "fable"}}}, "review.model must be"),
                     ({"stages": {"review": {"effort": "huge"}}}, "review.effort must be"),
                     ({"color": "red"}, "unknown key 'color'")]:
        sub = tmp_path / msg.split()[0].replace("'", "")
        sub.mkdir()
        override(sub, bad)
        r = run(sub)
        assert r.returncode == 2 and msg in r.stderr, (bad, r.stderr)


def test_bad_json_exits_2(tmp_path):
    override(tmp_path, "nope")
    r = run(tmp_path)
    assert r.returncode == 2 and "autopilot-profile.json" in r.stderr
