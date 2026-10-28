#!/usr/bin/env python3
"""Fail when the retired per-task review machinery comes back into the implement skill (#342)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RETIRED_PATHS = (
    "skills/subagent-driven-development",
    "skills/implement/task-reviewer-prompt.md",
    "skills/implement/references",
    "skills/implement/scripts",
)
FORBIDDEN_IN_IMPLEMENT = (
    "task-reviewer",
    "spec_verdict",
    "quality_verdict",
    "review_package",
    "task_brief",
    "resume_decision",
    ".review-receipt",
    ".harness-state",
)


def main() -> int:
    errors = [f"retired path is back: {p}" for p in RETIRED_PATHS if (ROOT / p).exists()]
    skill = ROOT / "skills/implement/SKILL.md"
    if not skill.is_file():
        errors.append("skills/implement/SKILL.md is missing")
    else:
        text = skill.read_text()
        prompt = (ROOT / "skills/implement/implementer-prompt.md").read_text()
        errors += [
            f"skills/implement still mentions retired {item}"
            for item in FORBIDDEN_IN_IMPLEMENT
            if item in text or item in prompt
        ]
        if "## Auto mode" not in text:
            errors.append("skills/implement/SKILL.md has no Auto mode section")
        if "3 rounds" not in text:
            errors.append("skills/implement/SKILL.md does not cap the fix loop at 3 rounds")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("task-review-contract: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
