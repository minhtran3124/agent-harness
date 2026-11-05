#!/usr/bin/env python3
"""Write ADR files for one run, with numbers assigned by code.

Input JSON: {"run": "<slug>", "decisions": [{ticket, stage, title, context, options, decision,
why, consequences, how_to_reverse, confidence, needs_review, adr, decided_by, owner_confirmed?}]}.
Duplicates (same ticket, same title slug or same non-empty context) are merged first, keeping the highest confidence (ties to the first).
A file is written only for a decision with adr true (it changes harness behavior, a data or config
contract, or how users work) that lists at least two real options (not n/a), and whose title does
not start with "Boundary: " or "UAT not run". needs_review is the separate owner-ask flag and never
makes a file; confidence never decides this, it only marks a guess in the table. Files are always born
accepted. A decision whose ticket already has an ADR in the folder with the same title slug or the
same non-empty context and the same decision text is skipped (table note "already recorded"); a changed decision gets a new file that supersedes the old one; this check covers numeric
tickets only. Every other decision stays a table row. --table-out FILE lists every merged decision as a markdown table for the PR body.
Output (stdout): JSON list of {number, path, ticket, title, needs_review, stage}; [] when no
decision needs a file. Exit 0 = ok, 2 = bad input or a file would be overwritten.

Run: python3 write_adrs.py --input decisions.json [--adr-dir docs/adr] [--dry-run] [--table-out FILE]
     python3 write_adrs.py --render-section written.json [--artifact URL]
     python3 write_adrs.py --fill-count BODY.md --written written.json   (replaces {{ADR_COUNT}} in BODY.md)
"""

import argparse
import datetime
import json
import os
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
    "adr",
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
        if not isinstance(d["adr"], bool):
            raise BadInput(f"decisions[{i}].adr must be true or false")
        if "owner_confirmed" in d and not isinstance(d["owner_confirmed"], bool):
            raise BadInput(f"decisions[{i}].owner_confirmed must be true or false")
        if d["confidence"] not in CONFIDENCE:
            raise BadInput(
                f"decisions[{i}].confidence must be one of {', '.join(CONFIDENCE)}"
            )
    return decisions


NO_FILE_TITLES = ("boundary: ", "uat not run")


def _real_options(d: dict) -> int:
    opts = d["options"]
    if not isinstance(opts, list):
        opts = [opts]
    return sum(1 for o in opts if str(o).strip().lower() not in ("", "n/a"))


def needs_adr(d: dict) -> bool:
    """A file needs adr true, two real options and a title that is not a scope note or UAT event."""
    if d["adr"] is not True or d.get("boundary") is True:
        return False
    if str(d["title"]).strip().lower().startswith(NO_FILE_TITLES):
        return False
    return _real_options(d) >= 2


def _norm_context(value) -> str:
    text = " ".join(as_text(value).lower().split())
    return "" if text == "n/a" else text   # ship.js fills a missing context with 'n/a'


def _context_key(d: dict) -> str:
    return _norm_context(d["context"])


SUPERSEDES_RE = re.compile(r"\A\s*Supersedes ADR [\d, ]+\.\s*")


def existing_keys(adr_dir: Path) -> list:
    """Read each NNNN-*.md: (number, ticket, title slug, context, decision, superseded). A file it cannot parse is skipped.

    The context is read without the leading "Supersedes ADR N." line this script adds, so a later run
    compares the original context text.
    """
    keys = []
    if not adr_dir.is_dir():
        return keys
    for p in sorted(adr_dir.iterdir()):
        m = ADR_RE.match(p.name)
        if not m:
            continue
        try:
            text = p.read_text()
            fm = re.match(r"---\n(.*?)\n---\n", text, re.S)
            tm = re.search(r"^# \d{4}\. (.+)$", text, re.M)
            tk = re.search(r"^ticket:[ \t]*(.+?)[ \t]*$", fm.group(1), re.M) if fm else None
            if not (tk and tm):
                continue
            cm = re.search(r"^## Context\n(.*?)(?=^## |\Z)", text, re.M | re.S)
            dm = re.search(r"^## Decision\n(.*?)(?=^## |\Z)", text, re.M | re.S)
            ctx = SUPERSEDES_RE.sub("", cm.group(1), count=1) if cm else ""
            superseded = bool(re.search(r"^status:[ \t]*superseded[ \t]*$", fm.group(1), re.M))
            keys.append((m.group(1), tk.group(1), slugify(tm.group(1)), _norm_context(ctx),
                         _norm_context(dm.group(1)) if dm else "", superseded))
        except (OSError, UnicodeError):
            continue
    return keys


def recorded_match(d: dict, keys: list):
    """Match against the live (not superseded) ADRs of the same numeric ticket with the same title slug or context.

    Returns None (no match), (number, True) when a live match has the same decision text, or
    ([numbers], False) with every live matching number when the decision text changed. A changed
    decision is new content: it gets a new ADR that supersedes all of them. A superseded ADR never
    matches, so a decision that reverts to an older text is written again.
    """
    ticket = str(d["ticket"]).strip()
    if not ticket.isdigit():
        return None   # 'run' and other non-numeric tickets repeat across runs
    slug, ctx = slugify(d["title"]), _context_key(d)
    dec = " ".join(as_text(d["decision"]).lower().split())
    hits = [(n, dtext) for n, t, s, c, dtext, sup in keys
            if t == ticket and not sup and (s == slug or (ctx and c == ctx))]
    for n, dtext in hits:
        if not dtext or dtext == dec:
            return n, True
    return ([n for n, _ in hits], False) if hits else None


def recorded_number(d: dict, keys: list):
    m = recorded_match(d, keys)
    return m[0] if m and m[1] else None


FRONTMATTER_RE = re.compile(r"\A---(\r?\n)(.*?)\r?\n---\r?\n", re.S)


def superseded_text(text: str, new: str):
    """The old ADR text with status superseded and superseded_by set, or None when it has no frontmatter.

    Handles CRLF (the line ending of the file is kept), a missing status line (one is added) and a
    stale superseded_by line (it is replaced, so the key appears once).
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    nl, fm = m.group(1), m.group(2)
    lines = [ln for ln in fm.split(nl) if not ln.startswith("superseded_by:")]
    if any(ln.startswith("status:") for ln in lines):
        lines = ["status: superseded" if ln.startswith("status:") else ln for ln in lines]
    else:
        lines.append("status: superseded")
    lines.append(f"superseded_by: {new}")
    return f"---{nl}" + nl.join(lines) + f"{nl}---{nl}" + text[m.end():]


def plan_supersede(adr_dir: Path, old: str, new: str):
    """Check that the old ADR can be marked, before anything is written. Returns (path, new text).

    Raises BadInput when the file is missing, is not writable or has no frontmatter, so the run stops
    with exit 2 and writes nothing, rather than leaving two live ADRs for one decision.
    """
    paths = sorted(adr_dir.glob(f"{old}-*.md"))
    if len(paths) != 1:
        raise BadInput(f"cannot mark ADR {old} superseded: found {len(paths)} files")
    p = paths[0]
    try:
        with open(p, newline="", encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeError) as e:
        raise BadInput(f"cannot mark ADR {old} superseded: {e}")
    if not os.access(p, os.W_OK):
        raise BadInput(f"cannot mark ADR {old} superseded: {p} is not writable")
    out = superseded_text(text, new)
    if out is None:
        raise BadInput(f"cannot mark ADR {old} superseded: {p} has no frontmatter")
    return p, out


def mark_superseded(path: Path, text: str) -> None:
    """Write the text from plan_supersede (the old ADR with status superseded and superseded_by).

    Order and failure behaviour: main() runs plan_supersede for every old ADR first, so a file that
    cannot be marked stops the run with exit 2 before any write. Only then does it write the new
    ADRs, and after that this function marks the old ones. If this write still fails (a race),
    main() exits 2 and names the old file, so the failure is loud and the owner sees which ADR to
    mark by hand. The new file is written first on purpose: a dangling superseded_by is worse
    than a loud failure.
    """
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(text)


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
        if any(d["adr"] for d in g["items"]):
            best["adr"] = True
        if best.get("owner_confirmed") is True and not all(
            d.get("owner_confirmed") is True for d in g["items"]
        ):
            best["owner_confirmed"] = False
        merged.append(best)
    return merged


def _cell(value) -> str:
    return " ".join(as_text(value).split()).replace("|", "\\|")


def decisions_table(decisions: list, recorded: dict = None) -> str:
    """Markdown table of every decision. ADR column: ADR file, owner-confirmed, already recorded, or table only."""
    recorded = recorded or {}
    rows = ["| Ticket | Title | Decision | Why | ADR |", "|---|---|---|---|---|"]
    for d in decisions:
        if id(d) in recorded:
            note = f"already recorded (ADR {recorded[id(d)]})"
        elif needs_adr(d):
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
            not needs_adr(d),
            str(d["ticket"]).zfill(8),
            str(d["stage"]),
        ),
    )


def render(template: str, d: dict, number: int, date: str) -> str:
    values = {k: as_text(d[k]) for k in REQUIRED if k != "needs_review"}   # needs_review is not an ADR field
    values["status"] = "accepted"
    values["number"] = f"{number:04d}"
    values["date"] = date
    out = template
    for k, v in values.items():
        out = out.replace("{" + k + "}", v)
    return out


def check_template(template: str) -> None:
    """Fail on a placeholder the script does not fill (for example a stale {needs_review} line)."""
    known = set(REQUIRED) | {"status", "number", "date"}
    known.discard("needs_review")
    bad = sorted(set(re.findall(r"\{([a-z_]+)\}", template)) - known)
    if bad:
        raise BadInput("TEMPLATE.md has a placeholder the script does not fill: " + ", ".join("{" + b + "}" for b in bad))


def plan(data: dict, adr_dir: Path, template: str, date: str) -> list:
    check_template(template)
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
                "_supersedes": d.get("_supersedes", []),
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
        out += ["ADRs added:", ""] + [line(w) for w in written] + [""]
    return "\n".join(out)


# Same text as docs/adr/TEMPLATE.md in the harness repo (a test keeps them equal), so a consuming
# repo that has no docs/adr/TEMPLATE.md can still write ADRs.
DEFAULT_TEMPLATE = '---\nticket: {ticket}\nstage: {stage}\nstatus: {status}\nconfidence: {confidence}\ndecided_by: {decided_by}\ndate: {date}\n---\n\n# {number}. {title}\n\n## Context\n\n{context}\n\n## Options\n\n{options}\n\n## Decision\n\n{decision}\n\n## Why\n\n{why}\n\n## Consequences\n\n{consequences}\n\n## How to reverse\n\n{how_to_reverse}\n'


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
    ap.add_argument("--fill-count", metavar="BODY_FILE",
                    help="replace {{ADR_COUNT}} in BODY_FILE with the number of entries in --written")
    ap.add_argument("--written", metavar="WRITTEN_JSON", help="written JSON for --fill-count")
    args = ap.parse_args()

    try:
        if args.fill_count:
            try:
                written = json.loads(Path(args.written or "").read_text())
                body = Path(args.fill_count)
                text = body.read_text()
            except (OSError, json.JSONDecodeError) as e:
                raise BadInput(f"cannot read --written or body: {e}")
            if not isinstance(written, list):
                raise BadInput("written JSON must be a list")
            body.write_text(text.replace("{{ADR_COUNT}}", str(len(written))))
            return 0
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
        keys = existing_keys(adr_dir)
        recorded = {}
        kept = []
        for d in merged:
            if not needs_adr(d):
                continue
            m = recorded_match(d, keys)
            if m and m[1]:
                recorded[id(d)] = m[0]
            elif m:
                kept.append({**d, "context": f"Supersedes ADR {', '.join(m[0])}.\n\n{as_text(d['context'])}",
                             "_supersedes": m[0]})
            else:
                kept.append(d)
        items = plan({**data, "decisions": kept}, adr_dir, template, datetime.date.today().isoformat()) if kept else []
        marks = {}   # old ADR path -> new text; the first new ADR to name an old one wins
        for it in items:
            for old in it.get("_supersedes", []):
                path, text = plan_supersede(adr_dir, old, it["number"])
                marks.setdefault(path, text)
        if not args.dry_run:
            adr_dir.mkdir(parents=True, exist_ok=True)
            for it in items:
                if Path(it["path"]).exists():
                    raise BadInput(f"refusing to overwrite {it['path']}")
            if args.table_out:
                Path(args.table_out).write_text(decisions_table(merged, recorded))
            for it in items:
                with open(it["path"], "x") as f:
                    f.write(it["_text"])
            for path, text in marks.items():
                try:
                    mark_superseded(path, text)
                except OSError as e:
                    raise BadInput(f"new ADR written but {path} could not be marked superseded, mark it by hand: {e}")
    except (BadInput, OSError) as e:
        print(f"write_adrs: {e}", file=sys.stderr)
        return 2
    print(json.dumps([{k: v for k, v in it.items() if not k.startswith("_")} for it in items], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
