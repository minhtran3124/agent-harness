#!/usr/bin/env python3
"""Create a deterministic, task-local brief without copying it into controller context."""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from pathlib import Path


def git_root() -> Path:
    return Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())


def section(text: str, heading: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", text)
    return match.group(1).strip() if match else "none"


def task_block(text: str, task_id: str) -> re.Match[str] | None:
    """Find an exact markdown task ID, never a dotted-prefix sibling."""
    return re.search(
        rf"(?ms)^### Task {re.escape(task_id)}(?=\s|—|-|$)[^\n]*\n(.*?)(?=^### Task |^## |\Z)",
        text,
    )


def mapped_rows(text: str, ids: list[str]) -> list[str]:
    wanted = set(ids)
    return [
        line
        for line in section(text, "3. Success Criteria").splitlines()
        if (match := re.match(r"^\|\s*(SC-\d+)\s*\|", line)) and match.group(1) in wanted
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    plan = args.plan.resolve()
    text = plan.read_text(encoding="utf-8")
    task = task_block(text, args.task)
    if not task:
        raise SystemExit(f"task-brief: task {args.task} not found in {plan}")
    criteria = re.search(r"(?m)^[-*] \*\*Criteria:\*\*\s*(.+)$", task.group(1))
    ids = re.findall(r"SC-\d+", criteria.group(1) if criteria else "")
    rows = mapped_rows(text, ids)
    root = git_root()
    digest = hashlib.sha256(f"{plan}:{args.task}".encode()).hexdigest()[:12]
    output = args.output or root / ".harness-state" / "sdd" / f"{plan.parent.name}-{args.task}-{digest}.brief.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = f"# Task brief: {args.task}\n\nPlan: `{plan}`\n\n## Global Constraints\n\n{section(text, 'Global Constraints')}\n\n## Task\n\n{task.group(0).strip()}\n\n## Mapped Success Criteria\n\n" + ("\n".join(rows) if rows else "none") + "\n\n## Interfaces\n\n" + (re.search(r"(?m)^[-*] \*\*Interfaces:\*\*\s*(.+)$", task.group(1)).group(1) if re.search(r"(?m)^[-*] \*\*Interfaces:\*\*\s*(.+)$", task.group(1)) else "none") + "\n"
    output.write_text(payload, encoding="utf-8")
    output.chmod(0o600)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
