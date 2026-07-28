#!/usr/bin/env python3
"""Append first-run skill-eval observations without permitting result replacement."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def git_sha(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def case_index(root: Path) -> dict[str, tuple[str, str, str]]:
    manifest = json.loads((root / "evals/skills/prompt-refactor/corpus-manifest.json").read_text())
    indexed: dict[str, tuple[str, str, str]] = {}
    for item in manifest["skills"]:
        skill = item["name"]
        for suite, key in (("activation", "activation"), ("behavior", "behavior")):
            for case in json.loads((root / item[key]).read_text())["cases"]:
                indexed[case["id"]] = (skill, suite, case.get("split", "holdout"))
    for case in json.loads((root / manifest["end_to_end"]).read_text())["cases"]:
        indexed[case["id"]] = (case.get("skill", "workflow"), "end-to-end", case.get("split", "holdout"))
    return indexed


def load(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": 1, "commit_sha": "", "environment": {}, "records": []}
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--verdict", choices=("pass", "missed", "false-positive", "blocked"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--client-version", required=True)
    parser.add_argument("--reasoning", required=True)
    parser.add_argument("--observation", required=True, help="concise first-run observed behavior and evidence")
    parser.add_argument("--safety-critical", action="store_true")
    parser.add_argument("--tokens", type=int, default=0)
    parser.add_argument("--tool-calls", type=int, default=0)
    parser.add_argument("--elapsed-ms", type=int, default=0)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        index = case_index(root)
        if args.case not in index:
            raise ValueError(f"unknown corpus case: {args.case}")
        data = load(args.results)
        if any(record.get("case_id") == args.case for record in data.get("records", [])):
            raise ValueError(f"first-run result already exists for {args.case}; create a separate attempt file")
        environment = {"model": args.model, "client_version": args.client_version, "reasoning": args.reasoning}
        if data["records"] and data.get("environment") != environment:
            raise ValueError("environment differs from existing result file")
        skill, suite, split = index[args.case]
        data["schema_version"] = 1
        data["commit_sha"] = git_sha(root)
        data["environment"] = environment
        data.setdefault("records", []).append({
            "case_id": args.case, "skill": skill, "suite": suite, "split": split,
            "first_run": True, "observation": args.observation, "verdict": args.verdict, "safety_critical": args.safety_critical,
            "tokens": args.tokens, "tool_calls": args.tool_calls, "elapsed_ms": args.elapsed_ms,
        })
        args.results.parent.mkdir(parents=True, exist_ok=True)
        args.results.write_text(json.dumps(data, indent=2) + "\n")
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"skill-eval-record: {exc}", file=sys.stderr)
        return 1
    print(f"skill-eval-record: recorded {args.case}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
