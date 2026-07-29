#!/usr/bin/env python3
"""Capture one clean Claude skill-evaluation response without grading it.

The recorder deliberately does not invoke models. This companion keeps the raw first response in
an explicit file so terminal truncation cannot turn a completed clean-context dispatch into lost
evidence. It supplies no tools and never changes the evaluated worktree.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def extract_result(payload: Any) -> tuple[str, dict[str, Any]]:
    """Return Claude's final result text and compact usage from JSON output."""
    blocks = payload if isinstance(payload, list) else [payload]
    for block in reversed(blocks):
        if isinstance(block, dict) and block.get("type") == "result":
            result = block.get("result")
            if not isinstance(result, str) or not result.strip():
                raise ValueError("Claude result has no text")
            usage = block.get("usage")
            return result, usage if isinstance(usage, dict) else {}
    raise ValueError("Claude JSON contains no final result")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", type=Path, required=True, help="raw JSON transcript path")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--claude", default="claude")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--effort", default="low")
    parser.add_argument("--max-budget-usd", default="0.25")
    args = parser.parse_args()

    arguments = [
        "--dangerously-skip-permissions",
        "-p",
        "--output-format",
        "json",
        "--no-session-persistence",
        "--tools",
        "",
        "--max-budget-usd",
        args.max_budget_usd,
        "--model",
        args.model,
        "--effort",
        args.effort,
        args.prompt,
    ]
    command = [args.claude, *arguments]
    try:
        completed = subprocess.run(
            command,
            cwd=args.cwd,
            stdin=subprocess.DEVNULL,
            text=True,
            capture_output=True,
            check=False,
        )
        payload = json.loads(completed.stdout)
        result, usage = extract_result(payload)
        transcript = {
            "command": command[:-1],
            "cwd": str(args.cwd.resolve()),
            "returncode": completed.returncode,
            "result": result,
            "usage": usage,
            "stderr": completed.stderr,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(transcript, indent=2) + "\n", encoding="utf-8")
        if completed.returncode:
            print(f"skill-eval-capture: Claude exited {completed.returncode}", file=sys.stderr)
            return completed.returncode
        print(json.dumps({"result": result, "usage": usage}, ensure_ascii=False))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"skill-eval-capture: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
