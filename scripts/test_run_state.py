import json
import os
import subprocess
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


def test_init_creates_queued_run():
    assert rs.main(["init", "--slug", "demo", "--run-id", "r1"]) == 0
    assert rs.read_json("specs/demo/RUN.json")["state"] == "queued"
    assert rs.read_json("specs/demo/RUN.json")["run_id"] == "r1"


def test_init_idempotent_same_run_id():
    assert rs.main(["init", "--slug", "demo", "--run-id", "r1"]) == 0
    assert rs.main(["init", "--slug", "demo", "--run-id", "r1"]) == 0


def test_init_conflict_different_run_id():
    assert rs.main(["init", "--slug", "demo", "--run-id", "r1"]) == 0
    assert rs.main(["init", "--slug", "demo", "--run-id", "r2"]) == 2


def test_transition_happy_path():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    rc = rs.main(
        [
            "transition",
            "--slug",
            "demo",
            "--to",
            "investigating",
            "--event",
            "agent.started",
        ]
    )
    assert rc == 0
    assert rs.read_json("specs/demo/RUN.json")["state"] == "investigating"


def test_idempotent_replay_and_conflict():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    args = [
        "transition",
        "--slug",
        "demo",
        "--to",
        "investigating",
        "--event",
        "agent.started",
        "--event-id",
        "fixed-id",
    ]
    assert rs.main(args) == 0
    line_count_after_first = sum(1 for _ in open("specs/demo/events.jsonl"))
    assert rs.main(args) == 0  # replay: no-op
    assert sum(1 for _ in open("specs/demo/events.jsonl")) == line_count_after_first

    conflicting = [
        "transition",
        "--slug",
        "demo",
        "--to",
        "planning",
        "--event",
        "agent.started",
        "--event-id",
        "fixed-id",
    ]
    assert rs.main(conflicting) == 2


def test_shipped_requires_valid_sha():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    for to_state in (
        "investigating",
        "planning",
        "implementing",
        "verifying",
        "ready_to_merge",
    ):
        rs.main(
            [
                "transition",
                "--slug",
                "demo",
                "--to",
                to_state,
                "--event",
                "agent.step",
            ]
        )
    assert (
        rs.main(
            [
                "transition",
                "--slug",
                "demo",
                "--to",
                "shipped",
                "--event",
                "ci.merged",
            ]
        )
        == 2
    )
    assert (
        rs.main(
            [
                "transition",
                "--slug",
                "demo",
                "--to",
                "shipped",
                "--event",
                "ci.merged",
                "--sha",
                "not-a-sha",
            ]
        )
        == 2
    )
    assert (
        rs.main(
            [
                "transition",
                "--slug",
                "demo",
                "--to",
                "shipped",
                "--event",
                "ci.merged",
                "--sha",
                "abc1234",
            ]
        )
        == 0
    )


def test_post_terminal_transition_rejected():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    for to_state in (
        "investigating",
        "planning",
        "implementing",
        "verifying",
        "ready_to_merge",
    ):
        rs.main(["transition", "--slug", "demo", "--to", to_state, "--event", "e"])
    rs.main(
        [
            "transition",
            "--slug",
            "demo",
            "--to",
            "shipped",
            "--event",
            "e",
            "--sha",
            "abc1234",
        ]
    )
    assert (
        rs.main(
            [
                "transition",
                "--slug",
                "demo",
                "--to",
                "investigating",
                "--event",
                "e",
            ]
        )
        == 2
    )


def test_status_json_output():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert rs.main(["status", "--slug", "demo", "--json"]) == 0
    data = json.loads(buf.getvalue())
    assert data["state"] == "queued"
    assert data["run_id"] == "r1"


def test_status_missing_run_exits_3():
    assert rs.main(["status", "--slug", "nope"]) == 3


def test_rebuild_reproduces_projection():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    rs.main(["transition", "--slug", "demo", "--to", "investigating", "--event", "e"])
    before = rs.read_json("specs/demo/RUN.json")
    os.remove("specs/demo/RUN.json")
    assert rs.main(["rebuild", "--slug", "demo"]) == 0
    assert rs.read_json("specs/demo/RUN.json") == before


def test_rebuild_check_detects_drift():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    rs.atomic_write_json("specs/demo/RUN.json", {"tampered": True})
    assert rs.main(["rebuild", "--slug", "demo", "--check"]) == 3


def test_corrupt_log_fails_visibly():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    with open("specs/demo/events.jsonl", "a") as f:
        f.write("not json at all\n")
    assert rs.main(["rebuild", "--slug", "demo"]) == 3
    assert rs.main(["rebuild", "--slug", "demo", "--check"]) == 3


def test_list_active_excludes_terminal_states():
    rs.main(["init", "--slug", "alive", "--run-id", "r1"])
    rs.main(["init", "--slug", "done", "--run-id", "r2"])
    for to_state in (
        "investigating",
        "planning",
        "implementing",
        "verifying",
        "ready_to_merge",
    ):
        rs.main(["transition", "--slug", "done", "--to", to_state, "--event", "e"])
    rs.main(
        [
            "transition",
            "--slug",
            "done",
            "--to",
            "shipped",
            "--event",
            "e",
            "--sha",
            "abc1234",
        ]
    )
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rs.main(["list", "--active", "--json"])
    slugs = {row["slug"] for row in json.loads(buf.getvalue())}
    assert slugs == {"alive"}


def test_concurrent_writers_sequence_contiguously():
    # Separate OS processes (not threads) so the fcntl lock is exercised for real —
    # threads share one process's fd table in a way that doesn't test flock the way
    # independent CLI invocations (e.g. two separate agent sessions) would.
    #
    # All 5 processes attempt the SAME edge (queued -> investigating) with DISTINCT
    # event_ids, so none can idempotently match another's line. Only the process that
    # wins the lock first sees from_state == "queued" and succeeds; by the time the
    # other 4 acquire the lock, the state has already moved to "investigating", and
    # "investigating -> investigating" is not a valid transition (not in
    # FORWARD_TRANSITIONS, and self-loops aren't part of the universal interrupt set
    # either) — so they exit 2 without appending anything. This is the actual property
    # SC-7 needs: the lock serializes concurrent access so exactly one FSM-valid winner
    # commits and the losers fail cleanly, with no duplicate/gapped seq numbers and no
    # partial or interleaved writes to events.jsonl.
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    script = os.path.abspath(__file__).replace("test_run_state.py", "run_state.py")
    procs = []
    for i in range(5):
        procs.append(
            subprocess.Popen(
                [
                    sys.executable,
                    script,
                    "transition",
                    "--slug",
                    "demo",
                    "--to",
                    "investigating",
                    "--event",
                    "agent.started",
                    "--event-id",
                    f"writer-{i}",
                ],
                cwd=os.getcwd(),
            )
        )
    returncodes = sorted(p.wait() for p in procs)
    assert returncodes == [0, 2, 2, 2, 2]

    events = rs.read_events("demo")
    seqs = [ev["seq"] for ev in events]
    assert seqs == list(range(1, len(events) + 1))  # contiguous: [1, 2], no gaps
    assert len(set(seqs)) == len(seqs)  # no duplicates
    assert len(events) == 2  # init + exactly one winner
    assert rs.read_json("specs/demo/RUN.json")["state"] == "investigating"
