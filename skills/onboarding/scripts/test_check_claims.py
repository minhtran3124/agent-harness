from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).with_name("check_claims.py")
SOURCE = "alpha\nbeta\ngamma\ndelta\n"


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def run(repo, *args):
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=repo, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip().splitlines()


def lines_version(text, a, b):
    chosen = "\n".join(text.split("\n")[a - 1:b]) + "\n"
    return f"repo-lines-v1:sha256:{hashlib.sha256(chosen.encode()).hexdigest()}:bWV0YQ"


def file_version(text):
    return f"repo-file-v1:sha256:{hashlib.sha256(text.encode()).hexdigest()}"


def make_repo(tmp_path, evidence, page="enforcement/gate.md"):
    """Build a repo with src/a.txt, one wiki page, and one claim per evidence list."""
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    git(repo, "init", "-q")
    (repo / "src" / "a.txt").write_text(SOURCE, encoding="utf-8")
    page_path = repo / "openwiki" / page
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text("# Page\n", encoding="utf-8")
    claims_path = repo / "openwiki" / ".claims" / Path(page).with_suffix(".json")
    claims_path.parent.mkdir(parents=True, exist_ok=True)
    claims = [{"statement": f"claim {i}", "evidence": ev} for i, ev in enumerate(evidence)]
    claims_path.write_text(json.dumps({"schemaVersion": 1, "claims": claims}), encoding="utf-8")
    return repo


def lines_ev(a, b, text=SOURCE, path="src/a.txt"):
    return {"resource": f"repo://{path}#L{a}-L{b}", "version": lines_version(text, a, b)}


def file_ev(text=SOURCE, path="src/a.txt"):
    return {"resource": f"repo://{path}", "version": file_version(text)}


def test_matching_lines_give_ok(tmp_path):
    repo = make_repo(tmp_path, [[lines_ev(2, 3)], [lines_ev(1, 4)]])
    code, out = run(repo, "enforcement/gate.md")
    assert code == 0
    assert out == ["ok src/a.txt#L2-L3 claim 0", "ok src/a.txt#L1-L4 claim 1"]


def test_edited_line_gives_stale(tmp_path):
    repo = make_repo(tmp_path, [[lines_ev(2, 3)]])
    (repo / "src" / "a.txt").write_text("alpha\nBETA\ngamma\ndelta\n", encoding="utf-8")
    code, out = run(repo, "enforcement/gate.md")
    assert code == 1
    assert out == ["stale src/a.txt#L2-L3 claim 0"]


def test_whole_file_ok_and_edited(tmp_path):
    repo = make_repo(tmp_path, [[file_ev()]])
    assert run(repo, "enforcement/gate.md") == (0, ["ok src/a.txt claim 0"])
    (repo / "src" / "a.txt").write_text(SOURCE + "epsilon\n", encoding="utf-8")
    assert run(repo, "enforcement/gate.md") == (1, ["stale src/a.txt claim 0"])


def test_deleted_file_gives_missing(tmp_path):
    repo = make_repo(tmp_path, [[lines_ev(1, 2)], [file_ev()]])
    (repo / "src" / "a.txt").unlink()
    code, out = run(repo, "enforcement/gate.md")
    assert code == 1
    assert out == ["missing src/a.txt#L1-L2 claim 0", "missing src/a.txt claim 1"]


def test_range_past_end_gives_missing(tmp_path):
    repo = make_repo(tmp_path, [[{"resource": "repo://src/a.txt#L3-L9", "version": lines_version(SOURCE, 3, 9)}]])
    code, out = run(repo, "enforcement/gate.md")
    assert code == 1
    assert out == ["missing src/a.txt#L3-L9 claim 0"]


def test_unknown_prefix_gives_unknown(tmp_path):
    repo = make_repo(tmp_path, [[{"resource": "repo://src/a.txt", "version": "repo-blob-v9:sha256:00"}]])
    code, out = run(repo, "enforcement/gate.md")
    assert code == 1
    assert out == ["unknown src/a.txt claim 0"]


def test_claim_takes_worst_evidence_result(tmp_path):
    repo = make_repo(tmp_path, [[lines_ev(1, 1), {"resource": "repo://src/gone.txt", "version": file_version("x")}]])
    code, out = run(repo, "enforcement/gate.md")
    assert code == 1
    assert out[0].startswith("missing ")


def test_root_page_quickstart(tmp_path):
    repo = make_repo(tmp_path, [[lines_ev(1, 1)]], page="quickstart.md")
    assert run(repo, "quickstart.md") == (0, ["ok src/a.txt#L1-L1 claim 0"])


def test_no_wiki_page_mode_exits_2(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    code, _ = run(repo, "quickstart.md")
    assert code == 2


def test_missing_claims_file_exits_3(tmp_path):
    repo = make_repo(tmp_path, [[lines_ev(1, 1)]])
    (repo / "openwiki" / ".claims" / "enforcement" / "gate.json").unlink()
    code, _ = run(repo, "enforcement/gate.md")
    assert code == 3


def test_missing_page_exits_4(tmp_path):
    repo = make_repo(tmp_path, [[lines_ev(1, 1)]])
    assert run(repo, "enforcement/other.md")[0] == 4
    (repo / "openwiki" / ".claims" / "enforcement" / "gate.json").unlink()
    (repo / "openwiki" / "enforcement" / "gate.md").unlink()
    assert run(repo, "enforcement/gate.md")[0] == 4


# The page exit codes below are copied into the "Each page" table of SKILL.md. This drift test keeps
# that copy complete and in step with the script.
PAGE_CODES = {"0", "1", "2", "3", "4"}


def table_rows(text, heading):
    section = text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]
    rows = [line.split("|")[1].strip() for line in section.splitlines() if line.startswith("| ")]
    return [row for row in rows if row[:1].isdigit()]


def test_skill_exit_tables_match_script_codes():
    text = SCRIPT.parents[1].joinpath("SKILL.md").read_text()
    assert {row.split()[0] for row in table_rows(text, "Each page")} == PAGE_CODES
