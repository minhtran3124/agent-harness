# Review package

BASE_SHA: 46062d93c5f30af2823e5524dce2ba5bb656c31e
HEAD_SHA: e791638156ca14af9c49642b326355b94fed4f5a

## Commits

e791638156ca14af9c49642b326355b94fed4f5a feat(gh-175): complete the versioned resume cursor authority (Task 2.1)

## Diff stat

 runtime/resume_decision.py      | 731 +++++++++++++++++++++++++++++++++++---
 runtime/test_resume_decision.py | 769 ++++++++++++++++++++++++++++++++++++----
 2 files changed, 1392 insertions(+), 108 deletions(-)

## Diff

```diff
diff --git a/runtime/resume_decision.py b/runtime/resume_decision.py
index 953850f..d228f33 100644
--- a/runtime/resume_decision.py
+++ b/runtime/resume_decision.py
@@ -1,84 +1,721 @@
 #!/usr/bin/env python3
 """Return a deterministic, read-only resume decision for one harness run.
 
-This keeps lifecycle branching out of the execution skill.  It deliberately does not transition
-state or rebuild a projection; callers must perform an explicit repair after seeing the result.
+This is the single public resume authority (design #175).  It answers two independent
+questions from one locked, semantically read-only inspection:
+
+  1. Lifecycle route  - execute-plan / resume-repair / resume-review-chain / wait / stop /
+     rebuild, derived from the durable FSM state in run_state.py.
+  2. Task cursor      - which task completion claims the plan ledger + branch support, which
+     Verify commands must be re-run, which task is next.
+
+It deliberately does not transition state, rebuild a projection, or run any plan-authored
+command; callers perform an explicit repair after seeing the result.  Contradictory or
+unresolvable evidence fails closed with a structured ``stop``; absence stays explicit
+unknown, never inferred success.
 """
 
 from __future__ import annotations
 
 import argparse
 import json
+import os
+import re
+import subprocess
 import sys
+from datetime import datetime, timezone
 from pathlib import Path
 
 import run_state as rs
 
+SCHEMA_VERSION = 1
+
+PLAN_STATUSES = {"proposed", "active", "paused", "shipped"}
+
+# Lifecycle routes that precede plan/task evidence (design 5.6).  ready_to_merge is not a
+# WAITING_STATES member in the engine but resume treats it as an external wait.
+_WAIT_STATES = rs.WAITING_STATES | {"ready_to_merge"}
+_REPAIR_STATES = {"fixing_ci", "addressing_review"}
+
+# Canonical execution spine, used to derive the legal catch-up path to implementing.
+_SPINE = ["queued", "investigating", "planning", "implementing"]
 
-def plan_status(slug: str) -> str | None:
+# --- Plan / status-log parsing (parity-aligned with render_plan for ORDERED IDS only) ---
+
+_MD_TASK_HEAD = re.compile(r"(?m)^###\s+Task\s+([0-9][\w.]*)[^\n]*$")
+_MD_NEXT_HEAD = re.compile(r"(?m)^#{2,3}\s")
+_MD_FIELD = re.compile(
+    r"^[-*]\s+\*\*(Files|Action|Verify|Done|Criteria|Interfaces)(?::\*\*|\*\*:)\s*(.*)$",
+    re.I,
+)
+
+# A completion claim is evaluated PER task mention (design 5.4).  A completion marker
+# associated with one `Task X.Y` mention never completes another task named in the same
+# entry; an explicit non-completion marker keeps that task pending.
+_TASK_MENTION = re.compile(r"(?i)\btasks?\s+#?(\d+(?:\.\d+)+)")
+_COMPLETE_RE = re.compile(r"✓|\bcomplete|\bdone\b|\bshipped\b", re.I)
+_NONCOMPLETE_RE = re.compile(
+    r"\bpending\b|\bin[-\s]?progress\b|\bblocked\b|\bincomplete\b|\bwip\b|\btodo\b"
+    r"|\bnot\s+(?:yet\s+)?(?:done|complete)",
+    re.I,
+)
+_BACKTICK_SHA = re.compile(r"`([0-9a-fA-F]{7,40})`")
+
+
+def read_plan_text(slug: str) -> str | None:
     path = Path("specs") / slug / "PLAN.md"
     if not path.is_file():
         return None
-    text = path.read_text(encoding="utf-8")
-    for line in text.splitlines():
-        if line.startswith("status:"):
-            return line.split(":", 1)[1].strip()
+    return path.read_text(encoding="utf-8")
+
+
+def plan_status_from_text(ptext: str) -> str | None:
+    for line in ptext.split("\n"):
+        s = line.strip()
+        if s.startswith("status:"):
+            return s.split(":", 1)[1].strip()
     return None
 
 
-def result(action: str, reason: str, **extra: object) -> dict[str, object]:
-    return {"action": action, "reason": reason, **extra}
+def _plan_block(slug: str) -> dict:
+    ptext = read_plan_text(slug)
+    if ptext is None:
+        return {"status": None, "format": None}
+    return {
+        "status": plan_status_from_text(ptext),
+        "format": "xml" if "<task" in ptext else "markdown",
+    }
+
+
+def _md_fields(block: str) -> dict:
+    _, _, rest = block.partition("\n")
+    fields = {"files": [], "action": [], "verify": [], "done": []}
+    cur = None
+    for line in rest.split("\n"):
+        s = line.strip()
+        m = _MD_FIELD.match(s)
+        if m:
+            key = m.group(1).lower()
+            cur = key if key in fields else None
+            if cur and m.group(2).strip():
+                fields[cur].append(m.group(2).strip())
+        elif cur and s:
+            fields[cur].append(s)
+    out = {k: "\n".join(v).strip() for k, v in fields.items()}
+    v = out["verify"]
+    if len(v) > 1 and v.startswith("`") and v.endswith("`"):
+        v = v[1:-1].strip()
+    out["verify"] = v
+    return out
+
+
+def _parse_md_tasks(ptext: str) -> list[dict]:
+    tasks = []
+    for h in _MD_TASK_HEAD.finditer(ptext):
+        nm = _MD_NEXT_HEAD.search(ptext, h.end())
+        block = ptext[h.start() : (nm.start() if nm else len(ptext))]
+        f = _md_fields(block)
+        if f["files"] or f["action"] or f["verify"] or f["done"]:
+            tasks.append({"id": h.group(1).strip().rstrip("."), "verify": f["verify"]})
+    return tasks
+
+
+def _parse_xml_tasks(ptext: str) -> list[dict]:
+    opens = list(re.finditer(r"<task\b([^>]*)>", ptext))
+    tasks = []
+    for i, m in enumerate(opens):
+        idm = re.search(r'id="([^"]*)"', m.group(1))
+        tid = idm.group(1).strip() if idm else ""
+        if not tid:
+            continue
+        end = opens[i + 1].start() if i + 1 < len(opens) else len(ptext)
+        seg = ptext[m.end() : end]
+        vm = re.search(r"<verify>(.*?)</verify>", seg, re.DOTALL)
+        tasks.append({"id": tid, "verify": vm.group(1).strip() if vm else ""})
+    return tasks
+
+
+def parse_tasks(ptext: str) -> tuple[list[dict], list[str]]:
+    """Ordered task list plus any duplicate ids.  XML wins in mixed files, mirroring
+    render_plan; parity is asserted over ORDERED IDS in the test suite, not here."""
+    tasks = _parse_xml_tasks(ptext) if "<task" in ptext else _parse_md_tasks(ptext)
+    seen: set[str] = set()
+    dups: list[str] = []
+    for t in tasks:
+        if t["id"] in seen and t["id"] not in dups:
+            dups.append(t["id"])
+        seen.add(t["id"])
+    return tasks, dups
+
+
+def _status_log_section(ptext: str) -> str:
+    out: list[str] = []
+    in_sec = False
+    for line in ptext.split("\n"):
+        h = re.match(r"^(#{1,6})\s+(.*)$", line)
+        if h:
+            if re.search(r"\bStatus Log\b", h.group(2), re.I):
+                in_sec = True
+                continue
+            if in_sec:
+                break
+        if in_sec:
+            out.append(line)
+    return "\n".join(out)
+
+
+def _status_entries(section: str) -> list[str]:
+    """Group each top-level bullet with its indented continuation into one entry blob,
+    so a completion marker cannot leak across entries."""
+    entries: list[list[str]] = []
+    cur: list[str] | None = None
+    for line in section.split("\n"):
+        if not line.strip():
+            continue
+        indent = len(line) - len(line.lstrip())
+        m = re.match(r"^[-*]\s+(.*)$", line.strip())
+        if indent == 0 and m:
+            cur = [m.group(1)]
+            entries.append(cur)
+        elif cur is not None:
+            cur.append(line.strip())
+    return [" ".join(c) for c in entries]
+
+
+def parse_status_completion(ptext: str, valid: set[str]) -> dict:
+    """Reconstruct per-mention completion from the Status Log.
+
+    Returns {complete: set, unknown: list, commits: {id: [sha]}}.  A task id is claimed
+    complete only when ITS OWN mention carries a completion marker and no non-completion
+    marker; `Task 1.1 complete; Task 1.2 pending` claims only 1.1.
+    """
+    complete: set[str] = set()
+    unknown: list[str] = []
+    commits: dict[str, list[str]] = {}
+    for blob in _status_entries(_status_log_section(ptext)):
+        shas = _BACKTICK_SHA.findall(blob)
+        mentions = list(_TASK_MENTION.finditer(blob))
+        for j, mm in enumerate(mentions):
+            end = mentions[j + 1].start() if j + 1 < len(mentions) else len(blob)
+            seg = blob[mm.start() : end]
+            if _COMPLETE_RE.search(seg) and not _NONCOMPLETE_RE.search(seg):
+                tid = mm.group(1)
+                if tid in valid:
+                    complete.add(tid)
+                    bucket = commits.setdefault(tid, [])
+                    for s in shas:
+                        if s not in bucket:
+                            bucket.append(s)
+                elif tid not in unknown:
+                    unknown.append(tid)
+    return {"complete": complete, "unknown": unknown, "commits": commits}
+
+
+# --- Git base selection + commit-range validation --------------------------------------
+
+
+def _git(args: list[str]) -> tuple[int, str]:
+    try:
+        p = subprocess.run(["git", *args], capture_output=True, text=True)
+    except OSError:
+        return 1, ""
+    return p.returncode, p.stdout.strip()
+
+
+def _upstream_nonself() -> str | None:
+    rc, up = _git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"])
+    if rc != 0 or not up:
+        return None
+    rc, branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
+    if rc == 0 and branch:
+        if up == branch:
+            return None
+        rc2, rems = _git(["remote"])
+        for rem in rems.split():
+            if up == f"{rem}/{branch}":
+                return None
+    return up
+
+
+def _derive_base() -> str | None:
+    rc, branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
+    if rc != 0 or not branch or branch == "HEAD":
+        return None
+    _, rems = _git(["remote"])
+    excl = {branch} | {f"{rem}/{branch}" for rem in rems.split()}
+    rc, refs = _git(
+        ["for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes"]
+    )
+    if rc != 0:
+        return None
+    cands: list[tuple[int, str]] = []
+    for r in refs.split("\n"):
+        r = r.strip()
+        if not r or r in excl:
+            continue
+        anc, _ = _git(["merge-base", "--is-ancestor", r, "HEAD"])
+        if anc != 0:
+            continue
+        cc, cnt = _git(["rev-list", "--count", f"{r}..HEAD"])
+        if cc != 0:
+            continue
+        cands.append((int(cnt or 0), r))
+    if not cands:
+        return None
+    cands.sort(
+        key=lambda x: (x[0], x[1])
+    )  # tie -> lexicographic (prefers remote-tracking)
+    return cands[0][1]
+
+
+def _resolve_base(base: str | None) -> tuple[str | None, str, str | None]:
+    """Mirror scripts/resolve-base-ref.sh conservatively.  Returns (ref, reason, full_sha)."""
+
+    def commit(ref: str) -> str | None:
+        rc, out = _git(["rev-parse", "--verify", "-q", f"{ref}^{{commit}}"])
+        return out if rc == 0 and out else None
+
+    if base:
+        full = commit(base)
+        if not full:
+            return None, "explicit-unresolved", None
+        rc, _ = _git(["merge-base", "--is-ancestor", base, "HEAD"])
+        if rc != 0:
+            return None, "explicit-not-ancestor", None
+        return base, "explicit", full
+
+    if os.environ.get("VERIFY_ROWS_BASE"):
+        ref = os.environ["VERIFY_ROWS_BASE"]
+        full = commit(ref)
+        if full:
+            return ref, "VERIFY_ROWS_BASE", full
+    if os.environ.get("GITHUB_BASE_REF"):
+        ref = f"origin/{os.environ['GITHUB_BASE_REF']}"
+        full = commit(ref)
+        if full:
+            return ref, "GITHUB_BASE_REF", full
+    up = _upstream_nonself()
+    if up:
+        full = commit(up)
+        if full:
+            return up, "branch-upstream", full
+    der = _derive_base()
+    if der:
+        full = commit(der)
+        if full:
+            return der, "nearest-ancestor", full
+    return None, "unresolved", None
+
+
+def _validate_commits(pairs: list[tuple[str, str]], base: str | None) -> dict:
+    """Validate claimed (task_id, sha) pairs resolve inside BASE..HEAD."""
+    if not pairs:
+        return {
+            "base_ref": None,
+            "base_reason": "no-claimed-commits",
+            "range": None,
+            "conflicts": [],
+        }
+    ref, reason, full_base = _resolve_base(base)
+    if not ref:
+        conflicts = [
+            {"type": "base-unresolved", "task_id": tid, "sha": sha}
+            for tid, sha in pairs
+        ]
+        return {
+            "base_ref": None,
+            "base_reason": reason,
+            "range": None,
+            "conflicts": conflicts,
+        }
+    rc, rangelist = _git(["rev-list", f"{full_base}..HEAD"])
+    in_range = set(rangelist.split()) if rc == 0 else set()
+    conflicts = []
+    for tid, sha in pairs:
+        rc2, full = _git(["rev-parse", "--verify", "-q", f"{sha}^{{commit}}"])
+        if rc2 != 0 or not full:
+            conflicts.append(
+                {"type": "unresolvable-commit", "task_id": tid, "sha": sha}
+            )
+        elif full not in in_range:
+            conflicts.append(
+                {"type": "commit-out-of-range", "task_id": tid, "sha": sha}
+            )
+    return {
+        "base_ref": ref,
+        "base_reason": reason,
+        "range": f"{full_base}..HEAD",
+        "conflicts": conflicts,
+    }
+
+
+def _build_cursor(ptext: str, base: str | None) -> tuple[dict, list[dict], dict]:
+    tasks, dups = parse_tasks(ptext)
+    task_ids = [t["id"] for t in tasks]
+    verify_by_id = {t["id"]: t["verify"] for t in tasks}
+    valid = set(task_ids)
+    comp = parse_status_completion(ptext, valid)
+    cur_conflicts = [{"type": "duplicate-task", "task_id": d} for d in dups]
+    cur_conflicts += [{"type": "unknown-task", "task_id": u} for u in comp["unknown"]]
+    complete_set = comp["complete"] & valid
+    claimed = [tid for tid in task_ids if tid in complete_set]
+    pending = [tid for tid in task_ids if tid not in complete_set]
+    checks = [{"task_id": tid, "command": verify_by_id.get(tid, "")} for tid in claimed]
+    pairs = [(tid, sha) for tid in claimed for sha in comp["commits"].get(tid, [])]
+    git_block = _validate_commits(pairs, base)
+    cursor = {
+        "task_ids": task_ids,
+        "claimed_complete": claimed,
+        "pending": pending,
+        "next_task": pending[0] if pending else None,
+        "checks_to_rerun": checks,
+        "conflicts": cur_conflicts,
+    }
+    return cursor, cur_conflicts, git_block
+
+
+def _conflict_reason_code(conflicts: list[dict]) -> str:
+    types = {c["type"] for c in conflicts}
+    if "base-unresolved" in types:
+        return "base-unresolved"
+    if types & {"unresolvable-commit", "commit-out-of-range"}:
+        return "git-evidence-conflict"
+    return "cursor-conflict"
+
+
+def _catch_up_path(state: str) -> list[str]:
+    return _SPINE[_SPINE.index(state) + 1 :]
+
+
+# --- Route builders (return action/reason blocks; decide() wraps them in the schema) ---
+
+
+def _build_execution(slug: str, base: str | None, state: str | None) -> dict:
+    """Execution-lane route for an active plan state, or for an untracked run (state=None)."""
+    ptext = read_plan_text(slug)
+    if ptext is None:
+        return {
+            "action": "stop",
+            "reason_code": "plan-missing",
+            "reason": "no PLAN.md; there is no executable task contract",
+            "plan": {"status": None, "format": None},
+        }
+    pstatus = plan_status_from_text(ptext)
+    plan_block = {
+        "status": pstatus,
+        "format": "xml" if "<task" in ptext else "markdown",
+    }
+    if pstatus not in PLAN_STATUSES:
+        return {
+            "action": "stop",
+            "reason_code": "plan-unknown-status",
+            "reason": f"unrecognized PLAN status: {pstatus!r}",
+            "plan": plan_block,
+        }
+    if pstatus == "shipped":
+        return {
+            "action": "stop",
+            "reason_code": "plan-shipped",
+            "reason": "PLAN is shipped; plan-task execution is closed",
+            "plan": plan_block,
+        }
+    cursor, cur_conflicts, git_block = _build_cursor(ptext, base)
+    conflicts = cur_conflicts + git_block["conflicts"]
+    if conflicts:
+        return {
+            "action": "stop",
+            "reason_code": _conflict_reason_code(conflicts),
+            "reason": "claimed task/commit evidence conflicts with the plan or branch",
+            "plan": plan_block,
+            "cursor": cursor,
+            "git": git_block,
+        }
+    warnings: list[str] = []
+    required_transition = None
+    if state is None:
+        reason_code = "untracked-executable"
+        reason = "untracked run with a valid plan; execute from the reconstructed cursor without initializing"
+        warnings.append("run-untracked")
+    elif state in ("queued", "investigating"):
+        reason_code = "catch-up"
+        reason = "advance legally through planning before implementation"
+        required_transition = {
+            "kind": "advance",
+            "from": state,
+            "path": _catch_up_path(state),
+        }
+    else:
+        reason_code = "active-plan"
+        reason = "resume remaining plan tasks from the reconstructed cursor"
+    if pstatus in ("proposed", "paused"):
+        reason_code = "plan-activation-required"
+        reason = f"activate the {pstatus} plan (status: active) before dispatching tasks, then resume"
+        warnings.append(f"plan-status-{pstatus}")
+        activation = {
+            "kind": "activate-plan",
+            "from_status": pstatus,
+            "to_status": "active",
+        }
+        if state in ("queued", "investigating"):
+            activation["then_advance"] = _catch_up_path(state)
+        required_transition = activation
+    return {
+        "action": "execute-plan",
+        "reason_code": reason_code,
+        "reason": reason,
+        "plan": plan_block,
+        "cursor": cursor,
+        "git": git_block,
+        "required_transition": required_transition,
+        "warnings": warnings,
+    }
+
+
+def _build_interrupt(state: str, snap) -> dict:
+    events = snap.events or []
+    proj = snap.projection or {}
+    origin = events[-1].get("from_state") if events else None
+    recovered = None
+    successors: list[str] = []
+    if origin:
+        successors = sorted(rs.FORWARD_TRANSITIONS.get(origin, set()))
+        if origin in rs.WAITING_STATES:
+            # Recover the original waiting_on from the latest EARLIER event that entered
+            # the waiting origin (design 5.6 / research gap #2).
+            for ev in reversed(events[:-1]):
+                if ev.get("to_state") == origin:
+                    recovered = ev.get("waiting_on")
+                    break
+    interrupt = {
+        "state": state,
+        "origin_state": origin,
+        "blocker": proj.get("waiting_on"),
+        "resume_event": proj.get("resume_event"),
+        "recovered_waiting_on": recovered,
+        "successors": successors,
+    }
+    required_transition = {
+        "kind": "return-to-origin",
+        "from": state,
+        "to": origin,
+        "then_successors": successors,
+    }
+    return {
+        "action": "wait",
+        "reason_code": "interrupt-blocked",
+        "reason": "resolve the interrupt, then return to the recorded origin state",
+        "interrupt": interrupt,
+        "required_transition": required_transition,
+    }
+
 
+# --- Advisory context: SUMMARY deviations + slug-scoped, non-stale STATE hint ----------
 
-def decide(slug: str) -> dict[str, object]:
-    run_path = Path(rs.run_json_path(slug))
-    event_path = Path(rs.events_path(slug))
-    has_run, has_events = run_path.is_file(), event_path.is_file()
-    if not has_run and not has_events:
-        return result("execute-plan", "run was never initialized", state="untracked")
-    if has_run and not has_events:
-        return result("stop", "RUN.json exists without canonical events.jsonl", state="corrupt")
-    if has_events and not has_run:
-        return result("rebuild", "events.jsonl exists but RUN.json projection is missing")
+
+def _read_deviations(slug: str) -> tuple[list[str], list[str]]:
+    path = Path("specs") / slug / "SUMMARY.md"
+    if not path.is_file():
+        return [], []
+    lines = path.read_text(encoding="utf-8").split("\n")
+    out: list[str] = []
+    found = False
+    i = 0
+    while i < len(lines):
+        if re.match(r"^#{2,4}\s+Deviations\b", lines[i].strip()):
+            found = True
+            i += 1
+            while i < len(lines):
+                s = lines[i].strip()
+                if re.match(r"^#{1,6}\s", s):
+                    break
+                m = re.match(r"^[-*]\s+(.*)$", s)
+                if m:
+                    out.append(m.group(1).strip())
+                i += 1
+            break
+        i += 1
+    warnings = [] if found else ["summary-deviations-missing"]
+    if out in (["none"], ["_none_"]):
+        out = []
+    return out, warnings
+
+
+def _read_state_hint(slug: str) -> tuple[dict | None, list[str]]:
+    path = Path("specs") / "STATE.md"
+    if not path.is_file():
+        return None, []
+    text = path.read_text(encoding="utf-8")
+    m = re.search(r"(?m)^##\s+Active Spec\b(.*?)(?=^##\s|\Z)", text, re.DOTALL)
+    if not m:
+        return None, []
+    block = m.group(1)
+
+    def field(name: str) -> str | None:
+        fm = re.search(rf"(?im)^\s*[-*]\s+\*\*{name}:\*\*\s*(.+?)\s*$", block)
+        return fm.group(1).strip() if fm else None
+
+    hslug = field("Slug")
+    if hslug is None:
+        return None, []
+    if hslug != slug:
+        return None, ["state-wrong-slug"]
+    updated = field("Updated")
+    if not updated:
+        return None, ["state-unparseable"]
     try:
-        events = rs.read_events(slug)
-        projection = rs.read_json(rs.run_json_path(slug))
-    except rs.StorageError as exc:
-        return result("stop", str(exc), state="corrupt")
-    rebuilt = rs.project(events)
-    if projection != rebuilt:
-        return result("rebuild", "RUN.json does not match events.jsonl", state=projection.get("state"))
+        d = datetime.strptime(updated, "%Y-%m-%d").date()
+    except ValueError:
+        return None, ["state-unparseable"]
+    if (datetime.now(timezone.utc).date() - d).days > 7:
+        return None, ["state-stale"]
+    return {"slug": hslug, "updated": updated, "last_action": field("Last action")}, []
+
+
+# --- Schema + top-level decision -------------------------------------------------------
+
+
+def _base_schema(slug: str, action: str, reason_code: str, reason: str) -> dict:
+    return {
+        "schema_version": SCHEMA_VERSION,
+        "slug": slug,
+        "action": action,
+        "reason_code": reason_code,
+        "reason": reason,
+        "run": {"status": None, "state": None},
+        "plan": None,
+        "cursor": None,
+        "git": None,
+        "interrupt": None,
+        "session_hint": None,
+        "deviations": [],
+        "required_transition": None,
+        "warnings": [],
+    }
+
+
+def decide(slug: str, base: str | None = None) -> dict:
+    snap = rs.snapshot_run_state(slug)
+    status = snap.status
+    projection = snap.projection or {}
     state = projection.get("state")
+    run_block = {"status": status, "state": state}
+    deviations, dev_warnings = _read_deviations(slug)
+    session_hint, hint_warnings = _read_state_hint(slug)
+    base_warnings = list(dev_warnings) + list(hint_warnings)
+
+    def mk(d: dict) -> dict:
+        r = _base_schema(slug, d.pop("action"), d.pop("reason_code"), d.pop("reason"))
+        r["run"] = d.pop("run", run_block)
+        r["deviations"] = deviations
+        r["session_hint"] = session_hint
+        r["warnings"] = base_warnings + list(d.pop("warnings", []))
+        for k, v in d.items():
+            r[k] = v
+        return r
+
+    # 1. Storage invalidity / rebuild precedence (design 5.1 / 5.6).
+    if status == "invalid":
+        return mk(
+            {
+                "action": "stop",
+                "reason_code": "storage-invalid",
+                "reason": f"durable storage is invalid: {snap.error}",
+            }
+        )
+    if status == "projection-only":
+        return mk(
+            {
+                "action": "stop",
+                "reason_code": "storage-projection-only",
+                "reason": "RUN.json exists with no canonical events.jsonl; the projection cannot be trusted",
+            }
+        )
+    if status == "events-only":
+        return mk(
+            {
+                "action": "rebuild",
+                "reason_code": "projection-missing",
+                "reason": "events.jsonl exists but RUN.json is missing; rebuild the projection before resuming",
+            }
+        )
+    if status == "drift":
+        return mk(
+            {
+                "action": "rebuild",
+                "reason_code": "projection-drift",
+                "reason": "RUN.json does not match a validated fold of events.jsonl; rebuild before resuming",
+            }
+        )
+    if status == "untracked":
+        return mk(_build_execution(slug, base, None))
+
+    # status == consistent from here.
     if state not in rs.ALL_STATES:
-        return result("stop", f"unknown run state: {state!r}", state=state)
+        return mk(
+            {
+                "action": "stop",
+                "reason_code": "unknown-state",
+                "reason": f"unknown run state: {state!r}",
+            }
+        )
+
+    # 2. Terminal / wait / interrupt / repair / review-chain routes take precedence over
+    #    plan+task evidence: a cursor conflict can never reroute one of these into execution.
     if state in rs.TERMINAL_STATES:
-        return result("stop", "run is terminal; human decision required", state=state)
-    if state in rs.WAITING_STATES:
-        return result("wait", "run is waiting on an external decision or result", state=state,
-                      waiting_on=projection.get("waiting_on"))
+        return mk(
+            {
+                "action": "stop",
+                "reason_code": "terminal-run",
+                "reason": "run is terminal; human decision required",
+            }
+        )
+    if state in _WAIT_STATES:
+        return mk(
+            {
+                "action": "wait",
+                "reason_code": "awaiting-external",
+                "reason": "run is waiting on an external decision or result",
+            }
+        )
     if state in rs.INTERRUPT_STATES:
-        origin = events[-1].get("from_state")
-        return result("wait", "resolve interrupt then return to recorded origin", state=state,
-                      origin_state=origin, waiting_on=projection.get("waiting_on"),
-                      resume_event=projection.get("resume_event"))
-    if state in {"fixing_ci", "addressing_review"}:
-        return result("resume-repair", "resume the named post-PR repair loop", state=state,
-                      plan_status=plan_status(slug))
+        return mk(_build_interrupt(state, snap))
+    if state in _REPAIR_STATES:
+        return mk(
+            {
+                "action": "resume-repair",
+                "reason_code": "post-pr-repair",
+                "reason": "resume the named post-PR repair loop",
+                "plan": _plan_block(slug),
+            }
+        )
     if state == "verifying":
-        return result("resume-review-chain", "tasks passed; resume final review chain", state=state)
-    if state in {"queued", "investigating"}:
-        return result("execute-plan", "advance legally through planning before implementation", state=state,
-                      required_path=["investigating", "planning", "implementing"])
-    return result("execute-plan", "resume plan execution", state=state, plan_status=plan_status(slug))
+        return mk(
+            {
+                "action": "resume-review-chain",
+                "reason_code": "review-chain",
+                "reason": "tasks passed; resume the final review chain and do not re-sweep task waves",
+            }
+        )
 
+    # 3. Execution states: plan validity/status, then task/git evidence, then execute.
+    return mk(_build_execution(slug, base, state))
 
-def main() -> int:
-    parser = argparse.ArgumentParser()
+
+def main(argv=None) -> int:
+    parser = argparse.ArgumentParser(
+        description="Read-only resume decision for one harness run."
+    )
     parser.add_argument("--slug", required=True)
-    args = parser.parse_args()
-    print(json.dumps(decide(args.slug), sort_keys=True))
+    parser.add_argument("--base", help="explicit BASE ref; must be an ancestor of HEAD")
+    args = parser.parse_args(argv)  # argparse exits 2 on CLI misuse
+    try:
+        decision = decide(args.slug, base=args.base)
+    except Exception as exc:  # unexpected internal failure: emit NO partial JSON
+        print(f"resume_decision: unexpected failure: {exc}", file=sys.stderr)
+        return 3
+    print(json.dumps(decision, sort_keys=True))
     return 0
 
 
 if __name__ == "__main__":
     raise SystemExit(main())
diff --git a/runtime/test_resume_decision.py b/runtime/test_resume_decision.py
index 9fd98cb..bb48fc7 100644
--- a/runtime/test_resume_decision.py
+++ b/runtime/test_resume_decision.py
@@ -1,90 +1,737 @@
-"""Executable resume-routing contract, independent of SDD prose."""
+"""Executable resume-routing + task-cursor contract, independent of SDD prose.
+
+Every lifecycle route, storage topology, and plan/task/git evidence case has an EXACT
+expected (action, reason_code).  A future unclassified FSM state fails the state matrix.
+No test parses SKILL.md prose; behaviour is proven end-to-end through decide().
+"""
 
 from __future__ import annotations
 
 import json
+import os
+import subprocess
+import sys
+from datetime import date, timedelta
 from pathlib import Path
 
-import run_state as rs
-import resume_decision as decision
+import pytest
+
+sys.path.insert(0, os.path.dirname(__file__))
+sys.path.insert(
+    0, os.path.join(os.path.dirname(__file__), "..", "skills", "visual-planner")
+)
+
+import run_state as rs  # noqa: E402
+import resume_decision as decision  # noqa: E402
+
+
+# --- fixtures / helpers ----------------------------------------------------------------
+
+_ACTIVE_MD_PLAN = """\
+issue: 175
+status: active
+
+# Plan
+
+### Task 1.1 — first (wave 1)
+
+- **Files:** a.py
+- **Action:** do a
+- **Verify:** `pytest -k a`
+- **Done:** a done
+
+### Task 1.2 — second (wave 1)
+
+- **Files:** b.py
+- **Action:** do b
+- **Verify:** `pytest -k b`
+- **Done:** b done
+"""
+
+
+def write_plan(slug: str, text: str = _ACTIVE_MD_PLAN) -> None:
+    d = Path("specs") / slug
+    d.mkdir(parents=True, exist_ok=True)
+    (d / "PLAN.md").write_text(text, encoding="utf-8")
 
 
 def init_to(slug: str, states: tuple[str, ...]) -> None:
-    rs.main(["init", "--slug", slug, "--run-id", f"run-{slug}"])
+    assert rs.main(["init", "--slug", slug, "--run-id", f"run-{slug}"]) == 0
     for state in states:
         args = ["transition", "--slug", slug, "--to", state, "--event", f"to.{state}"]
         if state in rs.WAITING_STATES:
             args += ["--waiting-on", state]
         if state in rs.INTERRUPT_STATES:
             args += ["--waiting-on", "blocker", "--resume-event", "resolved"]
-        rs.main(args)
+        if state == "shipped":
+            args += ["--sha", "deadbeef1234"]
+        assert rs.main(args) == 0, f"transition to {state} failed"
 
 
-def test_untracked_and_storage_split(tmp_path, monkeypatch):
-    monkeypatch.chdir(tmp_path)
-    assert decision.decide("missing")["action"] == "execute-plan"
-    Path("specs/projection").mkdir(parents=True)
-    Path(rs.run_json_path("projection")).write_text("{}")
-    assert decision.decide("projection")["action"] == "stop"
-    init_to("events", ())
-    Path(rs.run_json_path("events")).unlink()
-    assert decision.decide("events")["action"] == "rebuild"
+PATHS = {
+    "queued": (),
+    "investigating": ("investigating",),
+    "awaiting_confirmation": ("investigating", "awaiting_confirmation"),
+    "planning": ("investigating", "planning"),
+    "implementing": ("investigating", "planning", "implementing"),
+    "verifying": ("investigating", "planning", "implementing", "verifying"),
+    "awaiting_ci": (
+        "investigating",
+        "planning",
+        "implementing",
+        "verifying",
+        "awaiting_ci",
+    ),
+    "fixing_ci": (
+        "investigating",
+        "planning",
+        "implementing",
+        "verifying",
+        "awaiting_ci",
+        "fixing_ci",
+    ),
+    "awaiting_review": (
+        "investigating",
+        "planning",
+        "implementing",
+        "verifying",
+        "awaiting_ci",
+        "awaiting_review",
+    ),
+    "addressing_review": (
+        "investigating",
+        "planning",
+        "implementing",
+        "verifying",
+        "awaiting_ci",
+        "awaiting_review",
+        "addressing_review",
+    ),
+    "ready_to_merge": (
+        "investigating",
+        "planning",
+        "implementing",
+        "verifying",
+        "ready_to_merge",
+    ),
+    "blocked": ("investigating", "planning", "blocked"),
+    "escalated": ("investigating", "planning", "escalated"),
+    "cancelled": ("investigating", "planning", "cancelled"),
+    "superseded": ("investigating", "planning", "superseded"),
+    "shipped": (
+        "investigating",
+        "planning",
+        "implementing",
+        "verifying",
+        "ready_to_merge",
+        "shipped",
+    ),
+}
 
+# Exact (action, reason_code) per FSM state, given a VALID ACTIVE plan present.
+EXPECT = {
+    "queued": ("execute-plan", "catch-up"),
+    "investigating": ("execute-plan", "catch-up"),
+    "awaiting_confirmation": ("wait", "awaiting-external"),
+    "planning": ("execute-plan", "active-plan"),
+    "implementing": ("execute-plan", "active-plan"),
+    "verifying": ("resume-review-chain", "review-chain"),
+    "awaiting_ci": ("wait", "awaiting-external"),
+    "fixing_ci": ("resume-repair", "post-pr-repair"),
+    "awaiting_review": ("wait", "awaiting-external"),
+    "addressing_review": ("resume-repair", "post-pr-repair"),
+    "ready_to_merge": ("wait", "awaiting-external"),
+    "blocked": ("wait", "interrupt-blocked"),
+    "escalated": ("wait", "interrupt-blocked"),
+    "cancelled": ("stop", "terminal-run"),
+    "superseded": ("stop", "terminal-run"),
+    "shipped": ("stop", "terminal-run"),
+}
 
-def test_active_and_review_states_have_distinct_actions(tmp_path, monkeypatch):
+
+# --- state matrix (SC-2) ----------------------------------------------------------------
+
+
+def test_state_matrix_is_exhaustive_over_the_fsm(tmp_path, monkeypatch):
     monkeypatch.chdir(tmp_path)
-    init_to("planning", ("investigating", "planning"))
-    assert decision.decide("planning")["action"] == "execute-plan"
-    init_to("verifying", ("investigating", "planning", "implementing", "verifying"))
-    assert decision.decide("verifying")["action"] == "resume-review-chain"
-    init_to("repair", ("investigating", "planning", "implementing", "verifying", "awaiting_ci", "fixing_ci"))
-    assert decision.decide("repair")["action"] == "resume-repair"
+    # Adding an unclassified FSM state must fail the suite here.
+    assert set(PATHS) == rs.ALL_STATES
+    assert set(EXPECT) == rs.ALL_STATES
 
 
-def test_wait_interrupt_and_terminal_stop(tmp_path, monkeypatch):
+def test_state_matrix_exact_action_and_reason_code(tmp_path, monkeypatch):
     monkeypatch.chdir(tmp_path)
-    init_to("wait", ("investigating", "awaiting_confirmation"))
-    assert decision.decide("wait")["action"] == "wait"
-    init_to("blocked", ("investigating", "planning", "blocked"))
-    found = decision.decide("blocked")
-    assert found["action"] == "wait"
-    assert found["origin_state"] == "planning"
-    init_to("terminal", ("investigating", "planning", "cancelled"))
-    assert decision.decide("terminal")["action"] == "stop"
+    for state, path in PATHS.items():
+        slug = f"state-{state}"
+        write_plan(slug)
+        init_to(slug, path)
+        v = decision.decide(slug)
+        assert (v["action"], v["reason_code"]) == EXPECT[state], state
+
+
+# --- storage matrix (SC-2) --------------------------------------------------------------
 
 
-def test_projection_drift_requires_rebuild(tmp_path, monkeypatch):
+def test_storage_matrix_exact_action_per_topology(tmp_path, monkeypatch):
     monkeypatch.chdir(tmp_path)
+
+    # untracked run + valid non-shipped plan -> execute from the reconstructed cursor.
+    write_plan("untracked")
+    v = decision.decide("untracked")
+    assert (v["action"], v["reason_code"]) == ("execute-plan", "untracked-executable")
+    assert v["run"]["status"] == "untracked"
+    assert "run-untracked" in v["warnings"]
+
+    # projection-only -> stop (cannot trust a projection with no canonical log).
+    Path("specs/projonly").mkdir(parents=True)
+    Path(rs.run_json_path("projonly")).write_text("{}")
+    v = decision.decide("projonly")
+    assert (v["action"], v["reason_code"]) == ("stop", "storage-projection-only")
+
+    # events-only -> rebuild.
+    init_to("evonly", ("investigating", "planning"))
+    Path(rs.run_json_path("evonly")).unlink()
+    v = decision.decide("evonly")
+    assert (v["action"], v["reason_code"]) == ("rebuild", "projection-missing")
+
+    # drift -> rebuild.
     init_to("drift", ("investigating", "planning"))
-    path = Path(rs.run_json_path("drift"))
-    data = json.loads(path.read_text())
+    p = Path(rs.run_json_path("drift"))
+    data = json.loads(p.read_text())
     data["state"] = "queued"
-    path.write_text(json.dumps(data))
-    assert decision.decide("drift")["action"] == "rebuild"
-
-
-def test_every_engine_state_has_an_executable_resume_verdict(tmp_path, monkeypatch):
-    monkeypatch.chdir(tmp_path)
-    paths = {
-        "queued": (), "investigating": ("investigating",),
-        "awaiting_confirmation": ("investigating", "awaiting_confirmation"),
-        "planning": ("investigating", "planning"),
-        "implementing": ("investigating", "planning", "implementing"),
-        "verifying": ("investigating", "planning", "implementing", "verifying"),
-        "awaiting_ci": ("investigating", "planning", "implementing", "verifying", "awaiting_ci"),
-        "fixing_ci": ("investigating", "planning", "implementing", "verifying", "awaiting_ci", "fixing_ci"),
-        "awaiting_review": ("investigating", "planning", "implementing", "verifying", "awaiting_ci", "awaiting_review"),
-        "addressing_review": ("investigating", "planning", "implementing", "verifying", "awaiting_ci", "awaiting_review", "addressing_review"),
-        "ready_to_merge": ("investigating", "planning", "implementing", "verifying", "ready_to_merge"),
-        "blocked": ("investigating", "planning", "blocked"),
-        "escalated": ("investigating", "planning", "escalated"),
-        "cancelled": ("investigating", "planning", "cancelled"),
-        "superseded": ("investigating", "planning", "superseded"),
-        "shipped": ("investigating", "planning", "implementing", "verifying", "ready_to_merge", "shipped"),
+    p.write_text(json.dumps(data))
+    v = decision.decide("drift")
+    assert (v["action"], v["reason_code"]) == ("rebuild", "projection-drift")
+
+    # invalid storage -> stop.
+    Path("specs/invalid").mkdir(parents=True)
+    Path(rs.events_path("invalid")).write_text("not-json\n")
+    v = decision.decide("invalid")
+    assert (v["action"], v["reason_code"]) == ("stop", "storage-invalid")
+
+    # consistent + active plan + implementing -> execute-plan.
+    write_plan("consistent")
+    init_to("consistent", ("investigating", "planning", "implementing"))
+    v = decision.decide("consistent")
+    assert (v["action"], v["reason_code"]) == ("execute-plan", "active-plan")
+
+
+def test_storage_matrix_missing_plan_stops_execution(tmp_path, monkeypatch):
+    monkeypatch.chdir(tmp_path)
+    init_to("noplan", ("investigating", "planning", "implementing"))
+    v = decision.decide("noplan")
+    assert (v["action"], v["reason_code"]) == ("stop", "plan-missing")
+
+
+# --- shipped-plan repair exception (SC-3) ----------------------------------------------
+
+_SHIPPED_MD_PLAN = _ACTIVE_MD_PLAN.replace("status: active", "status: shipped")
+
+
+def test_shipped_plan_blocks_execute_but_repair_states_still_route(
+    tmp_path, monkeypatch
+):
+    monkeypatch.chdir(tmp_path)
+
+    # implementing + shipped plan -> plan-task execution is closed.
+    write_plan("ship-impl", _SHIPPED_MD_PLAN)
+    init_to("ship-impl", ("investigating", "planning", "implementing"))
+    v = decision.decide("ship-impl")
+    assert (v["action"], v["reason_code"]) == ("stop", "plan-shipped")
+
+    # fixing_ci + shipped plan -> still routes to repair.
+    write_plan("ship-ci", _SHIPPED_MD_PLAN)
+    init_to("ship-ci", PATHS["fixing_ci"])
+    v = decision.decide("ship-ci")
+    assert (v["action"], v["reason_code"]) == ("resume-repair", "post-pr-repair")
+    assert v["plan"]["status"] == "shipped"
+
+    # addressing_review + shipped plan -> still routes to repair.
+    write_plan("ship-rev", _SHIPPED_MD_PLAN)
+    init_to("ship-rev", PATHS["addressing_review"])
+    v = decision.decide("ship-rev")
+    assert (v["action"], v["reason_code"]) == ("resume-repair", "post-pr-repair")
+
+
+# --- interrupt / waiting-origin recovery (SC-4) ----------------------------------------
+
+
+def test_interrupt_blocked_from_active_origin_returns_transition(tmp_path, monkeypatch):
+    monkeypatch.chdir(tmp_path)
+    init_to("int-plan", ("investigating", "planning", "blocked"))
+    v = decision.decide("int-plan")
+    assert (v["action"], v["reason_code"]) == ("wait", "interrupt-blocked")
+    assert v["interrupt"]["origin_state"] == "planning"
+    assert (
+        v["interrupt"]["recovered_waiting_on"] is None
+    )  # planning is not a waiting state
+    assert v["required_transition"]["to"] == "planning"
+
+
+def test_waiting_origin_interrupt_recovers_original_waiting_on_and_successors(
+    tmp_path, monkeypatch
+):
+    monkeypatch.chdir(tmp_path)
+    # awaiting_ci(waiting_on=ci-run-42) -> blocked must recover ci-run-42.
+    rs.main(["init", "--slug", "wo", "--run-id", "run-wo"])
+    for st in ("investigating", "planning", "implementing", "verifying"):
+        assert (
+            rs.main(["transition", "--slug", "wo", "--to", st, "--event", f"to.{st}"])
+            == 0
+        )
+    assert (
+        rs.main(
+            [
+                "transition",
+                "--slug",
+                "wo",
+                "--to",
+                "awaiting_ci",
+                "--event",
+                "to.ci",
+                "--waiting-on",
+                "ci-run-42",
+            ]
+        )
+        == 0
+    )
+    assert (
+        rs.main(
+            [
+                "transition",
+                "--slug",
+                "wo",
+                "--to",
+                "blocked",
+                "--event",
+                "to.blocked",
+                "--waiting-on",
+                "human",
+                "--resume-event",
+                "resolved",
+            ]
+        )
+        == 0
+    )
+    v = decision.decide("wo")
+    assert (v["action"], v["reason_code"]) == ("wait", "interrupt-blocked")
+    assert v["interrupt"]["origin_state"] == "awaiting_ci"
+    assert v["interrupt"]["recovered_waiting_on"] == "ci-run-42"
+    assert set(v["interrupt"]["successors"]) == {
+        "fixing_ci",
+        "awaiting_review",
+        "ready_to_merge",
     }
-    assert set(paths) == rs.ALL_STATES
-    for state, path in paths.items():
-        slug = f"state-{state}"
-        init_to(slug, path)
-        verdict = decision.decide(slug)
-        assert verdict["action"] in {"execute-plan", "resume-repair", "resume-review-chain", "wait", "stop"}
+    assert v["required_transition"]["to"] == "awaiting_ci"
+
+
+# --- cursor reconstruction (SC-5) ------------------------------------------------------
+
+
+def test_cursor_markdown_orders_tasks_and_exposes_checks_to_rerun(
+    tmp_path, monkeypatch
+):
+    monkeypatch.chdir(tmp_path)
+    plan = _ACTIVE_MD_PLAN + "\n## Status Log\n\n- 2026-08-09 — Task 1.1 complete.\n"
+    write_plan("md-cur", plan)
+    init_to("md-cur", ("investigating", "planning", "implementing"))
+    v = decision.decide("md-cur")
+    assert v["cursor"]["task_ids"] == ["1.1", "1.2"]
+    assert v["cursor"]["claimed_complete"] == ["1.1"]
+    assert v["cursor"]["pending"] == ["1.2"]
+    assert v["cursor"]["next_task"] == "1.2"
+    assert v["cursor"]["checks_to_rerun"] == [
+        {"task_id": "1.1", "command": "pytest -k a"}
+    ]
+
+
+_XML_PLAN = """\
+status: active
+
+# Plan
+
+<task id="1.1" wave="1">
+<files>a.py</files>
+<action>do a</action>
+<verify>pytest -k a</verify>
+<done>a</done>
+</task>
+
+<task id="1.2" wave="1">
+<files>b.py</files>
+<action>do b</action>
+<verify>pytest -k b</verify>
+<done>b</done>
+</task>
+
+## Status Log
+
+- 2026-08-09 — Task 1.1 complete.
+"""
+
+
+def test_cursor_legacy_xml_orders_tasks(tmp_path, monkeypatch):
+    monkeypatch.chdir(tmp_path)
+    write_plan("xml-cur", _XML_PLAN)
+    init_to("xml-cur", ("investigating", "planning", "implementing"))
+    v = decision.decide("xml-cur")
+    assert v["cursor"]["task_ids"] == ["1.1", "1.2"]
+    assert v["cursor"]["claimed_complete"] == ["1.1"]
+    assert v["cursor"]["checks_to_rerun"] == [
+        {"task_id": "1.1", "command": "pytest -k a"}
+    ]
+
+
+def test_cursor_mixed_complete_pending_claims_only_its_own_mention(
+    tmp_path, monkeypatch
+):
+    """The landmine guard: a mixed Status Log entry must NOT complete both tasks."""
+    monkeypatch.chdir(tmp_path)
+    plan = (
+        _ACTIVE_MD_PLAN
+        + "\n## Status Log\n\n- 2026-08-09 — Task 1.1 complete; Task 1.2 pending\n"
+    )
+    write_plan("mixed", plan)
+    init_to("mixed", ("investigating", "planning", "implementing"))
+    v = decision.decide("mixed")
+    assert v["cursor"]["claimed_complete"] == ["1.1"]
+    assert v["cursor"]["pending"] == ["1.2"]
+
+
+def test_cursor_unknown_task_completion_stops(tmp_path, monkeypatch):
+    monkeypatch.chdir(tmp_path)
+    plan = _ACTIVE_MD_PLAN + "\n## Status Log\n\n- 2026-08-09 — Task 9.9 complete.\n"
+    write_plan("unk", plan)
+    init_to("unk", ("investigating", "planning", "implementing"))
+    v = decision.decide("unk")
+    assert (v["action"], v["reason_code"]) == ("stop", "cursor-conflict")
+
+
+# --- git evidence reconciliation (SC-5) ------------------------------------------------
+
+
+def _git_repo(tmp_path):
+    def g(*args):
+        subprocess.run(
+            ["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True
+        )
+
+    g("init", "-q")
+    g("config", "user.email", "t@t")
+    g("config", "user.name", "t")
+    g("commit", "--allow-empty", "-q", "-m", "base")
+    base = subprocess.run(
+        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True
+    ).stdout.strip()
+    g("commit", "--allow-empty", "-q", "-m", "head")
+    head = subprocess.run(
+        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True
+    ).stdout.strip()
+    return base, head
+
+
+def _plan_with_claim(sha: str) -> str:
+    return (
+        _ACTIVE_MD_PLAN
+        + f"\n## Status Log\n\n- 2026-08-09 — Task 1.1 complete (`{sha}`).\n"
+    )
+
+
+def test_git_evidence_in_range_commit_resumes(tmp_path, monkeypatch):
+    monkeypatch.chdir(tmp_path)
+    base, head = _git_repo(tmp_path)
+    write_plan("gr-ok", _plan_with_claim(head))
+    init_to("gr-ok", ("investigating", "planning", "implementing"))
+    v = decision.decide("gr-ok", base=base)
+    assert v["action"] == "execute-plan"
+    assert v["git"]["conflicts"] == []
+    assert v["cursor"]["claimed_complete"] == ["1.1"]
+
+
+def test_git_evidence_out_of_range_commit_stops(tmp_path, monkeypatch):
+    monkeypatch.chdir(tmp_path)
+    base, head = _git_repo(tmp_path)
+    # The base commit itself is NOT inside base..HEAD -> out of range.
+    write_plan("gr-bad", _plan_with_claim(base))
+    init_to("gr-bad", ("investigating", "planning", "implementing"))
+    v = decision.decide("gr-bad", base=base)
+    assert (v["action"], v["reason_code"]) == ("stop", "git-evidence-conflict")
+    assert v["git"]["conflicts"][0]["type"] == "commit-out-of-range"
+
+
+def test_git_evidence_unresolvable_commit_stops(tmp_path, monkeypatch):
+    monkeypatch.chdir(tmp_path)
+    base, head = _git_repo(tmp_path)
+    write_plan("gr-unres", _plan_with_claim("0000000"))
+    init_to("gr-unres", ("investigating", "planning", "implementing"))
+    v = decision.decide("gr-unres", base=base)
+    assert (v["action"], v["reason_code"]) == ("stop", "git-evidence-conflict")
+
+
+def test_git_evidence_wrong_base_not_ancestor_stops(tmp_path, monkeypatch):
+    monkeypatch.chdir(tmp_path)
+    base, head = _git_repo(tmp_path)
+    branch = subprocess.run(
+        ["git", "branch", "--show-current"],
+        cwd=tmp_path,
+        capture_output=True,
+        text=True,
+    ).stdout.strip()
+    # A commit on a divergent branch is not an ancestor of HEAD.
+    subprocess.run(
+        ["git", "checkout", "-q", "-b", "side", base],
+        cwd=tmp_path,
+        check=True,
+        capture_output=True,
+        text=True,
+    )
+    subprocess.run(
+        ["git", "commit", "--allow-empty", "-q", "-m", "side"],
+        cwd=tmp_path,
+        check=True,
+        capture_output=True,
+        text=True,
+    )
+    side = subprocess.run(
+        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True
+    ).stdout.strip()
+    subprocess.run(
+        ["git", "checkout", "-q", branch],
+        cwd=tmp_path,
+        check=True,
+        capture_output=True,
+        text=True,
+    )
+    write_plan("gr-wb", _plan_with_claim(head))
+    init_to("gr-wb", ("investigating", "planning", "implementing"))
+    v = decision.decide("gr-wb", base=side)
+    assert (v["action"], v["reason_code"]) == ("stop", "base-unresolved")
+
+
+# --- task-order parity vs render_plan (SC-5) -------------------------------------------
+
+
+def test_git_evidence_parity_cursor_matches_renderer_task_order(tmp_path, monkeypatch):
+    """Ordered task IDs must match render_plan for both markdown and legacy XML.
+    Ordering only — the renderer's presentation-grade done set is NOT compared."""
+    monkeypatch.chdir(tmp_path)
+    import render_plan
+
+    for body in (_ACTIVE_MD_PLAN, _XML_PLAN):
+        mine = [t["id"] for t in decision.parse_tasks(body)[0]]
+        theirs = [t["id"] for t in render_plan.extract_tasks(body)[0]]
+        assert mine == theirs == ["1.1", "1.2"]
+
+
+# --- STATE hint + SUMMARY deviations (SC-6) --------------------------------------------
+
+
+def _write_state(slug: str, updated: date, last: str = "did stuff") -> None:
+    Path("specs").mkdir(exist_ok=True)
+    Path("specs/STATE.md").write_text(
+        "# Workflow State\n\n## Active Spec\n\n"
+        f"- **Slug:** {slug}\n"
+        "- **Phase:** implement\n"
+        f"- **Last action:** {last}\n"
+        f"- **Updated:** {updated.isoformat()}\n\n"
+        "## Recent Specs\n",
+        encoding="utf-8",
+    )
+
+
+def test_state_hint_same_slug_recent_is_consumed(tmp_path, monkeypatch):
+    monkeypatch.chdir(tmp_path)
+    write_plan("sh-ok")
+    init_to("sh-ok", ("investigating", "planning", "implementing"))
+    _write_state("sh-ok", date.today() - timedelta(days=1))
+    v = decision.decide("sh-ok")
+    assert v["session_hint"] is not None
+    assert v["session_hint"]["slug"] == "sh-ok"
+    assert (
+        "state-stale" not in v["warnings"] and "state-wrong-slug" not in v["warnings"]
+    )
+    # STATE never overrides the durable route.
+    assert v["action"] == "execute-plan"
+
+
+def test_state_hint_wrong_slug_is_ignored_with_warning(tmp_path, monkeypatch):
+    monkeypatch.chdir(tmp_path)
+    write_plan("sh-wrong")
+    init_to("sh-wrong", ("investigating", "planning", "implementing"))
+    _write_state("some-other-slug", date.today())
+    v = decision.decide("sh-wrong")
+    assert v["session_hint"] is None
+    assert "state-wrong-slug" in v["warnings"]
+
+
+def test_state_hint_stale_is_ignored_with_warning(tmp_path, monkeypatch):
+    monkeypatch.chdir(tmp_path)
+    write_plan("sh-stale")
+    init_to("sh-stale", ("investigating", "planning", "implementing"))
+    _write_state("sh-stale", date.today() - timedelta(days=30))
+    v = decision.decide("sh-stale")
+    assert v["session_hint"] is None
+    assert "state-stale" in v["warnings"]
+
+
+def test_deviations_are_returned_verbatim_without_changing_routing(
+    tmp_path, monkeypatch
+):
+    monkeypatch.chdir(tmp_path)
+    write_plan("dev")
+    init_to("dev", ("investigating", "planning", "implementing"))
+    Path("specs/dev/SUMMARY.md").write_text(
+        "# Summary\n\n### Deviations\n\n"
+        "- Rule 2 — Added a guard for invalid input. `x.py`. Commit `abc1234`.\n"
+        "- Rule 3 — Added dep `foo>=1`. Commit `def5678`.\n\n"
+        "### Verify\n",
+        encoding="utf-8",
+    )
+    v = decision.decide("dev")
+    assert v["deviations"] == [
+        "Rule 2 — Added a guard for invalid input. `x.py`. Commit `abc1234`.",
+        "Rule 3 — Added dep `foo>=1`. Commit `def5678`.",
+    ]
+    assert v["action"] == "execute-plan"  # deviations never change the lifecycle route
+
+
+# --- paused / proposed plan activation (SC-2 execution route) --------------------------
+
+
+def test_state_hint_paused_plan_requires_activation_action(tmp_path, monkeypatch):
+    monkeypatch.chdir(tmp_path)
+    write_plan("paused", _ACTIVE_MD_PLAN.replace("status: active", "status: paused"))
+    init_to("paused", ("investigating", "planning", "implementing"))
+    v = decision.decide("paused")
+    assert (v["action"], v["reason_code"]) == (
+        "execute-plan",
+        "plan-activation-required",
+    )
+    assert v["required_transition"]["kind"] == "activate-plan"
+    assert v["required_transition"]["to_status"] == "active"
+
+
+# --- schema stability (SC-7) -----------------------------------------------------------
+
+_KEYS = {
+    "schema_version",
+    "slug",
+    "action",
+    "reason_code",
+    "reason",
+    "run",
+    "plan",
+    "cursor",
+    "git",
+    "interrupt",
+    "session_hint",
+    "deviations",
+    "required_transition",
+    "warnings",
+}
+
+
+def test_schema_all_action_families_carry_stable_top_level_keys(tmp_path, monkeypatch):
+    monkeypatch.chdir(tmp_path)
+    write_plan("sc-exec")
+    init_to("sc-exec", ("investigating", "planning", "implementing"))
+    write_plan("sc-wait")
+    init_to("sc-wait", ("investigating", "awaiting_confirmation"))
+    write_plan("sc-stop")
+    init_to("sc-stop", ("investigating", "planning", "cancelled"))
+    write_plan("sc-repair")
+    init_to("sc-repair", PATHS["fixing_ci"])
+    write_plan("sc-review")
+    init_to("sc-review", PATHS["verifying"])
+    write_plan("sc-int")
+    init_to("sc-int", ("investigating", "planning", "blocked"))
+    init_to("sc-rebuild", ("investigating", "planning"))
+    Path(rs.run_json_path("sc-rebuild")).unlink()
+
+    for slug in (
+        "sc-exec",
+        "sc-wait",
+        "sc-stop",
+        "sc-repair",
+        "sc-review",
+        "sc-int",
+        "sc-rebuild",
+    ):
+        v = decision.decide(slug)
+        assert set(v.keys()) == _KEYS, slug
+        assert v["schema_version"] == 1
+        assert v["slug"] == slug
+
+
+# --- semantic read-only (SC-7) ---------------------------------------------------------
+
+
+def _canon_bytes(slug: str) -> dict:
+    out = {}
+    for name, p in (
+        ("run", rs.run_json_path(slug)),
+        ("events", rs.events_path(slug)),
+        ("plan", str(Path("specs") / slug / "PLAN.md")),
+    ):
+        pp = Path(p)
+        out[name] = pp.read_bytes() if pp.exists() else None
+    return out
+
+
+def test_readonly_every_action_family_leaves_canonical_files_byte_identical(
+    tmp_path, monkeypatch
+):
+    monkeypatch.chdir(tmp_path)
+    families = {}
+
+    write_plan("ro-exec")
+    init_to("ro-exec", ("investigating", "planning", "implementing"))
+    families["ro-exec"] = None
+
+    write_plan("ro-wait")
+    init_to("ro-wait", ("investigating", "awaiting_confirmation"))
+    families["ro-wait"] = None
+
+    write_plan("ro-stop")
+    init_to("ro-stop", ("investigating", "planning", "cancelled"))
+    families["ro-stop"] = None
+
+    write_plan("ro-repair")
+    init_to("ro-repair", PATHS["fixing_ci"])
+    families["ro-repair"] = None
+
+    write_plan("ro-review")
+    init_to("ro-review", PATHS["verifying"])
+    families["ro-review"] = None
+
+    write_plan("ro-int")
+    init_to("ro-int", ("investigating", "planning", "blocked"))
+    families["ro-int"] = None
+
+    # rebuild family: events-only store, PLAN present.
+    write_plan("ro-rebuild")
+    init_to("ro-rebuild", ("investigating", "planning"))
+    Path(rs.run_json_path("ro-rebuild")).unlink()
+    families["ro-rebuild"] = None
+
+    for slug in families:
+        before = _canon_bytes(slug)
+        v = decision.decide(slug)
+        after = _canon_bytes(slug)
+        assert before == after, f"{slug} ({v['action']}) mutated canonical evidence"
+
+
+# --- CLI exit codes --------------------------------------------------------------------
+
+
+def test_readonly_cli_exit_codes(tmp_path, monkeypatch):
+    monkeypatch.chdir(tmp_path)
+    write_plan("cli")
+    init_to("cli", ("investigating", "planning", "implementing"))
+    assert decision.main(["--slug", "cli"]) == 0
+    # terminal / wait / rebuild are valid decisions -> exit 0.
+    init_to("cli-term", ("investigating", "planning", "cancelled"))
+    assert decision.main(["--slug", "cli-term"]) == 0
+    with pytest.raises(SystemExit) as ei:  # CLI misuse -> argparse exit 2
+        decision.main([])
+    assert ei.value.code == 2

```
