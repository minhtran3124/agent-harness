#!/usr/bin/env python3
"""Plan, validate and assemble the onboarding tour from the OpenWiki pages.

Run from the repository root. Wiki paths are relative to openwiki/.

  build_tour.py plan                 Print the wiki pages grouped by section, as JSON.
  build_tour.py build [--out PATH]   Validate the page records in .harness-state/onboarding/pages/
                                     against the wiki, then write one standalone HTML tour
                                     (default .harness-state/onboarding/tour.html).

Verifies:
  - Every wiki page has exactly one record, and each record has a why and at least one break.
  - Every break and test names a source: a heading of its own wiki page, or its title.
  - Every test command appears verbatim in its wiki page.
  - Verify counts come from check_claims.page_rows: how many claims cite lines unchanged since
    the wiki was generated.
  - Goals come from the quickstart task-routing table. Each goal lists only pages in the tour.
  - Wiki drift comes from openwiki/.last-update.json and git rev-list against HEAD.

Does not verify:
  - That a why or break sentence is true of the code. The source heading shows where the
    sentence came from. check_claims shows only whether the cited lines changed.
  - That a lesson path exists in the repository. Lessons are the docs/solutions/ paths the page cites.
  - That a sentence keeps the wiki's meaning. Review the page before relying on its wording.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import check_claims

WIKI = Path("openwiki")
PAGES_DIR = Path(".harness-state/onboarding/pages")
DEFAULT_OUT = Path(".harness-state/onboarding/tour.html")
TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "tour.html"
PLACEHOLDER = "/*__TOUR_DATA__*/null"
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)\s#]+\.md)(?:#[^)]*)?\)")
ENTRY_RE = re.compile(r"^- \[([^\]]+)\]\(([^)\s]+)\)", re.M)
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.M)
LESSON_RE = re.compile(r"docs/solutions/[A-Za-z0-9_./-]+\.md")
NOT_LESSONS = ("INDEX.md", "critical-patterns.md")


def sections() -> list[dict]:
    """Quickstart first, then each wiki directory in the order openwiki/index.md lists it."""
    index = (WIKI / "index.md").read_text(encoding="utf-8")
    files_block, _, dirs_block = index.partition("# Directories")
    out = [{"id": "start", "title": "Start here", "pages": [p for _, p in ENTRY_RE.findall(files_block)]}]
    for _, target in ENTRY_RE.findall(dirs_block):
        name = target.rstrip("/")
        section_index = (WIKI / name / "index.md").read_text(encoding="utf-8")
        pages = [f"{name}/{p}" for _, p in ENTRY_RE.findall(section_index) if p != "index.md"]
        out.append({"id": name, "title": name.replace("-", " ").capitalize(), "pages": pages})
    return out


def norm(text: str) -> str:
    return re.sub(r"[`*_]", "", text).strip().strip("#").strip().rstrip(":").lower()


def page_title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", text, re.M)
    return match.group(1) if match else fallback


def load_records() -> tuple[dict, list[str]]:
    records: dict = {}
    errors: list[str] = []
    for path in sorted(PAGES_DIR.glob("*.json")) if PAGES_DIR.is_dir() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"{path}: unreadable JSON ({exc})")
            continue
        for rec in data.get("pages", []) if isinstance(data, dict) else []:
            page = rec.get("page") if isinstance(rec, dict) else None
            if not isinstance(page, str):
                errors.append(f"{path}: a record has no page path")
            elif page in records:
                errors.append(f"{page}: has more than one record")
            else:
                records[page] = rec
    return records, errors


def validate(rec: dict, text: str, title: str) -> list[str]:
    errors = []
    if not isinstance(rec.get("why"), str) or not rec["why"].strip():
        errors.append("why is missing")
    headings = {norm(h) for h in HEADING_RE.findall(text)} | {norm(title)}
    breaks = rec.get("breaks")
    if not isinstance(breaks, list) or not breaks:
        errors.append("needs at least one break")
        breaks = []
    for i, item in enumerate(breaks):
        if not isinstance(item, dict) or not str(item.get("t", "")).strip():
            errors.append(f"break {i} has no text")
        elif norm(str(item.get("src", ""))) not in headings:
            errors.append(f"break {i} src is not a heading of this page: {item.get('src')!r}")
    tests = rec.get("tests", [])
    if not isinstance(tests, list):
        errors.append("tests must be a list")
        tests = []
    for i, item in enumerate(tests):
        cmd = str(item.get("cmd", "")) if isinstance(item, dict) else ""
        if not cmd.strip():
            errors.append(f"test {i} has no command")
        elif cmd not in text:
            errors.append(f"test {i} command is not in the wiki page: {cmd!r}")
        if isinstance(item, dict) and norm(str(item.get("src", ""))) not in headings:
            errors.append(f"test {i} src is not a heading of this page: {item.get('src')!r}")
    return errors


def verify(page: str) -> dict:
    code, message, rows = check_claims.page_rows(page)
    if code not in (0, 1):
        return {"ok": 0, "total": 0, "unverified": [message]}
    return {
        "ok": sum(1 for result, _, _ in rows if result == "ok"),
        "total": len(rows),
        "unverified": [f"{result} {target}: {stmt}" for result, target, stmt in rows if result != "ok"],
    }


def goals(in_tour: set[str]) -> list[dict]:
    """Goals from the quickstart routing table: Read first, then Then also, in listed order."""
    out = []
    in_routing = False
    for line in (WIKI / "quickstart.md").read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            in_routing = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if "I want to change" in cells[0]:
            in_routing = True
            continue
        if not in_routing or len(cells) < 3 or not cells[0].startswith("**"):
            continue
        label = re.sub(r"\*\*|`", "", cells[0]).split(" (")[0].strip()
        pages = []
        for target in LINK_RE.findall(cells[1]) + LINK_RE.findall(cells[2]):
            if target in in_tour and target not in pages:
                pages.append(target)
        out.append({"goal": label, "pages": pages})
    return out


def behind_count(head: str) -> int | None:
    try:
        proc = subprocess.run(["git", "rev-list", "--count", f"{head}..HEAD"],
                              capture_output=True, text=True)
        return int(proc.stdout.strip()) if proc.returncode == 0 else None
    except (OSError, ValueError):
        return None


def cmd_plan() -> int:
    if not WIKI.is_dir():
        print(f"no-wiki {WIKI}/")
        return 2
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    print(json.dumps({"sections": sections(), "pages_dir": str(PAGES_DIR)}, indent=2))
    return 0


def cmd_build(out: Path) -> int:
    if not WIKI.is_dir():
        print(f"no-wiki {WIKI}/")
        return 2
    planned = sections()
    records, errors = load_records()
    planned_pages = {p for s in planned for p in s["pages"]}
    errors += [f"{page}: record for a page that is not in the wiki" for page in records if page not in planned_pages]

    pages = []
    for section in planned:
        for page in section["pages"]:
            page_file = WIKI / page
            if not page_file.is_file():
                errors.append(f"{page}: listed in the wiki index but the file is missing")
                continue
            if page not in records:
                errors.append(f"{page}: no record in {PAGES_DIR}")
                continue
            text = page_file.read_text(encoding="utf-8")
            title = page_title(text, page)
            problems = validate(records[page], text, title)
            errors += [f"{page}: {p}" for p in problems]
            if problems:
                continue
            rec = records[page]
            lessons = [p for p in dict.fromkeys(LESSON_RE.findall(text))
                       if Path(p).name not in NOT_LESSONS]
            pages.append({
                "id": page[:-3],
                "src": page,
                "section": section["id"],
                "title": title,
                "why": rec["why"].strip(),
                "breaks": [{"t": b["t"].strip(), "src": b["src"]} for b in rec["breaks"]],
                "tests": [{"cmd": t["cmd"], "what": str(t.get("what", "")), "src": t["src"]} for t in rec.get("tests", [])],
                "lessons": lessons,
                "verify": verify(page),
            })
    if errors:
        for line in errors:
            print(f"error: {line}")
        print(f"{len(errors)} error(s); no tour written. Re-run the failing sections.")
        return 1

    last = json.loads((WIKI / ".last-update.json").read_text(encoding="utf-8"))
    data = {
        "wiki": {
            "generated": str(last.get("updatedAt", ""))[:10],
            "gitHead": last.get("gitHead"),
            "status": last.get("status"),
            "behind": behind_count(str(last.get("gitHead", ""))),
        },
        "sections": [{"id": s["id"], "title": s["title"]} for s in planned if s["pages"]],
        "goals": goals({p["src"] for p in pages}),
        "pages": pages,
    }
    payload = (json.dumps(data, ensure_ascii=False)
               .replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))
    html = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in html:
        print(f"error: template has no {PLACEHOLDER} marker: {TEMPLATE}")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html.replace(PLACEHOLDER, payload, 1), encoding="utf-8")
    ok = sum(p["verify"]["ok"] for p in pages)
    total = sum(p["verify"]["total"] for p in pages)
    print(f"wrote {out}: {len(pages)} pages, {ok} of {total} claims ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan", help="list wiki pages by section")
    build = sub.add_parser("build", help="validate records and write the HTML tour")
    build.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output HTML path")
    args = parser.parse_args()
    return cmd_plan() if args.command == "plan" else cmd_build(args.out)


if __name__ == "__main__":
    sys.exit(main())
