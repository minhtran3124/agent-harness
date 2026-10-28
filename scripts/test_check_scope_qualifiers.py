import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("check_scope_qualifiers.py")


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def commit(repo, files, message):
    for rel, text in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def make_repo(tmp_path, base_files, head_files):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    base = commit(repo, base_files, "base")
    head = commit(repo, head_files, "head")
    return repo, base, head


def run(repo, base, head, cwd=None):
    proc = subprocess.run([sys.executable, str(SCRIPT), "--base", base, "--head", head],
                          cwd=cwd or repo, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def check(tmp_path, before, after, path="skills/x/SKILL.md"):
    repo, base, head = make_repo(tmp_path, {path: before}, {path: after})
    return run(repo, base, head)


def test_dropped_if_is_listed(tmp_path):
    out = check(tmp_path, "a\nStop if the plan is wrong.\nb\n", "a\nStop the plan.\nb\n")
    assert out == '- skills/x/SKILL.md:2: dropped "if": Stop if the plan is wrong.\n'


def test_word_kept_in_same_hunk_is_not_listed(tmp_path):
    out = check(tmp_path, "a\nStop if the plan is wrong.\nb\n", "a\nIf the plan is wrong, stop.\nb\n")
    assert out == "- none\n"


def test_capital_when_matches(tmp_path):
    out = check(tmp_path, "a\nWhen done, stop.\n", "a\nStop.\n")
    assert out == '- skills/x/SKILL.md:2: dropped "when": When done, stop.\n'


def test_commonly_does_not_match_only(tmp_path):
    out = check(tmp_path, "a\nThis is commonly true.\n", "a\nThis is true.\n")
    assert out == "- none\n"


def test_two_word_for_a_new_matches(tmp_path):
    out = check(tmp_path, "a\nFor a new file, write it.\n", "a\nWrite the file.\n")
    assert out == '- skills/x/SKILL.md:2: dropped "for a new": For a new file, write it.\n'


def test_non_prose_paths_are_ignored(tmp_path):
    repo, base, head = make_repo(
        tmp_path,
        {"docs/d.md": "Stop if wrong.\n", "skills/x/run.py": "# only if\n"},
        {"docs/d.md": "Stop.\n", "skills/x/run.py": "# done\n"},
    )
    assert run(repo, base, head) == ""


def test_long_removed_line_is_trimmed(tmp_path):
    long = "   Stop if " + "x" * 200 + "\n"
    out = check(tmp_path, "a\n" + long, "a\nStop.\n")
    assert out == f'- skills/x/SKILL.md:2: dropped "if": {long.strip()[:120]}\n'


def test_bad_ref_prints_unavailable_and_exits_zero(tmp_path):
    repo, base, _ = make_repo(tmp_path, {"skills/x/SKILL.md": "a\n"}, {"skills/x/SKILL.md": "b\n"})
    out = run(repo, base, "no-such-ref")
    assert out.startswith("scope-qualifiers: unavailable (")
    assert len(out.splitlines()) == 1


# Replay of the pilot's Step 6 cut: git diff -U0 87d204c dc867ed -- skills/intake/SKILL.md
STEP6_BEFORE = "6. For a new SUMMARY, use `templates/SUMMARY.template.md`. `### Intent` holds the pin\n"
STEP6_AFTER = "6. Write a new SUMMARY from `templates/SUMMARY.template.md`. `### Intent` holds the pin\n"


def test_pilot_step6_cut_is_listed(tmp_path):
    out = check(tmp_path, "intro\n" + STEP6_BEFORE + "end\n", "intro\n" + STEP6_AFTER + "end\n",
                path="skills/intake/SKILL.md")
    assert out == f'- skills/intake/SKILL.md:2: dropped "for a new": {STEP6_BEFORE.strip()}\n'


# Replay of the pilot's Step 1 split, hunk @@ -21,4 of
# git diff -U0 bb923dc f49a9d1 -- skills/intake/SKILL.md
STEP1_BEFORE = (
    "   `Status: approved` and identical to its last commit. Read intent.md if present: stop unless its header line (`Status:` above\n"
    "   the first `##`) is exactly `approved`; pin with\n"
    "   `git log -1 --format=%H --diff-filter=AM -- specs/<slug>/intent.md` (empty: stop); if\n"
    "   `git diff --exit-code <pin> -- specs/<slug>/intent.md` is non-zero, stop; ask the\n"
)
STEP1_AFTER = (
    "   `Status: approved` and identical to its last commit. Read intent.md if present. Stop unless\n"
    "   its header line (`Status:` above the first `##`) is exactly `approved`. Pin with\n"
    "   `git log -1 --format=%H --diff-filter=AM -- specs/<slug>/intent.md` (empty: stop). If\n"
    "   `git diff --exit-code <pin> -- specs/<slug>/intent.md` is non-zero, stop. Ask the\n"
)


DROP_BEFORE, DROP_AFTER = "a\nStop if the plan is wrong.\nb\n", "a\nStop the plan.\nb\n"


def check_with_config(tmp_path, key, value, path="skills/x/SKILL.md"):
    # The hostile setting goes in the temp repo's local config, never the user's config.
    repo, base, head = make_repo(tmp_path, {path: DROP_BEFORE}, {path: DROP_AFTER})
    git(repo, "config", key, value)
    return run(repo, base, head)


def test_color_ui_always_still_lists_drop(tmp_path):
    out = check_with_config(tmp_path, "color.ui", "always")
    assert out == '- skills/x/SKILL.md:2: dropped "if": Stop if the plan is wrong.\n'


def test_external_diff_driver_is_ignored(tmp_path):
    out = check_with_config(tmp_path, "diff.external", "true")
    assert out == '- skills/x/SKILL.md:2: dropped "if": Stop if the plan is wrong.\n'


def test_noprefix_still_names_each_file(tmp_path):
    repo, base, head = make_repo(
        tmp_path,
        {"rules/a.md": DROP_BEFORE, "skills/x/SKILL.md": DROP_BEFORE},
        {"rules/a.md": DROP_AFTER, "skills/x/SKILL.md": DROP_AFTER},
    )
    git(repo, "config", "diff.noprefix", "true")
    assert run(repo, base, head) == (
        '- rules/a.md:2: dropped "if": Stop if the plan is wrong.\n'
        '- skills/x/SKILL.md:2: dropped "if": Stop if the plan is wrong.\n'
    )


def test_path_with_space_has_no_trailing_tab(tmp_path):
    out = check(tmp_path, DROP_BEFORE, DROP_AFTER, path="skills/x/a b.md")
    assert out == '- skills/x/a b.md:2: dropped "if": Stop if the plan is wrong.\n'


def test_non_ascii_path_is_not_dropped(tmp_path):
    out = check(tmp_path, DROP_BEFORE, DROP_AFTER, path="skills/x/café.md")
    assert out == '- skills/x/café.md:2: dropped "if": Stop if the plan is wrong.\n'


def test_ascii_stdout_encoding_still_exits_zero(tmp_path):
    repo, base, head = make_repo(tmp_path, {"skills/x/SKILL.md": "a\nStop if café.\n"},
                                 {"skills/x/SKILL.md": "a\nStop.\n"})
    env = {**os.environ, "PYTHONIOENCODING": "ascii"}
    proc = subprocess.run([sys.executable, str(SCRIPT), "--base", base, "--head", head],
                          cwd=repo, capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith('- skills/x/SKILL.md:2: dropped "if": Stop if caf')


def test_non_utf8_name_does_not_hide_other_prose(tmp_path):
    repo, base, _ = make_repo(tmp_path, {"skills/x/SKILL.md": DROP_BEFORE}, {"README.txt": "x\n"})
    try:
        (repo / os.fsdecode(b"bad-\xff.txt")).write_text("x\n", encoding="utf-8")
    except (OSError, UnicodeError):
        pytest.skip("filesystem rejects a non-UTF-8 file name")
    head = commit(repo, {"skills/x/SKILL.md": DROP_AFTER}, "head2")
    assert run(repo, base, head) == '- skills/x/SKILL.md:2: dropped "if": Stop if the plan is wrong.\n'


def test_closed_stdout_still_exits_zero(tmp_path):
    repo, base, head = make_repo(tmp_path, {"skills/x/SKILL.md": DROP_BEFORE},
                                 {"skills/x/SKILL.md": DROP_AFTER})
    proc = subprocess.run([sys.executable, str(SCRIPT), "--base", base, "--head", head],
                          cwd=repo, stderr=subprocess.PIPE, text=True, preexec_fn=lambda: os.close(1))
    assert proc.returncode == 0, proc.stderr


def test_inter_hunk_context_config_does_not_merge_hunks(tmp_path):
    before = "Stop if wrong.\nx\ny\nz\nKeep this.\n"
    after = "Stop.\nx\ny\nz\nKeep this if ok.\n"
    repo, base, head = make_repo(tmp_path, {"skills/x/SKILL.md": before}, {"skills/x/SKILL.md": after})
    git(repo, "config", "diff.interHunkContext", "5")
    assert run(repo, base, head) == '- skills/x/SKILL.md:1: dropped "if": Stop if wrong.\n'


def test_subdirectory_cwd_lists_same_drops(tmp_path):
    repo, base, head = make_repo(tmp_path, {"skills/x/SKILL.md": DROP_BEFORE},
                                 {"skills/x/SKILL.md": DROP_AFTER})
    want = '- skills/x/SKILL.md:2: dropped "if": Stop if the plan is wrong.\n'
    assert run(repo, base, head) == want
    assert run(repo, base, head, cwd=repo / "skills" / "x") == want
    git(repo, "config", "diff.relative", "true")
    assert run(repo, base, head, cwd=repo / "skills" / "x") == want


def test_literal_pathspecs_env_still_lists_drop(tmp_path):
    repo, base, head = make_repo(tmp_path, {"skills/x/SKILL.md": DROP_BEFORE},
                                 {"skills/x/SKILL.md": DROP_AFTER})
    env = {**os.environ, "GIT_LITERAL_PATHSPECS": "1"}
    proc = subprocess.run([sys.executable, str(SCRIPT), "--base", base, "--head", head],
                          cwd=repo / "skills", capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == '- skills/x/SKILL.md:2: dropped "if": Stop if the plan is wrong.\n'


def test_pilot_step1_split_is_not_listed_known_limit(tmp_path):
    # Known limit: the split moved sentences out of the condition's scope, but every
    # condition word survives in an added line of the same hunk, so nothing is listed.
    out = check(tmp_path, "intro\n" + STEP1_BEFORE + "end\n", "intro\n" + STEP1_AFTER + "end\n",
                path="skills/intake/SKILL.md")
    assert out == "- none\n"
