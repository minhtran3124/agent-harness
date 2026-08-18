#!/usr/bin/env python3
"""Aggregate deterministic source checks for the task-review rollout."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    commands = [
        [sys.executable, "scripts/check_task_review_contract.py"],
        [sys.executable, "scripts/check_plan_contract.py", "specs/superpowers-6-review-pipeline-adoption/PLAN.md"],
        ["bash", "tests/scripts/task-reviewer-readonly.test.sh"],
        ["bash", "tests/scripts/sdd-artifact-handoffs.test.sh"],
        ["bash", "tests/scripts/sdd-task-review-routing.test.sh"],
        ["bash", "tests/scripts/final-review-package-contract.test.sh"],
        ["bash", "scripts/lint-doc-truth.sh"],
    ]
    failed = [" ".join(command) for command in commands if subprocess.run(command, cwd=ROOT).returncode]
    if failed:
        print("task-review adoption failed: " + "; ".join(failed), file=sys.stderr)
        return 1
    print("task-review-adoption: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
