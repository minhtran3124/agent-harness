#!/usr/bin/env python3
"""Run the two-oracle blind reviewer once per review-chain fixture and record raw results."""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path

INSTRUCTIONS = (
    "You are a blind code reviewer running two oracles over one change. "
    "1. CORRECTNESS: find runtime bugs (code that crashes or returns a wrong result). "
    "Each finding names a trigger and the wrong outcome. "
    "2. INTENT: compare the diff to the user's request. "
    "Report gaps (asked, missing), drift (done differently) and excess (not asked for). "
    "Ignore style."
)

OUTPUT_REQUEST = (
    "Return your findings as a JSON array inside one fenced ```json block. Each finding is "
    '{"oracle": "correctness"|"intent", "class": str, "file": str, "line": int|null, '
    '"confidence": int, "summary": str}, with confidence from 0 to 100. '
    "Use class `unknown` for anything you cannot confirm from the diff alone "
    "(for example a symbol defined outside it). Return an empty array if you find nothing."
)


def build_prompt(intent: str, diff: str) -> str:
    return (f"{INSTRUCTIONS}\n\n{OUTPUT_REQUEST}\n\n"
            f"## User request (intent.md)\n\n{intent}\n\n## Diff (diff.patch)\n\n{diff}\n")


def extract(raw: str) -> tuple[str, dict]:
    try:
        data = json.loads(raw)
    except ValueError:
        return "", {}
    events = data if isinstance(data, list) else [data]
    result = next((e for e in reversed(events) if isinstance(e, dict) and e.get("type") == "result"), {})
    return result.get("result", ""), result.get("usage", {})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, default=Path("evals/skills/review-chain/fixtures"))
    parser.add_argument("--claude", default="claude")
    args = parser.parse_args()
    if args.output.exists():
        print(f"review-chain-eval: refusing to overwrite existing result: {args.output}")
        return 1
    fixtures = args.fixtures.resolve()
    try:
        client = subprocess.run([args.claude, "--version"], text=True, capture_output=True, check=False).stdout.strip()
    except OSError as exc:
        print(f"review-chain-eval: cannot run {args.claude}: {exc.strerror or exc}")
        return 1
    cases = {}
    for fixture in sorted(p for p in fixtures.iterdir() if p.is_dir()):
        absent = [n for n in ("intent.md", "diff.patch") if not (fixture / n).is_file()]
        if absent:
            print(f"review-chain-eval: skipping {fixture.name}: missing {', '.join(absent)}")
            continue
        call = build_prompt((fixture / "intent.md").read_text(), (fixture / "diff.patch").read_text())
        with tempfile.TemporaryDirectory() as empty:
            start = time.monotonic()
            proc = subprocess.run([args.claude, "-p", call, "--tools", "", "--model", args.model, "--effort", args.effort,
                                   "--output-format", "json"], cwd=empty, text=True, capture_output=True, check=False)
            elapsed = round(time.monotonic() - start, 3)
        result, usage = extract(proc.stdout)
        cases[fixture.name] = {"rc": proc.returncode, "elapsed": elapsed, "result": result, "usage": usage}
        print(f"{fixture.name}: rc={proc.returncode} elapsed={elapsed}s")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"model": args.model, "effort": args.effort, "client": client, "cases": cases}, indent=2) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
