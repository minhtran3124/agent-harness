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
_TASK_MENTION = re.compile(r"(?i)\btasks?\s+#?(\d+(?:\.\d+)+)")
_COMPLETE_RE = re.compile(r"✓|\bcomplete|\bdone\b|\bshipped\b", re.I)
_NONCOMPLETE_RE = re.compile(
    r"\bpending\b|\bin[-\s]?progress\b|\bblocked\b|\bincomplete\b|\bwip\b|\btodo\b"
    r"|\bnot\s+(?:yet\s+)?(?:done|complete)",
    re.I,
)
_BACKTICK_SHA = re.compile(r"`([0-9a-fA-F]{7,40})`")


def read_plan_text(slug: str) -> str | None:
    path = Path("specs") / slug / "PLAN.md"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def plan_status_from_text(ptext: str) -> str | None:
    for line in ptext.split("\n"):
        s = line.strip()
        if s.startswith("status:"):
            return s.split(":", 1)[1].strip()
    return None


def _plan_block(slug: str) -> dict:
    ptext = read_plan_text(slug)
    if ptext is None:
        return {"status": None, "format": None}
    return {
        "status": plan_status_from_text(ptext),
        "format": "xml" if "<task" in ptext else "markdown",
    }


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
    tasks = []
    for h in _MD_TASK_HEAD.finditer(ptext):
        nm = _MD_NEXT_HEAD.search(ptext, h.end())
        block = ptext[h.start() : (nm.start() if nm else len(ptext))]
        f = _md_fields(block)
        if f["files"] or f["action"] or f["verify"] or f["done"]:
            tasks.append({"id": h.group(1).strip().rstrip("."), "verify": f["verify"]})
    return tasks


def _parse_xml_tasks(ptext: str) -> list[dict]:
    opens = list(re.finditer(r"<task\b([^>]*)>", ptext))
    tasks = []
    for i, m in enumerate(opens):
        idm = re.search(r'id="([^"]*)"', m.group(1))
        tid = idm.group(1).strip() if idm else ""
        if not tid:
            continue
        end = opens[i + 1].start() if i + 1 < len(opens) else len(ptext)
        seg = ptext[m.end() : end]
        vm = re.search(r"<verify>(.*?)</verify>", seg, re.DOTALL)
        tasks.append({"id": tid, "verify": vm.group(1).strip() if vm else ""})
    return tasks


def parse_tasks(ptext: str) -> tuple[list[dict], list[str]]:
    """Ordered task list plus any duplicate ids.  XML wins in mixed files, mirroring
    render_plan; parity is asserted over ORDERED IDS in the test suite, not here."""
    tasks = _parse_xml_tasks(ptext) if "<task" in ptext else _parse_md_tasks(ptext)
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
    """Group each top-level bullet with its indented continuation into one entry blob,
    so a completion marker cannot leak across entries."""
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
        elif cur is not None:
            cur.append(line.strip())
    return [" ".join(c) for c in entries]


def parse_status_completion(ptext: str, valid: set[str]) -> dict:
    """Reconstruct per-mention completion from the Status Log.

    Returns {complete: set, unknown: list, commits: {id: [sha]}}.  A task id is claimed
    complete only when ITS OWN mention carries a completion marker and no non-completion
    marker; `Task 1.1 complete; Task 1.2 pending` claims only 1.1.
    """
    complete: set[str] = set()
    unknown: list[str] = []
    commits: dict[str, list[str]] = {}
    for blob in _status_entries(_status_log_section(ptext)):
        shas = _BACKTICK_SHA.findall(blob)
        mentions = list(_TASK_MENTION.finditer(blob))
        for j, mm in enumerate(mentions):
            end = mentions[j + 1].start() if j + 1 < len(mentions) else len(blob)
            seg = blob[mm.start() : end]
            if _COMPLETE_RE.search(seg) and not _NONCOMPLETE_RE.search(seg):
                tid = mm.group(1)
                if tid in valid:
                    complete.add(tid)
                    bucket = commits.setdefault(tid, [])
                    for s in shas:
                        if s not in bucket:
                            bucket.append(s)
                elif tid not in unknown:
                    unknown.append(tid)
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
        cands.append((int(cnt or 0), r))
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

    if os.environ.get("VERIFY_ROWS_BASE"):
        ref = os.environ["VERIFY_ROWS_BASE"]
        full = commit(ref)
        if full:
            return ref, "VERIFY_ROWS_BASE", full
    if os.environ.get("GITHUB_BASE_REF"):
        ref = f"origin/{os.environ['GITHUB_BASE_REF']}"
        full = commit(ref)
        if full:
            return ref, "GITHUB_BASE_REF", full
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
    if not pairs:
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
    in_range = set(rangelist.split()) if rc == 0 else set()
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
    checks = [{"task_id": tid, "command": verify_by_id.get(tid, "")} for tid in claimed]
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
    pstatus = plan_status_from_text(ptext)
    plan_block = {
        "status": pstatus,
        "format": "xml" if "<task" in ptext else "markdown",
    }
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
    }


# --- Advisory context: SUMMARY deviations + slug-scoped, non-stale STATE hint ----------


def _read_deviations(slug: str) -> tuple[list[str], list[str]]:
    path = Path("specs") / slug / "SUMMARY.md"
    if not path.is_file():
        return [], []
    lines = path.read_text(encoding="utf-8").split("\n")
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
    text = path.read_text(encoding="utf-8")
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
    }


def decide(slug: str, base: str | None = None) -> dict:
    snap = rs.snapshot_run_state(slug)
    status = snap.status
    projection = snap.projection or {}
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
