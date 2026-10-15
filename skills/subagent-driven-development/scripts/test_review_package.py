import importlib.util
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("review_package.py")
SPEC = importlib.util.spec_from_file_location("review_package", SCRIPT)
assert SPEC and SPEC.loader
review_package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review_package)

BAD = "We should probably utilize this; it is good.\n"
GOOD = "Do the test.\n"


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


def run_package(repo, base, head, monkeypatch, tmp_path):
    out = tmp_path / "pkg.md"
    monkeypatch.chdir(repo)
    monkeypatch.setattr(sys, "argv", ["review_package.py", "--base", base, "--head", head, "--output", str(out)])
    assert review_package.main() == 0
    return out.read_text(encoding="utf-8")


def hard(text):
    return review_package.lint_hard_count(text)


def test_changed_prose_file_shows_base_and_head_counts(tmp_path, monkeypatch):
    repo, base, head = make_repo(
        tmp_path,
        {"skills/x/SKILL.md": BAD, "other/notes.md": BAD},
        {"skills/x/SKILL.md": GOOD, "other/notes.md": GOOD},
    )
    payload = run_package(repo, base, head, monkeypatch, tmp_path)
    assert "## Diff\n" in payload
    section = payload.split("## STE lint\n", 1)[1].split("\n## Scope qualifiers\n", 1)[0]
    assert payload.index("## Diff\n") < payload.index("## STE lint\n")
    assert f"- skills/x/SKILL.md: base: {hard(BAD)}, head: {hard(GOOD)}" in section
    assert hard(BAD) > hard(GOOD)
    assert "other/notes.md" not in section


def test_new_file_shows_base_new(tmp_path, monkeypatch):
    repo, base, head = make_repo(
        tmp_path, {"README.txt": "x\n"}, {"rules/new.md": BAD, "agents/a.md": GOOD}
    )
    section = run_package(repo, base, head, monkeypatch, tmp_path).split("## STE lint\n", 1)[1].split("\n## Scope qualifiers\n", 1)[0]
    assert f"- rules/new.md: base: new, head: {hard(BAD)}" in section
    assert f"- agents/a.md: base: new, head: {hard(GOOD)}" in section


def test_synonym_rotation_does_not_raise_head_count(tmp_path, monkeypatch):
    rotated = "Check the config file. Then verify the output.\n"
    repo, base, head = make_repo(
        tmp_path,
        {"skills/x/SKILL.md": "Check the config file. Then check the output.\n"},
        {"skills/x/SKILL.md": rotated},
    )
    section = run_package(repo, base, head, monkeypatch, tmp_path).split("## STE lint\n", 1)[1].split("\n## Scope qualifiers\n", 1)[0]
    assert "- skills/x/SKILL.md: base: 0, head: 0" in section


def test_no_changed_prose_file_means_no_section(tmp_path, monkeypatch):
    repo, base, head = make_repo(
        tmp_path, {"skills/x/run.py": "a = 1\n"}, {"skills/x/run.py": "a = 2\n", "docs/d.md": BAD}
    )
    assert "## STE lint" not in run_package(repo, base, head, monkeypatch, tmp_path)


def test_broken_linter_writes_unavailable_line(tmp_path, monkeypatch):
    repo, base, head = make_repo(tmp_path, {"skills/x/SKILL.md": GOOD}, {"skills/x/SKILL.md": BAD})
    broken = tmp_path / "broken-lint.py"
    broken.write_text("import sys\nsys.exit(3)\n", encoding="utf-8")
    monkeypatch.setattr(review_package, "STE_LINT", broken)
    payload = run_package(repo, base, head, monkeypatch, tmp_path)
    section = payload.split("## STE lint\n", 1)[1].split("\n## Scope qualifiers\n", 1)[0].strip()
    assert section.startswith("ste-lint: unavailable (")
    assert len(section.splitlines()) == 1


def test_missing_linter_writes_unavailable_line(tmp_path, monkeypatch):
    repo, base, head = make_repo(tmp_path, {"skills/x/SKILL.md": GOOD}, {"skills/x/SKILL.md": BAD})
    monkeypatch.setattr(review_package, "STE_LINT", tmp_path / "absent.py")
    section = run_package(repo, base, head, monkeypatch, tmp_path).split("## STE lint\n", 1)[1].split("\n## Scope qualifiers\n", 1)[0].strip()
    assert section.startswith("ste-lint: unavailable (")
    assert len(section.splitlines()) == 1


def test_hanging_linter_writes_unavailable_line(tmp_path, monkeypatch):
    repo, base, head = make_repo(tmp_path, {"skills/x/SKILL.md": GOOD}, {"skills/x/SKILL.md": BAD})
    hang = tmp_path / "hang-lint.py"
    hang.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
    monkeypatch.setattr(review_package, "STE_LINT", hang)
    monkeypatch.setattr(review_package, "LINT_TIMEOUT", 0.5)
    section = run_package(repo, base, head, monkeypatch, tmp_path).split("## STE lint\n", 1)[1].split("\n## Scope qualifiers\n", 1)[0].strip()
    assert section.startswith("ste-lint: unavailable (")
    assert len(section.splitlines()) == 1


def test_multiline_error_text_stays_on_one_line(tmp_path, monkeypatch):
    repo, base, head = make_repo(tmp_path, {"skills/x/SKILL.md": GOOD}, {"skills/x/SKILL.md": BAD})

    def fail(text):
        raise RuntimeError("first line\nsecond line\n")

    monkeypatch.setattr(review_package, "lint_hard_count", fail)
    section = run_package(repo, base, head, monkeypatch, tmp_path).split("## STE lint\n", 1)[1].split("\n## Scope qualifiers\n", 1)[0].strip()
    assert section == "ste-lint: unavailable (first line second line)"


def test_undecodable_linter_output_writes_unavailable_line(tmp_path, monkeypatch):
    repo, base, head = make_repo(tmp_path, {"skills/x/SKILL.md": GOOD}, {"skills/x/SKILL.md": BAD})
    raw = tmp_path / "raw-lint.py"
    raw.write_text("import sys\nsys.stdout.buffer.write(b'\\xff\\xfe\\xfa')\n", encoding="utf-8")
    monkeypatch.setattr(review_package, "STE_LINT", raw)
    section = run_package(repo, base, head, monkeypatch, tmp_path).split("## STE lint\n", 1)[1].split("\n## Scope qualifiers\n", 1)[0].strip()
    assert section.startswith("ste-lint: unavailable (")
    assert len(section.splitlines()) == 1


def test_scope_qualifier_section_follows_ste_lint(tmp_path, monkeypatch):
    repo, base, head = make_repo(
        tmp_path, {"skills/x/SKILL.md": "a\nStop if wrong.\n"}, {"skills/x/SKILL.md": "a\nStop.\n"}
    )
    payload = run_package(repo, base, head, monkeypatch, tmp_path)
    assert payload.index("## STE lint\n") < payload.index("## Scope qualifiers\n")
    section = payload.split("## Scope qualifiers\n", 1)[1].strip()
    assert section == '- skills/x/SKILL.md:2: dropped "if": Stop if wrong.'


def test_missing_scope_module_writes_unavailable_line(tmp_path, monkeypatch):
    repo, base, head = make_repo(tmp_path, {"skills/x/SKILL.md": GOOD}, {"skills/x/SKILL.md": BAD})
    monkeypatch.setattr(review_package, "SCOPE_QUALIFIERS", tmp_path / "absent.py")
    section = run_package(repo, base, head, monkeypatch, tmp_path).split("## Scope qualifiers\n", 1)[1].strip()
    assert section.startswith("scope-qualifiers: unavailable (")
    assert len(section.splitlines()) == 1


def test_no_changed_prose_means_no_scope_section(tmp_path, monkeypatch):
    repo, base, head = make_repo(
        tmp_path, {"skills/x/run.py": "a = 1\n"}, {"skills/x/run.py": "a = 2\n", "docs/d.md": BAD}
    )
    monkeypatch.setattr(review_package, "SCOPE_QUALIFIERS", tmp_path / "absent.py")
    assert "## Scope qualifiers" not in run_package(repo, base, head, monkeypatch, tmp_path)
