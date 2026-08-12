import json
import os
import re
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


def test_read_events_missing_required_key_raises_storage_error():
    os.makedirs("specs/demo", exist_ok=True)
    with open("specs/demo/events.jsonl", "w") as f:
        f.write('{"seq": 1}\n')  # valid JSON, but missing required keys
    with pytest.raises(rs.StorageError):
        rs.read_events("demo")


def test_rebuild_missing_required_key_exits_3():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    with open("specs/demo/events.jsonl", "a") as f:
        f.write('{"seq": 2}\n')  # valid JSON, missing to_state/slug/run_id/etc.
    assert rs.main(["rebuild", "--slug", "demo"]) == 3


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


def test_chain_seq_must_be_contiguous_from_one():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    rs.main(["transition", "--slug", "demo", "--to", "investigating", "--event", "e"])
    events = rs.read_events("demo")
    events[1]["seq"] = 3  # skips seq 2
    with pytest.raises(rs.StorageError, match="expected seq 2, got 3"):
        rs.validate_chain(events, "demo", rs.events_path("demo"))


def test_chain_seq_must_be_int_not_bool():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    events = rs.read_events("demo")
    events[0]["seq"] = True  # True == 1, so only a type guard catches this
    with pytest.raises(rs.StorageError, match="seq is not an int"):
        rs.validate_chain(events, "demo", rs.events_path("demo"))


def test_chain_from_state_must_chain_to_previous_to_state():
    """A rewind: seq 3 claims from_state "queued" (matching seq 1's to_state), but
    its actual predecessor is seq 2, whose to_state is "investigating". Each hop is
    individually legal ("queued" -> "investigating" twice), so only invariant 2 - not
    hop legality - can catch this. A simpler fixture like from_state="planning" would
    raise identically with invariant 2 removed, since validate_transition would
    reject "planning" -> "investigating" on its own (vacuous per SC-12)."""
    events = [
        {
            "event_id": "e1",
            "seq": 1,
            "slug": "demo",
            "run_id": "r1",
            "from_state": None,
            "to_state": "queued",
            "event": "e",
            "waiting_on": None,
            "resume_event": None,
        },
        {
            "event_id": "e2",
            "seq": 2,
            "slug": "demo",
            "run_id": "r1",
            "from_state": "queued",
            "to_state": "investigating",
            "event": "e",
            "waiting_on": None,
            "resume_event": None,
        },
        {
            "event_id": "e3",
            "seq": 3,
            "slug": "demo",
            "run_id": "r1",
            "from_state": "queued",  # should be "investigating" (seq 2's to_state)
            "to_state": "investigating",
            "event": "e",
            "waiting_on": None,
            "resume_event": None,
        },
    ]
    with pytest.raises(rs.StorageError, match="does not match previous to_state"):
        rs.validate_chain(events, "demo", "specs/demo/events.jsonl")


def test_chain_slug_and_run_id_constant():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    rs.main(["transition", "--slug", "demo", "--to", "investigating", "--event", "e"])
    events = rs.read_events("demo")

    tampered = [dict(e) for e in events]
    tampered[1]["run_id"] = "other-run"
    with pytest.raises(rs.StorageError, match="does not match chain run_id"):
        rs.validate_chain(tampered, "demo", rs.events_path("demo"))

    # per-event slug must also stay constant across the chain
    slug_tampered = [dict(e) for e in events]
    slug_tampered[1]["slug"] = "other-slug"
    with pytest.raises(rs.StorageError, match="does not match chain slug"):
        rs.validate_chain(slug_tampered, "demo", rs.events_path("demo"))

    # events[0]["slug"] must also match the slug argument passed in
    with pytest.raises(rs.StorageError, match="does not match requested slug"):
        rs.validate_chain(events, "not-demo", rs.events_path("demo"))


def test_chain_legality_wraps_as_storage_error():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    events = rs.read_events("demo")
    illegal = dict(events[0])
    illegal.update(
        {
            "event_id": "bad-hop",
            "seq": 2,
            "from_state": "queued",
            "to_state": "shipped",  # not a legal hop from queued
        }
    )
    chain = events + [illegal]
    with pytest.raises(rs.StorageError, match="not a valid transition") as exc_info:
        rs.validate_chain(chain, "demo", rs.events_path("demo"))
    assert exc_info.value.exit_code == 3


def test_chain_event_id_unique():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    rs.main(["transition", "--slug", "demo", "--to", "investigating", "--event", "e"])
    events = rs.read_events("demo")
    events[1]["event_id"] = events[0]["event_id"]  # duplicate
    with pytest.raises(rs.StorageError, match="duplicate event_id"):
        rs.validate_chain(events, "demo", rs.events_path("demo"))


def test_chain_genesis_accepted_and_each_bad_variant_rejected():
    """SC-4: genesis is accepted, and a non-genesis event with a null from_state is
    not. Also covers the positive genesis assertion added after round-1 review: a
    bogus genesis (valid types, wrong values) is rejected only by that assertion,
    since hop legality is skipped for seq 1 - nothing else checks that the first
    event's to_state is a real state or its from_state is None. The assertion's two
    clauses are pinned separately (each fixture below violates exactly one), so
    dropping either clause alone still fails one of these."""
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    genesis = rs.read_events("demo")
    rs.validate_chain(genesis, "demo", rs.events_path("demo"))  # no exception

    rs.main(["transition", "--slug", "demo", "--to", "investigating", "--event", "e"])
    events = rs.read_events("demo")
    events[1]["from_state"] = None
    with pytest.raises(rs.StorageError, match="does not match previous to_state"):
        rs.validate_chain(events, "demo", rs.events_path("demo"))

    bad_genesis_from_state = [dict(genesis[0])]
    bad_genesis_from_state[0]["from_state"] = "verifying"  # to_state stays "queued"
    with pytest.raises(
        rs.StorageError, match=r"from_state 'verifying' to_state 'queued'"
    ):
        rs.validate_chain(bad_genesis_from_state, "demo", rs.events_path("demo"))

    bad_genesis_to_state = [dict(genesis[0])]
    bad_genesis_to_state[0]["to_state"] = "investigating"  # from_state stays None
    with pytest.raises(
        rs.StorageError, match=r"from_state None to_state 'investigating'"
    ):
        rs.validate_chain(bad_genesis_to_state, "demo", rs.events_path("demo"))


def test_chain_unhashable_to_state_raises_storage_error_not_typeerror():
    """Must be on a non-genesis event: at seq 1 the positive genesis assertion
    (`to_state != "queued"`) already rejects ["investigating"] with a plain `!=`, no
    TypeError involved, which would make this vacuous for the guard under test. At
    seq 2, only the to_state type guard stands between this and
    validate_transition's `to_state not in ALL_STATES`, which raises TypeError on an
    unhashable value."""
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    rs.main(["transition", "--slug", "demo", "--to", "investigating", "--event", "e"])
    events = rs.read_events("demo")
    events[1]["to_state"] = ["investigating"]  # unhashable
    with pytest.raises(rs.StorageError, match="to_state is not a string"):
        rs.validate_chain(events, "demo", rs.events_path("demo"))


def test_chain_unhashable_event_id_raises_storage_error_not_typeerror():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    events = rs.read_events("demo")
    events[0]["event_id"] = {}  # unhashable
    with pytest.raises(rs.StorageError, match="event_id is not a string"):
        rs.validate_chain(events, "demo", rs.events_path("demo"))


def test_chain_event_field_must_be_a_string():
    """REQUIRED_EVENT_KEYS omits "event", and no invariant previously checked it -
    cmd_transition's idempotent-replay scan dereferences it with a bare subscript
    (`ev["event"] == args.event` at :410), which raises an uncaught KeyError on a log
    entry missing the key entirely rather than the documented 0/2/3 exit contract."""
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    rs.main(["transition", "--slug", "demo", "--to", "investigating", "--event", "e"])
    events = rs.read_events("demo")
    del events[1]["event"]
    with pytest.raises(rs.StorageError, match="event is not a string"):
        rs.validate_chain(events, "demo", rs.events_path("demo"))


def test_event_field_missing_rejected_by_rebuild_and_transition():
    """Issue repro: a log missing "event" on a non-genesis event used to pass
    `rebuild` clean, and a later `transition` then raised an uncaught KeyError (exit
    1, a traceback) instead of the documented 0/2/3 contract. Both paths must now
    reject the log with exit 3, not crash."""
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    rs.main(["transition", "--slug", "demo", "--to", "investigating", "--event", "e"])
    with open("specs/demo/events.jsonl") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    del lines[1]["event"]
    with open("specs/demo/events.jsonl", "w") as f:
        for ev in lines:
            f.write(json.dumps(ev, sort_keys=True) + "\n")

    assert rs.main(["rebuild", "--slug", "demo"]) == 3

    rc = rs.main(
        [
            "transition",
            "--slug",
            "demo",
            "--to",
            "planning",
            "--event",
            "e2",
            "--event-id",
            "e2",
        ]
    )
    assert rc == 3


def test_chain_shipped_requires_sha():
    """A forged `shipped` event with sha None (or garbage) must be rejected by the
    validator itself. cmd_transition:434-438 enforces --sha matching SHA_RE only on
    the write path; validate_transition (hop legality) knows nothing about sha, so a
    hand-written log reaching read_events would otherwise validate clean."""
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
    events = rs.read_events("demo")

    no_sha = [dict(e) for e in events]
    no_sha[-1]["sha"] = None
    with pytest.raises(rs.StorageError, match="shipped requires sha"):
        rs.validate_chain(no_sha, "demo", rs.events_path("demo"))

    bad_sha = [dict(e) for e in events]
    bad_sha[-1]["sha"] = "zzzzzzz"  # not hex
    with pytest.raises(rs.StorageError, match="shipped requires sha"):
        rs.validate_chain(bad_sha, "demo", rs.events_path("demo"))


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


def test_stale_event_id_replay_raises_conflict_not_false_success():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    first = [
        "transition",
        "--slug",
        "demo",
        "--to",
        "investigating",
        "--event",
        "agent.started",
        "--event-id",
        "stale-id",
    ]
    assert rs.main(first) == 0
    # Run has advanced further since "stale-id" was recorded.
    assert (
        rs.main(
            [
                "transition",
                "--slug",
                "demo",
                "--to",
                "planning",
                "--event",
                "agent.step",
            ]
        )
        == 0
    )
    # Replaying the STALE event_id must NOT report a false idempotent success;
    # it must surface as a conflict since it no longer matches the current state.
    assert rs.main(first) == 2

    # Meanwhile, replaying the event_id of the actual LAST event still no-ops.
    last_line = json.loads(open("specs/demo/events.jsonl").readlines()[-1])
    replay_last = [
        "transition",
        "--slug",
        "demo",
        "--to",
        "planning",
        "--event",
        "agent.step",
        "--event-id",
        last_line["event_id"],
    ]
    line_count_before = sum(1 for _ in open("specs/demo/events.jsonl"))
    assert rs.main(replay_last) == 0
    assert sum(1 for _ in open("specs/demo/events.jsonl")) == line_count_before


def test_init_without_run_id_is_idempotent():
    assert rs.main(["init", "--slug", "demo"]) == 0
    assert rs.main(["init", "--slug", "demo"]) == 0


def test_transition_bad_meta_exits_2_not_traceback():
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    assert (
        rs.main(
            [
                "transition",
                "--slug",
                "demo",
                "--to",
                "investigating",
                "--event",
                "agent.started",
                "--meta",
                "badvalue",
            ]
        )
        == 2
    )


def test_list_plaintext_skips_malformed_run_json_without_crashing():
    rs.main(["init", "--slug", "alive", "--run-id", "r1"])
    os.makedirs("specs/broken", exist_ok=True)
    rs.atomic_write_json("specs/broken/RUN.json", {"not": "a real run"})
    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = rs.main(["list"])
    assert rc == 0
    assert "alive" in buf.getvalue()


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


def test_never_initialized_run_is_not_checkable():
    """Branch A of the resume recipe: nothing exists, so `--check` has nothing to
    validate and must not be read as corruption. Pins the contract that
    `subagent-driven-development` Step -1 relies on to skip the check for a legacy
    (pre-#129) or intake-skipped spec."""
    os.makedirs("specs/legacy", exist_ok=True)
    assert not os.path.exists("specs/legacy/events.jsonl")
    assert rs.main(["status", "--slug", "legacy"]) == 3
    assert rs.main(["rebuild", "--slug", "legacy", "--check"]) == 3


def test_missing_projection_over_valid_log_recovers_blocked_state():
    """Branch B: `status` reports the SAME `missing: RUN.json` as branch A, so the
    message is not a discriminator — the presence of events.jsonl is. The FSM state
    here is recoverable, so a resume that treats this as 'never initialized' would
    silently discard a real blocked run and its resume_event."""
    rs.main(["init", "--slug", "torn", "--run-id", "r1"])
    rs.main(["transition", "--slug", "torn", "--to", "investigating", "--event", "a"])
    rs.main(
        [
            "transition",
            "--slug",
            "torn",
            "--to",
            "blocked",
            "--event",
            "b",
            "--resume-event",
            "unblock",
        ]
    )
    os.remove("specs/torn/RUN.json")
    assert os.path.exists("specs/torn/events.jsonl")  # the discriminator
    assert rs.main(["status", "--slug", "torn"]) == 3
    assert rs.main(["rebuild", "--slug", "torn", "--check"]) == 3
    assert rs.main(["rebuild", "--slug", "torn"]) == 0
    recovered = rs.read_json("specs/torn/RUN.json")
    assert recovered["state"] == "blocked"
    assert recovered["resume_event"] == "unblock"


def test_blocked_to_implementing_clears_blocker_metadata():
    """Why `subagent-driven-development` Step -1 must STOP on blocked/escalated: the
    engine deliberately allows an interrupt state into any active state, and the new
    event carries no waiting_on/resume_event of its own — so resuming blindly erases
    the record of why the work was paused. If this ever becomes an invalid transition,
    this test fails and the skill's stop rule can be relaxed."""
    rs.main(["init", "--slug", "b", "--run-id", "r1"])
    for to_state in ("investigating", "planning"):
        rs.main(["transition", "--slug", "b", "--to", to_state, "--event", "e"])
    rs.main(
        [
            "transition",
            "--slug",
            "b",
            "--to",
            "blocked",
            "--event",
            "hit",
            "--resume-event",
            "dep-merged",
            "--waiting-on",
            "PR #999",
        ]
    )
    before = rs.read_json("specs/b/RUN.json")
    assert before["waiting_on"] == "PR #999"
    assert before["resume_event"] == "dep-merged"

    assert (
        rs.main(["transition", "--slug", "b", "--to", "implementing", "--event", "go"])
        == 0
    )
    after = rs.read_json("specs/b/RUN.json")
    assert after["state"] == "implementing"
    assert after["waiting_on"] is None
    assert after["resume_event"] is None


def test_projection_without_event_log_is_unrebuildable():
    """A RUN.json with no events.jsonl behind it is corruption, not a fresh start:
    `status` still exits 0 and reports a state (even a blocked one), while the
    projection can no longer be rebuilt or verified. Step -1 must stop here rather
    than classify it as never-initialized."""
    rs.main(["init", "--slug", "runonly", "--run-id", "r1"])
    rs.main(
        ["transition", "--slug", "runonly", "--to", "investigating", "--event", "a"]
    )
    rs.main(
        [
            "transition",
            "--slug",
            "runonly",
            "--to",
            "blocked",
            "--event",
            "b",
            "--resume-event",
            "unblock",
        ]
    )
    os.remove("specs/runonly/events.jsonl")
    assert os.path.exists("specs/runonly/RUN.json")
    assert rs.main(["status", "--slug", "runonly"]) == 0  # looks healthy
    assert rs.read_json("specs/runonly/RUN.json")["state"] == "blocked"
    assert rs.main(["rebuild", "--slug", "runonly", "--check"]) == 3


def test_terminal_run_rejects_resume_transition_at_cli():
    """Why Step -1 must STOP on a terminal run. `test_terminal_state_blocks_transition`
    pins this at the unit level; this one goes through the CLI, which is the layer the
    skill's prescribed `|| true` silences: the rejection is exit 2, so `|| true` turns it
    into exit 0 and a cancelled/superseded/shipped plan would be edited and shipped with
    the run frozen at its terminal state."""

    def _build(slug, terminal):
        rs.main(["init", "--slug", slug, "--run-id", f"r-{slug}"])
        rs.main(["transition", "--slug", slug, "--to", "investigating", "--event", "e"])
        if terminal == "shipped":
            for to_state in ("planning", "implementing", "verifying", "ready_to_merge"):
                rs.main(
                    ["transition", "--slug", slug, "--to", to_state, "--event", "e"]
                )
            rs.main(
                [
                    "transition",
                    "--slug",
                    slug,
                    "--to",
                    "shipped",
                    "--event",
                    "m",
                    "--sha",
                    "abc1234",
                ]
            )
        else:
            rs.main(["transition", "--slug", slug, "--to", terminal, "--event", "end"])

    for terminal in sorted(rs.TERMINAL_STATES):
        slug = f"t-{terminal}"
        os.makedirs(f"specs/{slug}", exist_ok=True)
        _build(slug, terminal)
        assert rs.read_json(f"specs/{slug}/RUN.json")["state"] == terminal
        # the exact call Step 1's checkpoint makes, minus the `|| true`
        assert (
            rs.main(
                ["transition", "--slug", slug, "--to", "implementing", "--event", "go"]
            )
            == 2
        )
        assert rs.read_json(f"specs/{slug}/RUN.json")["state"] == terminal


def legacy_step_minus_one_prose_table_covers_every_run_state():
    """The resume recipe must branch on EVERY state this engine can hold — four of the
    hazards found in review were simply states it did not mention. This fails when
    ALL_STATES gains a member the skill's table has not classified, which is the only
    durable guard: the table is prose, the state set is code."""
    skill = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "skills",
        "subagent-driven-development",
        "SKILL.md",
    )
    with open(skill, encoding="utf-8") as f:
        text = f.read()
    # Read the TABLE ROWS only, not the surrounding prose. Two earlier versions of this
    # slice were wrong in opposite directions: a sentence anchor that a rewording voided,
    # then a section-wide slice that went vacuous because the prose also names the states.
    start = text.index("| Run state | On resume | Why |")
    rows = []
    for line in text[start:].splitlines()[2:]:  # skip header + separator
        if not line.startswith("|"):
            break
        rows.append(line)
    table = "\n".join(rows)
    assert len(rows) >= 5, f"resume-state table parsed as {len(rows)} rows"
    uncovered = sorted(s for s in rs.ALL_STATES if f"`{s}`" not in table)
    assert not uncovered, f"resume recipe does not classify: {uncovered}"


def legacy_only_planning_and_interrupts_prose_reach_implementing_directly():
    """The exhaustiveness table is not enough on its own: a state can be *classified*
    and still have no legal one-hop path to the checkpoint's target. Only `planning`
    (forward edge) and the interrupt states (resume-into-any-active) may enter
    `implementing` directly, so every other 'proceed' verdict owes the reader a walk.
    If the engine adds an edge here, this fails and the table must be revisited."""
    direct = {s for s in rs.ALL_STATES if "implementing" in rs.valid_targets(s)}
    assert direct == {"planning", "blocked", "escalated"}

    # queued/investigating cannot shortcut, and the walk is what works
    rs.main(["init", "--slug", "q", "--run-id", "r1"])
    assert (
        rs.main(["transition", "--slug", "q", "--to", "implementing", "--event", "go"])
        == 2
    )
    assert rs.read_json("specs/q/RUN.json")["state"] == "queued"
    for hop in ("investigating", "planning", "implementing"):
        assert (
            rs.main(["transition", "--slug", "q", "--to", hop, "--event", "walk"]) == 0
        )
    assert rs.read_json("specs/q/RUN.json")["state"] == "implementing"

    # and the skill tells the reader to walk rather than shortcut
    skill = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "skills",
        "subagent-driven-development",
        "SKILL.md",
    )
    with open(skill, encoding="utf-8") as f:
        text = f.read()
    assert "walk the run state forward first" in text


def legacy_shipped_plan_prose_stop_exempts_the_repair_states():
    """The shipped-plan rule bars plan-task execution only. `fixing_ci` and
    `addressing_review` always meet a shipped plan — finishing marks the plan shipped
    before the PR exists, and those states only exist after it — so a blanket stop
    would block the very fixes such a resume was started for. Pins the exemption
    against a future edit that re-broadens the rule."""
    skill = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "skills",
        "subagent-driven-development",
        "SKILL.md",
    )
    with open(skill, encoding="utf-8") as f:
        text = f.read()
    start = text.index("A `shipped` plan bars plan-task execution")
    para = text[start : start + 1200]
    assert "not** a blanket stop" in para
    for repair_state in ("fixing_ci", "addressing_review"):
        assert f"`{repair_state}`" in para, f"{repair_state} not exempted"


def legacy_task_cursor_prose_directive_is_scoped_to_plan_execution_states():
    """The task-cursor sweep and the Step-0 fall-through apply only to states that
    actually resume plan execution. `fixing_ci` / `addressing_review` / `verifying`
    must be routed elsewhere: a failing check is the EXPECTED reason for a repair
    state, so sweeping tasks there turns a repair into shipped wave work. Pins the
    scoping against a future edit that re-broadens the directive."""
    skill = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "skills",
        "subagent-driven-development",
        "SKILL.md",
    )
    with open(skill, encoding="utf-8") as f:
        text = f.read()
    start = text.index("Two of the table's verdicts do not lead here at all")
    scope = text[start : text.index("Then fall through to Step 0", start)]
    for excluded in ("fixing_ci", "addressing_review", "verifying"):
        assert f"`{excluded}`" in scope, f"{excluded} not excluded from the task sweep"
    for included in ("planning", "implementing", "queued", "investigating"):
        assert f"`{included}`" in scope, (
            f"{included} not named as a plan-execution state"
        )


def test_interrupt_origin_is_only_in_the_event_log():
    """Interrupts are universal, so `blocked` does not say where the run came from —
    and the projection does not carry `from_state`, only the event log does. A resume
    that falls through to `implementing` therefore drags a run blocked out of
    `verifying` into wave execution, which is legal and thus unstopped."""
    rs.main(["init", "--slug", "v", "--run-id", "r1"])
    for to_state in ("investigating", "planning", "implementing", "verifying"):
        rs.main(["transition", "--slug", "v", "--to", to_state, "--event", "e"])
    rs.main(
        [
            "transition",
            "--slug",
            "v",
            "--to",
            "blocked",
            "--event",
            "ci.red",
            "--resume-event",
            "fix-landed",
            "--waiting-on",
            "flaky test",
        ]
    )

    projection = rs.read_json("specs/v/RUN.json")
    assert projection["state"] == "blocked"
    assert "from_state" not in projection  # status cannot answer "from where?"

    last = rs.read_events("v")[-1]
    assert last["from_state"] == "verifying"  # only the log knows

    # returning to the origin is legal — and so is the blind hop that skips it
    assert (
        rs.main(["transition", "--slug", "v", "--to", "verifying", "--event", "ok"])
        == 0
    )
    assert rs.read_json("specs/v/RUN.json")["state"] == "verifying"


def test_returning_to_a_waiting_state_needs_its_waiting_on():
    """Follow-on to SC-18: returning to `from_state` is not always a plain transition.
    A waiting target requires --waiting-on, and the interrupt event has overwritten
    waiting_on with its own blocker — the original lives in the event that ENTERED the
    wait. Without recovering it the return exits 2 and the run stays blocked."""
    rs.main(["init", "--slug", "w", "--run-id", "r1"])
    for to_state in ("investigating", "planning", "implementing", "verifying"):
        rs.main(["transition", "--slug", "w", "--to", to_state, "--event", "e"])
    rs.main(
        [
            "transition",
            "--slug",
            "w",
            "--to",
            "awaiting_ci",
            "--event",
            "pushed",
            "--waiting-on",
            "CI run 42",
        ]
    )
    rs.main(
        [
            "transition",
            "--slug",
            "w",
            "--to",
            "blocked",
            "--event",
            "infra.down",
            "--resume-event",
            "runner-back",
            "--waiting-on",
            "GH runners outage",
        ]
    )
    assert rs.read_json("specs/w/RUN.json")["waiting_on"] == "GH runners outage"

    events = rs.read_events("w")
    origin = events[-1]["from_state"]
    assert origin == "awaiting_ci"

    # the plain return fails — this is what the round-12 wording would have produced
    assert (
        rs.main(["transition", "--slug", "w", "--to", origin, "--event", "back"]) == 2
    )
    assert rs.read_json("specs/w/RUN.json")["state"] == "blocked"

    # the original waiting_on is in the event that entered the wait, not the last one
    recovered = next(
        e["waiting_on"] for e in reversed(events[:-1]) if e["to_state"] == origin
    )
    assert recovered == "CI run 42"
    assert (
        rs.main(
            [
                "transition",
                "--slug",
                "w",
                "--to",
                origin,
                "--event",
                "back",
                "--waiting-on",
                recovered,
            ]
        )
        == 0
    )
    projection = rs.read_json("specs/w/RUN.json")
    assert projection["state"] == "awaiting_ci"
    assert projection["waiting_on"] == "CI run 42"


def legacy_waiting_state_successors_are_documented_in_prose():
    """Follow-on to SC-19: when an interrupted wait completes, the recipe must name a
    successor. The table's verdict for the waiting states is `STOP and report`, which
    is about ARRIVING there — so the successor mapping is separate, and it must match
    the engine. Every legal forward target of every waiting state has to appear in the
    successor table, or the recipe sends the reader to guess."""
    skill = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "skills",
        "subagent-driven-development",
        "SKILL.md",
    )
    with open(skill, encoding="utf-8") as f:
        text = f.read()
    start = text.index("| Origin wait | Outcome | Transition to |")
    rows = []
    for line in text[start:].splitlines()[2:]:
        stripped = line.strip()  # this table is indented inside a list item
        if not stripped.startswith("|"):
            break
        rows.append(stripped)
    table = "\n".join(rows)
    assert len(rows) >= 5, f"successor table parsed as {len(rows)} rows"

    # Validate each row as an (origin, target) PAIR against that origin's forward edges.
    # Whole-table name membership is not enough: a target filed under the wrong origin
    # would pass while the recipe routes a resume to the wrong lifecycle successor.
    CANCEL_ROUTE = {"cancelled"}  # deliberate abandon path, not a forward edge
    documented = {}
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        origins = re.findall(r"`([a-z_]+)`", cells[0])
        targets = re.findall(r"`([a-z_]+)`", cells[-1])
        assert len(origins) == 1, f"row names {len(origins)} origins: {row}"
        assert len(targets) == 1, f"row names {len(targets)} targets: {row}"
        origin, target = origins[0], targets[0]
        assert origin in rs.WAITING_STATES, f"{origin} is not a waiting state: {row}"
        legal = rs.FORWARD_TRANSITIONS[origin] | CANCEL_ROUTE
        assert target in legal, (
            f"{origin} -> {target} is not a legal successor of {origin}"
        )
        documented.setdefault(origin, set()).add(target)

    for wait in sorted(rs.WAITING_STATES):
        assert wait in documented, f"{wait} has no successor row"
        missing = rs.FORWARD_TRANSITIONS[wait] - documented[wait]
        assert not missing, f"{wait} -> {sorted(missing)} not documented"

    # Membership is not enough: EXECUTE every documented successor from `blocked`,
    # supplying whatever the engine requires for that target's class. This is what
    # catches a documented route that cannot actually be taken — the defect class that
    # hit the return path first, then this table one step later.
    targets = set()
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        targets.update(re.findall(r"`([a-z_]+)`", cells[-1]))
    assert {"awaiting_review", "fixing_ci", "planning"} <= targets, targets

    for i, target in enumerate(sorted(targets)):
        slug = f"succ{i}"
        os.makedirs(f"specs/{slug}", exist_ok=True)
        rs.main(["init", "--slug", slug, "--run-id", f"r{i}"])
        rs.main(["transition", "--slug", slug, "--to", "investigating", "--event", "e"])
        rs.main(
            [
                "transition",
                "--slug",
                slug,
                "--to",
                "blocked",
                "--event",
                "hit",
                "--resume-event",
                "cleared",
                "--waiting-on",
                "the blocker",
            ]
        )
        argv = ["transition", "--slug", slug, "--to", target, "--event", "resume"]
        if target in rs.WAITING_STATES:
            # a waiting target without its own waiting_on is rejected — prove it,
            # so this assertion cannot pass vacuously
            assert rs.main(list(argv)) == 2, f"{target} accepted without waiting_on"
            argv += ["--waiting-on", "the successor wait"]
        if target in rs.INTERRUPT_STATES:
            argv += ["--resume-event", "later"]
        if target == "shipped":
            argv += ["--sha", "abc1234"]
        assert rs.main(argv) == 0, (
            f"documented successor blocked -> {target} is not takeable"
        )
        assert rs.read_json(f"specs/{slug}/RUN.json")["state"] == target


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


def _write_forged_log(slug):
    """Writes the issue's exact repro to specs/<slug>/events.jsonl: two events, both
    `seq: 1` - the second forged with from_state "verifying" straight to the terminal
    "shipped", under a different run_id. Before validate_chain was wired in, project()
    blindly folded this into a RUN.json reporting `shipped`.

    Returns the (genesis, forged) dicts it wrote, so a caller that also needs the raw
    events (e.g. to compute the pre-fix blind projection) gets the identical objects
    rather than a second, independently-constructed pair."""
    genesis = {
        "event_id": "e1",
        "seq": 1,
        "ts": "2026-01-01T00:00:00Z",
        "slug": slug,
        "run_id": "r1",
        "from_state": None,
        "to_state": "queued",
        "event": "run.init",
        "waiting_on": None,
        "resume_event": None,
        "sha": None,
        "metadata": {},
    }
    forged = {
        "event_id": "e2",
        "seq": 1,
        "ts": "2026-01-01T00:00:01Z",
        "slug": slug,
        "run_id": "r2",
        "from_state": "verifying",
        "to_state": "shipped",
        "event": "ci.merged",
        "waiting_on": None,
        "resume_event": None,
        "sha": "abc1234",
        "metadata": {},
    }
    os.makedirs(f"specs/{slug}", exist_ok=True)
    with open(f"specs/{slug}/events.jsonl", "w") as f:
        f.write(json.dumps(genesis, sort_keys=True) + "\n")
        f.write(json.dumps(forged, sort_keys=True) + "\n")
    return genesis, forged


def test_issue_174_forged_log_rejected_by_rebuild():
    # Exit 3 has four producers on this path (missing:, corrupt event log, empty
    # event log, invalid event chain) - pin the message too, or a drifted
    # _write_forged_log (wrong slug, wrong dir, file not written) could go green on
    # an unrelated "missing:" instead of the chain rejection this test exists for.
    _write_forged_log("forged1")
    import io
    import contextlib

    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = rs.main(["rebuild", "--slug", "forged1"])
    assert rc == 3
    assert "invalid event chain" in err.getvalue()


def test_issue_174_forged_log_rejected_by_rebuild_check():
    # Seed RUN.json with exactly what the pre-fix blind project() computes over this
    # log - --check needs something to compare against, and the seeded genesis/forged
    # objects (returned by _write_forged_log, not reconstructed) are the ones that
    # actually landed on disk.
    genesis, forged = _write_forged_log("forged2")
    rs.atomic_write_json("specs/forged2/RUN.json", rs.project([genesis, forged]))

    import io
    import contextlib

    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = rs.main(["rebuild", "--slug", "forged2", "--check"])
    assert rc == 3
    assert "invalid event chain" in err.getvalue()


def test_allow_invalid_chain_rebuilds_with_warning():
    _write_forged_log("forged3")
    import io
    import contextlib

    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = rs.main(["rebuild", "--slug", "forged3", "--allow-invalid-chain"])
    assert rc == 0
    assert "chain validation skipped (--allow-invalid-chain)" in err.getvalue()
    assert os.path.exists("specs/forged3/RUN.json")
    assert rs.read_json("specs/forged3/RUN.json")["state"] == "shipped"


def test_allow_invalid_chain_with_check_returns_drift_verdict():
    # rebuild --allow-invalid-chain writes RUN.json first: --check needs an existing
    # RUN.json to compare the rebuilt projection against.
    _write_forged_log("forged4")
    assert rs.main(["rebuild", "--slug", "forged4", "--allow-invalid-chain"]) == 0

    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = rs.main(
            ["rebuild", "--slug", "forged4", "--check", "--allow-invalid-chain"]
        )
    assert rc == 0
    # Must be a distinct verdict from the fully-validated match message, byte-
    # distinguishable on stdout alone (a `2>/dev/null` consumer never sees the
    # "chain validation skipped" warning, which is stderr-only).
    assert "matches an UNVALIDATED fold" in buf.getvalue()
    assert "matches events.jsonl" not in buf.getvalue()

    rs.atomic_write_json("specs/forged4/RUN.json", {"tampered": True})
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = rs.main(
            ["rebuild", "--slug", "forged4", "--check", "--allow-invalid-chain"]
        )
    assert rc == 3
    assert "DRIFT:" in err.getvalue()


def test_transition_on_invalid_chain_exits_3_and_appends_nothing():
    # Before validate_chain was wired in, this exits 2: project() folds the forged
    # log to "shipped" (a terminal state) and validate_transition rejects the
    # transition as post-terminal. The contract value is 3, from the exit-code
    # docstring - do not copy the pre-wiring 2.
    _write_forged_log("forged5")
    before = open("specs/forged5/events.jsonl", "rb").read()
    rc = rs.main(
        ["transition", "--slug", "forged5", "--to", "investigating", "--event", "e"]
    )
    assert rc == 3
    after = open("specs/forged5/events.jsonl", "rb").read()
    assert after == before


def test_status_detects_invalid_chain_and_exits_3():
    """Issue #174's third repro line: 'status' used to read RUN.json directly and
    never touch the event log, so a forged/corrupted events.jsonl was invisible to
    it and it happily reported a state (exit 0). Reuses the exact forged-log
    fixture the rebuild tests above already trust."""
    genesis, forged = _write_forged_log("statuschain")
    rs.atomic_write_json("specs/statuschain/RUN.json", rs.project([genesis, forged]))
    import io
    import contextlib

    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = rs.main(["status", "--slug", "statuschain"])
    assert rc == 3
    assert "invalid event chain" in err.getvalue()


def test_status_json_mode_also_detects_invalid_chain():
    """--json must get the identical treatment, not a separate code path that
    forgot the check — both branches go through the same guard before printing."""
    genesis, forged = _write_forged_log("statuschainjson")
    rs.atomic_write_json(
        "specs/statuschainjson/RUN.json", rs.project([genesis, forged])
    )
    import io
    import contextlib

    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = rs.main(["status", "--slug", "statuschainjson", "--json"])
    assert rc == 3
    assert "invalid event chain" in err.getvalue()


def test_status_detects_run_json_drift_distinctly_from_invalid_chain():
    """A chain-VALID log whose RUN.json was hand-edited is a SEPARATE failure mode
    from a corrupted chain, and must be named distinctly — not by reusing the
    "invalid event chain" wording that belongs to chain corruption, or a reader
    debugging drift would go looking for the wrong thing (a bad event, not a bad
    RUN.json)."""
    rs.main(["init", "--slug", "drifted", "--run-id", "r1"])
    rs.main(
        ["transition", "--slug", "drifted", "--to", "investigating", "--event", "e"]
    )
    tampered = rs.read_json("specs/drifted/RUN.json")
    tampered["state"] = "planning"  # log actually says "investigating"
    rs.atomic_write_json("specs/drifted/RUN.json", tampered)

    import io
    import contextlib

    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = rs.main(["status", "--slug", "drifted"])
    assert rc == 3
    assert "does not match events.jsonl" in err.getvalue()
    assert "invalid event chain" not in err.getvalue()


def test_status_agreement_still_prints_projection_and_exits_0():
    """The non-corruption path must be unchanged: a clean chain that agrees with
    RUN.json still prints the projection and exits 0, in both plaintext and --json,
    exactly as before this fix."""
    rs.main(["init", "--slug", "clean", "--run-id", "r1"])
    rs.main(["transition", "--slug", "clean", "--to", "investigating", "--event", "e"])

    import io
    import contextlib

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = rs.main(["status", "--slug", "clean", "--json"])
    assert rc == 0
    data = json.loads(buf.getvalue())
    assert data["state"] == "investigating"

    buf2 = io.StringIO()
    with contextlib.redirect_stdout(buf2):
        rc2 = rs.main(["status", "--slug", "clean"])
    assert rc2 == 0
    assert "state: investigating" in buf2.getvalue()


def test_transition_to_cancelled_closes_a_bricked_run():
    """GitHub issue #174 Fix 2: once the chain is invalid, `transition` used to
    exit 3 forever with no way to close the run out. A transition to a TERMINAL,
    non-shipped target (`cancelled`/`superseded`) must now be allowed to proceed
    over the invalid chain, appending a closing event and writing a RUN.json whose
    state is the closed state — so `list --active` stops advertising it."""
    _write_forged_log("brick1")
    import io
    import contextlib

    err = io.StringIO()
    out = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
        rc = rs.main(
            [
                "transition",
                "--slug",
                "brick1",
                "--to",
                "cancelled",
                "--event",
                "operator.abandon",
            ]
        )
    assert rc == 0
    assert "INVALID event chain" in err.getvalue()  # loud, on stderr
    assert "closed over invalid chain" in out.getvalue()

    run_json = rs.read_json("specs/brick1/RUN.json")
    assert run_json["state"] == "cancelled"

    # the closing event landed on disk, honestly labeled
    events = rs.read_events("brick1", validate=False)
    closing = events[-1]
    assert closing["to_state"] == "cancelled"
    assert closing["from_state"] == "shipped"  # the forged log's last recorded to_state
    assert closing["seq"] == 2  # max int seq in the forged log (1) + 1, not 1 again


def test_transition_to_shipped_over_invalid_chain_still_hard_blocked():
    """`shipped` is terminal too, but it is NOT in CLOSEABLE_OVER_INVALID_CHAIN —
    only cancelled/superseded may bypass. This is the "nothing else" half of Fix 2:
    without it, any terminal target would silently acquire the bypass."""
    _write_forged_log("brick2")
    rc = rs.main(
        [
            "transition",
            "--slug",
            "brick2",
            "--to",
            "shipped",
            "--event",
            "e",
            "--sha",
            "abc1234",
        ]
    )
    assert rc == 3
    before = open("specs/brick2/events.jsonl", "rb").read()
    assert rc == 3
    with open("specs/brick2/events.jsonl", "rb") as f:
        assert f.read() == before  # nothing appended


def test_transition_to_non_terminal_over_invalid_chain_still_hard_blocked():
    """The bypass is scoped to terminal closure only — a non-terminal target
    (e.g. resuming into `implementing`) over an invalid chain must still be refused
    exactly as before Fix 2, with nothing appended to the log."""
    _write_forged_log("brick3")
    before = open("specs/brick3/events.jsonl", "rb").read()
    rc = rs.main(
        ["transition", "--slug", "brick3", "--to", "implementing", "--event", "e"]
    )
    assert rc == 3
    with open("specs/brick3/events.jsonl", "rb") as f:
        assert f.read() == before


def test_closing_seq_does_not_reuse_a_duplicated_seq():
    """Direct unit test of the seq-repair helper: the forged log has TWO events both
    claiming seq=1. A naive `events[-1]["seq"] + 1` would compute 2 only by luck of
    which event is last; pin the actual property, that the closing seq is beyond
    the max int seq anywhere in the log, not just the last line."""
    genesis, forged = _write_forged_log("seqcheck")
    events = rs.read_events("seqcheck", validate=False)
    assert [e["seq"] for e in events] == [1, 1]  # both claim seq 1
    assert rs._closing_seq_over_invalid_chain(events) == 2


def test_closing_seq_falls_back_to_event_count_with_no_int_seq():
    """If every seq in the log is non-int (total corruption), there is no int max
    to take — the fallback must still produce a seq, not raise."""
    events = [
        {"event_id": "e1", "seq": "not-an-int", "to_state": "queued"},
        {"event_id": "e2", "seq": None, "to_state": "investigating"},
    ]
    assert rs._closing_seq_over_invalid_chain(events) == 3  # len(events) + 1


def test_real_repo_event_logs_all_validate():
    """SC-3: every real events.jsonl checked into this repo must still validate - no
    false positives from the new invariants. isolated_cwd chdirs into a tmp_path, so
    the repo's events.jsonl files are resolved from __file__ and read/validated
    directly (rs.read_events's relative specs/<slug> path is unusable here).

    `runtime/` ships to consumer repos (scripts/install-harness.sh PAYLOAD,
    scripts/deploy-harness.sh SYNCED_DIRS_RE) where specs/*/events.jsonl may
    legitimately be empty - that is ground truth this harness does not own, not a
    failure. It also must not contradict --allow-invalid-chain: the moment anyone
    legitimately uses that flag on a real spec, a hard failure here would redden the
    whole suite on every unrelated branch. Skip rather than fail when there is
    nothing to check; the per-log assertion below stays a hard failure."""
    import glob

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs = glob.glob(os.path.join(repo_root, "specs", "*", "events.jsonl"))
    if not logs:
        pytest.skip("no real events.jsonl found under specs/ to validate")
    for path in logs:
        slug = os.path.basename(os.path.dirname(path))
        events = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        rs.validate_chain(events, slug, path)  # raises on any violation


def test_rebuild_on_empty_event_log_exits_3_with_empty_log_message():
    """Pins two things at once: the pre-existing empty-log contract at
    run_state.py:129-130 (no test anywhere exercised this branch before) and the
    ordering constraint that validate_chain runs AFTER the `if not events` check. If
    validate_chain moved above it, `first = events[0]` would raise an uncaught
    IndexError on an empty list instead of this clean StorageError - a traceback and
    exit 1, not this test's exit 3. The message assertion (not just the exit code)
    is what pins the ordering: an IndexError never reaches main()'s `except
    RunStateError` handler, so it can't produce this message under any exit code."""
    os.makedirs("specs/empty", exist_ok=True)
    open("specs/empty/events.jsonl", "w").close()  # zero events, zero bytes

    import io
    import contextlib

    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = rs.main(["rebuild", "--slug", "empty"])
    assert rc == 3
    assert "empty event log" in err.getvalue()


# --- Round-16 review fixes (5 confirmed defects in cmd_status's chain check and the
# cmd_transition close-over-invalid-chain bypass, both added in 751118f) ---------


def test_status_holds_a_lock_across_its_two_reads():
    """Fix 1: cmd_status used to read RUN.json, then read+fold events.jsonl,
    OUTSIDE any lock — a transition landing between the two reads could make the
    fold newer than the projection it's compared against, reporting phantom
    'projection drift' on a store that was never actually corrupt.

    A real two-process race is not reliably reproducible in a unit test (timing-
    dependent), so this pins the MECHANISM instead: cmd_status must hold the lock
    file (shared, so concurrent status calls don't serialize against each other —
    only against a writer's exclusive lock) for the duration of both reads. We spy
    on read_json (the first read cmd_status performs) and, from inside the spy,
    attempt a NON-BLOCKING EXCLUSIVE lock on the same lock file cmd_status should
    already be holding shared. If cmd_status is not actually holding a lock at
    that point, the exclusive attempt SUCCEEDS (the race window is still open); if
    the fix holds the shared lock first, the exclusive attempt must fail with
    BlockingIOError. flock locks apply to open file descriptions, not processes or
    threads, so a second open() from within the same process still contends
    correctly against a lock held via a different open() on the same path.

    This does not cover the race directly — only the locking mechanism the fix
    relies on to close it."""
    import fcntl

    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    rs.main(["transition", "--slug", "demo", "--to", "investigating", "--event", "e"])

    attempts = []
    original_read_json = rs.read_json

    def spy_read_json(path):
        lock_fh = open(rs.lock_path("demo"), "a+")
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            attempts.append("acquired")  # BAD: no lock was held by cmd_status
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        except BlockingIOError:
            attempts.append("blocked")  # GOOD: cmd_status already holds it
        finally:
            lock_fh.close()
        return original_read_json(path)

    import pytest as _pytest  # local import: only needed for monkeypatch below

    mp = _pytest.MonkeyPatch()
    try:
        mp.setattr(rs, "read_json", spy_read_json)
        assert rs.main(["status", "--slug", "demo"]) == 0
    finally:
        mp.undo()
    assert attempts == ["blocked"]


def test_status_readonly_lock_does_not_create_storage_for_a_typo_slug():
    """Wrinkle called out in the review: locked_run.__enter__ unconditionally does
    os.makedirs(spec_dir) and open(lock_path, "a+") — naively reusing it for a
    read-only command would make `status` fabricate a directory and a .lock file
    for ANY slug argument, including a typo. Pins that a status call on a slug
    whose spec directory does not exist creates nothing at all — identical to the
    pre-fix behavior, which never touched the filesystem beyond the failed read."""
    assert not os.path.exists("specs/typo-slug")
    assert rs.main(["status", "--slug", "typo-slug"]) == 3
    assert not os.path.exists("specs/typo-slug")


def test_status_readonly_lock_still_detects_real_drift():
    """The lock in Fix 1 must not swallow the drift detection it's guarding —
    holding the lock during the read is additive, not a replacement for the
    existing compare-and-raise logic."""
    rs.main(["init", "--slug", "drifted2", "--run-id", "r1"])
    rs.main(
        ["transition", "--slug", "drifted2", "--to", "investigating", "--event", "e"]
    )
    tampered = rs.read_json("specs/drifted2/RUN.json")
    tampered["state"] = "planning"  # log actually says "investigating"
    rs.atomic_write_json("specs/drifted2/RUN.json", tampered)
    assert rs.main(["status", "--slug", "drifted2"]) == 3


def test_close_over_invalid_chain_is_idempotent_on_event_id_replay():
    """Fix 2: the close path skipped the --event-id historical-replay scan the
    normal path performs. Closing twice with the SAME --event-id used to append
    TWO events sharing that event_id — a violation of validate_chain's own
    uniqueness invariant (6), authored by the repair path itself into a log it
    exists to be honest about. A repeat with the same id must be an idempotent
    no-op returning 0, exactly as the normal path behaves for a replayed id."""
    _write_forged_log("closeidem")
    first = rs.main(
        [
            "transition",
            "--slug",
            "closeidem",
            "--to",
            "cancelled",
            "--event",
            "operator.abandon",
            "--event-id",
            "close-1",
        ]
    )
    assert first == 0
    line_count_after_first = sum(1 for _ in open("specs/closeidem/events.jsonl"))

    second = rs.main(
        [
            "transition",
            "--slug",
            "closeidem",
            "--to",
            "cancelled",
            "--event",
            "operator.abandon",
            "--event-id",
            "close-1",
        ]
    )
    assert second == 0
    assert (
        sum(1 for _ in open("specs/closeidem/events.jsonl")) == line_count_after_first
    )  # nothing new appended

    events = rs.read_events("closeidem", validate=False)
    event_ids = [e["event_id"] for e in events]
    assert len(event_ids) == len(set(event_ids)), f"duplicate event_id in {event_ids}"


def test_close_over_invalid_chain_cannot_hop_out_of_terminal_state():
    """Fix 3: the bypass guard only checked `args.to`, never the run's current
    state — so a closed run stayed closeable forever. Reproduced: --to cancelled
    then --to superseded both used to exit 0, appending a `cancelled ->
    superseded` hop that validate_transition forbids out of a terminal state.
    Once closed, ANY further close attempt (even a different --to) must be an
    idempotent no-op, not a fresh forbidden hop."""
    _write_forged_log("brick-hop")
    first = rs.main(
        [
            "transition",
            "--slug",
            "brick-hop",
            "--to",
            "cancelled",
            "--event",
            "operator.abandon",
        ]
    )
    assert first == 0
    line_count_after_first = sum(1 for _ in open("specs/brick-hop/events.jsonl"))

    second = rs.main(
        [
            "transition",
            "--slug",
            "brick-hop",
            "--to",
            "superseded",
            "--event",
            "operator.supersede",
        ]
    )
    assert second == 0  # idempotent no-op, not a fresh hop
    assert (
        sum(1 for _ in open("specs/brick-hop/events.jsonl")) == line_count_after_first
    )  # nothing appended

    events = rs.read_events("brick-hop", validate=False)
    assert events[-1]["to_state"] == "cancelled"  # still the FIRST close, untouched
    run_json = rs.read_json("specs/brick-hop/RUN.json")
    assert run_json["state"] == "cancelled"


def test_close_over_invalid_chain_repeated_same_target_no_self_loop():
    """Companion to the hop case: repeating the SAME --to target (cancelled twice,
    no matching --event-id the second time) must not append a `cancelled ->
    cancelled` self-loop either — the already-closed check is unconditional on
    args, not just on --event-id matching."""
    _write_forged_log("brick-selfloop")
    assert (
        rs.main(
            [
                "transition",
                "--slug",
                "brick-selfloop",
                "--to",
                "cancelled",
                "--event",
                "operator.abandon",
            ]
        )
        == 0
    )
    line_count_after_first = sum(1 for _ in open("specs/brick-selfloop/events.jsonl"))

    assert (
        rs.main(
            [
                "transition",
                "--slug",
                "brick-selfloop",
                "--to",
                "cancelled",
                "--event",
                "operator.abandon.retry",
            ]
        )
        == 0
    )
    assert (
        sum(1 for _ in open("specs/brick-selfloop/events.jsonl"))
        == line_count_after_first
    )
    events = rs.read_events("brick-selfloop", validate=False)
    assert events[-1]["event"] == "operator.abandon"  # the retry appended nothing


def test_close_over_invalid_chain_uses_requested_slug_not_chain_slug():
    """Fix 5: project() (used by the close path) takes slug from events[0], which
    invariant 3 is exactly what an invalid chain can have broken — a chain slug
    that does not match the directory it lives in (e.g. the renamed-directory
    case). The projection the close path writes must carry the REQUESTED slug
    (the directory it's actually writing into), not whatever the corrupt chain's
    first event claims."""
    genesis = {
        "event_id": "e1",
        "seq": 1,
        "ts": "2026-01-01T00:00:00Z",
        "slug": "old-slug-before-rename",  # does not match the directory below
        "run_id": "r1",
        "from_state": None,
        "to_state": "queued",
        "event": "run.init",
        "waiting_on": None,
        "resume_event": None,
        "sha": None,
        "metadata": {},
    }
    os.makedirs("specs/new-slug-after-rename", exist_ok=True)
    with open("specs/new-slug-after-rename/events.jsonl", "w") as f:
        f.write(json.dumps(genesis, sort_keys=True) + "\n")

    rc = rs.main(
        [
            "transition",
            "--slug",
            "new-slug-after-rename",
            "--to",
            "cancelled",
            "--event",
            "operator.abandon",
        ]
    )
    assert rc == 0
    run_json = rs.read_json("specs/new-slug-after-rename/RUN.json")
    assert run_json["slug"] == "new-slug-after-rename"  # the REQUESTED slug
    assert run_json["slug"] != "old-slug-before-rename"


def test_close_over_invalid_chain_refuses_when_run_id_is_not_a_string():
    """Fix 5, second half: run_id has no equivalent external source of truth (unlike
    slug, which is always the caller's own argument) — if events[0]'s run_id is not
    a string, the close path cannot honestly manufacture one. It must refuse to
    close rather than write a RUN.json whose run_id is a raw dict/int/None (the
    observed symptom: `list` printing `{'x': 1}: cancelled`), and it must leave the
    log byte-identical — the refusal writes nothing."""
    genesis = {
        "event_id": "e1",
        "seq": 1,
        "ts": "2026-01-01T00:00:00Z",
        "slug": "badrunid",
        "run_id": {"x": 1},  # not a string
        "from_state": None,
        "to_state": "queued",
        "event": "run.init",
        "waiting_on": None,
        "resume_event": None,
        "sha": None,
        "metadata": {},
    }
    forged = dict(genesis)
    forged.update(
        {"event_id": "e2", "seq": 1, "to_state": "shipped", "from_state": "verifying"}
    )  # duplicate seq -> invalid chain, same shape as _write_forged_log
    os.makedirs("specs/badrunid", exist_ok=True)
    with open("specs/badrunid/events.jsonl", "w") as f:
        f.write(json.dumps(genesis, sort_keys=True) + "\n")
        f.write(json.dumps(forged, sort_keys=True) + "\n")
    before = open("specs/badrunid/events.jsonl", "rb").read()

    rc = rs.main(
        [
            "transition",
            "--slug",
            "badrunid",
            "--to",
            "cancelled",
            "--event",
            "operator.abandon",
        ]
    )
    assert rc == 3
    with open("specs/badrunid/events.jsonl", "rb") as f:
        assert f.read() == before  # nothing appended
    assert not os.path.exists("specs/badrunid/RUN.json")  # nothing written


def test_read_events_non_utf8_byte_raises_storage_error_not_traceback():
    """Fix 4: read_events only guarded FileNotFoundError / JSONDecodeError. A
    non-UTF-8 byte anywhere in the log used to raise an uncaught
    UnicodeDecodeError — exit 1 with a traceback, outside the documented 0/2/3
    contract, on a corrupted-log input this feature's whole scenario is about."""
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    with open("specs/demo/events.jsonl", "ab") as f:
        f.write(b"\xff\xfe not valid utf-8\n")
    with pytest.raises(rs.StorageError, match="cannot read"):
        rs.read_events("demo")


def test_read_events_directory_raises_storage_error_not_traceback():
    """Same chokepoint, a different OSError subclass: events.jsonl being a
    directory (os.path.exists is True for directories too, so the existing
    FileNotFoundError guard does not catch this) used to raise an uncaught
    IsADirectoryError."""
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    os.remove("specs/demo/events.jsonl")
    os.makedirs("specs/demo/events.jsonl")
    with pytest.raises(rs.StorageError, match="cannot read"):
        rs.read_events("demo")


@pytest.mark.skipif(
    os.name != "posix" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="permission bits are meaningless as root or on a non-POSIX filesystem",
)
def test_read_events_permission_denied_raises_storage_error_not_traceback():
    """Third OSError subclass in the same repro set: chmod 000 used to raise an
    uncaught PermissionError."""
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    os.chmod("specs/demo/events.jsonl", 0o000)
    try:
        with pytest.raises(rs.StorageError, match="cannot read"):
            rs.read_events("demo")
    finally:
        os.chmod("specs/demo/events.jsonl", 0o644)  # let tmp_path teardown clean up


def test_read_json_directory_raises_storage_error_not_traceback():
    """Same fix, the other chokepoint: read_json only guarded FileNotFoundError /
    JSONDecodeError. RUN.json being a directory used to raise an uncaught
    IsADirectoryError instead of the documented StorageError."""
    os.makedirs("specs/demo/RUN.json", exist_ok=True)
    with pytest.raises(rs.StorageError, match="cannot read"):
        rs.read_json("specs/demo/RUN.json")


def test_status_on_non_utf8_event_log_exits_3_not_traceback():
    """End-to-end through the CLI: cmd_status now reads events.jsonl too (the
    prior commit's Fix 1), so this corruption class is directly reachable through
    `status`, not just through read_events in isolation."""
    rs.main(["init", "--slug", "demo", "--run-id", "r1"])
    with open("specs/demo/events.jsonl", "ab") as f:
        f.write(b"\xff\xfe garbage\n")
    assert rs.main(["status", "--slug", "demo"]) == 3


# --- gh-175 Task 1.1: one locked durable-state snapshot (design section 5.1) -----
# snapshot_run_state is the single locked, read-only primitive that classifies a
# slug's storage topology into exactly six statuses and returns validated data.
# cmd_status is refactored to consume it (its exit codes/messages/output are pinned
# unchanged by the pre-existing status tests above); resume will consume the same
# primitive under a stricter policy in a later task.


def test_snapshot_untracked_when_neither_artifact_exists():
    """Spec dir exists but holds neither RUN.json nor events.jsonl — nothing to
    classify, so the neutral verdict is `untracked` with no events/projection."""
    os.makedirs("specs/blank", exist_ok=True)
    snap = rs.snapshot_run_state("blank")
    assert snap.status == "untracked"
    assert snap.events is None
    assert snap.projection is None
    assert snap.error is None


def test_snapshot_projection_only_when_run_json_without_log():
    """RUN.json present, canonical log absent: `projection-only`. The projection is
    returned verbatim (status still trusts it for backward-compat); resume will map
    this to a stop because a projection with no log behind it cannot be validated."""
    rs.main(["init", "--slug", "proj", "--run-id", "r1"])
    os.remove("specs/proj/events.jsonl")
    snap = rs.snapshot_run_state("proj")
    assert snap.status == "projection-only"
    assert snap.projection == rs.read_json("specs/proj/RUN.json")
    assert snap.events is None


def test_snapshot_events_only_when_valid_log_without_projection():
    """A valid log with its RUN.json removed folds cleanly but has no projection on
    disk: `events-only`. The returned projection is the fold of the log (what a
    rebuild would write), and the events are the validated list."""
    rs.main(["init", "--slug", "evonly", "--run-id", "r1"])
    rs.main(["transition", "--slug", "evonly", "--to", "investigating", "--event", "e"])
    os.remove("specs/evonly/RUN.json")
    snap = rs.snapshot_run_state("evonly")
    assert snap.status == "events-only"
    assert snap.projection == rs.project(rs.read_events("evonly"))
    assert snap.projection["state"] == "investigating"
    assert [e["seq"] for e in snap.events] == [1, 2]


def test_snapshot_drift_when_projection_disagrees_with_fold():
    """Both artifacts exist, the chain is legal, but RUN.json was hand-edited to
    disagree with the fold: `drift`. The returned projection is the *correct* fold,
    not the tampered RUN.json — so a consumer can rebuild from it."""
    rs.main(["init", "--slug", "drift1", "--run-id", "r1"])
    rs.main(["transition", "--slug", "drift1", "--to", "investigating", "--event", "e"])
    tampered = rs.read_json("specs/drift1/RUN.json")
    tampered["state"] = "planning"  # log actually says "investigating"
    rs.atomic_write_json("specs/drift1/RUN.json", tampered)
    snap = rs.snapshot_run_state("drift1")
    assert snap.status == "drift"
    assert snap.projection["state"] == "investigating"  # the validated fold
    assert snap.projection != tampered


def test_snapshot_invalid_on_forged_event_chain():
    """#174 chain validation fires inside the snapshot: an illegal chain (the issue's
    forged two-seq-1 log) is classified `invalid`, carrying the StorageError message,
    and returns no events/projection — even when a matching RUN.json also exists, so
    `invalid` deterministically wins over `drift`/`consistent`."""
    genesis, forged = _write_forged_log("snapforged")
    rs.atomic_write_json("specs/snapforged/RUN.json", rs.project([genesis, forged]))
    snap = rs.snapshot_run_state("snapforged")
    assert snap.status == "invalid"
    assert "invalid event chain" in snap.error
    assert snap.events is None
    assert snap.projection is None


def test_snapshot_consistent_on_validated_matching_pair():
    """The healthy path: a legal log whose fold equals RUN.json is `consistent`, and
    both the validated events and the matching projection are returned."""
    rs.main(["init", "--slug", "ok", "--run-id", "r1"])
    rs.main(["transition", "--slug", "ok", "--to", "investigating", "--event", "e"])
    snap = rs.snapshot_run_state("ok")
    assert snap.status == "consistent"
    assert snap.projection == rs.read_json("specs/ok/RUN.json")
    assert snap.projection["state"] == "investigating"
    assert [e["seq"] for e in snap.events] == [1, 2]


def test_snapshot_creates_no_storage_for_a_typo_slug():
    """Read-only by construction: a snapshot on a slug whose spec directory does not
    exist (a typo) classifies `untracked` and creates NOTHING — no directory, no lock
    file. locked_run_readonly only acquires when spec_dir already exists."""
    assert not os.path.exists("specs/typo-snap")
    snap = rs.snapshot_run_state("typo-snap")
    assert snap.status == "untracked"
    assert not os.path.exists("specs/typo-snap")


def test_snapshot_holds_shared_lock_across_both_reads():
    """Torn-read mechanism (mirrors test_status_holds_a_lock_across_its_two_reads):
    snapshot_run_state must hold the shared lock across BOTH the events read and the
    RUN.json read, so a writer's exclusive lock cannot interleave and make the fold
    newer than the projection it is compared against (a false `drift`). Spy on
    read_json (the second read the snapshot performs on the consistent path) and,
    from inside the spy, attempt a NON-BLOCKING EXCLUSIVE lock on the same lock file.
    If the snapshot is holding the shared lock, that attempt must fail with
    BlockingIOError. flock applies to open file descriptions, so a second open() from
    the same process still contends against a lock held via a different open()."""
    import fcntl

    rs.main(["init", "--slug", "spy", "--run-id", "r1"])
    rs.main(["transition", "--slug", "spy", "--to", "investigating", "--event", "e"])

    attempts = []
    original_read_json = rs.read_json

    def spy_read_json(path):
        lock_fh = open(rs.lock_path("spy"), "a+")
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            attempts.append("acquired")  # BAD: no lock was held by the snapshot
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        except BlockingIOError:
            attempts.append("blocked")  # GOOD: the snapshot already holds it
        finally:
            lock_fh.close()
        return original_read_json(path)

    mp = pytest.MonkeyPatch()
    try:
        mp.setattr(rs, "read_json", spy_read_json)
        snap = rs.snapshot_run_state("spy")
    finally:
        mp.undo()
    assert snap.status == "consistent"
    assert attempts == ["blocked"]


def test_snapshot_serializes_behind_a_writer_and_never_sees_a_torn_pair():
    """Behavioral torn-read proof. A transition holds locked_run (exclusive) across
    its append -> projection-write; a snapshot reader needs the shared lock, so it
    must block until the writer's whole critical section lands and can therefore never
    fold a log line the projection has not yet caught up to.

    Deterministic: a writer thread takes the exclusive lock, publishes the TORN state
    (event appended, RUN.json still stale), signals, holds the window briefly, then
    finishes the projection write and releases. The reader — released only after the
    writer completes — observes a CONSISTENT pair, never `drift`. Correctness does not
    depend on the sleep: the exclusive lock strictly serializes the reader behind the
    writer regardless of timing, so a torn verdict is impossible, not merely unlikely."""
    import threading
    import time

    rs.main(["init", "--slug", "tornsnap", "--run-id", "r1"])
    rs.main(
        ["transition", "--slug", "tornsnap", "--to", "investigating", "--event", "e"]
    )

    torn_published = threading.Event()
    writer_done = threading.Event()

    def writer():
        with rs.locked_run("tornsnap"):
            events = rs.read_events("tornsnap", validate=False)
            new_event = {
                "event_id": "torn-3",
                "seq": events[-1]["seq"] + 1,
                "ts": rs.now_iso(),
                "slug": "tornsnap",
                "run_id": events[0]["run_id"],
                "from_state": "investigating",
                "to_state": "planning",
                "event": "agent.step",
                "waiting_on": None,
                "resume_event": None,
                "sha": None,
                "metadata": {},
            }
            with open(rs.events_path("tornsnap"), "a") as f:
                f.write(json.dumps(new_event, sort_keys=True) + "\n")
                f.flush()
                os.fsync(f.fileno())
            # On-disk state is now TORN: fold == seq 3 (planning), RUN.json == seq 2.
            torn_published.set()
            time.sleep(0.2)  # keep the torn window open past the reader's lock attempt
            rs.atomic_write_json(
                rs.run_json_path("tornsnap"),
                rs.project(rs.read_events("tornsnap", validate=False)),
            )
        writer_done.set()

    t = threading.Thread(target=writer)
    t.start()
    try:
        assert torn_published.wait(timeout=5)
        snap = rs.snapshot_run_state("tornsnap")
    finally:
        t.join(timeout=5)
    assert writer_done.is_set()
    assert snap.status == "consistent"  # never "drift" — the torn pair was invisible
    assert snap.projection["state"] == "planning"
    assert snap.projection["seq"] == 3


def test_runtime_diagnosis_is_optional_and_projects_last_supplied_pair():
    evidence = "codex-mode-0123456789abcdef"
    assert rs.main(
        [
            "init", "--slug", "mode", "--run-id", "r1",
            "--runtime-mode", "advisory",
            "--runtime-evidence-id", evidence,
        ]
    ) == 0
    first = rs.read_events("mode")[0]
    assert first["metadata"] == {
        "runtime_mode": "advisory",
        "runtime_evidence_id": evidence,
    }
    assert rs.main(
        ["transition", "--slug", "mode", "--to", "investigating", "--event", "start"]
    ) == 0
    projection = rs.read_json("specs/mode/RUN.json")
    assert projection["runtime_mode"] == "advisory"
    assert projection["runtime_evidence_id"] == evidence

    replacement = "codex-mode-fedcba9876543210"
    assert rs.main(
        [
            "transition", "--slug", "mode", "--to", "planning", "--event", "plan",
            "--runtime-mode", "unsupported",
            "--runtime-evidence-id", replacement,
        ]
    ) == 0
    projection = rs.read_json("specs/mode/RUN.json")
    assert projection["runtime_mode"] == "unsupported"
    assert projection["runtime_evidence_id"] == replacement


def test_runtime_diagnosis_requires_a_valid_complete_pair_and_legacy_stays_exact():
    assert rs.main(["init", "--slug", "legacy", "--run-id", "r1"]) == 0
    projection = rs.read_json("specs/legacy/RUN.json")
    assert "runtime_mode" not in projection
    assert "runtime_evidence_id" not in projection
    assert rs.main(
        [
            "transition", "--slug", "legacy", "--to", "investigating", "--event", "start",
            "--runtime-mode", "enforced",
        ]
    ) == 2
    assert rs.main(
        [
            "transition", "--slug", "legacy", "--to", "investigating", "--event", "start",
            "--runtime-evidence-id", "codex-mode-0123456789abcdef",
        ]
    ) == 2


def test_forged_runtime_metadata_makes_event_chain_invalid():
    assert rs.main(["init", "--slug", "forged", "--run-id", "r1"]) == 0
    path = "specs/forged/events.jsonl"
    event = json.loads(open(path).readline())
    event["metadata"] = {"runtime_mode": "enforced"}
    with open(path, "w") as handle:
        handle.write(json.dumps(event) + "\n")
    with pytest.raises(rs.StorageError, match="supplied together"):
        rs.read_events("forged")
