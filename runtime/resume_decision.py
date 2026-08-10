#!/usr/bin/env python3
"""Return a deterministic, read-only resume decision for one harness run.

This is the single public resume authority (design #175).  It answers two independent
questions from one locked, semantically read-only inspection:

  1. Lifecycle route  - execute-plan / resume-repair / resume-review-chain / wait / stop /
     rebuild, derived from the durable FSM state in run_state.py.
  2. Task cursor      - which task completion claims the plan ledger + branch support, which
     Verify commands must be re-run, which task is next.

It deliberately does not transition state, rebuild a projection, or run any plan-authored
command; callers perform an explicit repair after seeing the result.  Contradictory or
unresolvable evidence fails closed with a structured ``stop``; absence stays explicit
unknown, never inferred success.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import run_state as rs

SCHEMA_VERSION = 1

PLAN_STATUSES = {"proposed", "active", "paused", "shipped"}

# Lifecycle routes that precede plan/task evidence (design 5.6).  ready_to_merge is not a
# WAITING_STATES member in the engine but resume treats it as an external wait.
_WAIT_STATES = rs.WAITING_STATES | {"ready_to_merge"}
_REPAIR_STATES = {"fixing_ci", "addressing_review"}

# Canonical execution spine, used to derive the legal catch-up path to implementing.
_SPINE = ["queued", "investigating", "planning", "implementing"]

# --- Plan / status-log parsing (parity-aligned with render_plan for ORDERED IDS only) ---

_MD_TASK_HEAD = re.compile(r"(?m)^###\s+Task\s+([0-9][\w.]*)[^\n]*$")
_MD_NEXT_HEAD = re.compile(r"(?m)^#{2,3}\s")
_MD_FIELD = re.compile(
    r"^[-*]\s+\*\*(Files|Action|Verify|Done|Criteria|Interfaces)(?::\*\*|\*\*:)\s*(.*)$",
    re.I,
)

# A completion claim is evaluated PER task mention (design 5.4).  A completion marker
# associated with one `Task X.Y` mention never completes another task named in the same
# entry; an explicit non-completion marker keeps that task pending.
_ID_RE = re.compile(r"\d+(?:\.\d+)+")
# A keyword-anchored id list after one `task(s)` keyword: `Tasks 2.1, 2.2, 2.3`, a
# `Tasks 0.1/0.2/0.3` slash-list, or a `1.1–1.4` range.  A keyword-anchored id is claimable
# on the strength of the entry's completion alone (a cross-reference like `task 3.1` beside
# a per-wave completion); a BARE number needs completion evidence in its own clause, which
# is what separates a real task ref from `ruff to 1.2` / `design 5.4`.  Also decides which
# non-plan ids are `unknown` (fail closed) vs a bare number to ignore.
_TASK_KEYWORD = re.compile(
    r"(?i)\btasks?\s+#?(\d+(?:\.\d+)+(?:\s*(?:,|and|&|\+|·|/|–|-)\s*#?\d+(?:\.\d+)+)*)"
)
# Clause boundaries: sentence/`;` breaks plus the em-dash the Status Log uses between a
# mention and its follow-on note.  Splitting only scopes suppression locality — the
# completion gate is entry-level — so a finer split never drops a real completion.
_CLAUSE_SEP = re.compile(r"[;.]\s+|\s+—\s+")
# A reference decimal (a version, doc section, or percentage) that collides with a real
# task id: `bumped ruff to 1.2`, `per design 5.4`, `coverage 2.1%`.  Suppressed by the word
# immediately before the id or a trailing `%` — corpus-checked to hit no real task mention,
# which never sits right after one of these words (it sits after `task`/`wave`/`(`/a sha).
_REF_PRE = re.compile(
    r"(?i)\b(?:to|per|of|via|v|versions?|sections?|§|design|coverage|ruff|deps?"
    r"|bump(?:ed)?)\s+#?$"
)
# render_plan's build-kind vocabulary + ✓ + done: the completion signals resume must
# recognise to stay at parity with the renderer's done set on non-pending entries.
_COMPLETE_RE = re.compile(
    r"✓|\bbuilt\b|\bbuild\b|\bship(?:s|ped)?\b|\bimplement(?:ed)?\b"
    r"|\bexecut(?:e[ds]?|ed|ing)?\b|\bcomplete[ds]?\b|\bverified\b|\bpassed\b"
    r"|\bmerged\b|\blanded\b|\bdone\b",
    re.I,
)
_NONCOMPLETE_RE = re.compile(
    r"\bpending\b|\bin[-\s]?progress\b|\bblocked\b|\bincomplete\b|\bwip\b|\btodo\b"
    r"|\bnot\s+(?:yet\s+)?(?:done|complete|started)|\bdeferr(?:ed|ing)\b"
    r"|\bqueued\b|\bscheduled\b|remains?\s+open",
    re.I,
)
# Future / queued markers keep a keyword-anchored mention pending even inside an otherwise-
# completed entry: `Task 1.2 will follow` / `Task 1.2 next` sits in a clause whose completion
# governs a *sibling*, not 1.2 (design 5.4).  The bare `next` is kept (it is the trailing form
# `Task 1.2 next`), but suppression is completion-GOVERNED (see parse_status_completion): a
# completion marker between the id and the future word wins, so `1.2 complete, next wave 2`
# still claims 1.2 while `1.2 next` does not.
_FUTURE_RE = re.compile(
    r"will\s+follow|to\s+follow|\bup\s+next\b|\bnext\s+up\b|\bnext\b|\bstarting\b|\bupcoming\b",
    re.I,
)
_BACKTICK_SHA = re.compile(r"`([0-9a-fA-F]{7,40})`")

# Sentinel distinct from "missing": PLAN.md exists but could not be read (finding O).
_UNREADABLE = object()


def mask_fences(body: str) -> str:
    """Blank fenced code regions (offsets preserved), mirroring render_plan.mask_fences
    so example/illustration <task> blocks and prose `<task…>` mentions cannot parse as
    real tasks."""
    out = []
    in_fence = False
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(" " * len(line))
            continue
        out.append(" " * len(line) if in_fence else line)
    return "\n".join(out)


def mask_inline_code(text: str) -> str:
    """Blank inline `code` spans (offsets preserved), mirroring render_plan."""
    return "\n".join(
        re.sub(r"`[^`\n]*`", lambda m: " " * len(m.group(0)), line)
        for line in text.split("\n")
    )


def _balanced_task_spans(scan: str) -> list[tuple[int, int]]:
    """Top-level <task>…</task> char spans in `scan` (depth-balanced), mirroring
    render_plan._balanced_spans so a nested example <task> inside an <action> is ignored."""
    spans: list[tuple[int, int]] = []
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


def _fenced_blocks(body: str) -> list[tuple[int, int]]:
    """(start, end) char spans of fenced code-block CONTENTS, mirroring render_plan."""
    spans: list[tuple[int, int]] = []
    off = 0
    in_fence = False
    start = 0
    for line in body.split("\n"):
        nxt = off + len(line) + 1
        if line.lstrip().startswith("```"):
            if in_fence:
                spans.append((start, off))
            else:
                start = nxt
            in_fence = not in_fence
        off = nxt
    return spans


def _plan_format(ptext: str) -> str:
    """xml vs markdown decided on the fence/inline-masked copy, so a markdown plan that
    merely mentions `<task` in prose is not mislabelled xml (finding A)."""
    return "xml" if "<task" in mask_inline_code(mask_fences(ptext)) else "markdown"


def read_plan_text(slug: str):
    """PLAN.md text, or None when absent, or the ``_UNREADABLE`` sentinel when it exists
    but cannot be read (encoding/I/O error) — so the decision fails closed rather than
    crashing on a non-UTF-8 byte (finding O)."""
    path = Path("specs") / slug / "PLAN.md"
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return _UNREADABLE


def plan_status_from_text(ptext: str) -> str | None:
    for line in ptext.split("\n"):
        s = line.strip()
        if s.startswith("status:"):
            return s.split(":", 1)[1].strip()
    return None


def _plan_block(slug: str) -> dict:
    ptext = read_plan_text(slug)
    if ptext is None or ptext is _UNREADABLE:
        return {"status": None, "format": None}
    return {"status": plan_status_from_text(ptext), "format": _plan_format(ptext)}


def _md_fields(block: str) -> dict:
    _, _, rest = block.partition("\n")
    fields = {"files": [], "action": [], "verify": [], "done": []}
    cur = None
    for line in rest.split("\n"):
        s = line.strip()
        m = _MD_FIELD.match(s)
        if m:
            key = m.group(1).lower()
            cur = key if key in fields else None
            if cur and m.group(2).strip():
                fields[cur].append(m.group(2).strip())
        elif cur and s:
            fields[cur].append(s)
    out = {k: "\n".join(v).strip() for k, v in fields.items()}
    v = out["verify"]
    if len(v) > 1 and v.startswith("`") and v.endswith("`"):
        v = v[1:-1].strip()
    out["verify"] = v
    return out


def _parse_md_tasks(ptext: str) -> list[dict]:
    """Markdown tasks, parity with render_plan._extract_md_tasks: headings are detected on
    the fence/inline-masked copy (fenced or backticked examples ignored; offsets
    preserved) and fields are sliced from the ORIGINAL body."""
    scan = mask_inline_code(mask_fences(ptext))
    tasks = []
    for h in _MD_TASK_HEAD.finditer(scan):
        nm = _MD_NEXT_HEAD.search(scan, h.end())
        block = ptext[h.start() : (nm.start() if nm else len(ptext))]
        f = _md_fields(block)
        if f["files"] or f["action"] or f["verify"] or f["done"]:
            tasks.append({"id": h.group(1).strip().rstrip("."), "verify": f["verify"]})
    return tasks


def _xml_task_from_block(block: str) -> dict:
    # Bind the FIRST real `id` attribute of the opening tag (finding 4).  The old greedy
    # `[^>]*\bid="` bound the LAST id-suffixed attribute (a trailing `data-id` would win);
    # reading the attribute run like render_plan.parse_task_block and rejecting hyphen/word-
    # prefixed names (`wave-id`, `data-id`) via the lookbehind binds only a standalone `id`.
    # NOTE: deliberate divergence from render_plan.parse_task_block, which uses a bare
    # `id="([^"]*)"` and so binds a leading `wave-id="3"` on `<task wave-id="3" id="1.1">`.
    # resume binds the real `id` (1.1); the corpus parity fixture cannot detect this because
    # no tracked XML plan carries an id-suffixed attribute (all 21 scanned identical).
    open_m = re.search(r"<task\b([^>]*)>", block)
    attrs = open_m.group(1) if open_m else ""
    idm = re.search(r'(?<![\w-])id="([^"]*)"', attrs)
    tid = idm.group(1).strip() if idm else ""
    vm = re.search(r"<verify>(.*?)</verify>", block, re.DOTALL)
    return {"id": tid, "verify": vm.group(1).strip() if vm else ""}


def _parse_xml_tasks(ptext: str) -> list[dict]:
    """XML tasks, parity with render_plan.extract_tasks' XML path: scan a fence- and
    inline-code-masked copy so only real <task> blocks match, slice id/verify from the
    ORIGINAL, and fall back to per-fence scanning when no raw tasks exist."""
    spans = _balanced_task_spans(mask_inline_code(mask_fences(ptext)))
    keep = [t for t in (_xml_task_from_block(ptext[s:e]) for s, e in spans) if t["id"]]
    if not keep:
        for s, e in _fenced_blocks(ptext):
            blk = ptext[s:e]
            if "<task" not in blk:
                continue
            inner = _balanced_task_spans(mask_inline_code(blk))
            if inner:
                for bs, be in inner:
                    t = _xml_task_from_block(blk[bs:be])
                    if t["id"]:
                        keep.append(t)
            else:
                t = _xml_task_from_block(blk)
                if t["id"]:
                    keep.append(t)
    return keep


def parse_tasks(ptext: str) -> tuple[list[dict], list[str]]:
    """Ordered task list plus any duplicate ids.  Mirrors render_plan.extract_tasks: the
    fence-masked XML scan (with a per-fence fallback) wins; markdown is the fallback when
    it yields nothing — so a markdown plan that merely mentions `<task` in a fence or
    backticks is not misparsed as zero-task XML (finding A/B).  Parity over ORDERED IDS is
    asserted in the test suite."""
    tasks = _parse_xml_tasks(ptext) or _parse_md_tasks(ptext)
    seen: set[str] = set()
    dups: list[str] = []
    for t in tasks:
        if t["id"] in seen and t["id"] not in dups:
            dups.append(t["id"])
        seen.add(t["id"])
    return tasks, dups


def _status_log_section(ptext: str) -> str:
    out: list[str] = []
    in_sec = False
    for line in ptext.split("\n"):
        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            if re.search(r"\bStatus Log\b", h.group(2), re.I):
                in_sec = True
                continue
            if in_sec:
                break
        if in_sec:
            out.append(line)
    return "\n".join(out)


def _status_entries(section: str) -> list[str]:
    """Group each top-level bullet with its INDENTED continuation lines into one entry
    blob.  An indent-0 non-bullet line CLOSES the current entry (finding L): it must not
    fold into the previous bullet, or a completion marker on that trailing line would leak
    across the boundary and complete a task the bullet only started."""
    entries: list[list[str]] = []
    cur: list[str] | None = None
    for line in section.split("\n"):
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        m = re.match(r"^[-*]\s+(.*)$", line.strip())
        if indent == 0 and m:
            cur = [m.group(1)]
            entries.append(cur)
        elif indent > 0 and cur is not None:
            cur.append(line.strip())
        else:
            cur = None
    return [" ".join(c) for c in entries]


def _fill_range(a: str, b: str, valid: set[str]) -> list[str]:
    """Ids between same-parent endpoints a..b that exist in the plan (finding C): a
    hyphen/en-dash range `1.1–1.4` means 1.1,1.2,1.3,1.4, not just its endpoints, but only
    the ids the plan actually defines."""
    pa, pb = a.rsplit(".", 1), b.rsplit(".", 1)
    if pa[0] != pb[0]:
        return []
    try:
        lo, hi = int(pa[1]), int(pb[1])
    except ValueError:
        return []
    return [f"{pa[0]}.{n}" for n in range(lo, hi + 1) if f"{pa[0]}.{n}" in valid]


def parse_status_completion(ptext: str, valid: set[str]) -> dict:
    """Reconstruct completion from the Status Log, per task mention (design 5.4).

    Returns {complete: set, unknown: list, commits: {id: [sha]}}.  An entry is considered
    only when it carries completion evidence of its own — a completion marker or a commit
    sha — so a pure note (`started Task 1.2`) claims nothing.  Within such an entry each
    mention is judged in its own CELL (the span bounded by its neighbouring ids, clamped to
    its clause): a non-completion or future marker in that cell (`pending`, `will follow`,
    `next`) keeps only THAT mention pending, so `Task 1.1 done and Task 1.2 will follow`
    stays at {1.1} — the reopened over-claim landmine — while a governing completion still
    reaches sibling ids merely listed under one wave/sha (`Wave 1 — sha (1.1, 2.1)`).  A
    reference decimal that collides with a task id is dropped when a version/section word
    sits immediately before it (`ruff to 1.2`, `design 5.4`) or a `%` immediately after
    (`coverage 2.1%`).  Comma/`and`/slash lists and hyphen/en-dash ranges under a `task(s)`
    keyword expand.  A sha is attributed to its own mention's segment; the first mention's
    segment widens back to the clause start so a leading `(sha): tasks 1.1–1.4` attributes.
    A keyword-anchored id outside the plan is `unknown` (fail closed); a bare one is ignored.
    """
    complete: set[str] = set()
    unknown: list[str] = []
    commits: dict[str, list[str]] = {}
    for blob in _status_entries(_status_log_section(ptext)):
        # Entry-level gate: no completion evidence anywhere in the entry -> nothing is done.
        if not (_COMPLETE_RE.search(blob) or _BACKTICK_SHA.search(blob)):
            continue
        # Work on the whole entry blob (not clause fragments): clause boundaries only bound
        # the suppression-marker search so a marker in another sentence cannot leak, while
        # SHA attribution spans the raw blob so a trailing `Task X — `sha`` is not split off
        # its own task (finding: the em-dash clause split misattributed shas to the next id).
        seps = [(m.start(), m.end()) for m in _CLAUSE_SEP.finditer(blob)]

        def _clause_span(p: int) -> tuple[int, int]:
            lo, hi = 0, len(blob)
            for s, e in seps:
                if e <= p:
                    lo = e
                elif s >= p:
                    hi = s
                    break
            return lo, hi

        kw_spans = [m.span(1) for m in _TASK_KEYWORD.finditer(blob)]
        toks = [(m.group(0), m.start(), m.end()) for m in _ID_RE.finditer(blob)]
        for i, (tid, start, end) in enumerate(toks):
            # Strict per-mention completion (design 5.4): only a KEYWORD-ANCHORED id (governed
            # by a `task(s)` token, directly or as a member of its comma/and/slash list or
            # hyphen/en-dash range) can be claimed.  A bare number is never claimed, which
            # safely rejects `design 5.4`, `v1.2`, `Python 3.1`, `1.2 not started`, and
            # `shipped 1.2 support` — under-claiming a bare mention re-dispatches its task
            # (safe) rather than skipping real work (the forbidden over-claim direction).
            if not any(lo <= start < hi for lo, hi in kw_spans):
                continue
            # Reference decimal immediately after a version/section word, or a trailing `%`.
            if _REF_PRE.search(blob[:start]) or blob[end : end + 1] == "%":
                continue
            clo, chi = _clause_span(start)
            nxt = toks[i + 1][1] if i + 1 < len(toks) else chi
            fwd = blob[end : min(chi, nxt)]
            back = blob[max(clo, toks[i - 1][2] if i > 0 else clo) : start]
            # Completion-GOVERNED suppression.  A future word that precedes the id (`Next up:
            # Task 1.2`, `starting Task 1.2`) suppresses it.  A non-completion/future word that
            # follows suppresses ONLY when no completion marker sits between the id and it — so
            # `1.2 next` / `1.2 will follow` stay pending, but `1.2 complete, next wave 2` is
            # claimed (the completion governs; the later `next` is about a sibling/wave).
            supp = bool(_FUTURE_RE.search(back)) and not _COMPLETE_RE.search(back)
            if not supp:
                marks = [
                    m.start()
                    for rx in (_NONCOMPLETE_RE, _FUTURE_RE)
                    if (m := rx.search(fwd))
                ]
                if marks:
                    comp = _COMPLETE_RE.search(fwd)
                    if comp is None or min(marks) < comp.start():
                        supp = True
            if supp:
                continue
            # SHA attribution over the raw blob: a sha belongs to the anchored id it follows,
            # so window = [this id start .. next id start]; the first id widens back to the
            # entry start to catch a leading `(sha): tasks 1.1-1.4`.
            sha_hi = toks[i + 1][1] if i + 1 < len(toks) else len(blob)
            shas = _BACKTICK_SHA.findall(blob[(0 if i == 0 else start) : sha_hi])
            ids = [tid]
            if i + 1 < len(toks) and re.fullmatch(
                r"\s*[–-]\s*", blob[end : toks[i + 1][1]]
            ):
                ids += _fill_range(tid, toks[i + 1][0], valid)
            for cid in ids:
                if cid in valid:
                    complete.add(cid)
                    bucket = commits.setdefault(cid, [])
                    for s in shas:
                        if s not in bucket:
                            bucket.append(s)
                elif cid not in unknown:
                    unknown.append(cid)
    return {"complete": complete, "unknown": unknown, "commits": commits}


# --- Git base selection + commit-range validation --------------------------------------


def _git(args: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(["git", *args], capture_output=True, text=True)
    except OSError:
        return 1, ""
    return p.returncode, p.stdout.strip()


def _upstream_nonself() -> str | None:
    rc, up = _git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"])
    if rc != 0 or not up:
        return None
    rc, branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    if rc == 0 and branch:
        if up == branch:
            return None
        rc2, rems = _git(["remote"])
        for rem in rems.split():
            if up == f"{rem}/{branch}":
                return None
    return up


def _derive_base() -> str | None:
    rc, branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    if rc != 0 or not branch or branch == "HEAD":
        return None
    _, rems = _git(["remote"])
    excl = {branch} | {f"{rem}/{branch}" for rem in rems.split()}
    rc, refs = _git(
        ["for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes"]
    )
    if rc != 0:
        return None
    cands: list[tuple[int, str]] = []
    for r in refs.split("\n"):
        r = r.strip()
        if not r or r in excl:
            continue
        anc, _ = _git(["merge-base", "--is-ancestor", r, "HEAD"])
        if anc != 0:
            continue
        cc, cnt = _git(["rev-list", "--count", f"{r}..HEAD"])
        if cc != 0:
            continue
        n = int(cnt or 0)
        if n == 0:
            # ref is AT HEAD (e.g. a backup branch): a zero-length range would sort
            # first and yield an empty BASE..HEAD -> a false git-evidence conflict
            # (finding I).  Skip it, same as the excluded self/remote copies.
            continue
        cands.append((n, r))
    if not cands:
        return None
    cands.sort(
        key=lambda x: (x[0], x[1])
    )  # tie -> lexicographic (prefers remote-tracking)
    return cands[0][1]


def _resolve_base(base: str | None) -> tuple[str | None, str, str | None]:
    """Mirror scripts/resolve-base-ref.sh conservatively.  Returns (ref, reason, full_sha)."""

    def commit(ref: str) -> str | None:
        rc, out = _git(["rev-parse", "--verify", "-q", f"{ref}^{{commit}}"])
        return out if rc == 0 and out else None

    if base:
        full = commit(base)
        if not full:
            return None, "explicit-unresolved", None
        rc, _ = _git(["merge-base", "--is-ancestor", base, "HEAD"])
        if rc != 0:
            return None, "explicit-not-ancestor", None
        return base, "explicit", full

    # Env-declared bases are TERMINAL, mirroring resolve-base-ref.sh which binds the env
    # tier and exits 1 when it does not resolve rather than falling through to
    # upstream/derivation and silently diffing against a different base (finding G).
    if os.environ.get("VERIFY_ROWS_BASE"):
        ref = os.environ["VERIFY_ROWS_BASE"]
        full = commit(ref)
        if full:
            return ref, "VERIFY_ROWS_BASE", full
        return None, "VERIFY_ROWS_BASE-unresolved", None
    if os.environ.get("GITHUB_BASE_REF"):
        ref = f"origin/{os.environ['GITHUB_BASE_REF']}"
        full = commit(ref)
        if full:
            return ref, "GITHUB_BASE_REF", full
        return None, "GITHUB_BASE_REF-unresolved", None
    up = _upstream_nonself()
    if up:
        full = commit(up)
        if full:
            return up, "branch-upstream", full
    der = _derive_base()
    if der:
        full = commit(der)
        if full:
            return der, "nearest-ancestor", full
    return None, "unresolved", None


def _validate_commits(pairs: list[tuple[str, str]], base: str | None) -> dict:
    """Validate claimed (task_id, sha) pairs resolve inside BASE..HEAD."""
    # A DECLARED base (explicit --base, or VERIFY_ROWS_BASE / GITHUB_BASE_REF) is resolved
    # and validated UNCONDITIONALLY — before the no-commits short-circuit — mirroring
    # resolve-base-ref.sh, which errors on an unresolvable declared base rather than
    # falling through (finding G).  The auto-derived (undeclared) path still falls through.
    declared = (
        bool(base)
        or bool(os.environ.get("VERIFY_ROWS_BASE"))
        or bool(os.environ.get("GITHUB_BASE_REF"))
    )
    if not pairs:
        if declared:
            ref, reason, _full = _resolve_base(base)
            if not ref:
                return {
                    "base_ref": None,
                    "base_reason": reason,
                    "range": None,
                    "conflicts": [
                        {"type": "base-unresolved", "task_id": None, "sha": None}
                    ],
                }
        return {
            "base_ref": None,
            "base_reason": "no-claimed-commits",
            "range": None,
            "conflicts": [],
        }
    ref, reason, full_base = _resolve_base(base)
    if not ref:
        conflicts = [
            {"type": "base-unresolved", "task_id": tid, "sha": sha}
            for tid, sha in pairs
        ]
        return {
            "base_ref": None,
            "base_reason": reason,
            "range": None,
            "conflicts": conflicts,
        }
    rc, rangelist = _git(["rev-list", f"{full_base}..HEAD"])
    if rc != 0:
        # rev-list itself failed (e.g. a shallow clone where BASE is unreachable): the
        # range is UNKNOWN, not empty.  Emit a distinct conflict so this is not
        # misreported as every commit being out of range (finding J).
        return {
            "base_ref": ref,
            "base_reason": "range-unavailable",
            "range": f"{full_base}..HEAD",
            "conflicts": [
                {"type": "range-unavailable", "task_id": tid, "sha": sha}
                for tid, sha in pairs
            ],
        }
    in_range = set(rangelist.split())
    conflicts = []
    for tid, sha in pairs:
        rc2, full = _git(["rev-parse", "--verify", "-q", f"{sha}^{{commit}}"])
        if rc2 != 0 or not full:
            conflicts.append(
                {"type": "unresolvable-commit", "task_id": tid, "sha": sha}
            )
        elif full not in in_range:
            conflicts.append(
                {"type": "commit-out-of-range", "task_id": tid, "sha": sha}
            )
    return {
        "base_ref": ref,
        "base_reason": reason,
        "range": f"{full_base}..HEAD",
        "conflicts": conflicts,
    }


def _build_cursor(ptext: str, base: str | None) -> tuple[dict, list[dict], dict]:
    tasks, dups = parse_tasks(ptext)
    task_ids = [t["id"] for t in tasks]
    verify_by_id = {t["id"]: t["verify"] for t in tasks}
    valid = set(task_ids)
    comp = parse_status_completion(ptext, valid)
    cur_conflicts = [{"type": "duplicate-task", "task_id": d} for d in dups]
    cur_conflicts += [{"type": "unknown-task", "task_id": u} for u in comp["unknown"]]
    complete_set = comp["complete"] & valid
    claimed = [tid for tid in task_ids if tid in complete_set]
    pending = [tid for tid in task_ids if tid not in complete_set]
    # A claimed-complete task with no Verify command cannot be re-verified: an empty
    # command "passes" vacuously.  Fail closed with a conflict (→ stop), like every other
    # evidence defect, rather than emitting {"command": ""} (finding F).
    checks = []
    for tid in claimed:
        cmd = (verify_by_id.get(tid) or "").strip()
        if cmd:
            checks.append({"task_id": tid, "command": cmd})
        else:
            cur_conflicts.append({"type": "missing-verify", "task_id": tid})
    pairs = [(tid, sha) for tid in claimed for sha in comp["commits"].get(tid, [])]
    git_block = _validate_commits(pairs, base)
    cursor = {
        "task_ids": task_ids,
        "claimed_complete": claimed,
        "pending": pending,
        "next_task": pending[0] if pending else None,
        "checks_to_rerun": checks,
        "conflicts": cur_conflicts,
    }
    return cursor, cur_conflicts, git_block


def _conflict_reason_code(conflicts: list[dict]) -> str:
    types = {c["type"] for c in conflicts}
    if "base-unresolved" in types:
        return "base-unresolved"
    if "range-unavailable" in types:
        return "range-unavailable"
    if "missing-verify" in types:
        return "missing-verify"
    if types & {"unresolvable-commit", "commit-out-of-range"}:
        return "git-evidence-conflict"
    return "cursor-conflict"


def _catch_up_path(state: str) -> list[str]:
    return _SPINE[_SPINE.index(state) + 1 :]


# --- Route builders (return action/reason blocks; decide() wraps them in the schema) ---


def _build_execution(slug: str, base: str | None, state: str | None) -> dict:
    """Execution-lane route for an active plan state, or for an untracked run (state=None)."""
    ptext = read_plan_text(slug)
    if ptext is None:
        return {
            "action": "stop",
            "reason_code": "plan-missing",
            "reason": "no PLAN.md; there is no executable task contract",
            "plan": {"status": None, "format": None},
        }
    if ptext is _UNREADABLE:
        return {
            "action": "stop",
            "reason_code": "plan-unreadable",
            "reason": "PLAN.md exists but could not be read (encoding or I/O error)",
            "plan": {"status": None, "format": None},
        }
    pstatus = plan_status_from_text(ptext)
    plan_block = {"status": pstatus, "format": _plan_format(ptext)}
    if pstatus not in PLAN_STATUSES:
        return {
            "action": "stop",
            "reason_code": "plan-unknown-status",
            "reason": f"unrecognized PLAN status: {pstatus!r}",
            "plan": plan_block,
        }
    if pstatus == "shipped":
        return {
            "action": "stop",
            "reason_code": "plan-shipped",
            "reason": "PLAN is shipped; plan-task execution is closed",
            "plan": plan_block,
        }
    cursor, cur_conflicts, git_block = _build_cursor(ptext, base)
    conflicts = cur_conflicts + git_block["conflicts"]
    if conflicts:
        return {
            "action": "stop",
            "reason_code": _conflict_reason_code(conflicts),
            "reason": "claimed task/commit evidence conflicts with the plan or branch",
            "plan": plan_block,
            "cursor": cursor,
            "git": git_block,
        }
    warnings: list[str] = []
    required_transition = None
    if state is None:
        reason_code = "untracked-executable"
        reason = "untracked run with a valid plan; execute from the reconstructed cursor without initializing"
        warnings.append("run-untracked")
    elif state in ("queued", "investigating"):
        reason_code = "catch-up"
        reason = "advance legally through planning before implementation"
        required_transition = {
            "kind": "advance",
            "from": state,
            "path": _catch_up_path(state),
        }
    else:
        reason_code = "active-plan"
        reason = "resume remaining plan tasks from the reconstructed cursor"
    if pstatus in ("proposed", "paused"):
        reason_code = "plan-activation-required"
        reason = f"activate the {pstatus} plan (status: active) before dispatching tasks, then resume"
        warnings.append(f"plan-status-{pstatus}")
        activation = {
            "kind": "activate-plan",
            "from_status": pstatus,
            "to_status": "active",
        }
        if state in ("queued", "investigating"):
            activation["then_advance"] = _catch_up_path(state)
        required_transition = activation
    return {
        "action": "execute-plan",
        "reason_code": reason_code,
        "reason": reason,
        "plan": plan_block,
        "cursor": cursor,
        "git": git_block,
        "required_transition": required_transition,
        "warnings": warnings,
    }


def _build_interrupt(state: str, snap) -> dict:
    events = snap.events or []
    proj = snap.projection or {}
    origin = events[-1].get("from_state") if events else None
    recovered = None
    successors: list[str] = []
    if origin:
        successors = sorted(rs.FORWARD_TRANSITIONS.get(origin, set()))
        if origin in rs.WAITING_STATES:
            # Recover the original waiting_on from the latest EARLIER event that entered
            # the waiting origin (design 5.6 / research gap #2).
            for ev in reversed(events[:-1]):
                if ev.get("to_state") == origin:
                    recovered = ev.get("waiting_on")
                    break
    interrupt = {
        "state": state,
        "origin_state": origin,
        "blocker": proj.get("waiting_on"),
        "resume_event": proj.get("resume_event"),
        "recovered_waiting_on": recovered,
        "successors": successors,
    }
    required_transition = {
        "kind": "return-to-origin",
        "from": state,
        "to": origin,
        "then_successors": successors,
    }
    return {
        "action": "wait",
        "reason_code": "interrupt-blocked",
        "reason": "resolve the interrupt, then return to the recorded origin state",
        "interrupt": interrupt,
        "required_transition": required_transition,
        # Every action=="wait" response carries the blocker at the same stable top-level
        # path (finding H): the interrupt's own waiting_on, or the recovered origin blocker.
        "waiting_on": proj.get("waiting_on") or recovered,
    }


# --- Advisory context: SUMMARY deviations + slug-scoped, non-stale STATE hint ----------


def _read_deviations(slug: str) -> tuple[list[str], list[str]]:
    path = Path("specs") / slug / "SUMMARY.md"
    if not path.is_file():
        return [], []
    try:
        lines = path.read_text(encoding="utf-8").split("\n")
    except (OSError, UnicodeDecodeError):
        # Advisory reader: degrade to no deviations + a warning, never crash the decision
        # (finding O).
        return [], ["summary-unreadable"]
    out: list[str] = []
    found = False
    i = 0
    while i < len(lines):
        if re.match(r"^#{2,4}\s+Deviations\b", lines[i].strip()):
            found = True
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if re.match(r"^#{1,6}\s", s):
                    break
                m = re.match(r"^[-*]\s+(.*)$", s)
                if m:
                    out.append(m.group(1).strip())
                i += 1
            break
        i += 1
    warnings = [] if found else ["summary-deviations-missing"]
    if out in (["none"], ["_none_"]):
        out = []
    return out, warnings


def _read_state_hint(slug: str) -> tuple[dict | None, list[str]]:
    path = Path("specs") / "STATE.md"
    if not path.is_file():
        return None, []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # STATE.md is repo-global advisory context: degrade to no hint + a warning rather
        # than crashing the whole decision on one unreadable byte (finding O).
        return None, ["state-unreadable"]
    m = re.search(r"(?m)^##\s+Active Spec\b(.*?)(?=^##\s|\Z)", text, re.DOTALL)
    if not m:
        return None, []
    block = m.group(1)

    def field(name: str) -> str | None:
        fm = re.search(rf"(?im)^\s*[-*]\s+\*\*{name}:\*\*\s*(.+?)\s*$", block)
        return fm.group(1).strip() if fm else None

    hslug = field("Slug")
    if hslug is None:
        return None, []
    if hslug != slug:
        return None, ["state-wrong-slug"]
    updated = field("Updated")
    if not updated:
        return None, ["state-unparseable"]
    try:
        d = datetime.strptime(updated, "%Y-%m-%d").date()
    except ValueError:
        return None, ["state-unparseable"]
    if (datetime.now(timezone.utc).date() - d).days > 7:
        return None, ["state-stale"]
    return {"slug": hslug, "updated": updated, "last_action": field("Last action")}, []


# --- Schema + top-level decision -------------------------------------------------------


def _base_schema(slug: str, action: str, reason_code: str, reason: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "action": action,
        "reason_code": reason_code,
        "reason": reason,
        "run": {"status": None, "state": None},
        "plan": None,
        "cursor": None,
        "git": None,
        "interrupt": None,
        "session_hint": None,
        "deviations": [],
        "required_transition": None,
        "warnings": [],
        "waiting_on": None,
    }


def decide(slug: str, base: str | None = None) -> dict:
    snap = rs.snapshot_run_state(slug)
    status = snap.status
    # A truthy non-dict RUN.json (e.g. `[1,2]`, `"x"`, `5`) is a valid projection-only
    # topology, not a crash: guard the .get() deref so it fails closed via the topology
    # branch below instead of raising AttributeError -> exit 3 (finding D).
    projection = snap.projection if isinstance(snap.projection, dict) else {}
    state = projection.get("state")
    run_block = {"status": status, "state": state}
    deviations, dev_warnings = _read_deviations(slug)
    session_hint, hint_warnings = _read_state_hint(slug)
    base_warnings = list(dev_warnings) + list(hint_warnings)

    def mk(d: dict) -> dict:
        r = _base_schema(slug, d.pop("action"), d.pop("reason_code"), d.pop("reason"))
        r["run"] = d.pop("run", run_block)
        r["deviations"] = deviations
        r["session_hint"] = session_hint
        r["warnings"] = base_warnings + list(d.pop("warnings", []))
        for k, v in d.items():
            r[k] = v
        return r

    # 1. Storage invalidity / rebuild precedence (design 5.1 / 5.6).
    if status == "invalid":
        return mk(
            {
                "action": "stop",
                "reason_code": "storage-invalid",
                "reason": f"durable storage is invalid: {snap.error}",
            }
        )
    if status == "projection-only":
        return mk(
            {
                "action": "stop",
                "reason_code": "storage-projection-only",
                "reason": "RUN.json exists with no canonical events.jsonl; the projection cannot be trusted",
            }
        )
    if status == "events-only":
        return mk(
            {
                "action": "rebuild",
                "reason_code": "projection-missing",
                "reason": "events.jsonl exists but RUN.json is missing; rebuild the projection before resuming",
            }
        )
    if status == "drift":
        return mk(
            {
                "action": "rebuild",
                "reason_code": "projection-drift",
                "reason": "RUN.json does not match a validated fold of events.jsonl; rebuild before resuming",
            }
        )
    if status == "untracked":
        return mk(_build_execution(slug, base, None))

    # status == consistent from here.
    if state not in rs.ALL_STATES:
        return mk(
            {
                "action": "stop",
                "reason_code": "unknown-state",
                "reason": f"unknown run state: {state!r}",
            }
        )

    # 2. Terminal / wait / interrupt / repair / review-chain routes take precedence over
    #    plan+task evidence: a cursor conflict can never reroute one of these into execution.
    if state in rs.TERMINAL_STATES:
        return mk(
            {
                "action": "stop",
                "reason_code": "terminal-run",
                "reason": "run is terminal; human decision required",
            }
        )
    if state in _WAIT_STATES:
        return mk(
            {
                "action": "wait",
                "reason_code": "awaiting-external",
                "reason": "run is waiting on an external decision or result",
                # Surface the blocker identity on the wait route (finding H): legitimately
                # null for ready_to_merge, which carries no waiting_on.
                "waiting_on": projection.get("waiting_on"),
            }
        )
    if state in rs.INTERRUPT_STATES:
        return mk(_build_interrupt(state, snap))
    if state in _REPAIR_STATES:
        return mk(
            {
                "action": "resume-repair",
                "reason_code": "post-pr-repair",
                "reason": "resume the named post-PR repair loop",
                "plan": _plan_block(slug),
            }
        )
    if state == "verifying":
        return mk(
            {
                "action": "resume-review-chain",
                "reason_code": "review-chain",
                "reason": "tasks passed; resume the final review chain and do not re-sweep task waves",
            }
        )

    # 3. Execution states: plan validity/status, then task/git evidence, then execute.
    return mk(_build_execution(slug, base, state))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only resume decision for one harness run."
    )
    parser.add_argument("--slug", required=True)
    parser.add_argument("--base", help="explicit BASE ref; must be an ancestor of HEAD")
    args = parser.parse_args(argv)  # argparse exits 2 on CLI misuse
    try:
        decision = decide(args.slug, base=args.base)
    except Exception as exc:  # unexpected internal failure: emit NO partial JSON
        print(f"resume_decision: unexpected failure: {exc}", file=sys.stderr)
        return 3
    print(json.dumps(decision, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
