"""Executable resume-routing + task-cursor contract, independent of SDD prose.

Every lifecycle route, storage topology, and plan/task/git evidence case has an EXACT
expected (action, reason_code).  A future unclassified FSM state fails the state matrix.
No test parses SKILL.md prose; behaviour is proven end-to-end through decide().
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "skills", "visual-planner")
)

import run_state as rs  # noqa: E402
import resume_decision as decision  # noqa: E402


# --- fixtures / helpers ----------------------------------------------------------------

_ACTIVE_MD_PLAN = """\
issue: 175
status: active

# Plan

### Task 1.1 — first (wave 1)

- **Files:** a.py
- **Action:** do a
- **Verify:** `pytest -k a`
- **Done:** a done

### Task 1.2 — second (wave 1)

- **Files:** b.py
- **Action:** do b
- **Verify:** `pytest -k b`
- **Done:** b done
"""


def write_plan(slug: str, text: str = _ACTIVE_MD_PLAN) -> None:
    d = Path("specs") / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "PLAN.md").write_text(text, encoding="utf-8")


def init_to(slug: str, states: tuple[str, ...]) -> None:
    assert rs.main(["init", "--slug", slug, "--run-id", f"run-{slug}"]) == 0
    for state in states:
        args = ["transition", "--slug", slug, "--to", state, "--event", f"to.{state}"]
        if state in rs.WAITING_STATES:
            args += ["--waiting-on", state]
        if state in rs.INTERRUPT_STATES:
            args += ["--waiting-on", "blocker", "--resume-event", "resolved"]
        if state == "shipped":
            args += ["--sha", "deadbeef1234"]
        assert rs.main(args) == 0, f"transition to {state} failed"


PATHS = {
    "queued": (),
    "investigating": ("investigating",),
    "awaiting_confirmation": ("investigating", "awaiting_confirmation"),
    "planning": ("investigating", "planning"),
    "implementing": ("investigating", "planning", "implementing"),
    "verifying": ("investigating", "planning", "implementing", "verifying"),
    "awaiting_ci": (
        "investigating",
        "planning",
        "implementing",
        "verifying",
        "awaiting_ci",
    ),
    "fixing_ci": (
        "investigating",
        "planning",
        "implementing",
        "verifying",
        "awaiting_ci",
        "fixing_ci",
    ),
    "awaiting_review": (
        "investigating",
        "planning",
        "implementing",
        "verifying",
        "awaiting_ci",
        "awaiting_review",
    ),
    "addressing_review": (
        "investigating",
        "planning",
        "implementing",
        "verifying",
        "awaiting_ci",
        "awaiting_review",
        "addressing_review",
    ),
    "ready_to_merge": (
        "investigating",
        "planning",
        "implementing",
        "verifying",
        "ready_to_merge",
    ),
    "blocked": ("investigating", "planning", "blocked"),
    "escalated": ("investigating", "planning", "escalated"),
    "cancelled": ("investigating", "planning", "cancelled"),
    "superseded": ("investigating", "planning", "superseded"),
    "shipped": (
        "investigating",
        "planning",
        "implementing",
        "verifying",
        "ready_to_merge",
        "shipped",
    ),
}

# Exact (action, reason_code) per FSM state, given a VALID ACTIVE plan present.
EXPECT = {
    "queued": ("execute-plan", "catch-up"),
    "investigating": ("execute-plan", "catch-up"),
    "awaiting_confirmation": ("wait", "awaiting-external"),
    "planning": ("execute-plan", "active-plan"),
    "implementing": ("execute-plan", "active-plan"),
    "verifying": ("resume-review-chain", "review-chain"),
    "awaiting_ci": ("wait", "awaiting-external"),
    "fixing_ci": ("resume-repair", "post-pr-repair"),
    "awaiting_review": ("wait", "awaiting-external"),
    "addressing_review": ("resume-repair", "post-pr-repair"),
    "ready_to_merge": ("wait", "awaiting-external"),
    "blocked": ("wait", "interrupt-blocked"),
    "escalated": ("wait", "interrupt-blocked"),
    "cancelled": ("stop", "terminal-run"),
    "superseded": ("stop", "terminal-run"),
    "shipped": ("stop", "terminal-run"),
}


# --- state matrix (SC-2) ----------------------------------------------------------------


def test_state_matrix_is_exhaustive_over_the_fsm(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Adding an unclassified FSM state must fail the suite here.
    assert set(PATHS) == rs.ALL_STATES
    assert set(EXPECT) == rs.ALL_STATES


def test_state_matrix_exact_action_and_reason_code(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for state, path in PATHS.items():
        slug = f"state-{state}"
        write_plan(slug)
        init_to(slug, path)
        v = decision.decide(slug)
        assert (v["action"], v["reason_code"]) == EXPECT[state], state


# --- storage matrix (SC-2) --------------------------------------------------------------


def test_storage_matrix_exact_action_per_topology(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # untracked run + valid non-shipped plan -> execute from the reconstructed cursor.
    write_plan("untracked")
    v = decision.decide("untracked")
    assert (v["action"], v["reason_code"]) == ("execute-plan", "untracked-executable")
    assert v["run"]["status"] == "untracked"
    assert "run-untracked" in v["warnings"]

    # projection-only -> stop (cannot trust a projection with no canonical log).
    Path("specs/projonly").mkdir(parents=True)
    Path(rs.run_json_path("projonly")).write_text("{}")
    v = decision.decide("projonly")
    assert (v["action"], v["reason_code"]) == ("stop", "storage-projection-only")

    # events-only -> rebuild.
    init_to("evonly", ("investigating", "planning"))
    Path(rs.run_json_path("evonly")).unlink()
    v = decision.decide("evonly")
    assert (v["action"], v["reason_code"]) == ("rebuild", "projection-missing")

    # drift -> rebuild.
    init_to("drift", ("investigating", "planning"))
    p = Path(rs.run_json_path("drift"))
    data = json.loads(p.read_text())
    data["state"] = "queued"
    p.write_text(json.dumps(data))
    v = decision.decide("drift")
    assert (v["action"], v["reason_code"]) == ("rebuild", "projection-drift")

    # invalid storage -> stop.
    Path("specs/invalid").mkdir(parents=True)
    Path(rs.events_path("invalid")).write_text("not-json\n")
    v = decision.decide("invalid")
    assert (v["action"], v["reason_code"]) == ("stop", "storage-invalid")

    # consistent + active plan + implementing -> execute-plan.
    write_plan("consistent")
    init_to("consistent", ("investigating", "planning", "implementing"))
    v = decision.decide("consistent")
    assert (v["action"], v["reason_code"]) == ("execute-plan", "active-plan")


def test_storage_matrix_missing_plan_stops_execution(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_to("noplan", ("investigating", "planning", "implementing"))
    v = decision.decide("noplan")
    assert (v["action"], v["reason_code"]) == ("stop", "plan-missing")


# --- shipped-plan repair exception (SC-3) ----------------------------------------------

_SHIPPED_MD_PLAN = _ACTIVE_MD_PLAN.replace("status: active", "status: shipped")


def test_shipped_plan_blocks_execute_but_repair_states_still_route(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    # implementing + shipped plan -> plan-task execution is closed.
    write_plan("ship-impl", _SHIPPED_MD_PLAN)
    init_to("ship-impl", ("investigating", "planning", "implementing"))
    v = decision.decide("ship-impl")
    assert (v["action"], v["reason_code"]) == ("stop", "plan-shipped")

    # fixing_ci + shipped plan -> still routes to repair.
    write_plan("ship-ci", _SHIPPED_MD_PLAN)
    init_to("ship-ci", PATHS["fixing_ci"])
    v = decision.decide("ship-ci")
    assert (v["action"], v["reason_code"]) == ("resume-repair", "post-pr-repair")
    assert v["plan"]["status"] == "shipped"

    # addressing_review + shipped plan -> still routes to repair.
    write_plan("ship-rev", _SHIPPED_MD_PLAN)
    init_to("ship-rev", PATHS["addressing_review"])
    v = decision.decide("ship-rev")
    assert (v["action"], v["reason_code"]) == ("resume-repair", "post-pr-repair")


# --- interrupt / waiting-origin recovery (SC-4) ----------------------------------------


def test_interrupt_blocked_from_active_origin_returns_transition(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_to("int-plan", ("investigating", "planning", "blocked"))
    v = decision.decide("int-plan")
    assert (v["action"], v["reason_code"]) == ("wait", "interrupt-blocked")
    assert v["interrupt"]["origin_state"] == "planning"
    assert (
        v["interrupt"]["recovered_waiting_on"] is None
    )  # planning is not a waiting state
    assert v["required_transition"]["to"] == "planning"


def test_waiting_origin_interrupt_recovers_original_waiting_on_and_successors(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    # awaiting_ci(waiting_on=ci-run-42) -> blocked must recover ci-run-42.
    rs.main(["init", "--slug", "wo", "--run-id", "run-wo"])
    for st in ("investigating", "planning", "implementing", "verifying"):
        assert (
            rs.main(["transition", "--slug", "wo", "--to", st, "--event", f"to.{st}"])
            == 0
        )
    assert (
        rs.main(
            [
                "transition",
                "--slug",
                "wo",
                "--to",
                "awaiting_ci",
                "--event",
                "to.ci",
                "--waiting-on",
                "ci-run-42",
            ]
        )
        == 0
    )
    assert (
        rs.main(
            [
                "transition",
                "--slug",
                "wo",
                "--to",
                "blocked",
                "--event",
                "to.blocked",
                "--waiting-on",
                "human",
                "--resume-event",
                "resolved",
            ]
        )
        == 0
    )
    v = decision.decide("wo")
    assert (v["action"], v["reason_code"]) == ("wait", "interrupt-blocked")
    assert v["interrupt"]["origin_state"] == "awaiting_ci"
    assert v["interrupt"]["recovered_waiting_on"] == "ci-run-42"
    assert set(v["interrupt"]["successors"]) == {
        "fixing_ci",
        "awaiting_review",
        "ready_to_merge",
    }
    assert v["required_transition"]["to"] == "awaiting_ci"


# --- cursor reconstruction (SC-5) ------------------------------------------------------


def test_cursor_markdown_orders_tasks_and_exposes_checks_to_rerun(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    plan = _ACTIVE_MD_PLAN + "\n## Status Log\n\n- 2026-08-09 — Task 1.1 complete.\n"
    write_plan("md-cur", plan)
    init_to("md-cur", ("investigating", "planning", "implementing"))
    v = decision.decide("md-cur")
    assert v["cursor"]["task_ids"] == ["1.1", "1.2"]
    assert v["cursor"]["claimed_complete"] == ["1.1"]
    assert v["cursor"]["pending"] == ["1.2"]
    assert v["cursor"]["next_task"] == "1.2"
    assert v["cursor"]["checks_to_rerun"] == [
        {"task_id": "1.1", "command": "pytest -k a"}
    ]


_XML_PLAN = """\
status: active

# Plan

<task id="1.1" wave="1">
<files>a.py</files>
<action>do a</action>
<verify>pytest -k a</verify>
<done>a</done>
</task>

<task id="1.2" wave="1">
<files>b.py</files>
<action>do b</action>
<verify>pytest -k b</verify>
<done>b</done>
</task>

## Status Log

- 2026-08-09 — Task 1.1 complete.
"""


def test_cursor_legacy_xml_orders_tasks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_plan("xml-cur", _XML_PLAN)
    init_to("xml-cur", ("investigating", "planning", "implementing"))
    v = decision.decide("xml-cur")
    assert v["cursor"]["task_ids"] == ["1.1", "1.2"]
    assert v["cursor"]["claimed_complete"] == ["1.1"]
    assert v["cursor"]["checks_to_rerun"] == [
        {"task_id": "1.1", "command": "pytest -k a"}
    ]


def test_cursor_mixed_complete_pending_claims_only_its_own_mention(
    tmp_path, monkeypatch
):
    """The landmine guard: a mixed Status Log entry must NOT complete both tasks."""
    monkeypatch.chdir(tmp_path)
    plan = (
        _ACTIVE_MD_PLAN
        + "\n## Status Log\n\n- 2026-08-09 — Task 1.1 complete; Task 1.2 pending\n"
    )
    write_plan("mixed", plan)
    init_to("mixed", ("investigating", "planning", "implementing"))
    v = decision.decide("mixed")
    assert v["cursor"]["claimed_complete"] == ["1.1"]
    assert v["cursor"]["pending"] == ["1.2"]


def test_cursor_unknown_task_completion_stops(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    plan = _ACTIVE_MD_PLAN + "\n## Status Log\n\n- 2026-08-09 — Task 9.9 complete.\n"
    write_plan("unk", plan)
    init_to("unk", ("investigating", "planning", "implementing"))
    v = decision.decide("unk")
    assert (v["action"], v["reason_code"]) == ("stop", "cursor-conflict")


# --- git evidence reconciliation (SC-5) ------------------------------------------------


def _git_repo(tmp_path):
    def g(*args):
        subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True
        )

    g("init", "-q")
    g("config", "user.email", "t@t")
    g("config", "user.name", "t")
    g("commit", "--allow-empty", "-q", "-m", "base")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True
    ).stdout.strip()
    g("commit", "--allow-empty", "-q", "-m", "head")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True
    ).stdout.strip()
    return base, head


def _plan_with_claim(sha: str) -> str:
    return (
        _ACTIVE_MD_PLAN
        + f"\n## Status Log\n\n- 2026-08-09 — Task 1.1 complete (`{sha}`).\n"
    )


def test_git_evidence_in_range_commit_resumes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base, head = _git_repo(tmp_path)
    write_plan("gr-ok", _plan_with_claim(head))
    init_to("gr-ok", ("investigating", "planning", "implementing"))
    v = decision.decide("gr-ok", base=base)
    assert v["action"] == "execute-plan"
    assert v["git"]["conflicts"] == []
    assert v["cursor"]["claimed_complete"] == ["1.1"]


def test_git_evidence_out_of_range_commit_stops(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base, head = _git_repo(tmp_path)
    # The base commit itself is NOT inside base..HEAD -> out of range.
    write_plan("gr-bad", _plan_with_claim(base))
    init_to("gr-bad", ("investigating", "planning", "implementing"))
    v = decision.decide("gr-bad", base=base)
    assert (v["action"], v["reason_code"]) == ("stop", "git-evidence-conflict")
    assert v["git"]["conflicts"][0]["type"] == "commit-out-of-range"


def test_git_evidence_unresolvable_commit_stops(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base, head = _git_repo(tmp_path)
    write_plan("gr-unres", _plan_with_claim("0000000"))
    init_to("gr-unres", ("investigating", "planning", "implementing"))
    v = decision.decide("gr-unres", base=base)
    assert (v["action"], v["reason_code"]) == ("stop", "git-evidence-conflict")


def test_git_evidence_wrong_base_not_ancestor_stops(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    base, head = _git_repo(tmp_path)
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    ).stdout.strip()
    # A commit on a divergent branch is not an ancestor of HEAD.
    subprocess.run(
        ["git", "checkout", "-q", "-b", "side", base],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-q", "-m", "side"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    side = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True
    ).stdout.strip()
    subprocess.run(
        ["git", "checkout", "-q", branch],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    write_plan("gr-wb", _plan_with_claim(head))
    init_to("gr-wb", ("investigating", "planning", "implementing"))
    v = decision.decide("gr-wb", base=side)
    assert (v["action"], v["reason_code"]) == ("stop", "base-unresolved")


# --- task-order parity vs render_plan (SC-5) -------------------------------------------


def test_git_evidence_parity_cursor_matches_renderer_task_order(tmp_path, monkeypatch):
    """Ordered task IDs must match render_plan for both markdown and legacy XML.
    Ordering only — the renderer's presentation-grade done set is NOT compared."""
    monkeypatch.chdir(tmp_path)
    import render_plan

    for body in (_ACTIVE_MD_PLAN, _XML_PLAN):
        mine = [t["id"] for t in decision.parse_tasks(body)[0]]
        theirs = [t["id"] for t in render_plan.extract_tasks(body)[0]]
        assert mine == theirs == ["1.1", "1.2"]


# --- STATE hint + SUMMARY deviations (SC-6) --------------------------------------------


def _write_state(slug: str, updated: date, last: str = "did stuff") -> None:
    Path("specs").mkdir(exist_ok=True)
    Path("specs/STATE.md").write_text(
        "# Workflow State\n\n## Active Spec\n\n"
        f"- **Slug:** {slug}\n"
        "- **Phase:** implement\n"
        f"- **Last action:** {last}\n"
        f"- **Updated:** {updated.isoformat()}\n\n"
        "## Recent Specs\n",
        encoding="utf-8",
    )


def test_state_hint_same_slug_recent_is_consumed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_plan("sh-ok")
    init_to("sh-ok", ("investigating", "planning", "implementing"))
    _write_state("sh-ok", date.today() - timedelta(days=1))
    v = decision.decide("sh-ok")
    assert v["session_hint"] is not None
    assert v["session_hint"]["slug"] == "sh-ok"
    assert (
        "state-stale" not in v["warnings"] and "state-wrong-slug" not in v["warnings"]
    )
    # STATE never overrides the durable route.
    assert v["action"] == "execute-plan"


def test_state_hint_wrong_slug_is_ignored_with_warning(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_plan("sh-wrong")
    init_to("sh-wrong", ("investigating", "planning", "implementing"))
    _write_state("some-other-slug", date.today())
    v = decision.decide("sh-wrong")
    assert v["session_hint"] is None
    assert "state-wrong-slug" in v["warnings"]


def test_state_hint_stale_is_ignored_with_warning(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_plan("sh-stale")
    init_to("sh-stale", ("investigating", "planning", "implementing"))
    _write_state("sh-stale", date.today() - timedelta(days=30))
    v = decision.decide("sh-stale")
    assert v["session_hint"] is None
    assert "state-stale" in v["warnings"]


def test_deviations_are_returned_verbatim_without_changing_routing(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    write_plan("dev")
    init_to("dev", ("investigating", "planning", "implementing"))
    Path("specs/dev/SUMMARY.md").write_text(
        "# Summary\n\n### Deviations\n\n"
        "- Rule 2 — Added a guard for invalid input. `x.py`. Commit `abc1234`.\n"
        "- Rule 3 — Added dep `foo>=1`. Commit `def5678`.\n\n"
        "### Verify\n",
        encoding="utf-8",
    )
    v = decision.decide("dev")
    assert v["deviations"] == [
        "Rule 2 — Added a guard for invalid input. `x.py`. Commit `abc1234`.",
        "Rule 3 — Added dep `foo>=1`. Commit `def5678`.",
    ]
    assert v["action"] == "execute-plan"  # deviations never change the lifecycle route


# --- paused / proposed plan activation (SC-2 execution route) --------------------------


def test_state_hint_paused_plan_requires_activation_action(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_plan("paused", _ACTIVE_MD_PLAN.replace("status: active", "status: paused"))
    init_to("paused", ("investigating", "planning", "implementing"))
    v = decision.decide("paused")
    assert (v["action"], v["reason_code"]) == (
        "execute-plan",
        "plan-activation-required",
    )
    assert v["required_transition"]["kind"] == "activate-plan"
    assert v["required_transition"]["to_status"] == "active"


# --- schema stability (SC-7) -----------------------------------------------------------

_KEYS = {
    "schema_version",
    "slug",
    "action",
    "reason_code",
    "reason",
    "run",
    "plan",
    "cursor",
    "git",
    "interrupt",
    "session_hint",
    "deviations",
    "required_transition",
    "warnings",
}


def test_schema_all_action_families_carry_stable_top_level_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_plan("sc-exec")
    init_to("sc-exec", ("investigating", "planning", "implementing"))
    write_plan("sc-wait")
    init_to("sc-wait", ("investigating", "awaiting_confirmation"))
    write_plan("sc-stop")
    init_to("sc-stop", ("investigating", "planning", "cancelled"))
    write_plan("sc-repair")
    init_to("sc-repair", PATHS["fixing_ci"])
    write_plan("sc-review")
    init_to("sc-review", PATHS["verifying"])
    write_plan("sc-int")
    init_to("sc-int", ("investigating", "planning", "blocked"))
    init_to("sc-rebuild", ("investigating", "planning"))
    Path(rs.run_json_path("sc-rebuild")).unlink()

    for slug in (
        "sc-exec",
        "sc-wait",
        "sc-stop",
        "sc-repair",
        "sc-review",
        "sc-int",
        "sc-rebuild",
    ):
        v = decision.decide(slug)
        assert set(v.keys()) == _KEYS, slug
        assert v["schema_version"] == 1
        assert v["slug"] == slug


# --- semantic read-only (SC-7) ---------------------------------------------------------


def _canon_bytes(slug: str) -> dict:
    out = {}
    for name, p in (
        ("run", rs.run_json_path(slug)),
        ("events", rs.events_path(slug)),
        ("plan", str(Path("specs") / slug / "PLAN.md")),
    ):
        pp = Path(p)
        out[name] = pp.read_bytes() if pp.exists() else None
    return out


def test_readonly_every_action_family_leaves_canonical_files_byte_identical(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    families = {}

    write_plan("ro-exec")
    init_to("ro-exec", ("investigating", "planning", "implementing"))
    families["ro-exec"] = None

    write_plan("ro-wait")
    init_to("ro-wait", ("investigating", "awaiting_confirmation"))
    families["ro-wait"] = None

    write_plan("ro-stop")
    init_to("ro-stop", ("investigating", "planning", "cancelled"))
    families["ro-stop"] = None

    write_plan("ro-repair")
    init_to("ro-repair", PATHS["fixing_ci"])
    families["ro-repair"] = None

    write_plan("ro-review")
    init_to("ro-review", PATHS["verifying"])
    families["ro-review"] = None

    write_plan("ro-int")
    init_to("ro-int", ("investigating", "planning", "blocked"))
    families["ro-int"] = None

    # rebuild family: events-only store, PLAN present.
    write_plan("ro-rebuild")
    init_to("ro-rebuild", ("investigating", "planning"))
    Path(rs.run_json_path("ro-rebuild")).unlink()
    families["ro-rebuild"] = None

    for slug in families:
        before = _canon_bytes(slug)
        v = decision.decide(slug)
        after = _canon_bytes(slug)
        assert before == after, f"{slug} ({v['action']}) mutated canonical evidence"


# --- CLI exit codes --------------------------------------------------------------------


def test_readonly_cli_exit_codes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_plan("cli")
    init_to("cli", ("investigating", "planning", "implementing"))
    assert decision.main(["--slug", "cli"]) == 0
    # terminal / wait / rebuild are valid decisions -> exit 0.
    init_to("cli-term", ("investigating", "planning", "cancelled"))
    assert decision.main(["--slug", "cli-term"]) == 0
    with pytest.raises(SystemExit) as ei:  # CLI misuse -> argparse exit 2
        decision.main([])
    assert ei.value.code == 2
