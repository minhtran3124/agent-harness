#!/usr/bin/env python3
"""Deterministic renderer: specs/<slug>/PLAN.md -> specs/<slug>/PLAN.html

Replaces the "model emits the template verbatim" flow described in the original
SKILL.md. Parsing + template-fill + self-check all run here, so each invocation
costs one Bash call instead of thousands of output tokens, and the output is
byte-for-byte deterministic for a given PLAN.md + template.html.

Usage:
    python3 render_plan.py <path-to-PLAN.md | slug> [output.html]

Argument resolution mirrors the SKILL.md spec:
  * arg endswith "PLAN.md" and exists -> use directly
  * otherwise treat as slug -> glob specs/**/<slug>/PLAN.md (0 -> error, >1 -> error)
Output defaults to <plan-dir>/PLAN.html (overwritten silently; untracked).
"""

from __future__ import annotations

import html as _html
import json
import re
import sys
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parent / "template.html"

# Heading token table (rule 3). Key = normalized heading (after stripping "N. ").
SECTION_TOKENS = {
    "motivation": "motivation",
    "non-goals": "non-goals",
    "success criteria": "success",
    "file structure": "files",
    "tasks": "tasks",
    "risks": "risks",
    "manual smoke verification": "manual",
    "status log": "status",
}

SOURCE_FILES = ["PLAN.md", "design.md", "research-brief.md"]


# --------------------------------------------------------------------------- #
# Escaping / slug helpers
# --------------------------------------------------------------------------- #
def esc(s: str) -> str:
    """Escape &<>" but preserve author-written entities (e.g. &lt;next&gt;).

    We unescape first so source like `&lt;slug&gt;` (intended as <slug>) and
    `jq . &gt; /dev/null` round-trip to the same rendered glyph instead of
    double-escaping into a literal `&lt;`.
    """
    s = _html.unescape(s)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "section"


def natural_key(task_id: str):
    """Natural sort for ids like 1.1, 1.10, P2.3."""
    parts = re.split(r"(\d+)", task_id)
    return [int(p) if p.isdigit() else p for p in parts]


def wave_sort_key(w: str):
    if w == "—":
        return (2, 0, "")
    try:
        return (0, int(w), "")
    except ValueError:
        return (1, 0, w)


# --------------------------------------------------------------------------- #
# Frontmatter + body split
# --------------------------------------------------------------------------- #
def parse_frontmatter(text: str):
    """Parse a leading `--- … ---` YAML-ish block into a dict.

    Hardened against an UNTERMINATED block: the old code did
    `text.find("\\n---")`, which on a missing closing fence runs forward to the
    first `---` horizontal rule in the body and swallows real content as
    "frontmatter" (the eng-383 `## slug:` + no-close case dropped its intro
    fields). Now we scan line-by-line and bail — returning the full body with an
    empty dict — if the fence isn't closed before a Markdown heading (`# …`,
    which frontmatter never contains) or a sane line budget.
    """
    fm: dict[str, str] = {}
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return fm, text
    close = None
    for idx in range(1, min(len(lines), 40)):
        stripped = lines[idx].strip()
        if stripped == "---":
            close = idx
            break
        if stripped.startswith("#"):  # heading => opening fence was never closed
            break
    if close is None:
        return fm, text
    for line in lines[1:close]:
        s = line.strip()
        if ":" in s and not s.startswith("#"):
            k, _, v = s.partition(":")
            fm[k.strip()] = v.strip()
    body = "\n".join(lines[close + 1 :]).lstrip("\n")
    return fm, body


# --------------------------------------------------------------------------- #
# Task extraction (balanced; tolerant of raw OR fenced blocks and of nested
# example <task> inside an <action>)
# --------------------------------------------------------------------------- #
def mask_fences(body: str) -> str:
    """Replace fenced code regions with equal-length blanks (offsets preserved).

    Real PLAN.md files write real tasks as RAW <task> blocks and use ``` fences
    only for examples/illustrations. Masking fences hides example <task> blocks
    and bare prose like `<phase>.<task>` so the balanced scan sees only real
    tasks. Backslash-escaped delimiters (e.g. `\\```xml` shown inside a markdown
    fence) are not treated as fences — they start with `\\`, not a backtick."""
    out = []
    in_fence = False
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(" " * len(line))
            continue
        out.append(" " * len(line) if in_fence else line)
    return "\n".join(out)


def _balanced_spans(scan: str):
    """Top-level <task>…</task> char spans in `scan` (depth-balanced)."""
    spans = []
    depth = 0
    start = None
    for tok in re.finditer(r"</?task\b[^>]*>", scan):
        if not tok.group(0).startswith("</"):
            if depth == 0:
                start = tok.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0 and start is not None:
                spans.append((start, tok.end()))
                start = None
            if depth < 0:
                depth = 0
    return spans


def extract_tasks(body: str):
    """Return (tasks, spans). Spans are TOP-LEVEL <task> blocks in source order.

    Primary path scans a fence-masked copy so example/illustration tasks inside
    ``` fences are ignored; blocks are then sliced from the ORIGINAL body so an
    <action> that legitimately contains fenced code keeps it. Empty-id matches
    are dropped. If no raw tasks exist, fall back to scanning the unmasked body
    (covers spec-compliant plans that fence their real tasks)."""
    spans = _balanced_spans(mask_fences(body))
    tasks = [parse_task_block(body[s:e]) for s, e in spans]
    keep = [(t, sp) for t, sp in zip(tasks, spans) if t["id"]]
    if not keep:
        spans = _balanced_spans(body)
        keep = [
            (parse_task_block(body[s:e]), (s, e))
            for s, e in spans
            if parse_task_block(body[s:e])["id"]
        ]
    tasks = [t for t, _ in keep]
    spans = [sp for _, sp in keep]
    return tasks, spans


def _child(block: str, tag: str, greedy: bool = False) -> str:
    pat = rf"<{tag}>(.*{'' if greedy else '?'})</{tag}>"
    m = re.search(pat, block, re.DOTALL)
    return m.group(1) if m else ""


def parse_task_block(block: str) -> dict:
    open_m = re.search(r"<task\b([^>]*)>", block)
    attrs = open_m.group(1) if open_m else ""
    wid = re.search(r'id="([^"]*)"', attrs)
    wwave = re.search(r'wave="([^"]*)"', attrs)
    task_id = wid.group(1) if wid else ""
    wave = wwave.group(1) if wwave else "—"

    # action is the only child that can nest same-named tags (example tasks),
    # so capture it greedily (to the LAST </action>) and remove its span before
    # extracting the post-action children (verify/done) to avoid grabbing an
    # example's <verify>.
    action_m = re.search(r"<action>(.*)</action>", block, re.DOTALL)
    action = action_m.group(1).strip() if action_m else ""
    block_wo_action = (
        block[: action_m.start()] + block[action_m.end() :] if action_m else block
    )

    files = _child(block_wo_action, "files")
    verify = _child(block_wo_action, "verify")
    done = _child(block_wo_action, "done")

    return {
        "id": task_id.strip(),
        "wave": (wave.strip() or "—"),
        "files": files.strip(),
        "action": action,
        "verify": verify.strip(),
        "done": done.strip(),
    }


# --------------------------------------------------------------------------- #
# Minimal Markdown -> HTML (subset per SKILL.md rule 6)
# --------------------------------------------------------------------------- #
def render_inline(s: str) -> str:
    s = esc(s)
    s = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*([^*]+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"(?<!\w)_([^_\n]+?)_(?!\w)", r"<em>\1</em>", s)
    return s


_SENTINEL = "\x00"


def _parse_table(rows: list[str]) -> str:
    def cells(row: str):
        row = row.replace(r"\|", _SENTINEL).strip()
        row = row.strip("|")
        parts = [c.strip().replace(_SENTINEL, "|") for c in row.split("|")]
        return parts

    header = cells(rows[0])
    body_rows = [cells(r) for r in rows[2:]]
    ncol = len(header)
    if any(len(r) != ncol for r in body_rows):
        return f"<pre>{esc(chr(10).join(rows))}</pre>"
    out = ["<table><thead><tr>"]
    out += [f"<th>{render_inline(c)}</th>" for c in header]
    out.append("</tr></thead><tbody>")
    for r in body_rows:
        out.append(
            "<tr>" + "".join(f"<td>{render_inline(c)}</td>" for c in r) + "</tr>"
        )
    out.append("</tbody></table>")
    return "".join(out)


def md_to_html(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            out.append(f"<pre><code>{esc(chr(10).join(buf))}</code></pre>")
            continue

        if not stripped:
            i += 1
            continue

        if stripped in ("---", "***", "___"):
            out.append("<hr>")
            i += 1
            continue

        hm = re.match(r"(#{3,6})\s+(.*)$", stripped)
        if hm:
            lvl = min(len(hm.group(1)), 4)
            out.append(f"<h{lvl}>{render_inline(hm.group(2))}</h{lvl}>")
            i += 1
            continue

        # table: a row with '|' followed by a separator row of dashes
        if (
            "|" in line
            and i + 1 < n
            and re.match(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$", lines[i + 1])
        ):
            rows = [line]
            j = i + 1
            rows.append(lines[j])  # separator
            j += 1
            while j < n and "|" in lines[j] and lines[j].strip():
                rows.append(lines[j])
                j += 1
            out.append(_parse_table(rows))
            i = j
            continue

        # lists
        lm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if lm:
            ordered = bool(re.match(r"\d+\.", lm.group(2)))
            tag = "ol" if ordered else "ul"
            items = []
            while i < n:
                m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                if not m:
                    if lines[i].strip() == "":
                        break
                    # continuation line of previous item
                    if items:
                        items[-1] += " " + lines[i].strip()
                        i += 1
                        continue
                    break
                items.append(m.group(3))
                i += 1
            body = "".join(f"<li>{render_inline(it)}</li>" for it in items)
            out.append(f"<{tag}>{body}</{tag}>")
            continue

        # paragraph
        buf = [line]
        i += 1
        while (
            i < n
            and lines[i].strip()
            and not re.match(r"^\s*(```|#{3,6}\s|[-*]\s|\d+\.\s)", lines[i])
            and lines[i].strip() not in ("---", "***", "___")
        ):
            buf.append(lines[i])
            i += 1
        out.append(f"<p>{render_inline(' '.join(s.strip() for s in buf))}</p>")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
def split_sections(body: str):
    """Return (intro_region, [(display_title, token, content), ...])."""
    parts = re.split(r"(?m)^##\s+", body)
    intro = parts[0]
    # drop the leading "# Title" line from intro region
    intro = re.sub(r"(?m)^#\s+.*$", "", intro, count=1).strip()
    sections = []
    for chunk in parts[1:]:
        nl = chunk.find("\n")
        heading = chunk if nl == -1 else chunk[:nl]
        content = "" if nl == -1 else chunk[nl + 1 :]
        clean = re.sub(r"^\d+\.\s+", "", heading.strip())
        token = SECTION_TOKENS.get(clean.lower(), "other")
        sections.append((clean, token, content.strip()))
    return intro, sections


def get_title(body: str) -> str:
    m = re.search(r"(?m)^#\s+(.*)$", body)
    return m.group(1).strip() if m else "Plan"


# --------------------------------------------------------------------------- #
# Status log timeline
# --------------------------------------------------------------------------- #
# Status-log entries are human-written `- YYYY-MM-DD <sep> narrative` lines (sep
# is —, :, or -), often wrapping across lines with nested sub-bullets. The old
# strict `Task <id> — <sha>` / `Wave <id> complete` grammar matched ZERO real
# logs (all fell back to prose). This relaxed parser captures any dated bullet.
_STATUS_DATE = re.compile(r"^[-*]\s+(\d{4}-\d{2}-\d{2})\s*[—:–-]+\s*(.*)$")
_STATUS_BULLET = re.compile(r"^[-*]\s+(.*)$")

# Entry kind from keywords -> colour (deterministic map; first match wins).
# Priority build > decision > plan > open so e.g. "design finalized … open ops
# items" reads as PLAN (its dominant act), not OPEN.
_KIND_RULES = [
    (
        "build",
        re.compile(
            r"\b(built|build|ship(?:s|ped)?|implement(?:ed)?|execut(?:e[ds]?|ed)|"
            r"complete[ds]?|verified|passed|merged|landed)\b",
            re.I,
        ),
    ),
    (
        "decision",
        re.compile(
            r"\b(client|decisions?|decided|confirmed|chose|chosen|accepted|agreed|"
            r"answered|direction|descope[d]?)\b|\bscope\b",
            re.I,
        ),
    ),
    (
        "plan",
        re.compile(
            r"\b(plan(?:ned)?|drafted|draft|written|design|research|brief|"
            r"review(?:ed)?|revis(?:e[ds]?|ion)|finaliz(?:e[ds]?)|rewrote|spec)\b",
            re.I,
        ),
    ),
    (
        "open",
        re.compile(
            r"\b(open|blockers?|blocked|awaiting|flagged|flag|todo|pending|"
            r"unresolved|deferred|outstanding|follow-up)\b",
            re.I,
        ),
    ),
]


def _status_kind(text: str) -> str:
    for kind, rx in _KIND_RULES:
        if rx.search(text):
            return kind
    return "note"


def parse_status_entries(content: str):
    """Return list of entry dicts: {date, note, subs:[...], kind}."""
    entries: list[dict] = []
    cur: dict | None = None
    for raw in content.split("\n"):
        if not raw.strip() or raw.strip().startswith("<!--"):
            continue
        indent = len(raw) - len(raw.lstrip())
        stripped = raw.strip()
        if indent == 0:
            md = _STATUS_DATE.match(stripped)
            if md:
                cur = {"date": md.group(1), "note": md.group(2).strip(), "subs": []}
                entries.append(cur)
                continue
            mb = _STATUS_BULLET.match(stripped)
            if mb:
                cur = {"date": "", "note": mb.group(1).strip(), "subs": []}
                entries.append(cur)
                continue
            if cur is not None:  # top-level continuation prose
                cur["note"] += " " + stripped
            continue
        if cur is None:
            continue
        sb = _STATUS_BULLET.match(stripped)  # indented sub-bullet vs continuation
        if sb:
            cur["subs"].append(sb.group(1).strip())
        else:
            cur["note"] += " " + stripped
    for e in entries:
        e["kind"] = _status_kind(e["note"] + " " + " ".join(e["subs"]))
    return entries


def _done_task_ids(entries, task_ids) -> set[str]:
    """Task ids the log marks complete (in a build entry, or beside a ✓/'complete'
    marker), intersected with real plan task ids so the progress strip is honest."""
    valid = set(task_ids)
    done: set[str] = set()
    for e in entries:
        blob = e["note"] + " " + " ".join(e["subs"])
        if (
            e.get("kind") == "build"
            or "✓" in blob
            or re.search(r"\bcomplete", blob, re.I)
        ):
            done |= set(re.findall(r"\bP?\d+(?:\.\d+)+\b", blob)) & valid
    return done


_TIMELINE_FOLD_THRESHOLD = 8  # collapse older entries past this many
_TIMELINE_KEEP_RECENT = 5


def _render_timeline_entry(e: dict) -> str:
    kind = e.get("kind", "note")
    date = f'<span class="t-date">{esc(e["date"])}</span>' if e["date"] else ""
    chip = f'<span class="t-kind" data-kind="{kind}">{kind}</span>'
    note = f'<div class="t-note">{render_inline(e["note"])}</div>' if e["note"] else ""
    subs = ""
    if e["subs"]:
        lis = "".join(f"<li>{render_inline(s)}</li>" for s in e["subs"])
        subs = f'<ul class="t-subs">{lis}</ul>'
    return (
        f'<div class="timeline-entry" data-kind="{kind}">'
        f'<div class="t-meta">{date}{chip}</div>{note}{subs}</div>'
    )


def render_timeline(content: str):
    entries = parse_status_entries(content)
    if not entries:
        return None  # caller falls back to prose so rich free-form logs survive
    rows = ['<div class="timeline">']
    if len(entries) > _TIMELINE_FOLD_THRESHOLD:
        older, recent = (
            entries[:-_TIMELINE_KEEP_RECENT],
            entries[-_TIMELINE_KEEP_RECENT:],
        )
        inner = "".join(_render_timeline_entry(e) for e in older)
        rows.append(
            f'<details class="timeline-fold"><summary>Show {len(older)} earlier '
            f"updates</summary>{inner}</details>"
        )
        rows.extend(_render_timeline_entry(e) for e in recent)
    else:
        rows.extend(_render_timeline_entry(e) for e in entries)
    rows.append("</div>")
    return "\n".join(rows), entries


# --------------------------------------------------------------------------- #
# Builders for placeholders
# --------------------------------------------------------------------------- #
def build_stats(tasks, waves, status_entries):
    if not tasks:
        return ""
    files = set()
    for t in tasks:
        for f in t["files"].split(","):
            f = f.strip()
            if f:
                files.add(f)
    n_waves = len(waves)
    parallel = sum(1 for w in waves if len(waves[w]) >= 2)
    blocks = [
        f'<div class="stat"><span class="stat-num">{len(tasks)}</span><span class="stat-lbl">Tasks</span></div>',
        f'<div class="stat"><span class="stat-num">{n_waves}</span><span class="stat-lbl">Waves</span></div>',
        f'<div class="stat"><span class="stat-num">{len(files)}</span><span class="stat-lbl">Files touched</span></div>',
        f'<div class="stat"><span class="stat-num">{parallel}/{n_waves}</span><span class="stat-lbl">Parallel waves</span></div>',
    ]
    progress = ""
    if status_entries:
        done_ids = _done_task_ids(status_entries, [t["id"] for t in tasks])
        if done_ids:
            n = len(tasks)
            m = len(done_ids)
            pct = round(m / n * 100) if n else 0
            progress = (
                '<div class="stat-progress"><div class="progress-row">'
                '<span class="progress-label">Progress</span>'
                '<div class="progress-track">'
                f'<div class="progress-fill" style="width:{pct}%"></div></div>'
                f'<span class="progress-pct">{m}/{n}</span></div></div>'
            )
    return f'<div class="stats-card">{"".join(blocks)}{progress}</div>'


SUMMARY_BEGIN = "<!-- AT-A-GLANCE:BEGIN (generated — do not edit; refreshed by render_plan.py --summarize) -->"
SUMMARY_END = "<!-- AT-A-GLANCE:END -->"
_SUMMARY_RE = re.compile(re.escape(SUMMARY_BEGIN) + r".*?" + re.escape(SUMMARY_END), re.DOTALL)
_DONE_TRUNC = 80
_FENCE = chr(96) * 3  # ``` without embedding a literal triple-backtick run in this source


def _mermaid_node_id(task_id):
    return "T" + re.sub(r"[^0-9A-Za-z]", "_", task_id)


def render_summary_block(tasks, done_ids):
    """Additive 'At a glance' block (both sentinels included). Pure + deterministic."""
    if not tasks:
        return f"{SUMMARY_BEGIN}\n## At a glance\n\n_No tasks defined yet._\n{SUMMARY_END}"
    files = set()
    for t in tasks:
        for f in t["files"].split(","):
            f = f.strip()
            if f:
                files.add(f)
    waves = sorted({t["wave"] for t in tasks}, key=wave_sort_key)
    ordered = sorted(tasks, key=lambda t: (wave_sort_key(t["wave"]), natural_key(t["id"])))

    def title(t):
        return t.get("title") or t["id"]

    def cell(s):
        return str(s).replace("|", "\\|")

    def done_cell(t):
        d = " ".join(t["done"].split())
        return (d[:_DONE_TRUNC] + "…") if len(d) > _DONE_TRUNC else d

    # count only done ids that are real task ids, so the count stays consistent
    # with the per-task checkboxes below (a stale Status-Log id can't inflate it).
    n_done = len(done_ids & {t["id"] for t in tasks})
    count_line = (
        f"**{len(tasks)} tasks · {len(waves)} waves · "
        f"{len(files)} files · {n_done}/{len(tasks)} done**"
    )
    rows = ["| Wave | Task | Title | Files | Done (acceptance) |", "|---|---|---|---|---|"]
    for t in ordered:
        rows.append(
            f"| {cell(t['wave'])} | {cell(t['id'])} | {cell(title(t))} | "
            f"{cell(t['files'])} | {cell(done_cell(t))} |"
        )
    table = "\n".join(rows)

    mer = [f"{_FENCE}mermaid", "flowchart LR"]
    for idx, w in enumerate(waves):
        mer.append(f"  subgraph W{idx}[Wave {w}]")
        for t in [x for x in ordered if x["wave"] == w]:
            label = f"{t['id']} {title(t)}".replace('"', "'")
            mer.append(f'    {_mermaid_node_id(t["id"])}["{label}"]')
        mer.append("  end")
    for idx in range(len(waves) - 1):
        mer.append(f"  W{idx} --> W{idx + 1}")
    mer.append(_FENCE)
    mermaid = "\n".join(mer)

    checks = [f"- [{'x' if t['id'] in done_ids else ' '}] {t['id']} — {title(t)}" for t in ordered]
    progress = "### Progress\n" + "\n".join(checks)

    inner = "\n\n".join(["## At a glance", count_line, table, mermaid, progress])
    return f"{SUMMARY_BEGIN}\n{inner}\n{SUMMARY_END}"


def inject_summary_block(plan_text, block):
    """Insert/replace the 'At a glance' block. Idempotent by sentinel.
    Both sentinels present -> replace the region between them (inclusive).
    Else insert `block` immediately before the first '## ' heading (keeping the
    H1 and any directive blockquote above it); no '## ' -> append; empty -> block."""
    has_begin = SUMMARY_BEGIN in plan_text
    has_end = SUMMARY_END in plan_text
    if has_begin and has_end:
        return _SUMMARY_RE.sub(lambda _m: block, plan_text, count=1)  # lambda: avoid backref parsing
    if has_begin != has_end:
        # Orphan sentinel (a half-deleted generated region): strip it before a
        # fresh insert, else a later inject's non-greedy _SUMMARY_RE would span
        # from the orphan BEGIN into the new block's END and swallow real content.
        plan_text = plan_text.replace(SUMMARY_BEGIN, "").replace(SUMMARY_END, "")
    m = re.search(r"(?m)^##\s", plan_text)
    if m:
        return plan_text[: m.start()] + block + "\n\n" + plan_text[m.start() :]
    if plan_text.strip():
        return plan_text.rstrip("\n") + "\n\n" + block + "\n"
    return block + "\n"


def build_wave_diagram(waves):
    if not waves:
        return ""
    order = sorted(waves.keys(), key=wave_sort_key)
    col_w, col_gap, node_w, node_h, node_gap, pad_top, pad_left, pad_bottom = (
        170,
        40,
        130,
        30,
        10,
        52,
        12,
        16,
    )
    max_tasks = max(len(waves[w]) for w in order)
    width = pad_left * 2 + len(order) * col_w + (len(order) - 1) * col_gap
    height = pad_top + max_tasks * (node_h + node_gap) + pad_bottom
    svg = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img">',
        '<defs><marker id="arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="3" '
        'orient="auto"><path class="arrowhead" d="M0,0 L6,3 L0,6 Z"/></marker></defs>',
    ]
    centers = []
    for idx, w in enumerate(order):
        col_x = pad_left + idx * (col_w + col_gap)
        node_x = col_x + (col_w - node_w) / 2
        n = len(waves[w])
        label = "Wave —" if w == "—" else f"Wave {w}"
        meta = f"{n} tasks · parallel" if n >= 2 else f"{n} task"
        svg.append(
            f'<text class="wave-label" x="{col_x + col_w / 2:.0f}" y="20" text-anchor="middle">{esc(label)}</text>'
        )
        svg.append(
            f'<text class="wave-meta" x="{col_x + col_w / 2:.0f}" y="38" text-anchor="middle">{esc(meta)}</text>'
        )
        for ti, t in enumerate(waves[w]):
            y = pad_top + ti * (node_h + node_gap)
            tid = t["id"] or "?"
            svg.append(f'<a href="#task-{slugify(tid)}">')
            svg.append(
                f'<rect class="task-node" x="{node_x:.0f}" y="{y}" width="{node_w}" '
                f'height="{node_h}" rx="8"/>'
            )
            svg.append(
                f'<text class="task-id" x="{node_x + node_w / 2:.0f}" y="{y + node_h / 2 + 4:.0f}" '
                f'text-anchor="middle">Task {esc(tid)}</text>'
            )
            svg.append("</a>")
        centers.append((col_x, col_x + col_w))
    mid_y = pad_top - 4
    for idx in range(len(order) - 1):
        x1 = centers[idx][1]
        x2 = centers[idx + 1][0]
        svg.append(f'<path class="arrow" d="M{x1},{mid_y} L{x2 - 6},{mid_y}"/>')
    svg.append("</svg>")
    return "\n".join(svg)


def render_task_card(task, expanded=False, subtask_html=""):
    tid = task["id"] or "?"
    title = task.get("title", "")
    chips = ""
    for f in task["files"].split(","):
        f = f.strip()
        if f:
            chips += f'<span class="file-chip">{esc(f)}</span>'
    collapsed = "false" if expanded else "true"
    title_html = render_inline(title) if title else ""
    action_html = md_to_html(task["action"]) if task["action"] else ""
    done_html = md_to_html(task["done"]) if task["done"] else ""
    return f"""<article class="task-card" id="task-{slugify(tid)}" data-collapsed="{collapsed}">
  <div class="task-card-header">
    <span class="id">Task {esc(tid)}</span>
    <span class="title">{title_html}</span>
    <span class="chev">▾</span>
  </div>
  <div class="task-card-body">
    <div class="task-block"><div class="task-block-label">Files</div><div>{chips}</div></div>
    <div class="task-block"><div class="task-block-label">Action</div><div>{action_html}</div></div>
    <div class="task-block verify-block">
      <div class="task-block-label">Verify</div>
      <pre><code>{esc(task["verify"])}</code></pre>
      <button type="button" class="copy-btn">Copy</button>
    </div>
    <div class="task-block"><div class="task-block-label">Done</div><div>{done_html}</div></div>
    {subtask_html}
  </div>
</article>"""


def build_tasks_block(waves):
    if not waves:
        return '<section data-wave="empty"><div class="empty-state">No tasks defined yet</div></section>'
    order = sorted(waves.keys(), key=wave_sort_key)
    lowest = order[0]
    out = []
    for w in order:
        label = "Wave —" if w == "—" else f"Wave {w}"
        out.append(f'<section data-wave="{esc(w)}" id="wave-{slugify(w)}">')
        out.append(f"<h3>{esc(label)}</h3>")
        for idx, t in enumerate(waves[w]):
            expanded = w == lowest and idx == 0
            subs = t.get("subtasks", [])
            sub_html = ""
            if subs:
                inner = "".join(render_task_card(s) for s in subs)
                sub_html = f'<div class="subtasks">{inner}</div>'
            out.append(render_task_card(t, expanded=expanded, subtask_html=sub_html))
        out.append("</section>")
    return "\n".join(out)


def build_toc(sections, waves, has_review=False):
    items = []
    for title, token, _ in sections:
        if token == "tasks":
            continue
        items.append(f'<li><a href="#{slugify(title)}">{esc(title)}</a></li>')
    if has_review:
        items.append('<li><a href="#plan-review">Plan Review</a></li>')
    items.append('<li><a href="#tasks">Tasks</a></li>')
    for w in sorted(waves.keys(), key=wave_sort_key):
        label = "Wave —" if w == "—" else f"Wave {w}"
        items.append(f'<li><a href="#wave-{slugify(w)}">{esc(label)}</a></li>')
    return f"<ul>{''.join(items)}</ul>"


# Clause boundary for intro fields: a `;` (always — the parallel-action
# separator used in Architecture prose) OR a sentence-final `. ` before a
# capital / markdown-open char. Dotted identifiers (`render.yaml`,
# `sessionmanager.session()`) live inside backticks, so their `.` is followed by
# a backtick — never whitespace — and never splits. The capital/markdown
# lookahead keeps decimals (`SQLAlchemy 2.0 release`) and abbreviations from
# false-splitting. Verified against all repo plans: zero spurious breaks.
INTRO_CLAUSE = re.compile(r";\s+|(?<=\.)\s+(?=[A-Z*`(\[\"'])")


def _split_clauses(text: str) -> list[str]:
    return [
        c
        for c in (p.strip().rstrip(";").strip() for p in INTRO_CLAUSE.split(text))
        if c
    ]


# Architecture clauses are actions on components, so classify each by verb and
# colour-code it ("scope of change" map). This is a deterministic keyword map
# (CLAUDE.local.md §8 — a dict/regex, never a model call). Order = priority;
# first match wins, so a negation ("no … changes") outranks the bare "changes"
# verb, and a real mutation ("Existing logger swapped") outranks the incidental
# "existing". Anything unmatched falls back to "note" (rendered, never dropped).
_ACTION_RULES = [
    (
        "exclude",
        re.compile(
            r"^\s*(no|zero|never|without)\b"
            r"|\b(no|zero)\s+(new|migration|runtime|extra|additional|further|other|schema|breaking)\b",
            re.I,
        ),
    ),
    (
        "remove",
        re.compile(
            r"\b(remove[sd]?|removing|delete[sd]?|deleting|drop(?:s|ped)?|strip(?:s|ped)?|"
            r"deprecate[sd]?|retire[sd]?|prune[sd]?)\b",
            re.I,
        ),
    ),
    (
        "add",
        re.compile(
            r"\b(add[s]?|added|adding|new|create[sd]?|introduce[sd]?|expose[sd]?|ship[s]?|"
            r"wire[sd]?|scaffold|declare[sd]?|register[sd]?|plug)\b|\bstand up\b",
            re.I,
        ),
    ),
    (
        "change",
        re.compile(
            r"\b(replace[sd]?|swap(?:s|ped)?|change[sd]?|modif(?:y|ies|ied)|update[sd]?|"
            r"extend[s]?|extended|adapt[s]?|adapted|rework(?:s|ed)?|refactor[s]?|convert[sd]?|"
            r"migrate[sd]?|rename[sd]?|move[sd]?|fix(?:es|ed)?|inject[sd]?|silence[sd]?|"
            r"edit[s]?|edited)\b",
            re.I,
        ),
    ),
    (
        "keep",
        re.compile(
            r"\b(keep[s]?|kept|reuse[sd]?|preserve[sd]?|retain[sd]?|untouched|unchanged|"
            r"existing|leave[s]?|left)\b",
            re.I,
        ),
    ),
]
_ACTION_LABELS = {
    "add": "add",
    "change": "change",
    "keep": "keep",
    "remove": "remove",
    "exclude": "exclude",
    "note": "·",
}
_SUMMARY_ORDER = ["add", "change", "keep", "remove", "exclude"]  # note omitted


def _classify_clause(clause: str) -> str:
    for cat, rx in _ACTION_RULES:
        if rx.search(clause):
            return cat
    return "note"


def _render_change_map(value: str) -> str:
    """Architecture -> a colour-coded scope-of-change panel: a count dashboard
    of action categories plus one tagged row per clause. A single-clause field
    (no real breakdown) stays a plain paragraph."""
    clauses = _split_clauses(value)
    if len(clauses) <= 1:
        return f"<p>{render_inline(value)}</p>"
    tagged = [(c, _classify_clause(c)) for c in clauses]
    counts: dict[str, int] = {}
    for _, cat in tagged:
        counts[cat] = counts.get(cat, 0) + 1
    summary = "".join(
        f'<span class="change-tag" data-act="{cat}">{counts[cat]} {_ACTION_LABELS[cat]}</span>'
        for cat in _SUMMARY_ORDER
        if cat in counts
    )
    items = "".join(
        f'<li data-act="{cat}"><span class="act-badge" data-act="{cat}">'
        f'{_ACTION_LABELS[cat]}</span><span class="act-text">{render_inline(c)}</span></li>'
        for c, cat in tagged
    )
    summary_html = f'<div class="change-summary">{summary}</div>' if summary else ""
    return f'<div class="change-map">{summary_html}<ul class="change-list">{items}</ul></div>'


def _render_field_value(key: str, value: str) -> str:
    # Tech Stack -> chips (comma-separated tech list). Architecture -> scope-of-
    # change map (verb-classified rows). Goal/others -> bullets when multi-clause,
    # else a single paragraph (a one-line Goal stays prose).
    if key == "Tech Stack":
        items = [v.strip().rstrip(".").strip() for v in value.split(",") if v.strip()]
        chips = "".join(
            f'<span class="tech-chip">{render_inline(it)}</span>' for it in items if it
        )
        return f'<div class="tech-chips">{chips}</div>'
    if key == "Architecture":
        return _render_change_map(value)
    clauses = _split_clauses(value)
    if len(clauses) > 1:
        lis = "".join(f"<li>{render_inline(c)}</li>" for c in clauses)
        return f'<ul class="intro-list">{lis}</ul>'
    return f"<p>{render_inline(value)}</p>"


def build_intro_card(intro_region: str) -> str:
    fields = []
    for key in ("Goal", "Architecture", "Tech Stack"):
        # Capture the WHOLE paragraph (PLAN.md wraps these fields across several
        # lines). Stop at a blank line, the next `**Label:**` field, or EOF, then
        # collapse the wrapped newlines to spaces — same join md_to_html uses for
        # paragraphs — so multi-line values render in full and bold spanning a
        # line break (e.g. `**weekly Render\ncron**`) closes correctly.
        m = re.search(
            rf"(?ms)^\*\*{re.escape(key)}:\*\*\s*(.*?)(?=\n\s*\n|\n\*\*[^*]+:\*\*|\Z)",
            intro_region,
        )
        if m:
            value = re.sub(r"\s+", " ", m.group(1)).strip()
            fields.append((key, value))
    if not fields:
        return ""
    rows = "".join(
        f"<dt>{esc(k)}</dt><dd>{_render_field_value(k, v)}</dd>" for k, v in fields
    )
    return f'<div class="intro-card"><dl>{rows}</dl></div>'


def build_source_links(plan_dir: Path) -> str:
    links = []
    for f in SOURCE_FILES:
        if (plan_dir / f).exists():
            links.append(f'<a class="source-link" href="{f}">{f}</a>')
    return "".join(links)


# --------------------------------------------------------------------------- #
# Section-specific rich rendering (risks / success / non-goals / motivation).
# Each renderer DEGRADES GRACEFULLY: a Markdown table or a non-list body falls
# back to md_to_html, and leading/trailing prose around a bullet list is
# preserved. Only a clean bullet list gets the structured treatment.
# --------------------------------------------------------------------------- #
def _has_md_table(content: str) -> bool:
    lines = content.split("\n")
    return any(
        "|" in lines[i] and re.match(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$", lines[i + 1])
        for i in range(len(lines) - 1)
    )


def _md_list_items(content: str):
    """Split a section body into (pre_html, items, post_html). `items` are the
    top-level `-`/`*` bullets with wrapped continuation lines folded into one
    string each; pre/post are prose rendered around the list."""
    lines = content.split("\n")
    i, n = 0, len(lines)
    pre = []
    while i < n and not re.match(r"^\s*[-*]\s+", lines[i]):
        pre.append(lines[i])
        i += 1
    items: list[str] = []
    cur = None
    while i < n:
        m = re.match(r"^\s*[-*]\s+(.*)$", lines[i])
        if m:
            if cur is not None:
                items.append(cur)
            cur = m.group(1).strip()
        elif lines[i].strip() == "":
            i += 1
            break
        elif cur is not None:
            cur += " " + lines[i].strip()
        i += 1
    if cur is not None:
        items.append(cur)
    post = lines[i:]
    pre_h = md_to_html("\n".join(pre).strip()) if any(x.strip() for x in pre) else ""
    post_h = md_to_html("\n".join(post).strip()) if any(x.strip() for x in post) else ""
    return pre_h, items, post_h


# Risk severity — extracted ONLY from explicit author signals so we never
# fabricate a RAG colour. `(Medium)` / `(Real)` etc. tags map per the standard
# register scheme (Critical/High/Real -> high, Medium/Moderate/Known -> medium,
# Low -> low); an untagged risk stays neutral.
_SEV_TAG = re.compile(r"\((critical|high|medium|moderate|low|real|known)\)", re.I)
_SEV_MAP = {
    "critical": "high",
    "high": "high",
    "real": "high",
    "medium": "medium",
    "moderate": "medium",
    "known": "medium",
    "low": "low",
}


def _risk_severity(title: str, body: str):
    m = _SEV_TAG.search(title) or _SEV_TAG.search(body[:60])
    if m:
        return _SEV_MAP[m.group(1).lower()]
    if re.match(r"^\s*KNOWN\b", body):
        return "medium"
    return None


def render_risks(content: str) -> str:
    if _has_md_table(content):
        return md_to_html(content)
    pre_h, items, post_h = _md_list_items(content)
    if not items:
        return md_to_html(content)
    cards = []
    for it in items:
        m = re.match(r"\*\*(.+?)\*\*\s*[—–-]\s*(.*)$", it, re.S)
        title, body = (m.group(1).strip(), m.group(2).strip()) if m else ("", it)
        sev = _risk_severity(title, body)
        title = _SEV_TAG.sub("", title).strip()  # tag now shown as a chip
        mit = ""
        parts = re.split(r"(?i)\bmitigation:\s*", body, maxsplit=1)
        if len(parts) == 2:
            body, mit = parts[0].strip().rstrip(".;— "), parts[1].strip()
        sev_chip = (
            f'<span class="risk-sev" data-sev="{sev}">{sev}</span>' if sev else ""
        )
        head = (
            f'<div class="risk-head"><span class="risk-title">{render_inline(title)}</span>'
            f"{sev_chip}</div>"
            if (title or sev)
            else ""
        )
        body_h = f'<div class="risk-body">{render_inline(body)}</div>' if body else ""
        mit_h = (
            f'<div class="risk-mit"><span class="risk-mit-label">Mitigation</span> '
            f"{render_inline(mit)}</div>"
            if mit
            else ""
        )
        cards.append(
            f'<div class="risk-card" data-sev="{sev or "none"}">{head}{body_h}{mit_h}</div>'
        )
    return f'{pre_h}<div class="risk-grid">{"".join(cards)}</div>{post_h}'


def render_success(content: str) -> str:
    if _has_md_table(content):
        return md_to_html(content)
    pre_h, items, post_h = _md_list_items(content)
    if not items:
        return md_to_html(content)
    lis = []
    for it in items:
        h = render_inline(it).replace("→", '<span class="then-arrow">→</span>')
        lis.append(
            f'<li class="check-item"><span class="check-box"></span><span>{h}</span></li>'
        )
    return f'{pre_h}<ul class="check-list">{"".join(lis)}</ul>{post_h}'


def render_nongoals(content: str) -> str:
    if _has_md_table(content):
        return md_to_html(content)
    pre_h, items, post_h = _md_list_items(content)
    if not items:
        return md_to_html(content)
    lis = "".join(
        f'<li><span class="scope-mark">⊘</span><span>{render_inline(it)}</span></li>'
        for it in items
    )
    return f'{pre_h}<ul class="scope-out">{lis}</ul>{post_h}'


def render_motivation(content: str) -> str:
    return f'<div class="callout">{md_to_html(content)}</div>'


_SECTION_RENDERERS = {
    "risks": render_risks,
    "success": render_success,
    "non-goals": render_nongoals,
    "motivation": render_motivation,
}


def build_sections(sections, status_entries_holder):
    out = []
    for title, token, content in sections:
        if token == "tasks":
            continue
        anchor = slugify(title)
        out.append(f'<h2 id="{anchor}">{esc(title)}</h2>')
        if token == "status":
            tl = render_timeline(content)
            if tl is None:
                out.append(md_to_html(content))  # preserve free-form log
            else:
                html_str, entries = tl
                status_entries_holder.extend(entries)
                out.append(html_str)
        elif token in _SECTION_RENDERERS:
            out.append(_SECTION_RENDERERS[token](content))
        else:
            out.append(md_to_html(content))
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Plan Review (--review): renders an agent-supplied, graph-derived sidecar JSON.
# The script never calls the code-review-graph MCP itself (offline/deterministic);
# the agent gathers impact/tests/existence and writes the JSON. Schema:
#   {"files":[{"path","status":"new|existing|missing","dependents":int,
#              "dependent_names":[...],"tests":[...],"risk":"high|medium|low",
#              "note":"..."}], "flows":[...]}
# --------------------------------------------------------------------------- #
def build_review(review: dict) -> str:
    files = review.get("files") or []
    if not files:
        return ""

    total = len(files)
    new = sum(1 for f in files if f.get("status") == "new")
    existing = sum(1 for f in files if f.get("status") == "existing")
    missing = sum(1 for f in files if f.get("status") == "missing")
    deps_total = sum(int(f.get("dependents") or 0) for f in files)
    untested = sum(1 for f in files if not (f.get("tests") or []))

    stats = (
        '<div class="stats-card">'
        f'<div class="stat"><span class="stat-num">{total}</span><span class="stat-lbl">Files</span></div>'
        f'<div class="stat"><span class="stat-num">{new}</span><span class="stat-lbl">New</span></div>'
        f'<div class="stat"><span class="stat-num">{existing}</span><span class="stat-lbl">Existing</span></div>'
        f'<div class="stat"><span class="stat-num">{deps_total}</span><span class="stat-lbl">Dependents</span></div>'
        f'<div class="stat"><span class="stat-num">{untested}</span><span class="stat-lbl">Untested</span></div>'
        "</div>"
    )

    rows = []
    for f in files:
        status = f.get("status", "existing")
        risk = f.get("risk", "low")
        tests = f.get("tests") or []
        tcell = str(len(tests)) if tests else "—"
        rows.append(
            f"<tr><td><code>{esc(f.get('path', ''))}</code></td>"
            f'<td><span class="file-status" data-status="{esc(status)}">{esc(status)}</span></td>'
            f"<td>{esc(str(f.get('dependents', 0)))}</td>"
            f"<td>{tcell}</td>"
            f'<td><span class="risk-chip" data-risk="{esc(risk)}">{esc(risk)}</span></td></tr>'
        )
    table = (
        '<table class="review-table"><thead><tr><th>File</th><th>Status</th>'
        "<th>Dependents</th><th>Tests</th><th>Risk</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )

    high = [f for f in files if f.get("risk") == "high"]
    cards = ""
    if high:
        items = []
        for f in high:
            note = f.get("note", "")
            deps = f.get("dependent_names") or []
            dep_html = ""
            if deps:
                chips = "".join(
                    f'<span class="file-chip">{esc(d)}</span>' for d in deps[:12]
                )
                more = (
                    f' <span class="review-muted">+{len(deps) - 12} more</span>'
                    if len(deps) > 12
                    else ""
                )
                dep_html = (
                    '<div class="task-block"><div class="task-block-label">Dependents</div>'
                    f"<div>{chips}{more}</div></div>"
                )
            note_html = f"<p>{render_inline(note)}</p>" if note else ""
            items.append(
                '<div class="review-card"><div class="review-card-head">'
                f"<code>{esc(f.get('path', ''))}</code>"
                '<span class="risk-chip" data-risk="high">high</span></div>'
                f"{note_html}{dep_html}</div>"
            )
        cards = f'<div class="review-grid">{"".join(items)}</div>'

    flows = review.get("flows") or []
    flow_html = ""
    if flows:
        chips = "".join(f'<span class="wave-pill">{esc(fl)}</span>' for fl in flows)
        flow_html = (
            '<div class="task-block"><div class="task-block-label">Affected flows</div>'
            f'<div class="wave-strip">{chips}</div></div>'
        )

    missing_note = ""
    if missing:
        missing_note = (
            f'<p class="review-warn">⚠ {missing} file(s) referenced by the plan were '
            "not found in the graph — verify the path or treat as newly created.</p>"
        )

    return (
        '<h2 id="plan-review">Plan Review</h2>'
        f"{stats}{missing_note}{flow_html}{table}{cards}"
    )


def emit_files_json(plan_path: Path) -> str:
    """Emit the plan's per-task file list as JSON so the agent knows what to
    query in the code-review-graph before building the --review sidecar."""
    text = plan_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    fm, body = parse_frontmatter(text)
    tasks, _ = extract_tasks(body)
    files: set[str] = set()
    tlist = []
    for t in tasks:
        fl = [f.strip() for f in t["files"].split(",") if f.strip()]
        files.update(fl)
        tlist.append({"id": t["id"], "wave": t["wave"], "files": fl})
    return json.dumps(
        {"slug": fm.get("slug", ""), "files": sorted(files), "tasks": tlist}, indent=2
    )


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def _specs_bases() -> list[Path]:
    """Candidate specs/ roots, in priority order: cwd/specs, then this skill's
    own <root>/specs (TEMPLATE_PATH is .../.claude/skills/visual-planner/).
    Searching both lets the skill work whether invoked from apps/api or repo root."""
    bases, seen = [], set()
    for cand in (Path("specs"), TEMPLATE_PATH.parents[3] / "specs"):
        if cand.is_dir():
            key = cand.resolve()
            if key not in seen:
                seen.add(key)
                bases.append(cand)
    return bases


def resolve_input(arg: str) -> Path:
    p = Path(arg)
    if arg.endswith("PLAN.md") and p.exists():
        return p
    matches, seen = [], set()
    for base in _specs_bases():
        for m in sorted(base.glob(f"**/{arg}/PLAN.md")):
            key = m.resolve()
            if key not in seen:
                seen.add(key)
                matches.append(m)
    if not matches:
        raise SystemExit(f'No PLAN.md found for slug "{arg}".')
    if len(matches) > 1:
        lst = ", ".join(str(m) for m in matches)
        raise SystemExit(
            f'Multiple PLAN.md files match slug "{arg}": {lst}. Pass an explicit path instead.'
        )
    return matches[0]


def nest_subtasks(tasks, warnings):
    by_id = {t["id"]: t for t in tasks}
    top = []
    for t in tasks:
        segs = t["id"].split(".")
        if len(segs) >= 3:
            parent_id = ".".join(segs[:-1])
            parent = by_id.get(parent_id)
            if parent is not None:
                parent.setdefault("subtasks", []).append(t)
                continue
            warnings.append(f"Orphaned sub-task {t['id']} attached as top-level")
        top.append(t)
    return top


def group_waves(top_tasks):
    waves: dict[str, list] = {}
    for t in top_tasks:
        waves.setdefault(t["wave"], []).append(t)
    for w in waves:
        waves[w].sort(key=lambda t: natural_key(t["id"]))
    return waves


def attach_titles(tasks, body):
    """Rule 4a: nearest preceding `### Task <id> — Title` heading."""
    headings = list(re.finditer(r"(?m)^###\s+Task\s+(\S+)\s*[—-]\s*(.*)$", body))
    for t in tasks:
        for h in headings:
            if h.group(1) == t["id"]:
                t["title"] = h.group(2).strip()


def render(plan_path: Path, review: dict | None = None) -> tuple[str, list[str], dict]:
    text = plan_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    fm, body = parse_frontmatter(text)
    warnings: list[str] = []

    tasks, spans = extract_tasks(body)
    attach_titles(tasks, body)

    # strip task spans from prose body (reverse order to keep offsets valid)
    prose = body
    for start, end in sorted(spans, reverse=True):
        prose = prose[:start] + prose[end:]
    # collapse now-empty ```xml fences left behind by stripping fenced tasks
    prose = re.sub(r"(?m)^```xml\s*\n```\s*$", "", prose)

    title = get_title(body)
    intro_region, sections = split_sections(prose)

    top_tasks = nest_subtasks(tasks, warnings)
    waves = group_waves(top_tasks)

    status_entries: list = []
    sections_html = build_sections(sections, status_entries)

    status = (fm.get("status") or "proposed").lower()
    if status not in ("proposed", "active", "paused", "shipped"):
        status = "proposed"

    fields = {
        "TITLE": esc(title),
        "STATUS_BADGE": f'<span class="badge" data-status="{status}">{status}</span>',
        "OWNER": esc(fm["owner"]) if fm.get("owner") else "—",
        "CREATED": fm.get("created") or "—",
        "SLUG": esc(fm["slug"]) if fm.get("slug") else "—",
        "STATS": build_stats(top_tasks, waves, status_entries),
        "INTRO_CARD": build_intro_card(intro_region),
        "WAVE_DIAGRAM": build_wave_diagram(waves),
        "SECTIONS": sections_html,
        "REVIEW": build_review(review) if review else "",
        "TASKS": build_tasks_block(waves),
        "TOC": build_toc(
            sections, waves, has_review=bool(review and review.get("files"))
        ),
        "SOURCE_LINKS": build_source_links(plan_path.parent),
    }

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    for key, val in fields.items():
        template = template.replace("{{" + key + "}}", val)

    meta = {
        "n_waves": len(waves) if waves else 1,
        "slug": fm.get("slug", ""),
        "n_tasks": len(tasks),
    }
    return template, warnings, meta


def self_check(html_text: str, meta: dict):
    """Mechanical checks before claiming success (SKILL.md Self-check).

    NOTE: the original spec's check #2 ("<title> must contain the slug") is
    unsatisfiable — the template hardcodes `<title>{{TITLE}} · plan</title>`
    where TITLE is the H1 text, not the slug. We honor the intent (right plan
    rendered + all placeholders substituted) with two stronger checks instead.
    """
    failures = []
    if not html_text.strip():
        failures.append("output is empty")
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", html_text)
    if leftover:
        failures.append(f"unsubstituted placeholders remain: {sorted(set(leftover))}")
    if meta["slug"] and meta["slug"] not in html_text:
        failures.append(f'slug "{meta["slug"]}" not present anywhere in output')
    wave_wrappers = len(re.findall(r'<section data-wave="', html_text))
    if wave_wrappers != meta["n_waves"]:
        failures.append(
            f"wave wrapper count {wave_wrappers} != expected {meta['n_waves']}"
        )
    return failures


USAGE = (
    "Usage: render_plan.py <PLAN.md|slug> [output.html] "
    "[--emit-files] [--review sidecar.json]"
)


def main(argv):
    args = argv[1:]
    emit_files = False
    review_path = None
    positionals = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--emit-files":
            emit_files = True
        elif a == "--review":
            i += 1
            if i >= len(args):
                raise SystemExit("--review requires a path to the sidecar JSON")
            review_path = args[i]
        elif a.startswith("--"):
            raise SystemExit(f"Unknown flag: {a}\n{USAGE}")
        else:
            positionals.append(a)
        i += 1

    if not positionals:
        raise SystemExit(USAGE)

    plan_path = resolve_input(positionals[0])

    if emit_files:
        print(emit_files_json(plan_path))
        return

    # --review writes a separate file so a later plain render (e.g. the auto
    # render after plan approval) does not clobber the review build.
    default_name = "PLAN.review.html" if review_path else "PLAN.html"
    out_path = (
        Path(positionals[1])
        if len(positionals) > 1
        else plan_path.parent / default_name
    )
    review = None
    if review_path:
        review = json.loads(Path(review_path).read_text(encoding="utf-8"))

    html_text, warnings, meta = render(plan_path, review)
    out_path.write_text(html_text, encoding="utf-8")

    failures = self_check(html_text, meta)
    size = out_path.stat().st_size

    for w in warnings:
        print(f"WARNING: {w}")
    if failures:
        for f in failures:
            print(f"SELF-CHECK FAILED: {f}")
        raise SystemExit(1)

    print(f"Wrote {out_path.resolve()} ({size} bytes).")
    print(f"  tasks={meta['n_tasks']} waves={meta['n_waves']}")
    print(f"Open with: open {out_path.resolve()}")


if __name__ == "__main__":
    main(sys.argv)
