import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_claude_simplify.py"
BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
SPEC = importlib.util.spec_from_file_location("check_claude_simplify", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2.1.154", (2, 1, 154)),
        ("claude 2.1.220 (Claude Code)", (2, 1, 220)),
        ("Claude Code v3.0.0", (3, 0, 0)),
    ],
)
def test_parse_version_accepts_supported_client_shapes(raw, expected):
    assert MODULE.parse_version(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [None, "", "claude", "2.1", "2.1.154-beta.1", "v2.1.154 extra 9.9.9"],
)
def test_parse_version_rejects_missing_or_ambiguous_values(raw):
    assert MODULE.parse_version(raw) is None


@pytest.mark.parametrize(
    ("raw", "status"),
    [
        (None, "missing"),
        ("", "missing"),
        ("not-a-version", "malformed"),
        ("2.1.153", "too_old"),
        ("2.1.154", "supported"),
        ("2.2.0", "supported"),
    ],
)
def test_capability_has_inclusive_minimum_boundary(raw, status):
    assert MODULE.capability_status(raw)["status"] == status


def test_mutation_guard_minimum_version_constant_and_comparison():
    assert MODULE.MINIMUM_VERSION == (2, 1, 154)
    assert MODULE.capability_status("2.1.153")["status"] == "too_old"
    assert MODULE.capability_status("2.1.154")["status"] == "supported"


@pytest.mark.parametrize("lane", ["normal", "high-risk"])
def test_non_tiny_reviewable_source_is_required(lane):
    result = MODULE.evaluate_policy(
        lane=lane,
        base=BASE_SHA,
        head=HEAD_SHA,
        changed_paths=["scripts/tool.py"],
        numstat="1\t0\tscripts/tool.py\n",
        version="2.1.154",
    )
    assert result["required"] is True
    assert result["reason"] == "non_tiny_source_change"
    assert result["capability"]["status"] == "supported"
    assert result["target"] == f"{BASE_SHA}..{HEAD_SHA}"
    assert result["reviewable_paths"] == ["scripts/tool.py"]
    assert result["changed_source_lines"] == 1
    assert result["ok"] is True


def test_mutation_guard_tiny_threshold_is_strictly_greater_than_150():
    assert MODULE.TINY_SOURCE_LINE_THRESHOLD == 150
    at_boundary = MODULE.evaluate_policy(
        lane="tiny",
        base=BASE_SHA,
        head=HEAD_SHA,
        changed_paths=["app/main.py"],
        numstat="100\t50\tapp/main.py\n",
        version="2.1.154",
    )
    over_boundary = MODULE.evaluate_policy(
        lane="tiny",
        base=BASE_SHA,
        head=HEAD_SHA,
        changed_paths=["app/main.py"],
        numstat="100\t51\tapp/main.py\n",
        version="2.1.154",
    )
    assert (at_boundary["required"], at_boundary["reason"]) == (
        False,
        "tiny_source_change",
    )
    assert (over_boundary["required"], over_boundary["reason"]) == (
        True,
        "oversized_tiny_source_change",
    )


@pytest.mark.parametrize(
    ("path", "reason"),
    [
        ("docs/guide.md", "documentation_only"),
        ("specs/example/SUMMARY.md", "specs_bookkeeping_only"),
        ("evals/skills/demo/results/candidate.json", "evaluation_only"),
        ("vendor/acme/lib.py", "vendor_only"),
        ("generated/client.py", "generated_only"),
        (".claude/skills/demo/SKILL.md", "generated_only"),
        ("package-lock.json", "generated_only"),
    ],
)
def test_permitted_non_code_scope_is_skipped_with_bounded_reason(path, reason):
    result = MODULE.evaluate_policy(
        lane="high-risk",
        base=BASE_SHA,
        head=HEAD_SHA,
        changed_paths=[path],
        numstat=f"1000\t1000\t{path}\n",
        version=None,
    )
    assert result["required"] is False
    assert result["reason"] == reason
    assert result["capability"]["status"] == "missing"
    assert result["ok"] is True
    assert result["reviewable_paths"] == []
    assert result["changed_source_lines"] == 0


def test_mixed_exclusions_use_bounded_fallback_reason():
    result = MODULE.evaluate_policy(
        lane="normal",
        base=BASE_SHA,
        head=HEAD_SHA,
        changed_paths=["README.md", "vendor/acme.js"],
        numstat="2\t0\tREADME.md\n3\t0\tvendor/acme.js\n",
        version="2.1.154",
    )
    assert result["required"] is False
    assert result["reason"] == "excluded_only"
    assert result["reason"] in MODULE.POLICY_REASONS


def test_unknown_path_is_conservatively_reviewable():
    result = MODULE.evaluate_policy(
        lane="normal",
        base=BASE_SHA,
        head=HEAD_SHA,
        changed_paths=["config/runtime.custom"],
        numstat="1\t0\tconfig/runtime.custom\n",
        version="2.1.154",
    )
    assert result["required"] is True
    assert result["reviewable_paths"] == ["config/runtime.custom"]


def test_dependency_manifest_with_txt_suffix_is_not_mistaken_for_documentation():
    result = MODULE.evaluate_policy(
        lane="normal",
        base=BASE_SHA,
        head=HEAD_SHA,
        changed_paths=["requirements.txt"],
        numstat="1\t0\trequirements.txt\n",
        version="2.1.154",
    )
    assert result["required"] is True
    assert result["reviewable_paths"] == ["requirements.txt"]


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("build/output.py", "generated"),
        ("out/output.py", "generated"),
        ("dist/output.py", "generated"),
        ("coverage/output.py", "generated"),
        ("src/build/output.py", "reviewable"),
        ("src/out/output.py", "reviewable"),
        ("src/dist/output.py", "reviewable"),
        ("src/coverage/output.py", "reviewable"),
        ("build", "reviewable"),
        ("out", "reviewable"),
        ("dist", "reviewable"),
        ("coverage", "reviewable"),
    ],
)
def test_mutation_guard_ambiguous_generated_directories_are_root_anchored(path, expected):
    assert MODULE.classify_path(path) == expected


@pytest.mark.parametrize(
    "path",
    [
        "doc",
        "docs",
        "documentation",
        "specs",
        "evals",
        "vendor",
        "vendors",
        "third_party",
        "third-party",
        "node_modules",
        ".claude",
        "generated",
        "__pycache__",
    ],
)
def test_mutation_guard_directory_authority_singleton_files_are_reviewable(path):
    assert MODULE.classify_path(path) == "reviewable"


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("docs/guide", "documentation"),
        ("specs/example", "specs_bookkeeping"),
        ("evals/results/candidate.json", "evaluation"),
        ("vendor/acme", "vendor"),
        ("src/node_modules/acme", "vendor"),
        (".claude/settings.json", "generated"),
        ("src/generated/client.py", "generated"),
        ("src/__pycache__/module.pyc", "generated"),
    ],
)
def test_mutation_guard_directory_authority_requires_an_actual_subtree(path, expected):
    assert MODULE.classify_path(path) == expected


@pytest.mark.parametrize(
    "path",
    [
        " docs/guide.md",
        "docs/guide.md ",
        "docs\\guide.md",
        "./docs/guide.md",
        "docs//guide.md",
    ],
)
def test_mutation_guard_unsafe_path_spellings_are_rejected_not_coerced(path):
    with pytest.raises(ValueError):
        MODULE.classify_path(path)


def test_internal_posix_space_is_preserved_and_reviewable():
    result = MODULE.evaluate_policy(
        lane="normal",
        base=BASE_SHA,
        head=HEAD_SHA,
        changed_paths=["src/my file.py"],
        numstat="1\t0\tsrc/my file.py\n",
        version="2.1.154",
    )
    assert result["reviewable_paths"] == ["src/my file.py"]
    assert result["required"] is True


@pytest.mark.parametrize(
    ("changed_path", "numstat_path"),
    [
        ("docs/guide.md", " docs/guide.md"),
        ("docs/guide.md", "docs/guide.md "),
        ("docs/guide.md", "docs\\guide.md"),
    ],
)
def test_mutation_guard_changed_path_and_numstat_are_not_coerced_into_agreement(
    changed_path, numstat_path
):
    with pytest.raises(ValueError):
        MODULE.evaluate_policy(
            lane="normal",
            base=BASE_SHA,
            head=HEAD_SHA,
            changed_paths=[changed_path],
            numstat=f"1\t0\t{numstat_path}\n",
            version="2.1.154",
        )


def test_cli_rejects_carriage_return_that_could_be_coerced_as_a_line_ending(tmp_path):
    paths = tmp_path / "paths.txt"
    stats = tmp_path / "numstat.txt"
    paths.write_bytes(b"docs/guide.md\r\n")
    stats.write_bytes(b"1\t0\tdocs/guide.md\r\n")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--lane",
            "normal",
            "--base",
            BASE_SHA,
            "--head",
            HEAD_SHA,
            "--changed-paths-file",
            str(paths),
            "--numstat-file",
            str(stats),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "unsafe surrounding whitespace" in result.stderr


def test_only_reviewable_path_numstat_contributes_to_tiny_threshold():
    result = MODULE.evaluate_policy(
        lane="tiny",
        base=BASE_SHA,
        head=HEAD_SHA,
        changed_paths=["docs/large.md", "src/small.py"],
        numstat="500\t500\tdocs/large.md\n75\t75\tsrc/small.py\n",
        version="2.1.154",
    )
    assert result["changed_source_lines"] == 150
    assert result["required"] is False
    assert result["reason"] == "tiny_source_change"


@pytest.mark.parametrize("version", [None, "garbage", "2.1.153"])
def test_required_case_fails_closed_on_invalid_capability(version):
    result = MODULE.evaluate_policy(
        lane="normal",
        base=BASE_SHA,
        head=HEAD_SHA,
        changed_paths=["src/main.py"],
        numstat="1\t0\tsrc/main.py\n",
        version=version,
    )
    assert result["required"] is True
    assert result["ok"] is False
    assert result["error"] == "required_capability_unavailable"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"lane": "unexpected", "base": BASE_SHA, "head": HEAD_SHA},
        {"lane": "normal", "base": "", "head": HEAD_SHA},
        {"lane": "normal", "base": BASE_SHA, "head": ""},
        {"lane": "normal", "base": BASE_SHA, "head": BASE_SHA},
        {"lane": "normal", "base": "simplify", "head": HEAD_SHA},
        {"lane": "normal", "base": BASE_SHA, "head": "HEAD"},
        {"lane": "normal", "base": "a" * 39, "head": HEAD_SHA},
        {"lane": "normal", "base": BASE_SHA, "head": "b" * 41},
        {"lane": "normal", "base": "A" * 40, "head": HEAD_SHA},
        {"lane": "normal", "base": BASE_SHA, "head": "B" * 40},
        {"lane": "normal", "base": BASE_SHA, "head": "A" * 40},
    ],
)
def test_policy_rejects_invalid_lane_or_implicit_target(kwargs):
    with pytest.raises(ValueError):
        MODULE.evaluate_policy(
            changed_paths=[],
            numstat="",
            version="2.1.154",
            **kwargs,
        )


def test_rename_numstat_is_attributed_to_destination_path():
    result = MODULE.evaluate_policy(
        lane="tiny",
        base=BASE_SHA,
        head=HEAD_SHA,
        changed_paths=["src/new.py"],
        numstat="100\t51\tsrc/{old.py => new.py}\n",
        version="2.1.154",
    )
    assert result["required"] is True
    assert result["changed_source_lines"] == 151


def test_binary_reviewable_change_remains_reviewable_but_adds_no_line_count():
    result = MODULE.evaluate_policy(
        lane="normal",
        base=BASE_SHA,
        head=HEAD_SHA,
        changed_paths=["src/fixture.bin"],
        numstat="-\t-\tsrc/fixture.bin\n",
        version="2.1.154",
    )
    assert result["required"] is True
    assert result["changed_source_lines"] == 0


@pytest.mark.parametrize(
    ("changed_paths", "numstat"),
    [
        (
            ["docs/guide.md"],
            "1\t0\tdocs/guide.md\n100\t100\tsrc/hidden.py\n",
        ),
        (
            ["docs/guide.md", "src/hidden.py"],
            "1\t0\tdocs/guide.md\n",
        ),
    ],
)
def test_mutation_guard_changed_paths_and_numstat_sets_must_match(changed_paths, numstat):
    with pytest.raises(ValueError, match="changed paths and numstat disagree"):
        MODULE.evaluate_policy(
            lane="high-risk",
            base=BASE_SHA,
            head=HEAD_SHA,
            changed_paths=changed_paths,
            numstat=numstat,
            version="2.1.154",
        )


def test_cli_emits_json_and_fails_closed_for_required_old_client(tmp_path):
    paths = tmp_path / "paths.txt"
    stats = tmp_path / "numstat.txt"
    paths.write_text("src/main.py\n", encoding="utf-8")
    stats.write_text("1\t0\tsrc/main.py\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--lane",
            "normal",
            "--base",
            BASE_SHA,
            "--head",
            HEAD_SHA,
            "--changed-paths-file",
            str(paths),
            "--numstat-file",
            str(stats),
            "--claude-code-version",
            "2.1.153",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["required"] is True
    assert payload["capability"]["status"] == "too_old"


@pytest.mark.parametrize(
    ("base", "head"),
    [
        ("simplify", HEAD_SHA),
        (BASE_SHA, "HEAD"),
        ("a" * 39, HEAD_SHA),
        (BASE_SHA, "b" * 41),
        ("A" * 40, HEAD_SHA),
        (BASE_SHA, "B" * 40),
        (BASE_SHA, "A" * 40),
    ],
)
def test_cli_rejects_symbolic_or_malformed_targets(tmp_path, base, head):
    paths = tmp_path / "paths.txt"
    stats = tmp_path / "numstat.txt"
    paths.write_text("", encoding="utf-8")
    stats.write_text("", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--lane",
            "tiny",
            "--base",
            base,
            "--head",
            head,
            "--changed-paths-file",
            str(paths),
            "--numstat-file",
            str(stats),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "resolved lowercase 40-hex SHA" in result.stderr


@pytest.mark.parametrize("numstat", ["malformed\n", "x\t1\tsrc/main.py\n"])
def test_cli_rejects_malformed_numstat(tmp_path, numstat):
    paths = tmp_path / "paths.txt"
    stats = tmp_path / "numstat.txt"
    paths.write_text("src/main.py\n", encoding="utf-8")
    stats.write_text(numstat, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--lane",
            "normal",
            "--base",
            BASE_SHA,
            "--head",
            HEAD_SHA,
            "--changed-paths-file",
            str(paths),
            "--numstat-file",
            str(stats),
            "--claude-code-version",
            "2.1.154",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "malformed numstat" in result.stderr


def test_cli_requires_explicit_base_and_head(tmp_path):
    paths = tmp_path / "paths.txt"
    stats = tmp_path / "numstat.txt"
    paths.write_text("", encoding="utf-8")
    stats.write_text("", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--lane",
            "tiny",
            "--changed-paths-file",
            str(paths),
            "--numstat-file",
            str(stats),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2


def test_policy_self_test_command_passes():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--self-test-policy"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "simplify-policy: self-test passed" in result.stdout
