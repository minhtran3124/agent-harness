"""Acceptance tests for #567: one decision store per record type (decisions in docs/adr/,
lessons in docs/solutions/).

Black-box: write_adrs.py through its command line; the published docs, folder listings and the
repo's own check scripts. Run: python3 -m pytest tests/acceptance/test_adr_store_567.py
"""
import collections
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "plugins/harness/scripts/write_adrs.py"
SK = ROOT / "plugins/harness/skills"
ADR = ROOT / "docs/adr"
SOL = ROOT / "docs/solutions"
BASE = "ccf0b7a"  # commit the ticket branched from

MOVED = [
    "harness-bootstrap/meta-repo-signal-remapping-decisions.md",
    "harness/gap-closure-decisions.md",
    "harness/gate-mode-as-data-decisions.md",
    "harness/resync-protected-files-decisions.md",
    "harness/review-model-diversity-dropped-decisions.md",
    "harness/ste100-adoption-decisions.md",
    "scripts/bash-empty-array-and-jsonl-parsing-gotchas-decisions.md",
    "harness/consumer-risk-modes-index-safe.md",
]
STAY = ["harness/adr-creation-review.md", "harness/techstacks-project-owned-stack-profiles.md"]
# source record dates, one per decision (confirmed_at of each source file)
EXPECTED_DATES = collections.Counter(
    ["2026-07-17"] * 4 + ["2026-07-23"] * 4 + ["2026-07-10"] * 3 + ["2026-10-02"]
    + ["2026-10-15"] * 4 + ["2026-07-04"] + ["2026-08-06"]
)


def dec(**kw):
    d = {
        "ticket": 567, "stage": "design", "title": "Use a queue", "context": "ctx of queue",
        "options": ["a", "b"], "decision": "a", "why": "w", "consequences": "q",
        "how_to_reverse": "git revert", "confidence": "medium", "needs_review": False,
        "adr": True, "decided_by": "claude",
    }
    d.update(kw)
    return d


def setup(tmp_path, decisions):
    adr = tmp_path / "adr"
    adr.mkdir()
    (adr / "README.md").write_text("r")
    (adr / "TEMPLATE.md").write_text((ADR / "TEMPLATE.md").read_text())
    inp = tmp_path / "in.json"
    inp.write_text(json.dumps({"run": "r", "decisions": decisions}))
    return adr, inp


def run(adr, inp, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(inp), "--adr-dir", str(adr), *extra],
        capture_output=True, text=True,
    )


def front(path):
    text = Path(path).read_text()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, f"no frontmatter in {path}"
    return dict(
        (k.strip(), v.strip()) for k, v in (l.split(":", 1) for l in m.group(1).splitlines() if ":" in l)
    )


def new_adrs():
    out = []
    for p in sorted(ADR.glob("[0-9][0-9][0-9][0-9]-*.md")):
        if int(p.name[:4]) >= 13:
            out.append(p)
    return out


def sh(*cmd):
    return subprocess.run(list(cmd), cwd=ROOT, capture_output=True, text=True)


# ---------- AC1 ----------
def test_ac1_valid_date_is_kept(tmp_path):
    adr, inp = setup(tmp_path, [dec(date="2026-07-17")])
    r = run(adr, inp)
    assert r.returncode == 0, r.stderr
    f = next(adr.glob("0001-*.md"))
    assert front(f)["date"] == "2026-07-17"


def test_ac1_invalid_date_exits_2(tmp_path):
    for i, bad in enumerate(["2026-13-01", "17/07/2026", "not-a-date", "2026-02-30", 20260717]):
        d = tmp_path / f"c{i}"
        d.mkdir()
        adr, inp = setup(d, [dec(date=bad)])
        r = run(adr, inp)
        assert r.returncode == 2, (bad, r.returncode, r.stderr)
        assert "write_adrs:" in r.stderr
        assert not list(adr.glob("0001-*.md"))


def test_ac1_absent_date_uses_today(tmp_path):
    adr, inp = setup(tmp_path, [dec()])
    before = datetime.date.today().isoformat()
    assert run(adr, inp).returncode == 0
    after = datetime.date.today().isoformat()
    assert front(next(adr.glob("0001-*.md")))["date"] in {before, after}


def test_ac1_unit_tests_cover_date():
    text = (ROOT / "scripts/test_write_adrs.py").read_text()
    assert "date" in text
    assert re.search(r"def test_\w*date", text), "scripts/test_write_adrs.py needs date tests"
    assert sh(sys.executable, "-m", "pytest", "-q", "scripts/test_write_adrs.py").returncode == 0


# ---------- AC2 ----------
def test_ac2_eighteen_adrs_from_0013():
    adrs = new_adrs()
    nums = [int(p.name[:4]) for p in adrs]
    assert nums[:18] == list(range(13, 31)), nums


def test_ac2_born_accepted_placeholder_ticket_one_stage_and_source_dates():
    adrs = new_adrs()[:18]
    stages, dates = set(), collections.Counter()
    for p in adrs:
        fm = front(p)
        assert fm["status"] == "accepted", p.name
        assert not re.fullmatch(r"\d+", fm["ticket"]), (p.name, fm["ticket"])
        assert fm["ticket"] not in ("", "null", "None"), p.name
        stages.add(fm["stage"])
        dates[fm["date"]] += 1
        text = p.read_text()
        for h in ("## Context", "## Options", "## Decision", "## Why", "## Consequences", "## How to reverse"):
            assert h in text, (p.name, h)
    assert len(stages) == 1, stages
    assert dates == EXPECTED_DATES


def test_ac2_no_hand_copy_markers_and_body_matches_sources():
    # each ADR body must carry real content, not an unfilled template placeholder
    assert len(new_adrs()) >= 18
    for p in new_adrs()[:18]:
        t = p.read_text()
        assert not re.search(r"\{(context|options|decision|why|number|title|date)\}", t), p.name
        assert re.search(r"^# 00(1[3-9]|2\d|30)\. \S", t, re.M), p.name


# ---------- AC3 ----------
def test_ac3_sources_removed_and_lessons_stay():
    for rel in MOVED:
        assert not (SOL / rel).exists(), rel
    for rel in STAY:
        assert (SOL / rel).is_file(), rel
    assert not list(SOL.rglob("*-decisions.md"))


def test_ac3_staying_lessons_no_longer_say_they_move():
    for rel in STAY:
        t = (SOL / rel).read_text().lower()
        assert not re.search(r"(will|to|should) (be )?move[sd]? to docs/adr|moves? to docs/adr|move to `?docs/adr", t), rel


def test_ac3_prune_566_still_passes():
    r = sh(sys.executable, "-m", "pytest", "-q", "tests/acceptance/test_adr_prune_566.py")
    assert r.returncode == 0, r.stdout[-1500:]


# ---------- AC4 ----------
def test_ac4_compound_points_decision_track_at_docs_adr():
    for rel in ("compound/SKILL.md", "compound/README.md"):
        t = (SK / rel).read_text()
        assert "docs/adr/" in t, rel
        assert "-decisions.md" not in t, rel
        assert not re.search(r"decision track[^\n]*retired|retired[^\n]*decision track", t, re.I), rel


def test_ac4_recall_reads_docs_adr_for_already_decided():
    t = (SK / "recall/SKILL.md").read_text()
    assert "docs/adr/" in t
    m = re.search(r"Already decided\.?\*\*[^\n]*", t)
    assert m and ("adr" in m.group(0).lower() or "docs/adr" in t.split("Already decided")[1][:600])


def test_ac4_recall_evals_paths_exist():
    data = json.loads((SK / "recall/evals/evals.json").read_text())
    paths = set(re.findall(r'"path":\s*"([^"]+)"', json.dumps(data)))
    paths |= set(re.findall(r"docs/(?:solutions|adr)/[\w./-]+\.md", json.dumps(data)))
    assert paths
    for p in paths:
        assert (ROOT / p).is_file(), p
    assert "-decisions.md" not in json.dumps(data)
    assert any(p.startswith("docs/adr/") for p in paths)


def test_ac4_recall_run_logs_unchanged():
    r = sh("git", "diff", "--name-only", BASE, "--", "tests/evals/recall/runs")
    assert r.returncode == 0 and r.stdout.strip() == "", r.stdout


# ---------- AC5 ----------
def test_ac5_claude_md_and_decision_record_name_one_store_per_type():
    for p in (ROOT / "CLAUDE.md", SK / "decision-record/SKILL.md"):
        t = p.read_text()
        assert "docs/adr/" in t and "docs/solutions/" in t, p
        assert re.search(r"one store|single store|store per record type|per record type", t, re.I), p


# ---------- AC6 ----------
def test_ac6_index_regenerated():
    r = sh(sys.executable, "plugins/harness/scripts/rebuild_solution_index.py", "--check")
    assert r.returncode == 0, r.stdout + r.stderr
    idx = (SOL / "INDEX.md").read_text()
    for rel in MOVED:
        assert Path(rel).name not in idx, rel


def test_ac6_no_link_to_a_moved_file():
    hits = []
    names = [Path(m).name for m in MOVED]
    for p in ROOT.rglob("*"):
        if (not p.is_file() or p.suffix not in {".md", ".json", ".sh", ".py", ".js"}
                or any(x in p.parts for x in (".git", "node_modules", "runs", "specs"))
                or p.name == "test_adr_store_567.py"):
            continue
        t = p.read_text(errors="ignore")
        for n in names:
            if n in t:
                hits.append((str(p.relative_to(ROOT)), n))
    assert not hits, hits


def test_ac6_md_links_pass():
    r = sh("bash", "scripts/check-md-links.sh")
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr


# ---------- AC7 ----------
def test_ac7_ste_baseline_and_word_ceiling():
    r = sh(sys.executable, "scripts/check_ste_baseline.py")
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr
    r = sh(sys.executable, "scripts/audit_skill_prompts.py")
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr


def test_ac7_two_skills_at_most_600_words():
    for rel in ("compound/SKILL.md", "recall/SKILL.md"):
        body = (SK / rel).read_text()
        body = re.sub(r"^---\n.*?\n---\n", "", body, count=1, flags=re.S)
        assert len(body.split()) <= 600, (rel, len(body.split()))


# ---------- AC8 ----------
def test_ac8_shellcheck_passes():
    r = sh("bash", "scripts/check-shellcheck.sh")
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr
