"""Executable resume-routing contract, independent of SDD prose."""

from __future__ import annotations

import json
from pathlib import Path

import run_state as rs
import resume_decision as decision


def init_to(slug: str, states: tuple[str, ...]) -> None:
    rs.main(["init", "--slug", slug, "--run-id", f"run-{slug}"])
    for state in states:
        args = ["transition", "--slug", slug, "--to", state, "--event", f"to.{state}"]
        if state in rs.WAITING_STATES:
            args += ["--waiting-on", state]
        if state in rs.INTERRUPT_STATES:
            args += ["--waiting-on", "blocker", "--resume-event", "resolved"]
        rs.main(args)


def test_untracked_and_storage_split(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert decision.decide("missing")["action"] == "execute-plan"
    Path("specs/projection").mkdir(parents=True)
    Path(rs.run_json_path("projection")).write_text("{}")
    assert decision.decide("projection")["action"] == "stop"
    init_to("events", ())
    Path(rs.run_json_path("events")).unlink()
    assert decision.decide("events")["action"] == "rebuild"


def test_active_and_review_states_have_distinct_actions(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_to("planning", ("investigating", "planning"))
    assert decision.decide("planning")["action"] == "execute-plan"
    init_to("verifying", ("investigating", "planning", "implementing", "verifying"))
    assert decision.decide("verifying")["action"] == "resume-review-chain"
    init_to("repair", ("investigating", "planning", "implementing", "verifying", "awaiting_ci", "fixing_ci"))
    assert decision.decide("repair")["action"] == "resume-repair"


def test_wait_interrupt_and_terminal_stop(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_to("wait", ("investigating", "awaiting_confirmation"))
    assert decision.decide("wait")["action"] == "wait"
    init_to("blocked", ("investigating", "planning", "blocked"))
    found = decision.decide("blocked")
    assert found["action"] == "wait"
    assert found["origin_state"] == "planning"
    init_to("terminal", ("investigating", "planning", "cancelled"))
    assert decision.decide("terminal")["action"] == "stop"


def test_projection_drift_requires_rebuild(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_to("drift", ("investigating", "planning"))
    path = Path(rs.run_json_path("drift"))
    data = json.loads(path.read_text())
    data["state"] = "queued"
    path.write_text(json.dumps(data))
    assert decision.decide("drift")["action"] == "rebuild"


def test_every_engine_state_has_an_executable_resume_verdict(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    paths = {
        "queued": (), "investigating": ("investigating",),
        "awaiting_confirmation": ("investigating", "awaiting_confirmation"),
        "planning": ("investigating", "planning"),
        "implementing": ("investigating", "planning", "implementing"),
        "verifying": ("investigating", "planning", "implementing", "verifying"),
        "awaiting_ci": ("investigating", "planning", "implementing", "verifying", "awaiting_ci"),
        "fixing_ci": ("investigating", "planning", "implementing", "verifying", "awaiting_ci", "fixing_ci"),
        "awaiting_review": ("investigating", "planning", "implementing", "verifying", "awaiting_ci", "awaiting_review"),
        "addressing_review": ("investigating", "planning", "implementing", "verifying", "awaiting_ci", "awaiting_review", "addressing_review"),
        "ready_to_merge": ("investigating", "planning", "implementing", "verifying", "ready_to_merge"),
        "blocked": ("investigating", "planning", "blocked"),
        "escalated": ("investigating", "planning", "escalated"),
        "cancelled": ("investigating", "planning", "cancelled"),
        "superseded": ("investigating", "planning", "superseded"),
        "shipped": ("investigating", "planning", "implementing", "verifying", "ready_to_merge", "shipped"),
    }
    assert set(paths) == rs.ALL_STATES
    for state, path in paths.items():
        slug = f"state-{state}"
        init_to(slug, path)
        verdict = decision.decide(slug)
        assert verdict["action"] in {"execute-plan", "resume-repair", "resume-review-chain", "wait", "stop"}
