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


def test_invalid_transition_rejected():
    with pytest.raises(rs.InvalidTransitionError):
        rs.validate_transition("queued", "shipped", None, None)


def test_terminal_state_blocks_transition():
    for terminal in rs.TERMINAL_STATES:
        assert rs.valid_targets(terminal) == set()
        with pytest.raises(rs.InvalidTransitionError):
            rs.validate_transition(terminal, "investigating", None, None)


def test_waiting_and_resume_metadata_required():
    with pytest.raises(rs.InvalidTransitionError):
        rs.validate_transition("investigating", "awaiting_confirmation", None, None)
    rs.validate_transition(
        "investigating", "awaiting_confirmation", "human review", None
    )

    with pytest.raises(rs.InvalidTransitionError):
        rs.validate_transition("implementing", "blocked", None, None)
    rs.validate_transition("implementing", "blocked", None, "ci.green")


def test_forward_happy_path_is_valid():
    chain = [
        ("queued", "investigating"),
        ("investigating", "planning"),
        ("planning", "implementing"),
        ("implementing", "verifying"),
        ("verifying", "ready_to_merge"),
        ("ready_to_merge", "shipped"),
    ]
    for from_state, to_state in chain:
        rs.validate_transition(from_state, to_state, None, None)


def test_project_folds_events_and_carries_sha_forward():
    events = [
        {
            "seq": 1,
            "ts": "t1",
            "slug": "s",
            "run_id": "r",
            "to_state": "queued",
            "event_id": "e1",
            "waiting_on": None,
            "resume_event": None,
            "sha": None,
        },
        {
            "seq": 2,
            "ts": "t2",
            "slug": "s",
            "run_id": "r",
            "to_state": "verifying",
            "event_id": "e2",
            "waiting_on": None,
            "resume_event": None,
            "sha": "abc1234",
        },
        {
            "seq": 3,
            "ts": "t3",
            "slug": "s",
            "run_id": "r",
            "to_state": "ready_to_merge",
            "event_id": "e3",
            "waiting_on": None,
            "resume_event": None,
            "sha": None,
        },
    ]
    proj = rs.project(events)
    assert proj["state"] == "ready_to_merge"
    assert proj["seq"] == 3
    assert (
        proj["sha"] == "abc1234"
    )  # carried forward, not cleared by the sha-less event
    assert proj["created_at"] == "t1"
    assert proj["updated_at"] == "t3"
