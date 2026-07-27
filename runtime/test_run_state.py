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


def test_step_minus_one_covers_every_run_state():
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


def test_only_planning_and_interrupts_reach_implementing_directly():
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


def test_shipped_plan_stop_exempts_the_repair_states():
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


def test_task_cursor_directive_is_scoped_to_plan_execution_states():
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


def test_waiting_state_successors_are_documented():
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

    for wait in sorted(rs.WAITING_STATES):
        assert f"`{wait}`" in table, f"{wait} has no successor row"
        for target in sorted(rs.FORWARD_TRANSITIONS[wait]):
            assert f"`{target}`" in table, f"{wait} -> {target} not documented"


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
