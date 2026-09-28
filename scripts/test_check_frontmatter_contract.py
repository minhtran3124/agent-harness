"""Tests for scripts/check_frontmatter_contract.py — run via pytest (wired into run-tests.sh).

Every negative case asserts the checker actually BITES, because a gate that only ever gets a
passing fixture is indistinguishable from a gate that cannot fail.
"""

import json
import subprocess
import sys
from pathlib import Path

CHECKER = Path(__file__).resolve().parent / "check_frontmatter_contract.py"

MANIFEST = {"skills": ["alpha"], "agents": ["reviewer"]}

SKILL_OK = """---
name: alpha
description: Does the alpha thing. Use when the user asks for alpha.
allowed-tools: Read
---

# Alpha
"""

AGENT_OK = """---
name: reviewer
description: Reviews things.
---

# Reviewer
"""


def build(
    root: Path, skill: str = SKILL_OK, agent: str = AGENT_OK, manifest=None
) -> None:
    (root / "skills" / "alpha").mkdir(parents=True, exist_ok=True)
    (root / "agents").mkdir(parents=True, exist_ok=True)
    (root / "harness-manifest.json").write_text(
        json.dumps(MANIFEST if manifest is None else manifest)
    )
    (root / "skills" / "alpha" / "SKILL.md").write_text(skill)
    (root / "agents" / "reviewer.md").write_text(agent)


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
    assert "2 registered" in result.stdout


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
  two lines.
---

# Alpha
""",
    )
    result = run(tmp_path)
    assert result.returncode == 0, result.stderr


def test_no_frontmatter_fails(tmp_path):
    build(tmp_path, agent="# Reviewer\n\nNo frontmatter here.\n")
    result = run(tmp_path)
    assert result.returncode == 1
    assert "has no frontmatter block" in result.stderr
    assert "agents/reviewer.md" in result.stderr


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
    assert "registered as `alpha`" in result.stderr


def test_unregistered_non_agent_files_are_ignored(tmp_path):
    """The three agents/ files that are not agents need no allowlist — they are unregistered."""
    build(tmp_path)
    for name in ("README.md", "PROJECT.md", "PROJECT.template.md"):
        (tmp_path / "agents" / name).write_text("# not an agent\n")
    result = run(tmp_path)
    assert result.returncode == 0, result.stderr


def test_empty_register_fails_closed(tmp_path):
    """Checking nothing must not read as a pass."""
    build(tmp_path, manifest={"skills": [], "agents": []})
    result = run(tmp_path)
    assert result.returncode == 1
    assert "registers no skills or agents" in result.stderr


def test_missing_manifest_fails(tmp_path):
    build(tmp_path)
    (tmp_path / "harness-manifest.json").unlink()
    result = run(tmp_path)
    assert result.returncode == 1
    assert "not found" in result.stderr


def test_invalid_manifest_json_fails(tmp_path):
    build(tmp_path)
    (tmp_path / "harness-manifest.json").write_text("{not json")
    result = run(tmp_path)
    assert result.returncode == 1
    assert "invalid JSON" in result.stderr


def test_missing_file_is_left_to_check_manifest(tmp_path):
    """Presence drift is check_manifest.py's job; this checker must not double-report it."""
    build(tmp_path)
    (tmp_path / "skills" / "alpha" / "SKILL.md").unlink()
    result = run(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "1 registered" in result.stdout


def test_live_repo_passes():
    """The real tree must satisfy the contract this checker enforces."""
    root = Path(__file__).resolve().parent.parent
    result = run(root)
    assert result.returncode == 0, result.stderr
