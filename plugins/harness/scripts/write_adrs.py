#!/usr/bin/env python3
"""Write ADR files for one run, with numbers assigned by code.

Input JSON: {"run": "<slug>", "decisions": [{ticket, stage, title, context, options, decision,
why, consequences, how_to_reverse, confidence, needs_review, decided_by, owner_confirmed?}]}.
Duplicates (same ticket, same title slug or same non-empty context) are merged first, keeping the highest confidence (ties to the first). A file is
written only for a decision that has needs_review (critical, cross-ticket, public contract, data,
security, cost, or a costly trade-off); confidence never decides this, it only marks a guess in the
table. Every other decision stays a table row. --table-out FILE lists every merged decision as a markdown table for the PR body.
Output (stdout): JSON list of {number, path, ticket, title, needs_review, stage}; [] when no
decision needs a file. Exit 0 = ok, 2 = bad input or a file would be overwritten.

Run: python3 write_adrs.py --input decisions.json [--adr-dir docs/adr] [--dry-run] [--table-out FILE]
     python3 write_adrs.py --render-section written.json [--artifact URL]
"""

import argparse
import datetime
import json
import re
import sys
import unicodedata
from pathlib import Path

REQUIRED = [
    "ticket",
    "stage",
    "title",
    "context",
    "options",
    "decision",
    "why",
    "consequences",
    "how_to_reverse",
    "confidence",
    "needs_review",
    "decided_by",
]
CONFIDENCE = ("high", "medium", "low")
ADR_RE = re.compile(r"^(\d{4})-.+\.md$")
SLUG_MAX = 60


class BadInput(Exception):
    pass


def slugify(title: str) -> str:
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:SLUG_MAX].strip("-")
    return slug or "decision"


def next_number(adr_dir: Path) -> int:
    highest = 0
    if adr_dir.is_dir():
        for p in adr_dir.iterdir():
            m = ADR_RE.match(p.name)
            if m:
                highest = max(highest, int(m.group(1)))
    return highest + 1


def as_text(value) -> str:
    if isinstance(value, list):
        return "\n".join(f"- {v}" for v in value)
    return str(value).strip()


def validate(data) -> list:
    if not isinstance(data, dict):
        raise BadInput("input must be a JSON object")
    decisions = data.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        raise BadInput("'decisions' must be a non-empty list")
    for i, d in enumerate(decisions):
        if not isinstance(d, dict):
            raise BadInput(f"decisions[{i}] must be an object")
        for f in REQUIRED:
            if f not in d or d[f] is None or (isinstance(d[f], str) and not d[f].strip()):
                raise BadInput(f"decisions[{i}] missing required field '{f}'")
        if not isinstance(d["needs_review"], bool):
            raise BadInput(f"decisions[{i}].needs_review must be true or false")
        if "owner_confirmed" in d and not isinstance(d["owner_confirmed"], bool):
            raise BadInput(f"decisions[{i}].owner_confirmed must be true or false")
        if d["confidence"] not in CONFIDENCE:
            raise BadInput(
                f"decisions[{i}].confidence must be one of {', '.join(CONFIDENCE)}"
            )
    return decisions


def needs_adr(d: dict) -> bool:
    """A decision gets an ADR file only when it is flagged needs_review. Confidence does not count."""
    return d["needs_review"]


def _context_key(d: dict) -> str:
    text = " ".join(str(d["context"]).lower().split())
    return "" if text == "n/a" else text   # ship.js fills a missing context with 'n/a'


def dedupe(decisions: list) -> list:
    """Merge duplicates: same ticket and (same title slug or identical non-empty context).

    Keeps the item with the highest confidence (high, then medium, then low; a tie keeps the
    first). If any merged item needs review, the kept one does too. The kept one is
    owner_confirmed only when every merged item is. Order follows the first appearance of each group.
    """
    groups = []   # each: {"ticket", "slugs", "contexts", "items"}
    for d in decisions:
        slug, ctx = slugify(d["title"]), _context_key(d)
        for g in groups:
            if str(g["ticket"]) == str(d["ticket"]) and (slug in g["slugs"] or (ctx and ctx in g["contexts"])):
                break
        else:
            g = {"ticket": d["ticket"], "slugs": set(), "contexts": set(), "items": []}
            groups.append(g)
        g["slugs"].add(slug)
        if ctx:
            g["contexts"].add(ctx)
        g["items"].append(d)
    merged = []
    for g in groups:
        best = dict(min(g["items"], key=lambda d: CONFIDENCE.index(d["confidence"])))   # min keeps the first on a tie
        if any(d["needs_review"] for d in g["items"]):
            best["needs_review"] = True
        if best.get("owner_confirmed") is True and not all(
            d.get("owner_confirmed") is True for d in g["items"]
        ):
            best["owner_confirmed"] = False
        merged.append(best)
    return merged


def _cell(value) -> str:
    return " ".join(as_text(value).split()).replace("|", "\\|")


def decisions_table(decisions: list) -> str:
    """Markdown table of every decision. ADR column: owner-confirmed, ADR file, or table only."""
    rows = ["| Ticket | Title | Decision | Why | ADR |", "|---|---|---|---|---|"]
    for d in decisions:
        if needs_adr(d):
            note = "ADR file"
        elif d.get("owner_confirmed") is True:
            note = "owner-confirmed"
        elif d["confidence"] == "low":
            note = "table only (low confidence, check)"
        else:
            note = "table only"
        rows.append(f"| #{d['ticket']} | {_cell(d['title'])} | {_cell(d['decision'])} | {_cell(d['why'])} | {note} |")
    return "\n".join(rows) + "\n"


def order(decisions: list) -> list:
    return sorted(
        decisions,
        key=lambda d: (
            not d["needs_review"],
            str(d["ticket"]).zfill(8),
            str(d["stage"]),
        ),
    )


def render(template: str, d: dict, number: int, date: str) -> str:
    values = {k: as_text(d[k]) for k in REQUIRED}
    values["needs_review"] = "true" if d["needs_review"] else "false"
    values["status"] = "needs-review" if d["needs_review"] else "accepted"
    values["number"] = f"{number:04d}"
    values["date"] = date
    out = template
    for k, v in values.items():
        out = out.replace("{" + k + "}", v)
    return out


def plan(data: dict, adr_dir: Path, template: str, date: str) -> list:
    decisions = order(validate(data))
    number = next_number(adr_dir)
    taken = {p.name for p in adr_dir.iterdir()} if adr_dir.is_dir() else set()
    items = []
    for d in decisions:
        base = slugify(d["title"])
        slug, n = base, 2
        while f"{number:04d}-{slug}.md" in taken:
            suffix = f"-{n}"
            slug, n = base[: SLUG_MAX - len(suffix)].strip("-") + suffix, n + 1
        name = f"{number:04d}-{slug}.md"
        taken.add(name)
        items.append(
            {
                "number": f"{number:04d}",
                "path": str(adr_dir / name),
                "ticket": d["ticket"],
                "stage": d["stage"],
                "title": d["title"],
                "needs_review": d["needs_review"],
                "_text": render(template, d, number, date),
            }
        )
        number += 1
    return items


def render_section(written: list, artifact: str = "") -> str:
    def line(w):
        name = Path(w["path"]).name
        return (
            f"- [ADR {w['number']}](docs/adr/{name}) "
            f"(#{w['ticket']}, {w.get('stage', '')}): {w['title']}"
        )

    out = ["## Decisions", ""]
    if artifact:
        out += [f"Artifact: {artifact} (private; the ADR files are the source of truth)", ""]
    if written:
        out += ["Needs review:", ""] + [line(w) for w in written] + [""]
    return "\n".join(out)


# Same text as docs/adr/TEMPLATE.md in the harness repo (a test keeps them equal), so a consuming
# repo that has no docs/adr/TEMPLATE.md can still write ADRs.
DEFAULT_TEMPLATE = '---\nticket: {ticket}\nstage: {stage}\nstatus: {status}\nneeds_review: {needs_review}\nconfidence: {confidence}\ndecided_by: {decided_by}\ndate: {date}\n---\n\n# {number}. {title}\n\n## Context\n\n{context}\n\n## Options\n\n{options}\n\n## Decision\n\n{decision}\n\n## Why\n\n{why}\n\n## Consequences\n\n{consequences}\n\n## How to reverse\n\n{how_to_reverse}\n'


def load_template(adr_dir: Path) -> str:
    """The repo's own template wins; the built-in default is the last resort."""
    path = adr_dir / "TEMPLATE.md"
    if path.is_file():
        return path.read_text()
    return DEFAULT_TEMPLATE


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", help="decisions JSON file")
    ap.add_argument("--adr-dir", default="docs/adr")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    ap.add_argument("--table-out", metavar="FILE",
                    help="write the markdown table of all merged decisions to FILE")
    ap.add_argument("--render-section", metavar="WRITTEN_JSON",
                    help="render the PR '## Decisions' section from this script's JSON output")
    ap.add_argument("--artifact", default="", help="artifact URL for the section (optional)")
    args = ap.parse_args()

    try:
        if args.render_section:
            try:
                written = json.loads(Path(args.render_section).read_text())
            except (OSError, json.JSONDecodeError) as e:
                raise BadInput(f"cannot read written JSON: {e}")
            print(render_section(written, args.artifact))
            return 0
        if not args.input:
            raise BadInput("--input is required")
        try:
            data = json.loads(Path(args.input).read_text())
        except (OSError, json.JSONDecodeError) as e:
            raise BadInput(f"cannot read input: {e}")
        adr_dir = Path(args.adr_dir)
        template = load_template(adr_dir)
        merged = dedupe(validate(data))
        kept = [d for d in merged if needs_adr(d)]
        items = plan({**data, "decisions": kept}, adr_dir, template, datetime.date.today().isoformat()) if kept else []
        if not args.dry_run:
            adr_dir.mkdir(parents=True, exist_ok=True)
            for it in items:
                if Path(it["path"]).exists():
                    raise BadInput(f"refusing to overwrite {it['path']}")
            if args.table_out:
                Path(args.table_out).write_text(decisions_table(merged))
            for it in items:
                with open(it["path"], "x") as f:
                    f.write(it["_text"])
    except (BadInput, OSError) as e:
        print(f"write_adrs: {e}", file=sys.stderr)
        return 2
    print(json.dumps([{k: v for k, v in it.items() if k != "_text"} for it in items], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
