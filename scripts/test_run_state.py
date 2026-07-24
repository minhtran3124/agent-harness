import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import run_state as rs


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("specs", exist_ok=True)
    yield tmp_path


def test_atomic_write_json_leaves_no_tmp_file_and_correct_content():
    os.makedirs("specs/demo", exist_ok=True)
    path = "specs/demo/RUN.json"
    rs.atomic_write_json(path, {"a": 1})
    assert rs.read_json(path) == {"a": 1}
    assert not [
        f for f in os.listdir("specs/demo") if f.endswith(".tmp." + str(os.getpid()))
    ]


def test_read_events_missing_file_raises_storage_error():
    with pytest.raises(rs.StorageError):
        rs.read_events("nope")


def test_read_events_corrupt_line_raises_storage_error():
    os.makedirs("specs/demo", exist_ok=True)
    with open("specs/demo/events.jsonl", "w") as f:
        f.write('{"seq": 1}\n')
        f.write("not json\n")
    with pytest.raises(rs.StorageError):
        rs.read_events("demo")


def test_read_events_truncated_last_line_raises_storage_error():
    os.makedirs("specs/demo", exist_ok=True)
    with open("specs/demo/events.jsonl", "w") as f:
        f.write('{"seq": 1}\n')
        f.write('{"seq": 2, "trunc')  # no closing brace/newline
    with pytest.raises(rs.StorageError):
        rs.read_events("demo")
