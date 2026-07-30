#!/usr/bin/env python3
"""Create a deterministic, task-local brief without copying it into controller context."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from pathlib import Path


def git_root() -> Path:
    return Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )


def section(text: str, heading: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", text)
    return match.group(1).strip() if match else "none"


def task_block(text: str, task_id: str) -> re.Match[str] | None:
    """Find an exact markdown task ID, never a dotted-prefix sibling."""
    return re.search(
        rf"(?ms)^### Task {re.escape(task_id)}(?=\s|:|—|-|$)[^\n]*\n(.*?)(?=^### Task |^## |\Z)",
        text,
    )


def mapped_rows(text: str, ids: list[str]) -> list[str]:
    wanted = set(ids)
    return [
        line
        for line in section(text, "3. Success Criteria").splitlines()
        if (match := re.match(r"^\|\s*(SC-\d+)\s*\|", line))
        and match.group(1) in wanted
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--task", help="a '### Task N.N' id from the plan")
    parser.add_argument(
        "--delta-description",
        help="for a non-task delta review (e.g. the simplify stage): a short "
        "description of what's under review, in place of --task",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if bool(args.task) == bool(args.delta_description):
        raise SystemExit(
            "task-brief: exactly one of --task or --delta-description is required"
        )
    plan = args.plan.resolve()
    text = plan.read_text(encoding="utf-8")
    root = git_root()
    if args.task:
        task = task_block(text, args.task)
        if not task:
            raise SystemExit(f"task-brief: task {args.task} not found in {plan}")
        criteria = re.search(r"(?m)^[-*] \*\*Criteria:\*\*\s*(.+)$", task.group(1))
        ids = re.findall(r"SC-\d+", criteria.group(1) if criteria else "")
        rows = mapped_rows(text, ids)
        interfaces = re.search(r"(?m)^[-*] \*\*Interfaces:\*\*\s*(.+)$", task.group(1))
        digest = hashlib.sha256(f"{plan}:{args.task}".encode()).hexdigest()[:12]
        output = (
            args.output
            or root
            / ".harness-state"
            / "sdd"
            / f"{plan.parent.name}-{args.task}-{digest}.brief.md"
        )
        payload = (
            f"# Task brief: {args.task}\n\nPlan: `{plan}`\n\n## Global Constraints\n\n{section(text, 'Global Constraints')}\n\n## Task\n\n{task.group(0).strip()}\n\n## Mapped Success Criteria\n\n"
            + ("\n".join(rows) if rows else "none")
            + "\n\n## Interfaces\n\n"
            + (interfaces.group(1) if interfaces else "none")
            + "\n"
        )
    else:
        digest = hashlib.sha256(
            f"{plan}:{args.delta_description}".encode()
        ).hexdigest()[:12]
        output = (
            args.output
            or root
            / ".harness-state"
            / "sdd"
            / f"{plan.parent.name}-delta-{digest}.brief.md"
        )
        payload = f"# Delta brief\n\nPlan: `{plan}`\n\n## Global Constraints\n\n{section(text, 'Global Constraints')}\n\n## Delta\n\n{args.delta_description}\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    output.chmod(0o600)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
