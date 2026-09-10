"""Tests for scripts/check_skill_tool_conformance.py — run via pytest (wired into run-tests.sh).

The negative cases are the point. Each one is a real under-grant shape observed in the
`allowed-tools` rollout, so a regression that blinds the checker fails here rather than
shipping a skill that breaks mid-task.

The false-positive cases matter just as much: every heuristic here was narrowed after it
misfired on the live tree, and these tests pin the narrowing so it is not casually widened
back.
"""

import json
import subprocess
import sys
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_skill_tool_conformance.py"


def build(
    root: Path, skill_md: str, *, references: dict[str, str] | None = None
) -> None:
    (root / "skills" / "alpha" / "references").mkdir(parents=True, exist_ok=True)
    (root / "harness-manifest.json").write_text(json.dumps({"skills": ["alpha"]}))
    (root / "skills" / "alpha" / "SKILL.md").write_text(skill_md)
    for name, text in (references or {}).items():
        (root / "skills" / "alpha" / "references" / name).write_text(text)


def run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--root", str(root)],
        capture_output=True,
        text=True,
    )


def skill(tools: str, body: str) -> str:
    return f"---\nname: alpha\ndescription: d\nallowed-tools: {tools}\n---\n\n{body}\n"


# ── negative cases: the checker must bite ────────────────────────────────────────────────


def test_script_without_matching_pattern_fails(tmp_path):
    """using-git-worktrees shape: a .sh the body mandates, outside Bash(git *)/Bash(ls *)."""
    build(
        tmp_path,
        skill(
            "Read, Bash(git *), Bash(ls *)",
            "Run `skills/alpha/scripts/detect.sh` first.",
        ),
    )
    result = run(tmp_path)
    assert result.returncode == 1
    assert "detect.sh" in result.stderr


def test_python_command_with_no_bash_grant_fails(tmp_path):
    """writing-plans shape: no Bash entry at all, but the body runs a python3 script."""
    build(
        tmp_path,
        skill(
            "Read, Write, Grep, Glob",
            "Run `python3 scripts/check_plan_contract.py specs/<slug>/PLAN.md`.",
        ),
    )
    result = run(tmp_path)
    assert result.returncode == 1
    assert "check_plan_contract.py" in result.stderr


def test_placeholder_in_argument_does_not_hide_the_command(tmp_path):
    """A `<slug>` in an ARGUMENT must not make a real instruction look illustrative.

    Filtering the whole span on "<" silently lost two of five known under-grants.
    """
    build(tmp_path, skill("Read", "Run `python3 x.py specs/<slug>/PLAN.md`."))
    assert run(tmp_path).returncode == 1


def test_dispatch_of_named_prompt_without_agent_fails(tmp_path):
    """brainstorming shape: a mandatory dispatch declared in a references/ loop file."""
    build(
        tmp_path,
        skill("Read, Write, Grep, Glob", "Read `references/loop.md` and complete it."),
        references={
            "loop.md": "1. Dispatch `spec-document-reviewer-prompt.md` with the design path.\n"
        },
    )
    result = run(tmp_path)
    assert result.returncode == 1
    assert "neither Agent nor Task" in result.stderr


def test_runnable_fenced_block_is_checked(tmp_path):
    build(tmp_path, skill("Read", "```bash\npython3 scripts/thing.py\n```"))
    assert run(tmp_path).returncode == 1


# ── positive cases: the checker must stay quiet ──────────────────────────────────────────


def test_matching_pattern_passes(tmp_path):
    build(
        tmp_path,
        skill(
            "Read, Bash(python3 scripts/check_plan_contract.py *)",
            "Run `python3 scripts/check_plan_contract.py specs/<slug>/PLAN.md`.",
        ),
    )
    assert run(tmp_path).returncode == 0


def test_bare_bash_permits_everything(tmp_path):
    build(
        tmp_path, skill("Read, Bash", "Run `python3 anything.py` and `bash other.sh`.")
    )
    assert run(tmp_path).returncode == 0


def test_pattern_with_trailing_star_matches_the_bare_command(tmp_path):
    """`Bash(git diff *)` grants `git diff` itself, not only `git diff <something>`."""
    build(tmp_path, skill("Read, Bash(git diff *)", "Inspect with `git diff`."))
    assert run(tmp_path).returncode == 0


def test_native_tool_stands_in_for_its_shell_equivalent(tmp_path):
    """A skill holding Grep does not additionally need Bash(grep *)."""
    build(tmp_path, skill("Read, Grep", "Search with `grep -rn thing app/`."))
    assert run(tmp_path).returncode == 0


def test_deployed_path_rewrite_still_matches(tmp_path):
    """deploy-harness.sh rewrites scripts/x.py to .claude/scripts/x.py in derived docs."""
    build(
        tmp_path,
        skill(
            "Read, Bash(python3 scripts/x.py *)",
            "Run `python3 .claude/scripts/x.py foo`.",
        ),
    )
    assert run(tmp_path).returncode == 0


def test_illustrative_block_is_skipped(tmp_path):
    """Matches lint-skill-bash.sh's convention so the two checkers agree."""
    build(tmp_path, skill("Read", "```bash\npython3 x.py <placeholder>\n```"))
    assert run(tmp_path).returncode == 0


def test_bare_dispatch_word_is_not_a_finding(tmp_path):
    """ "dispatch prompts" is a noun here, and "do not dispatch" is a prohibition.

    The unqualified word produced 3 false positives and 0 true ones on the live tree.
    """
    build(
        tmp_path,
        skill(
            "Read",
            "Do not edit, scaffold, or dispatch implementation.\nFor changes to skills, dispatch prompts, agents, or rules, obtain a reviewer.",
        ),
    )
    assert run(tmp_path).returncode == 0


def test_backticked_path_in_prose_is_not_a_command(tmp_path):
    build(
        tmp_path,
        skill("Read", "emitted by the FIND stage (`./reviewer-prompt.md`, six angles)"),
    )
    assert run(tmp_path).returncode == 0


def test_frontmatter_vocabulary_is_not_scanned(tmp_path):
    """A description legitimately says "dispatch prompts"; it must not trip the scan."""
    build(
        tmp_path,
        "---\nname: alpha\ndescription: Use for changed skills, dispatch prompts, agents.\nallowed-tools: Read\n---\n\nBody.\n",
    )
    assert run(tmp_path).returncode == 0


def test_prompt_payloads_are_out_of_scope(tmp_path):
    """A *prompt*.md is dispatched and runs under the SUBAGENT's grant, not the skill's."""
    (tmp_path / "skills" / "alpha").mkdir(parents=True)
    (tmp_path / "harness-manifest.json").write_text(json.dumps({"skills": ["alpha"]}))
    (tmp_path / "skills" / "alpha" / "SKILL.md").write_text(skill("Read", "Body."))
    (tmp_path / "skills" / "alpha" / "some-prompt.md").write_text(
        "Run `git diff HEAD~1`.\n"
    )
    assert run(tmp_path).returncode == 0


# ── structural ───────────────────────────────────────────────────────────────────────────


def test_reported_line_numbers_are_absolute(tmp_path):
    """Blanking frontmatter (not slicing it) keeps reported lines pointing at the real file."""
    body = "\n".join(["prose"] * 6 + ["Run `python3 x.py`."])
    build(tmp_path, skill("Read", body))
    result = run(tmp_path)
    # 5 frontmatter lines, a blank, 6 prose lines (7-12) -> the command is on line 13
    assert "SKILL.md:13" in result.stderr, result.stderr


def test_empty_register_fails_closed(tmp_path):
    (tmp_path / "harness-manifest.json").write_text(json.dumps({"skills": []}))
    result = run(tmp_path)
    assert result.returncode == 1
    assert "refusing to report clean" in result.stderr
