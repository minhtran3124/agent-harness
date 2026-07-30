"""Tests for scripts/check_simplify_adoption.py — run via pytest (wired into run-tests.sh).

Mirrors scripts/test_check_manifest.py's pattern: build a minimal, self-consistent synthetic
layout under tmp_path for each check, assert the clean fixture passes, then mutate one guard at
a time and assert the corresponding drift is reported (a mutant that kills nothing exposes a
vacuous check).
"""

import json
import re
from pathlib import Path

import pytest

import check_simplify_adoption as csa

CHECKER = Path(__file__).resolve().parent / "check_simplify_adoption.py"

SKILL_MD = """# subagent-driven-development

Execute waves.
  1. one read-only task reviewer per task
  2. required /simplify cleanup — see references/simplify-stage.md
  3. workflow-engine diffs — see references/review-chain.md
"""

STAGE_MD = """# Simplify stage

Reference stage doc.
"""

RESUME_MD = "# Resume\n"
REVIEW_CHAIN_MD = "# Review chain\n"
FINISHING_SKILL_MD = (
    "# finishing-a-development-branch\n\n"
    "python3 scripts/check_review_receipt.py <plan_dir> --require correctness,intent "
    "--require-audit-if <base> --require-simplify-if <base>\n"
)

POLICY_MD = """# Claude Code `/simplify` stage policy

The cleanup-only behavior is supported by Claude Code **2.1.154 or newer**. Older clients fail
closed.
"""

CHECKER_STUB = """MINIMUM_VERSION = (2, 1, 154)
TINY_SOURCE_LINE_THRESHOLD = 150
"""

RECEIPT_STUB = """def main(argv):
    parser.add_argument(
        "--require-simplify-if",
        default=None,
    )
"""

HOOK_STUB = """SIZE_THRESHOLD=""
case "$LANE_VAL" in
  tiny)   SIZE_THRESHOLD=150 ;;
  normal) SIZE_THRESHOLD=600 ;;
esac
"""

CLEAN_DOC = "# CLAUDE.md\n\nNo stale claims here.\n"


def build(root: Path) -> None:
    """Write a minimal, self-consistent simplify-stage layout under root."""
    (root / "rules").mkdir(parents=True, exist_ok=True)
    (root / "rules" / "simplify-stage.md").write_text(POLICY_MD, encoding="utf-8")

    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "scripts" / "check_claude_simplify.py").write_text(
        CHECKER_STUB, encoding="utf-8"
    )
    (root / "scripts" / "check_review_receipt.py").write_text(
        RECEIPT_STUB, encoding="utf-8"
    )

    (root / "hooks").mkdir(parents=True, exist_ok=True)
    (root / "hooks" / "risk-corroboration.sh").write_text(HOOK_STUB, encoding="utf-8")

    sdd = root / "skills" / "subagent-driven-development"
    (sdd / "references").mkdir(parents=True, exist_ok=True)
    (sdd / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
    (sdd / "references" / "simplify-stage.md").write_text(STAGE_MD, encoding="utf-8")
    (sdd / "references" / "resume.md").write_text(RESUME_MD, encoding="utf-8")
    (sdd / "references" / "review-chain.md").write_text(
        REVIEW_CHAIN_MD, encoding="utf-8"
    )

    finishing = root / "skills" / "finishing-a-development-branch"
    finishing.mkdir(parents=True, exist_ok=True)
    (finishing / "SKILL.md").write_text(FINISHING_SKILL_MD, encoding="utf-8")

    (root / "CLAUDE.md").write_text(CLEAN_DOC, encoding="utf-8")
    (root / "HARNESS.md").write_text(CLEAN_DOC, encoding="utf-8")
    (root / "skills" / "README.md").write_text(CLEAN_DOC, encoding="utf-8")

    (root / "harness-manifest.json").write_text(
        json.dumps(
            {
                "contracts": {
                    "simplify-stage-contract": {
                        "surface": [
                            "rules/simplify-stage.md",
                            "scripts/check_claude_simplify.py",
                        ],
                        "consumers": [
                            "skills/subagent-driven-development/references/simplify-stage.md",
                            "skills/subagent-driven-development/references/resume.md",
                            "skills/subagent-driven-development/references/review-chain.md",
                            "scripts/check_review_receipt.py",
                            "hooks/risk-corroboration.sh",
                            "skills/finishing-a-development-branch/SKILL.md",
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def mirror_to_claude(root: Path) -> None:
    """Copy every deployable target file into a matching .claude/ mirror."""
    claude = root / ".claude"
    for rel in (
        "rules/simplify-stage.md",
        "skills/subagent-driven-development/references/simplify-stage.md",
        "skills/subagent-driven-development/references/resume.md",
        "skills/subagent-driven-development/references/review-chain.md",
        "hooks/risk-corroboration.sh",
        "skills/finishing-a-development-branch/SKILL.md",
    ):
        src = root / rel
        dst = claude / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


# --- positive fixture -----------------------------------------------------------------


def test_clean_fixture_passes(tmp_path):
    build(tmp_path)
    assert csa.check(tmp_path) == 0


def test_real_repo_documentation_and_version_checks_pass():
    """The real repo's policy/version/receipt/hook wiring is consistent (no synthetic root).

    Deliberately does not assert the aggregate exit code — deployed-parity may legitimately
    report drift pre-deploy (scripts/deploy-harness.sh is a separate, later step). This test
    only pins the source-level checks that must always hold on this branch.
    """
    root = Path(__file__).resolve().parent.parent
    problems: list[str] = []
    csa._check_version_floor(root, problems)
    csa._check_receipt_flag(root, problems)
    csa._check_finish_gate(root, problems)
    csa._check_hook_threshold(root, problems)
    csa._check_documentation(root, problems)
    assert problems == []


def test_no_claude_mirror_skips_deployed_parity_gracefully(tmp_path, capsys):
    build(tmp_path)
    assert csa.check(tmp_path) == 0
    captured = capsys.readouterr()
    assert "skip" in (captured.out + captured.err).lower()


# --- policy / version floor -------------------------------------------------------------


def test_version_floor_mismatch_is_detected(tmp_path):
    build(tmp_path)
    (tmp_path / "scripts" / "check_claude_simplify.py").write_text(
        "MINIMUM_VERSION = (2, 1, 999)\nTINY_SOURCE_LINE_THRESHOLD = 150\n",
        encoding="utf-8",
    )
    assert csa.check(tmp_path) == 1


def test_version_floor_missing_policy_statement_is_detected(tmp_path):
    build(tmp_path)
    (tmp_path / "rules" / "simplify-stage.md").write_text(
        "# policy\n\nno version floor stated here.\n", encoding="utf-8"
    )
    assert csa.check(tmp_path) == 1


# --- ordering ----------------------------------------------------------------------------


def test_ordering_reversed_reference_is_detected(tmp_path):
    build(tmp_path)
    sdd_skill = tmp_path / "skills" / "subagent-driven-development" / "SKILL.md"
    text = sdd_skill.read_text(encoding="utf-8")
    a, b = "references/simplify-stage.md", "references/review-chain.md"
    text = text.replace(a, "__TMP__").replace(b, a).replace("__TMP__", b)
    sdd_skill.write_text(text, encoding="utf-8")
    assert csa.check(tmp_path) == 1


def test_ordering_missing_reference_is_detected(tmp_path):
    build(tmp_path)
    sdd_skill = tmp_path / "skills" / "subagent-driven-development" / "SKILL.md"
    sdd_skill.write_text("# subagent-driven-development\n\nno references here.\n")
    assert csa.check(tmp_path) == 1


# --- receipt --------------------------------------------------------------------------


def test_receipt_missing_require_simplify_if_flag_is_detected(tmp_path):
    build(tmp_path)
    (tmp_path / "scripts" / "check_review_receipt.py").write_text(
        "def main(argv):\n    pass\n", encoding="utf-8"
    )
    assert csa.check(tmp_path) == 1


# --- finish-gate ------------------------------------------------------------------------


def test_finish_gate_missing_require_simplify_if_flag_is_detected(tmp_path):
    build(tmp_path)
    (tmp_path / "skills" / "finishing-a-development-branch" / "SKILL.md").write_text(
        "# finishing-a-development-branch\n\nno gate here.\n", encoding="utf-8"
    )
    assert csa.check(tmp_path) == 1


def test_finish_gate_missing_file_is_detected(tmp_path):
    build(tmp_path)
    (tmp_path / "skills" / "finishing-a-development-branch" / "SKILL.md").unlink()
    assert csa.check(tmp_path) == 1


# --- hook threshold ---------------------------------------------------------------------


def test_hook_threshold_drift_is_detected(tmp_path):
    build(tmp_path)
    (tmp_path / "hooks" / "risk-corroboration.sh").write_text(
        'SIZE_THRESHOLD=""\ncase "$LANE_VAL" in\n  tiny)   SIZE_THRESHOLD=999 ;;\nesac\n',
        encoding="utf-8",
    )
    assert csa.check(tmp_path) == 1


# --- documentation staleness -------------------------------------------------------------


@pytest.mark.parametrize(
    "stale_sentence",
    [
        "Running /simplify is optional even on required scope.",
        "The /simplify stage owns correctness for the diff.",
    ],
)
def test_stale_documentation_claim_is_detected(tmp_path, stale_sentence):
    build(tmp_path)
    (tmp_path / "CLAUDE.md").write_text(
        CLEAN_DOC + stale_sentence + "\n", encoding="utf-8"
    )
    assert csa.check(tmp_path) == 1


def test_documentation_check_does_not_false_positive_on_unrelated_text(tmp_path):
    build(tmp_path)
    (tmp_path / "CLAUDE.md").write_text(
        CLEAN_DOC + "This optional flag has nothing to do with cleanup.\n",
        encoding="utf-8",
    )
    assert csa.check(tmp_path) == 0


# --- deployed parity --------------------------------------------------------------------


def test_deployed_parity_in_sync_passes(tmp_path):
    build(tmp_path)
    mirror_to_claude(tmp_path)
    assert csa.check(tmp_path) == 0


def test_deployed_parity_stale_hook_is_detected(tmp_path):
    build(tmp_path)
    mirror_to_claude(tmp_path)
    (tmp_path / "hooks" / "risk-corroboration.sh").write_text(
        HOOK_STUB + "# a wording change not yet deployed\n", encoding="utf-8"
    )
    assert csa.check(tmp_path) == 1


def test_deployed_parity_missing_mirrored_file_is_detected(tmp_path):
    build(tmp_path)
    mirror_to_claude(tmp_path)
    (tmp_path / ".claude" / "rules" / "simplify-stage.md").unlink()
    assert csa.check(tmp_path) == 1


# --- CLI -----------------------------------------------------------------------------


def test_cli_root_flag(tmp_path, capsys):
    build(tmp_path)
    rc = csa.main(["--root", str(tmp_path)])
    assert rc == 0


def test_cli_reports_problems_on_stderr(tmp_path, capsys):
    build(tmp_path)
    (tmp_path / "scripts" / "check_claude_simplify.py").write_text(
        "MINIMUM_VERSION = (9, 9, 9)\nTINY_SOURCE_LINE_THRESHOLD = 150\n",
        encoding="utf-8",
    )
    rc = csa.main(["--root", str(tmp_path)])
    assert rc == 1
    captured = capsys.readouterr()
    assert re.search(r"simplify-adoption:.*drift", captured.err)
