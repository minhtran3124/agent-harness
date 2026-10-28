"""Tests for plan_groups.py."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("plan_groups.py")


def run(data, *extra):
    return subprocess.run([sys.executable, str(SCRIPT), *extra], input=json.dumps(data),
                          capture_output=True, text=True)


def groups(r):
    return {x["n"]: x["group"] for x in json.loads(r.stdout)}


def test_single_ticket_is_group_one():
    r = run([{"n": 346, "deps": []}])
    assert r.returncode == 0 and groups(r) == {346: 1}


def test_independent_tickets_share_group_one():
    assert groups(run([{"n": 1, "deps": []}, {"n": 2}])) == {1: 1, 2: 1}


def test_longest_path_wins():
    r = run([{"n": 4, "deps": [2, 3]}, {"n": 3, "deps": [2]}, {"n": 2, "deps": []}])
    assert groups(r) == {2: 1, 3: 2, 4: 3}


def test_output_keeps_input_order():
    r = run([{"n": 9, "deps": [5]}, {"n": 5, "deps": []}])
    assert [x["n"] for x in json.loads(r.stdout)] == [9, 5]


def test_dep_outside_batch_is_ignored_with_note():
    r = run([{"n": 7, "deps": [99]}])
    assert r.returncode == 0 and groups(r) == {7: 1}
    assert "#99" in r.stderr and "closed" in r.stderr


def test_cycle_exits_2_naming_tickets():
    r = run([{"n": 1, "deps": [2]}, {"n": 2, "deps": [3]}, {"n": 3, "deps": [1]}])
    assert r.returncode == 2
    assert all(f"#{n}" in r.stderr for n in (1, 2, 3))


def test_input_file(tmp_path):
    f = tmp_path / "in.json"
    f.write_text(json.dumps([{"n": 1, "deps": []}, {"n": 2, "deps": [1]}]))
    r = subprocess.run([sys.executable, str(SCRIPT), "--input", str(f)],
                       capture_output=True, text=True)
    assert groups(r) == {1: 1, 2: 2}


def test_bad_json_exits_2():
    r = subprocess.run([sys.executable, str(SCRIPT)], input="nope", capture_output=True, text=True)
    assert r.returncode == 2
