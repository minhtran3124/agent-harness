"""Tests for scripts/check_frontmatter_contract.py — run via pytest (wired into run-tests.sh).

Every negative case asserts the checker actually BITES, because a gate that only ever gets a
passing fixture is indistinguishable from a gate that cannot fail.
"""

import subprocess
import sys
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_frontmatter_contract.py"

SKILL_OK = """---
name: alpha
description: Does the alpha thing. Use when the user asks for alpha.
allowed-tools: Read
---

# Alpha
"""

AGENT_OK = """---
name: advisor
description: Advises on things. Use when a second opinion is needed.
---

# Advisor
"""


def build(root: Path, skill: str = SKILL_OK, agent: str = AGENT_OK) -> None:
    (root / "skills" / "alpha").mkdir(parents=True, exist_ok=True)
    (root / "agents").mkdir(parents=True, exist_ok=True)
    (root / "skills" / "alpha" / "SKILL.md").write_text(skill)
    (root / "agents" / "advisor.md").write_text(agent)


def run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--root", str(root)],
        capture_output=True,
        text=True,
    )


def test_clean_tree_passes(tmp_path):
    build(tmp_path)
    result = run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "2 skill(s)/agent(s)" in result.stdout


def test_missing_description_fails(tmp_path):
    build(
        tmp_path,
        skill=SKILL_OK.replace(
            "description: Does the alpha thing. Use when the user asks for alpha.\n", ""
        ),
    )
    result = run(tmp_path)
    assert result.returncode == 1
    assert "missing `description:`" in result.stderr
    assert "skills/alpha/SKILL.md" in result.stderr


def test_empty_description_fails(tmp_path):
    build(
        tmp_path,
        skill=SKILL_OK.replace(
            "description: Does the alpha thing. Use when the user asks for alpha.",
            "description:",
        ),
    )
    result = run(tmp_path)
    assert result.returncode == 1
    assert "empty `description:`" in result.stderr


def test_quoted_empty_description_fails(tmp_path):
    """`description: ""` satisfies a grep for a non-empty value but is still empty."""
    build(
        tmp_path,
        skill=SKILL_OK.replace(
            "description: Does the alpha thing. Use when the user asks for alpha.",
            'description: ""',
        ),
    )
    result = run(tmp_path)
    assert result.returncode == 1
    assert "empty `description:`" in result.stderr


def test_block_scalar_description_passes(tmp_path):
    """A `>`-folded description is a real value, not an empty one."""
    build(
        tmp_path,
        skill="""---
name: alpha
description: >
  Does the alpha thing across
  two lines. Use when asked.
---

# Alpha
""",
    )
    result = run(tmp_path)
    assert result.returncode == 0, result.stderr


def test_description_without_cue_fails(tmp_path):
    build(
        tmp_path,
        skill=SKILL_OK.replace(
            "description: Does the alpha thing. Use when the user asks for alpha.",
            "description: Does the alpha thing.",
        ),
    )
    result = run(tmp_path)
    assert result.returncode == 1
    assert "no trigger cue" in result.stderr
    assert "skills/alpha/SKILL.md" in result.stderr


def test_cue_is_case_insensitive_and_word_bounded(tmp_path):
    passing = [
        "description: Does alpha. Use it for alpha.",
        "description: Does alpha. WHEN alpha is needed.",
        "description: does alpha. when needed.",
        "description: >\n  Does alpha\n  across lines. Use when asked.",
    ]
    for desc in passing:
        build(tmp_path, skill=f"---\nname: alpha\n{desc}\n---\n\n# Alpha\n")
        result = run(tmp_path)
        assert result.returncode == 0, (desc, result.stderr)
    failing = [
        "description: Helps with reuse of alpha.",
        "description: Runs whenever alpha changes.",
        "description: Serves the user alpha.",
    ]
    for desc in failing:
        build(tmp_path, skill=f"---\nname: alpha\n{desc}\n---\n\n# Alpha\n")
        result = run(tmp_path)
        assert result.returncode == 1, desc
        assert "no trigger cue" in result.stderr, desc


def test_no_frontmatter_fails(tmp_path):
    build(tmp_path, agent="# Advisor\n\nNo frontmatter here.\n")
    result = run(tmp_path)
    assert result.returncode == 1
    assert "has no frontmatter block" in result.stderr
    assert "agents/advisor.md" in result.stderr


def test_unterminated_frontmatter_fails(tmp_path):
    """An unclosed block must not let a body line masquerade as frontmatter."""
    build(tmp_path, skill="---\nname: alpha\n\n# Alpha\n\ndescription: in the body\n")
    result = run(tmp_path)
    assert result.returncode == 1
    assert "has no frontmatter block" in result.stderr


def test_name_mismatch_fails(tmp_path):
    build(tmp_path, skill=SKILL_OK.replace("name: alpha", "name: beta"))
    result = run(tmp_path)
    assert result.returncode == 1
    assert "expected `alpha`" in result.stderr


def test_unregistered_non_agent_files_are_ignored(tmp_path):
    """The agents/ README that is not an agent needs no allowlist — they are not agents."""
    build(tmp_path)
    for name in ("README.md",):
        (tmp_path / "agents" / name).write_text("# not an agent\n")
    result = run(tmp_path)
    assert result.returncode == 0, result.stderr


def test_empty_tree_fails_closed(tmp_path):
    """Checking nothing must not read as a pass."""
    result = run(tmp_path)
    assert result.returncode == 1
    assert "refusing to report clean" in result.stderr


def test_unlisted_agent_file_is_still_checked(tmp_path):
    """The disk is the registry: any agents/*.md except README is an agent."""
    build(tmp_path)
    (tmp_path / "agents" / "extra.md").write_text("# no frontmatter\n")
    result = run(tmp_path)
    assert result.returncode == 1
    assert "agents/extra.md has no frontmatter" in result.stderr


def test_deleted_skill_is_no_longer_checked(tmp_path):
    build(tmp_path)
    (tmp_path / "skills" / "alpha" / "SKILL.md").unlink()
    result = run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "1 skill(s)/agent(s)" in result.stdout


def test_live_repo_passes():
    """The real tree must satisfy the contract this checker enforces."""
    root = Path(__file__).resolve().parent.parent / "plugins" / "harness"
    result = run(root)
    assert result.returncode == 0, result.stderr
