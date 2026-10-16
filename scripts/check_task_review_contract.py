#!/usr/bin/env python3
"""Fail when the consolidated task-review contract is incomplete or dual prompts stay live."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED = (
    "spec_verdict: pass | fail | cannot_verify",
    "quality_verdict: approved | needs_fixes",
    "Critical | Important | Minor",
    "IMPLEMENTER_REPORT_PATH",
    "REVIEW_PACKAGE_PATH",
    "checked_against: SC-n | none",
    "Quality verdict also covers test seams",
    "copied from the output of the implementation",
    "only synthetic fixtures",
    "one more named, focused read-only search for each declared seam",
)

IMPLEMENTER_REQUIRED = (
    "Write tests only at the seams in the task's `Seams:` field",
    "from a source that is independent of the code",
    "also test the seam on those inputs",
    "cannot observe the behavior, return `NEEDS_CONTEXT` before any edit",
    "Write the red test at a declared seam",
)


def main() -> int:
    prompt = (ROOT / "skills/subagent-driven-development/task-reviewer-prompt.md").read_text()
    errors = [f"task-review contract: missing {item}" for item in REQUIRED if item not in prompt]
    implementer = (ROOT / "skills/subagent-driven-development/implementer-prompt.md").read_text()
    errors += [
        f"implementer contract: missing {item}" for item in IMPLEMENTER_REQUIRED if item not in implementer
    ]
    sdd = (ROOT / "skills/subagent-driven-development/SKILL.md").read_text()
    if "spec then quality" in sdd or "spec-reviewer-prompt.md" in sdd:
        errors.append("task-review contract: SDD still dispatches retired dual review")
    runtime_docs = [
        ROOT / "skills/subagent-driven-development/SKILL.md",
        ROOT / "skills/subagent-driven-development/references/review-chain.md",
        ROOT / "harness-manifest.json",
    ]
    for old in ("spec-reviewer-prompt.md", "code-quality-reviewer-prompt.md"):
        if any(old in p.read_text(errors="ignore") for p in runtime_docs):
            errors.append(f"task-review contract: live reference to retired {old}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("task-review-contract: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
