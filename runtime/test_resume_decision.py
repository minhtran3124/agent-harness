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


@pytest.fixture(autouse=True)
def _hermetic_base_env(monkeypatch):
    """A declared base (VERIFY_ROWS_BASE / GITHUB_BASE_REF) is now validated even with no
    claimed commits (finding G); CI PR jobs export GITHUB_BASE_REF, so clear both by
    default and let base-specific tests set them explicitly.  Keeps every other test
    hermetic regardless of the CI environment."""
    monkeypatch.delenv("VERIFY_ROWS_BASE", raising=False)
    monkeypatch.delenv("GITHUB_BASE_REF", raising=False)


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
    "waiting_on",
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


# --- adversarial correctness fixes (gh-175 review) -------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]

_FOUR_TASK_PLAN = """\
issue: 175
status: active

# Plan

### Task 1.1 — a (wave 1)
- **Files:** a.py
- **Action:** do a
- **Verify:** `pytest -k a`
- **Done:** a

### Task 1.2 — b (wave 1)
- **Files:** b.py
- **Action:** do b
- **Verify:** `pytest -k b`
- **Done:** b

### Task 1.3 — c (wave 1)
- **Files:** c.py
- **Action:** do c
- **Verify:** `pytest -k c`
- **Done:** c

### Task 1.4 — d (wave 1)
- **Files:** d.py
- **Action:** do d
- **Verify:** `pytest -k d`
- **Done:** d
"""


def _corpus_plans():
    plans = sorted((_REPO_ROOT / "specs").glob("*/PLAN.md"))
    assert plans, "expected a non-empty specs/*/PLAN.md corpus"
    return plans


def test_corpus_parity_parse_tasks_matches_render_plan():
    """Finding A regression guard: resume's ordered task ids must equal render_plan's for
    EVERY real PLAN.md, so a fenced/inline `<task` mention can never zero out a plan."""
    import render_plan  # noqa: E402

    for p in _corpus_plans():
        txt = p.read_text(encoding="utf-8")
        mine = [t["id"] for t in decision.parse_tasks(txt)[0]]
        theirs = [t["id"] for t in render_plan.extract_tasks(txt)[0]]
        assert mine == theirs, p


def test_corpus_completion_never_drops_ids_render_marks_done():
    """Finding C corpus guard: on entries with NO explicit non-completion marker, resume's
    claimed-complete set must cover render_plan's done set, and no real entry may produce a
    spurious `unknown` (which would stop a healthy resume)."""
    import re as _re

    import render_plan  # noqa: E402

    for p in _corpus_plans():
        txt = p.read_text(encoding="utf-8")
        valid = {t["id"] for t in decision.parse_tasks(txt)[0]}
        comp = decision.parse_status_completion(txt, valid)
        entries = render_plan.parse_status_entries(decision._status_log_section(txt))
        theirs = set()
        for e in entries:
            blob = e["note"] + " " + " ".join(e["subs"])
            if decision._NONCOMPLETE_RE.search(blob):
                continue
            if (
                e.get("kind") == "build"
                or "✓" in blob
                or _re.search(r"\bcomplete", blob)
            ):
                theirs |= set(_re.findall(r"\bP?\d+(?:\.\d+)+\b", blob)) & valid
        assert theirs <= comp["complete"], (p, sorted(theirs - comp["complete"]))
        assert comp["unknown"] == [], (p, comp["unknown"])


def test_parser_markdown_plan_mentioning_task_tag_is_not_misparsed_as_xml(
    tmp_path, monkeypatch
):
    """Finding A/B: a markdown plan that mentions `<task` inside a fence AND inline code
    must still parse its markdown tasks, not collapse to zero-task XML."""
    monkeypatch.chdir(tmp_path)
    plan = (
        _ACTIVE_MD_PLAN
        + "\n## Notes\n\nInline `<task>` is prose, not a task.\n\n"
        + "```xml\n<task>fenced illustration, no id</task>\n```\n"
    )
    write_plan("fence", plan)
    init_to("fence", ("investigating", "planning", "implementing"))
    v = decision.decide("fence")
    assert v["plan"]["format"] == "markdown"
    assert v["cursor"]["task_ids"] == ["1.1", "1.2"]


def test_completion_multi_id_list_after_one_keyword(tmp_path, monkeypatch):
    """Finding C(a): `Tasks 1.1, 1.2, 1.3 complete` claims all three."""
    monkeypatch.chdir(tmp_path)
    plan = (
        _FOUR_TASK_PLAN
        + "\n## Status Log\n\n- 2026-08-09 — Wave 1 / Tasks 1.1, 1.2, 1.3 complete.\n"
    )
    write_plan("multi", plan)
    init_to("multi", ("investigating", "planning", "implementing"))
    v = decision.decide("multi")
    assert v["cursor"]["claimed_complete"] == ["1.1", "1.2", "1.3"]
    assert v["cursor"]["pending"] == ["1.4"]


def test_completion_range_expands_to_existing_ids(tmp_path, monkeypatch):
    """Finding C(b): an en-dash range `tasks 1.1–1.4` claims 1.1..1.4, not just endpoints."""
    monkeypatch.chdir(tmp_path)
    plan = _FOUR_TASK_PLAN + "\n## Status Log\n\n- 2026-08-09 — tasks 1.1–1.4 done.\n"
    write_plan("range", plan)
    init_to("range", ("investigating", "planning", "implementing"))
    v = decision.decide("range")
    assert v["cursor"]["claimed_complete"] == ["1.1", "1.2", "1.3", "1.4"]
    assert v["cursor"]["pending"] == []


def test_completion_range_plus_pending_keeps_landmine_closed(tmp_path, monkeypatch):
    """Finding C landmine: a range completes only within its own clause; a `; ... pending`
    clause never completes."""
    monkeypatch.chdir(tmp_path)
    plan = (
        _FOUR_TASK_PLAN
        + "\n## Status Log\n\n- 2026-08-09 — Tasks 1.1–1.3 done; Task 1.4 pending\n"
    )
    write_plan("rp", plan)
    init_to("rp", ("investigating", "planning", "implementing"))
    v = decision.decide("rp")
    assert v["cursor"]["claimed_complete"] == ["1.1", "1.2", "1.3"]
    assert v["cursor"]["pending"] == ["1.4"]


def test_completion_shas_scoped_to_each_mention_segment(tmp_path, monkeypatch):
    """Finding C: a sha is attributed to its own mention's segment, not entry-wide."""
    monkeypatch.chdir(tmp_path)
    comp = decision.parse_status_completion(
        "## Status Log\n\n- Task 1.1 complete (`aaaaaaa`); Task 1.2 complete (`bbbbbbb`).\n",
        {"1.1", "1.2"},
    )
    assert comp["commits"] == {"1.1": ["aaaaaaa"], "1.2": ["bbbbbbb"]}


def test_non_dict_projection_stops_without_crash(tmp_path, monkeypatch):
    """Finding D: a truthy non-dict RUN.json is projection-only, never an exit-3 crash."""
    monkeypatch.chdir(tmp_path)
    for i, payload in enumerate(("[1, 2]", '"x"', "5")):
        slug = f"nd{i}"
        Path(f"specs/{slug}").mkdir(parents=True)
        Path(rs.run_json_path(slug)).write_text(payload)
        v = decision.decide(slug)
        assert (v["action"], v["reason_code"]) == ("stop", "storage-projection-only")
        assert decision.main(["--slug", slug]) == 0


def test_claimed_task_without_verify_fails_closed(tmp_path, monkeypatch):
    """Finding F: a claimed-complete task with no Verify cannot pass vacuously."""
    monkeypatch.chdir(tmp_path)
    plan = _ACTIVE_MD_PLAN.replace("- **Verify:** `pytest -k a`\n", "")
    plan += "\n## Status Log\n\n- 2026-08-09 — Task 1.1 complete.\n"
    write_plan("nv", plan)
    init_to("nv", ("investigating", "planning", "implementing"))
    v = decision.decide("nv")
    assert (v["action"], v["reason_code"]) == ("stop", "missing-verify")
    assert any(
        c["type"] == "missing-verify" and c["task_id"] == "1.1"
        for c in v["cursor"]["conflicts"]
    )


def test_unreadable_plan_stops_and_advisory_reads_degrade(tmp_path, monkeypatch):
    """Finding O: a non-UTF-8 byte never crashes the decision (exit 3).  The plan read
    fails closed; SUMMARY/STATE degrade to a warning."""
    monkeypatch.chdir(tmp_path)
    # PLAN unreadable -> structured stop.
    init_to("urp", ("investigating", "planning", "implementing"))
    Path("specs/urp/PLAN.md").write_bytes(b"status: active\n\xff\xfe bad\n")
    v = decision.decide("urp")
    assert (v["action"], v["reason_code"]) == ("stop", "plan-unreadable")
    assert decision.main(["--slug", "urp"]) == 0

    # SUMMARY unreadable -> advisory warning, route unaffected.
    write_plan("urs")
    init_to("urs", ("investigating", "planning", "implementing"))
    Path("specs/urs/SUMMARY.md").write_bytes(b"# S\n\xff\n")
    v = decision.decide("urs")
    assert "summary-unreadable" in v["warnings"]
    assert v["action"] == "execute-plan"

    # STATE unreadable -> advisory warning, no hint.
    write_plan("urt")
    init_to("urt", ("investigating", "planning", "implementing"))
    Path("specs/STATE.md").write_bytes(b"# State\n\xff\n")
    v = decision.decide("urt")
    assert "state-unreadable" in v["warnings"]
    assert v["session_hint"] is None


def test_declared_bogus_base_without_commits_stops(tmp_path, monkeypatch):
    """Finding G: an explicit --base (or declared env base) that does not resolve fails
    closed even when there are no claimed commits."""
    monkeypatch.chdir(tmp_path)
    write_plan("gb")  # no Status Log -> no claimed commits
    init_to("gb", ("investigating", "planning", "implementing"))
    v = decision.decide("gb", base="does-not-exist")
    assert (v["action"], v["reason_code"]) == ("stop", "base-unresolved")

    monkeypatch.setenv("GITHUB_BASE_REF", "no-such-branch")
    v2 = decision.decide("gb")
    assert (v2["action"], v2["reason_code"]) == ("stop", "base-unresolved")


def test_declared_env_base_fails_closed_in_real_repo(tmp_path, monkeypatch):
    """Finding G (round 2): an env-declared base (VERIFY_ROWS_BASE / GITHUB_BASE_REF) that
    does not resolve must be TERMINAL — never fall through to upstream/derivation and
    silently diff against a different base (resolve-base-ref.sh exits 1 there).  Runs inside
    a real git repo with a derivable ancestor so the fall-through is genuinely exercised;
    the tmp-dir-only test above passes for the wrong reason (a non-git dir has nothing to
    fall through to)."""
    monkeypatch.chdir(tmp_path)

    def g(*a):
        subprocess.run(
            ["git", *a], cwd=tmp_path, check=True, capture_output=True, text=True
        )

    g("init", "-q")
    g("config", "user.email", "t@t")
    g("config", "user.name", "t")
    g("commit", "--allow-empty", "-q", "-m", "base")
    g("branch", "mainline")  # an ancestor ref derivation WOULD fall through to
    g("commit", "--allow-empty", "-q", "-m", "head")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True
    ).stdout.strip()

    # bogus VERIFY_ROWS_BASE, no claimed commits -> stop, never no-claimed-commits.
    write_plan("eb")
    init_to("eb", ("investigating", "planning", "implementing"))
    monkeypatch.setenv("VERIFY_ROWS_BASE", "bogusref")
    v = decision.decide("eb")
    assert (v["action"], v["reason_code"]) == ("stop", "base-unresolved")
    assert v["git"]["base_reason"] == "VERIFY_ROWS_BASE-unresolved"

    # bogus GITHUB_BASE_REF WITH a claimed commit -> still stops; must NOT validate the sha
    # against the derived `mainline` ancestor.
    monkeypatch.delenv("VERIFY_ROWS_BASE")
    monkeypatch.setenv("GITHUB_BASE_REF", "no-such-branch")
    write_plan("eb2", _plan_with_claim(head))
    init_to("eb2", ("investigating", "planning", "implementing"))
    v2 = decision.decide("eb2")
    assert (v2["action"], v2["reason_code"]) == ("stop", "base-unresolved")
    assert v2["git"]["base_reason"] == "GITHUB_BASE_REF-unresolved"


def test_no_declared_base_and_no_commits_proceeds(tmp_path, monkeypatch):
    """Finding G scope: the auto-derived (undeclared) path still falls through cleanly when
    there is nothing to validate."""
    monkeypatch.chdir(tmp_path)
    write_plan("nd-base")
    init_to("nd-base", ("investigating", "planning", "implementing"))
    v = decision.decide("nd-base")
    assert v["action"] == "execute-plan"
    assert v["git"]["conflicts"] == []


def test_derive_base_skips_candidate_at_head(tmp_path, monkeypatch):
    """Finding I: a ref sitting exactly at HEAD must not be chosen as base (empty range ->
    false git-evidence-conflict); the real ancestor base is used instead."""
    monkeypatch.chdir(tmp_path)

    def g(*a):
        subprocess.run(
            ["git", *a], cwd=tmp_path, check=True, capture_output=True, text=True
        )

    g("init", "-q")
    g("config", "user.email", "t@t")
    g("config", "user.name", "t")
    g("commit", "--allow-empty", "-q", "-m", "base")
    g("checkout", "-q", "-b", "feat")
    g("commit", "--allow-empty", "-q", "-m", "head")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True
    ).stdout.strip()
    g("branch", "backup")  # sits at HEAD -> must be skipped, not chosen as base
    write_plan("db", _plan_with_claim(head))
    init_to("db", ("investigating", "planning", "implementing"))
    v = decision.decide("db")  # no explicit base -> derive
    assert v["action"] == "execute-plan", (v["reason_code"], v["git"])
    assert v["git"]["conflicts"] == []


def test_rev_list_failure_reports_range_unavailable(tmp_path, monkeypatch):
    """Finding J: a rev-list failure (e.g. shallow clone) is UNKNOWN range, not empty; it
    must not masquerade as every commit being out of range."""
    monkeypatch.chdir(tmp_path)
    base, head = _git_repo(tmp_path)
    write_plan("rl", _plan_with_claim(head))
    init_to("rl", ("investigating", "planning", "implementing"))
    real_git = decision._git

    def fake(args):
        if args[:1] == ["rev-list"] and "--count" not in args:
            return 1, ""
        return real_git(args)

    monkeypatch.setattr(decision, "_git", fake)
    v = decision.decide("rl", base=base)
    assert (v["action"], v["reason_code"]) == ("stop", "range-unavailable")
    assert v["git"]["conflicts"][0]["type"] == "range-unavailable"


def test_status_log_indent0_line_does_not_fold_into_prior_entry(tmp_path, monkeypatch):
    """Finding L: an indent-0 non-bullet line closes the entry; a trailing completion
    sentence must not complete a task the bullet only started."""
    monkeypatch.chdir(tmp_path)
    plan = (
        _ACTIVE_MD_PLAN
        + "\n## Status Log\n\n- 2026-08-09 — started Task 1.2\nAll remaining work is done.\n"
    )
    write_plan("fold", plan)
    init_to("fold", ("investigating", "planning", "implementing"))
    v = decision.decide("fold")
    assert "1.2" not in v["cursor"]["claimed_complete"]
    assert v["cursor"]["pending"] == ["1.1", "1.2"]


def test_wait_route_surfaces_waiting_on(tmp_path, monkeypatch):
    """Finding H: the wait route carries the blocker identity; ready_to_merge is null."""
    monkeypatch.chdir(tmp_path)
    write_plan("wt")
    init_to("wt", PATHS["awaiting_ci"])
    v = decision.decide("wt")
    assert v["action"] == "wait"
    assert v["waiting_on"] == "awaiting_ci"

    write_plan("rtm")
    init_to("rtm", PATHS["ready_to_merge"])
    v2 = decision.decide("rtm")
    assert v2["action"] == "wait"
    assert v2["waiting_on"] is None


# --- round-2 correctness regressions ---------------------------------------------------

_V4 = {"1.1", "1.2", "1.3", "1.4"}


def _comp(text, valid=_V4):
    return decision.parse_status_completion(
        "## Status Log\n\n- 2026-08-09 — " + text + "\n", set(valid)
    )


@pytest.mark.parametrize(
    "text",
    [
        "Task 1.1 done and Task 1.2 will follow",
        "Task 1.1 shipped. Next up: Task 1.2",
        "Task 1.1 merged, Task 1.2 next",
        "Task 1.1 verified; starting Task 1.2",
        "Task 1.1 complete. Task 1.2 pending",
    ],
)
def test_completion_landmine_claims_only_the_completed_mention(text):
    """Round-2 finding 1: a completion marker governing one mention must NOT complete a
    future/pending sibling named in the same entry (the reopened over-claim landmine)."""
    assert sorted(_comp(text)["complete"]) == ["1.1"]


def test_completion_mixed_list_with_trailing_pending_endash():
    """Round-2 finding 1: `Tasks 1.1, 1.2 complete — 1.3 pending` claims the completed list
    but not the trailing pending id."""
    assert sorted(_comp("Tasks 1.1, 1.2 complete — 1.3 pending")["complete"]) == [
        "1.1",
        "1.2",
    ]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("implemented exactly per design 5.4", []),
        ("Task 1.1 complete (coverage 2.1% -> 5.4%)", ["1.1"]),
        ("Task 1.1 done; bumped ruff to 1.2", ["1.1"]),
    ],
)
def test_completion_reference_decimals_are_not_claimed(text, expected):
    """Round-2 finding 1: a version/section/percentage decimal that collides with a task id
    (`ruff to 1.2` — 1.2 IS a plan task here) must not be claimed as complete."""
    assert sorted(_comp(text)["complete"]) == expected


def test_completion_multi_id_and_range_still_expand():
    """Round-2 finding 1: legitimate multi-id lists and ranges keep expanding to members."""
    v6 = {"2.1", "2.2", "2.3", "2.4"}
    assert sorted(_comp("Tasks 2.1, 2.2, 2.3 done", v6)["complete"]) == [
        "2.1",
        "2.2",
        "2.3",
    ]
    assert sorted(_comp("tasks 1.1–1.4 complete")["complete"]) == [
        "1.1",
        "1.2",
        "1.3",
        "1.4",
    ]


def test_completion_leading_sha_attributes_to_following_ids():
    """Round-2 finding 1: a sha stated BEFORE the ids (`wave 1 shipped (sha): tasks 1.1–1.4`)
    is attributed to every id that follows it, not dropped."""
    comp = _comp("wave 1 shipped (`78db5a6`): tasks 1.1–1.4")
    assert comp["commits"] == {tid: ["78db5a6"] for tid in ("1.1", "1.2", "1.3", "1.4")}


def test_interrupt_route_carries_waiting_on_at_top_level(tmp_path, monkeypatch):
    """Round-2 finding 3: the interrupt route is action==wait, so it must expose the blocker
    at the same stable top-level `waiting_on` path as every other wait response."""
    monkeypatch.chdir(tmp_path)
    write_plan("iw")
    init_to("iw", ("investigating", "planning", "blocked"))
    v = decision.decide("iw")
    assert v["action"] == "wait"
    assert v["waiting_on"] == "blocker"  # the interrupt's own waiting_on
    assert set(v.keys()) == _KEYS and v["schema_version"] == 1


def test_interrupt_route_waiting_on_falls_back_to_recovered_origin(
    tmp_path, monkeypatch
):
    """Round-2 finding 3: when a waiting-origin interrupt recovers the original blocker, the
    top-level waiting_on is populated (never null on a wait route)."""
    monkeypatch.chdir(tmp_path)
    write_plan("iw2")
    init_to("iw2", ("investigating", "planning", "blocked"))
    v = decision.decide("iw2")
    assert v["action"] == "wait" and v["waiting_on"] is not None


def test_xml_id_binding_prefers_first_real_id_attribute():
    """Round-2 finding 4: bind the first REAL id attribute — a leading `wave-id` or a
    trailing `data-id` must never win over the standalone `id`."""
    assert (
        decision._xml_task_from_block(
            '<task wave-id="3" id="1.1"><verify>v</verify></task>'
        )["id"]
        == "1.1"
    )
    assert (
        decision._xml_task_from_block(
            '<task id="1.1" data-id="99"><verify>v</verify></task>'
        )["id"]
        == "1.1"
    )
