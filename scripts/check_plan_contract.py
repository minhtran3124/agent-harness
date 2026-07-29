#!/usr/bin/env python3
"""Validate the context contract required by new Superpowers-6 plans.

Legacy plans remain valid.  A plan opts into the new contract by declaring
``## Global Constraints`` (all plans written by the updated authoring skill do).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TASK = re.compile(r"(?ms)^### Task ([0-9][\w.]*)[^\n]*\n(.*?)(?=^### Task |^## |\Z)")
FIELD = re.compile(r"(?m)^[-*] \*\*(Criteria|Interfaces):\*\*\s*(.+)$")
SC = re.compile(r"\bSC-\d+\b")


def errors(text: str, name: str = "PLAN.md") -> list[str]:
    if "## Global Constraints" not in text:
        return []  # Legacy markdown/XML remains executable.
    found: list[str] = []
    section = re.search(r"(?ms)^## Global Constraints\s*\n(.*?)(?=^## |\Z)", text)
    if not section or not re.search(r"(?m)^[-*] .+", section.group(1)):
        found.append(f"{name}: Global Constraints must contain at least one bullet")
    criteria = set(re.findall(r"(?m)^\|\s*(SC-\d+)\s*\|", text))
    if not criteria:
        found.append(f"{name}: Success Criteria table has no SC rows")
    produced: set[str] = set()
    consumed: list[tuple[str, str]] = []
    tasks = list(TASK.finditer(text))
    if not tasks:
        found.append(f"{name}: no markdown tasks found")
    for task in tasks:
        task_id, body = task.group(1), task.group(2)
        fields = {k: v.strip() for k, v in FIELD.findall(body)}
        missing = {"Criteria", "Interfaces"} - set(fields)
        if missing:
            found.append(f"{name}: Task {task_id} missing {', '.join(sorted(missing))}")
            continue
        mapped = set(SC.findall(fields["Criteria"]))
        if not mapped:
            found.append(f"{name}: Task {task_id} Criteria needs an SC-n mapping")
        unknown = mapped - criteria
        if unknown:
            found.append(f"{name}: Task {task_id} references unknown criteria: {', '.join(sorted(unknown))}")
        interface = fields["Interfaces"]
        if not re.search(r"\bConsumes?\b", interface, re.I) or not re.search(r"\bProduces?\b", interface, re.I):
            found.append(f"{name}: Task {task_id} Interfaces must name what it consumes and produces")
        for value in re.findall(r"(?:Produces?|produces)\s*:?\s*([^.;]+)", interface, re.I):
            for token in re.findall(r"`?([\w./-]+)`?", value):
                if token not in {"and", "or"}:
                    produced.add(token)
        for value in re.findall(r"(?:Consumes?|consumes)\s*:?\s*([^.;]+)", interface, re.I):
            consumed.append((task_id, value))
    for task_id, value in consumed:
        for token in re.findall(r"`([\w./-]+)`", value):
            if token not in produced and not token.endswith((".md", ".json")):
                found.append(f"{name}: Task {task_id} consumes {token} with no producer")
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        valid = """## Global Constraints\n\n- Safe\n\n## 3. Success Criteria\n\n| ID | Behavior (observable) | Check (re-runnable) | Expected |\n| --- | --- | --- | --- |\n| SC-1 | works | `true` | exit 0 |\n\n## 4. Tasks\n\n### Task 1.1 — x\n\n- **Files:** x\n- **Action:** x\n- **Verify:** `true`\n- **Done:** x\n- **Criteria:** SC-1\n- **Interfaces:** Consumes: input. Produces: output.\n"""
        if errors(valid) or not errors("## Global Constraints\n\n## 4. Tasks\n"):
            return 1
        print("plan-contract: self-test passed")
        return 0
    if not args.plan:
        parser.error("plan is required unless --self-test is used")
    found = errors(args.plan.read_text(encoding="utf-8"), str(args.plan))
    if found:
        print("\n".join(found), file=sys.stderr)
        return 1
    print(f"plan-contract: {args.plan} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
