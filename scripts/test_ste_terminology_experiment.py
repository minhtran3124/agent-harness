import importlib.util
import pathlib
import shutil
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPERIMENT = ROOT / "specs/ste-terminology-evidence/experiment"


def load_rerun_module():
    path = EXPERIMENT / "rerun.py"
    spec = importlib.util.spec_from_file_location("ste_terminology_rerun", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(script: pathlib.Path):
    return subprocess.run(
        ["python3", str(script)],
        cwd=script.parent,
        capture_output=True,
        text=True,
        check=False,
    )


def test_final_output_matches_archived_results():
    completed = run(EXPERIMENT / "final.py")

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == (EXPERIMENT / "results.txt").read_text(encoding="utf-8")


def test_missing_trial_fails_instead_of_reporting_zeroes(tmp_path):
    copied = tmp_path / "experiment"
    shutil.copytree(EXPERIMENT, copied)
    ledger = copied / "raw-trials.txt"
    ledger.write_text(
        ledger.read_text(encoding="utf-8").replace(
            "r2-e4-B5 1: NO 2: NO 3: YES 4: NO\n", ""
        ),
        encoding="utf-8",
    )

    completed = run(copied / "final.py")

    assert completed.returncode == 1
    assert "missing trials [5]" in completed.stderr


def test_legacy_score_entrypoint_uses_canonical_scorer():
    legacy = run(EXPERIMENT / "score.py")
    canonical = run(EXPERIMENT / "final.py")

    assert legacy.returncode == canonical.returncode == 0
    assert legacy.stdout == canonical.stdout


def test_rerun_protocol_preserves_original_launch_inventory():
    rerun = load_rerun_module()

    assert len(rerun.GROUPS) == 14
    assert sum(group.trials for group in rerun.GROUPS) == 76
    assert sum(group.trials for group in rerun.GROUPS if group.model == "sonnet") == 70
    assert sum(group.trials for group in rerun.GROUPS if group.model == "opus") == 6


def test_rerun_e4_prompt_keeps_original_single_space_before_reply():
    rerun = load_rerun_module()
    e4_prompts = [group.prompt for group in rerun.GROUPS if "-e4-" in group.name]

    assert len(e4_prompts) == 4
    assert all(
        "Use YES if the statement holds and NO if it does not. Reply with" in prompt
        for prompt in e4_prompts
    )
    assert all("does not.\n\nReply with" not in prompt for prompt in e4_prompts)


def test_rerun_score_only_regenerates_summary(tmp_path):
    rerun = load_rerun_module()
    output = tmp_path / "rerun"
    output.mkdir()
    records = [
        {
            "group": "r1-e1-A",
            "exit_code": 0,
            "cost_usd": 0.125,
            "observation": {"ledger_appended": True, "count": "7"},
        }
    ]
    (output / "raw-results.jsonl").write_text(
        "\n".join(rerun.json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            "python3",
            str(EXPERIMENT / "rerun.py"),
            "--output",
            str(output),
            "--score-only",
        ],
        cwd=EXPERIMENT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith("launched=1 completed=1 scored=1\n")
    assert "cost_usd=0.125000" in completed.stdout
    assert (output / "results.txt").read_text(encoding="utf-8") == completed.stdout
