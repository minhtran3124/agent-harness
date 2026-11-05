"""Acceptance tests for #566: prune docs/adr to 12 records and renumber 0001-0012.

Black-box: the folder listing, file headings, published docs and a repo-wide reference scan.
AC2's PR-body half and AC7 (the full suite) cannot be checked from here; AC7 is the suite itself.
Run: python3 -m pytest tests/acceptance/test_adr_prune_566.py
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADR = ROOT / "docs/adr"
BASE = "749c6c6"  # commit the ticket branched from

# new number -> slug of the kept file (slug unchanged by the renumber)
KEPT = {
    "0001": "workflow-capabilities",
    "0002": "ship-workflow-real-run-findings",
    "0003": "verify-config-json-uses-a-loginenv-array-for-the-variable-na",
    "0004": "uat-ac-failure-marks-the-ticket-blocked-in-run-output",
    "0005": "infrastructure-failure-of-uat-does-not-fail-the-ticket",
    "0006": "a-fail-row-fails-uat-console-errors-are-report-only",
    "0007": "remove-techstacks-and-project-md-rules-from-repo-files",
    "0008": "merge-policy-design-gated-auto-merge-of-ticket-prs-into-feat",
    "0009": "merge-guard-fails-closed-unlike-every-other-harness-hook",
    "0010": "auto-merge-does-nothing-by-default-no-allow-rule-is-wired-an",
    "0011": "ask-only-for-the-one-merge-plain-form-case-mode-allowlist",
    "0012": "base-branch-merge-becomes-an-ask-prompt-not-a-deny",
}
OLD_KEPT = dict(zip(
    ["0001", "0002", "0005", "0006", "0007", "0009", "0010", "0108", "0109", "0111", "0129", "0130"],
    KEPT))
OLD_DELETED = (
    ["0003", "0004", "0008"] + [f"{n:04d}" for n in range(100, 108)] + ["0110", "0112", "0113", "0114"]
    + [f"{n:04d}" for n in range(123, 129)] + [f"{n:04d}" for n in range(131, 136)]
)
DELETED_SLUG_PREFIXES = [
    "0003-state-check-before-cleanup", "0004-branch-of-a-different-pr", "0008-uat-runs-serially",
    "0110-", "0112-", "0113-", "0114-", "0123-", "0124-", "0125-", "0126-", "0127-", "0128-",
    "0131-", "0132-", "0133-", "0134-", "0135-",
] + [f"{n:04d}-" for n in range(100, 108)]


def read(rel):
    return (ROOT / rel).read_text()


def adr_files():
    return sorted(p.name for p in ADR.iterdir())


def test_ac1_only_twelve_records_plus_readme_and_template():
    # Later ADRs (0013 and up) may be added; the pruned range 0001-0012 must stay exactly as kept.
    expected = sorted([f"{n}-{s}.md" for n, s in KEPT.items()] + ["README.md", "TEMPLATE.md"])
    names = adr_files()
    later = [n for n in names if re.match(r"(\d{4})-", n) and int(n[:4]) > 12]
    assert sorted(n for n in names if n not in later) == expected


def test_ac2_deleted_files_are_gone():
    assert len(OLD_DELETED) == 26
    names = adr_files()
    for prefix in DELETED_SLUG_PREFIXES:
        assert not [n for n in names if n.startswith(prefix)], prefix
    assert not [n for n in names if re.match(r"01\d\d-", n)]


def test_ac3_headings_match_new_number():
    for n, s in KEPT.items():
        text = (ADR / f"{n}-{s}.md").read_text()
        assert re.search(rf"^# {n}\. ", text, re.M), n


def test_ac3_internal_adr_references_resolve():
    valid = set(KEPT)
    for n, s in KEPT.items():
        text = (ADR / f"{n}-{s}.md").read_text()
        for line in text.splitlines():
            if re.search(r"superseded_by|supersedes|ADR ?\d{4}|adr/\d{4}", line, re.I):
                for num in re.findall(r"(?<!\d)(\d{4})(?!\d)", line):
                    if num.startswith(("0", "1")) and not re.match(r"20\d\d", num):
                        assert num in valid or num == "0000", f"{n}: {line}"


def test_ac3_new_0012_cites_0008_and_0009_not_old_numbers():
    text = (ADR / f"0012-{KEPT['0012']}.md").read_text()
    assert "0008" in text and "0009" in text
    assert "0108" not in text and "0109" not in text


def test_ac4_solutions_cite_adr_0007_with_path():
    path = "docs/adr/0007-remove-techstacks-and-project-md-rules-from-repo-files.md"
    for f in ("scaffold-template-instance-parity.md", "techstacks-project-owned-stack-profiles.md"):
        text = read(f"docs/solutions/harness/{f}")
        assert "ADR 0007" in text and path in text, f
        assert "ADR 0010" not in text and "adr/0010-remove" not in text, f


def test_ac4_hooks_doc_line_points_at_new_0010():
    lines = [l for l in read("docs/hooks.md").splitlines() if "not proven" in l]
    assert lines
    assert any(re.search(r"ADR 0010|adr/0010", l) for l in lines)
    assert not any("ADR 0007" in l for l in lines)


def test_ac4_recall_evals_uses_new_number():
    text = read("plugins/harness/skills/recall/evals/evals.json")
    assert "SUPERSEDED by ADR 0007 and techstacks/ does not exist" in text
    assert "SUPERSEDED by ADR 0010" not in text


def test_ac4_merge_guard_test_comment_uses_new_numbers():
    text = read("tests/hooks/merge-guard.test.sh")
    assert "ADR 0008, 0009" in text
    assert "ADR 0108, 0109" not in text


def test_ac5_every_adr_reference_points_at_an_existing_file():
    out = subprocess.run(
        ["grep", "-rnIE", r"adr/0[0-9]{3}|ADR ?0[0-9]{3}", ".",
         "--exclude-dir=.git", "--exclude-dir=specs", "--exclude-dir=tests", "--exclude=test_write_adrs.py"],
        cwd=ROOT, capture_output=True, text=True).stdout
    names = adr_files()
    bad = []
    for line in out.splitlines():
        for m in re.finditer(r"adr/(0\d{3})(-[\w.-]+\.md)?|ADR ?(0\d{3})", line):
            num = m.group(1) or m.group(3)
            if int(num) > 12:
                if m.group(2) and f"{num}{m.group(2)}" not in names:
                    bad.append(line)
            elif num not in KEPT:
                bad.append(line)
            elif m.group(2) and f"{num}{m.group(2)}" not in names:
                bad.append(line)
    assert not bad, bad[:10]


def _git_ok(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def run_logs_unchanged(root, base=BASE):
    """Existing run logs are not modified or deleted. New run dirs are allowed.
    When base is not in this clone (shallow or squash-merged), compare with the
    merge-base against the main branch; only when that is also missing, with HEAD."""
    ref = None
    if _git_ok(root, "cat-file", "-e", f"{base}^{{commit}}").returncode == 0:
        ref = base
    else:
        for main in ("github/main", "origin/main", "main"):
            mb = _git_ok(root, "merge-base", "HEAD", main)
            if mb.returncode == 0 and mb.stdout.strip():
                ref = mb.stdout.strip()
                break
    ref = ref or "HEAD"
    r = subprocess.run(["git", "diff", "--quiet", "--no-renames", "--diff-filter=MD", ref, "--",
                        "tests/evals/recall/runs"], cwd=root, capture_output=True)
    return r.returncode == 0


def test_ac5_recall_run_logs_unchanged():
    assert run_logs_unchanged(ROOT)


def test_ac5_run_logs_check_survives_missing_base_and_new_runs(tmp_path):
    def git(*a):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a],
                       cwd=tmp_path, check=True, capture_output=True)
    runs = tmp_path / "tests/evals/recall/runs/d1"
    runs.mkdir(parents=True)
    (runs / "a.md").write_text("a")
    git("init", "-q")
    git("add", ".")
    git("commit", "-qm", "x")
    (tmp_path / "tests/evals/recall/runs/d2").mkdir()
    (tmp_path / "tests/evals/recall/runs/d2/b.md").write_text("b")
    git("add", ".")
    assert run_logs_unchanged(tmp_path, base="deadbeef")
    assert run_logs_unchanged(tmp_path, base="HEAD")
    (runs / "a.md").write_text("changed")
    assert not run_logs_unchanged(tmp_path, base="deadbeef")


def test_ac5_run_logs_check_detects_committed_edit_when_base_missing(tmp_path):
    def git(*a):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a],
                       cwd=tmp_path, check=True, capture_output=True)
    runs = tmp_path / "tests/evals/recall/runs/d1"
    runs.mkdir(parents=True)
    (runs / "a.md").write_text("a")
    git("init", "-q", "-b", "main")
    git("add", ".")
    git("commit", "-qm", "base")
    git("checkout", "-q", "-b", "feat")
    (runs / "a.md").write_text("changed")
    git("add", ".")
    git("commit", "-qm", "edit a run log")
    assert not run_logs_unchanged(tmp_path, base="deadbeef")


def test_ac5_run_logs_check_detects_renamed_log(tmp_path):
    def git(*a):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a],
                       cwd=tmp_path, check=True, capture_output=True)
    runs = tmp_path / "tests/evals/recall/runs/d1"
    runs.mkdir(parents=True)
    (runs / "a.md").write_text("a log with enough content to be matched as a rename\n" * 5)
    git("init", "-q", "-b", "main")
    git("add", ".")
    git("commit", "-qm", "base")
    git("checkout", "-q", "-b", "feat")
    git("mv", "tests/evals/recall/runs/d1/a.md", "tests/evals/recall/runs/d1/moved.md")
    git("commit", "-qm", "move a run log")
    assert not run_logs_unchanged(tmp_path, base="deadbeef")


def test_ac6_readme_maps_all_38_old_numbers():
    text = read("docs/adr/README.md")
    lines = text.splitlines()

    def row(old):
        hits = [l for l in lines if re.match(rf"^\W*{old}(?!\d)", l)]
        assert hits, f"no map row for old {old}"
        return hits[0]

    for old, new in OLD_KEPT.items():
        r = row(old)
        assert new in r.replace(old, "", 1), (old, r)
        assert "deleted" not in r.lower(), (old, r)
    for old in OLD_DELETED:
        assert "deleted" in row(old).lower(), old
    assert re.search(r"old numbers?.*(PR|pull request).*(no longer|not) match|"
                     r"(PR|pull request).*old numbers?.*(no longer|not) match", text, re.I | re.S)


def test_map_row_0104_does_not_cite_script_without_refs():
    row = [l for l in read("docs/adr/README.md").splitlines() if l.startswith("| 0104 ")][0]
    assert "check_release_summary.py" not in row
    assert "fact-list-schema.md" in row
