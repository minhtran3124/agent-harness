#!/usr/bin/env python3
"""Generate the checked-in activation and behavior fixtures for skill prompts."""

from __future__ import annotations

import json
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "evals/skills/prompt-refactor"

# Each entry is intentionally user-intent phrasing, not a copy of the frontmatter description.
SPECS = {
    "brainstorming": (
        "Help me explore alternatives and approve a design for a new feature.",
        "The design is approved; implement the first task now.",
        "design approval before code",
        "stop implementation until design approval",
        "handoff xia2 then writing-plans",
    ),
    "compound": (
        "Capture the non-obvious bug fix and decision from this session as reusable knowledge.",
        "Search the existing knowledge base for a past decision.",
        "compound a complete failure record",
        "skip an incomplete learning",
        "write docs and rebuild the index",
    ),
    "context-propagation-audit": (
        "Audit whether a changed reviewer prompt delivers its path-scoped rule to child agents.",
        "Find runtime bugs in this application diff.",
        "audit a workflow-engine change",
        "skip a non-workflow diff",
        "report delivery proof for every consumer",
    ),
    "correctness-review": (
        "Run an adversarial runtime-bug review over this finished diff.",
        "Check whether this diff matches the user's original request.",
        "review a complete diff",
        "route a Rule 4 finding to escalation",
        "deduplicate and score candidates",
    ),
    "feature-intake": (
        "Classify this change request into a risk lane and confidence before any edit.",
        "Execute the approved implementation plan task by task.",
        "classify a new request",
        "escalate an ambiguous hard-gate request",
        "write SUMMARY and route work",
    ),
    "finishing-a-development-branch": (
        "Tests passed; push this branch and open a pull request without merging it.",
        "Review the uncommitted diff for likely runtime defects.",
        "finish a reviewed branch",
        "refuse a stale review receipt",
        "open PR but never merge",
    ),
    "intent-review": (
        "Compare this completed diff against the user's original request, not the plan.",
        "Find async, database, and contract runtime bugs in this diff.",
        "review verbatim intent",
        "stop when no intent oracle exists",
        "record gap excess or drift",
    ),
    "subagent-driven-development": (
        "Execute the active implementation plan in waves with isolated implementers and reviews.",
        "Create an implementation plan from this approved design.",
        "execute a valid plan",
        "stop on an invalid or blocked resume state",
        "run final review receipt chain",
    ),
    "using-git-worktrees": (
        "Set up an isolated worktree and branch before we start feature implementation.",
        "Open a pull request for an already completed branch.",
        "isolate a normal checkout",
        "detect a submodule or existing worktree",
        "deploy harness in the workspace",
    ),
    "visual-planner": (
        "Render this PLAN.md as HTML so I can inspect the execution waves.",
        "Write an implementation plan from the design and research brief.",
        "render a plain plan",
        "surface renderer self-check failure",
        "render graph review sidecar",
    ),
    "writing-plans": (
        "Turn the approved design and research brief into a detailed implementation plan.",
        "Start editing code for this tiny one-file typo.",
        "write a plan from required inputs",
        "stop when research brief is missing",
        "handoff isolated execution",
    ),
    "xia2": (
        "Research what already exists locally and upstream before we implement this capability.",
        "Apply the already approved implementation task without additional research.",
        "research a new capability",
        "surface a Deep risk under a waiver",
        "save the research brief",
    ),
}

# Behavior probes need the prerequisites that a real skill consumes; an expectation label alone
# is not a runnable scenario (notably compound needs a complete learning and intent needs an
# oracle plus a diff). Unlisted cases use the concise generic probe constructed below.
BEHAVIOR_PROMPTS = {
    "compound": {
        "golden": "Incident record: Deploying v2 served stale tenant permissions after role changes. Trigger: revoke a role then refresh within 60s. Root cause: cache key omitted permission version. Failed attempt: lowering cache TTL. Fix: include permission version in the key. Proof: regression test revokes a role then asserts 403 after refresh. Affected paths: auth/cache.py and policy service. Reusable decision: cache authorization by versioned permission state. Compound this complete failure record into durable knowledge.",
    },
    "feature-intake": {
        "handoff": "A request adds a public OAuth callback route and token validation. Classify it, write the required SUMMARY fields, and explicitly name the next workflow route.",
    },
    "intent-review": {
        "handoff": "Verbatim intent: 'Show a warning before deleting a project; do not delete until confirmation.' Diff behavior: the UI deletes immediately after the first click. Perform the intent-review handoff and record the applicable gap, excess, or drift finding.",
    },
}


def activation_cases(
    skill: str, positive: str, negative: str
) -> list[dict[str, object]]:
    positive_variants = [
        positive,
        f"Before we touch code, {positive.lower()}",
        f"I am unsure of the safest workflow; {positive.lower()}",
        f"Please do this in the repository: {positive.lower()}",
        f"This is time-sensitive, but {positive.lower()}",
        f"Use the project workflow to {positive.lower()}",
        f"Can you take ownership of this request? {positive}",
        f"Do not implement anything else; {positive.lower()}",
    ]
    negative_variants = [
        negative,
        f"Do only this instead: {negative.lower()}",
        f"The user asked us to {negative.lower()}",
        f"This request is adjacent but distinct: {negative.lower()}",
        f"Do not route to the wrong specialist; {negative.lower()}",
        f"For this branch, {negative.lower()}",
        f"Handle the direct request: {negative.lower()}",
        f"The next action should be: {negative.lower()}",
    ]
    cases = []
    for polarity, variants in ((True, positive_variants), (False, negative_variants)):
        for index, query in enumerate(variants, start=1):
            cases.append(
                {
                    "id": f"{skill}-{'trigger' if polarity else 'near-miss'}-{index}",
                    "skill": skill,
                    "query": query,
                    "should_trigger": polarity,
                    "split": "holdout" if index == len(variants) else "train",
                }
            )
    return cases


def behavior_cases(
    skill: str, golden: str, boundary: str, handoff: str
) -> list[dict[str, str]]:
    prompts = BEHAVIOR_PROMPTS.get(skill, {})
    return [
        {
            "id": f"{skill}-golden",
            "skill": skill,
            "kind": "golden",
            "expectation": golden,
            "prompt": prompts.get("golden", golden),
        },
        {
            "id": f"{skill}-boundary",
            "skill": skill,
            "kind": "boundary",
            "expectation": boundary,
            "prompt": prompts.get("boundary", boundary),
        },
        {
            "id": f"{skill}-handoff",
            "skill": skill,
            "kind": "handoff",
            "expectation": handoff,
            "prompt": prompts.get("handoff", handoff),
        },
    ]


def generate(root: Path) -> None:
    out = root / "evals/skills/prompt-refactor"
    activation_dir = out / "activation"
    behavior_dir = out / "behavior"
    activation_dir.mkdir(parents=True, exist_ok=True)
    behavior_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "skills": [],
        "end_to_end": "evals/skills/prompt-refactor/end-to-end.json",
    }
    for skill, (positive, negative, golden, boundary, handoff) in sorted(SPECS.items()):
        activation_path = activation_dir / f"{skill}.json"
        behavior_path = behavior_dir / f"{skill}.json"
        activation_path.write_text(
            json.dumps({"cases": activation_cases(skill, positive, negative)}, indent=2)
            + "\n"
        )
        behavior_path.write_text(
            json.dumps(
                {"cases": behavior_cases(skill, golden, boundary, handoff)}, indent=2
            )
            + "\n"
        )
        manifest["skills"].append(
            {
                "name": skill,
                "activation": activation_path.relative_to(root).as_posix(),
                "behavior": behavior_path.relative_to(root).as_posix(),
            }
        )
    (out / "end-to-end.json").write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "e2e-tiny",
                        "lane": "tiny",
                        "expectation": "branch then direct edit with SUMMARY evidence",
                        "prompt": "Scenario: one line of README.md has a typo. Nothing else changes. Name, in order, the workflow steps this repository requires from intake to shipping, and the evidence artifact that must be written.",
                    },
                    {
                        "id": "e2e-normal",
                        "lane": "normal",
                        "expectation": "isolate, execute plan, review, and open PR",
                        "prompt": "Scenario: add an optional --format flag to an existing script; roughly three files and five steps. Name, in order, the workflow steps this repository requires from intake to opening a pull request.",
                    },
                    {
                        "id": "e2e-high-risk",
                        "lane": "high-risk",
                        "expectation": "design, research, plan, execution, review, and receipt",
                        "prompt": "Scenario: add a new OAuth login provider plus a database migration that rewrites the users table. Name, in order, the workflow steps this repository requires from intake to shipping, including every required artifact and gate.",
                    },
                    {
                        "id": "e2e-resume",
                        "lane": "normal",
                        "expectation": "reconstruct cursor before any resumed task",
                        "prompt": "Scenario: an earlier session partly executed specs/<slug>/PLAN.md and ended. You are starting a brand-new session with no memory of that work. State exactly what you must establish before dispatching any remaining task.",
                    },
                    {
                        "id": "e2e-workflow-engine",
                        "lane": "high-risk",
                        "expectation": "context-propagation audit precedes correctness and intent",
                        "prompt": "Scenario: the finished diff changes skills/, agent dispatch prompts, and rules/. State the required review sequence, in order, before this branch may ship.",
                    },
                ]
            },
            indent=2,
        )
        + "\n"
    )
    (out / "corpus-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    generate(args.root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
