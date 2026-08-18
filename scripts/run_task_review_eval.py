#!/usr/bin/env python3
"""Capture first-run task-review observations with no fixture truths in prompts."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


def extract(raw: str) -> tuple[str, dict]:
    events = json.loads(raw)
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    return result.get("result", ""), result.get("usage", {})


def prompt(mode: str, body: str) -> list[str]:
    common = "Review the following isolated fixture. Do not make changes. Return concise labels and evidence.\n\n" + body
    if mode == "baseline":
        return [
            common + "\n\nSPEC pass or fail? Identify missing/extra requested behavior.",
            common + "\n\nQUALITY approved or needs_fixes? Classify any concern Critical, Important, or Minor.",
        ]
    return [common + "\n\nThe fixture statements are the complete provided evidence: do not demand files that the fixture does not claim to provide. Use cannot_verify only when the fixture explicitly says an external contract is unavailable. Return spec_verdict: pass|fail|cannot_verify; quality_verdict: approved|needs_fixes; findings with Critical|Important|Minor. Unknown evidence must be cannot_verify."]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, default=Path("evals/skills/task-review/fixtures"))
    parser.add_argument("--claude", default="claude")
    parser.add_argument("--model", default="claude-fable-5")
    parser.add_argument("--reasoning", default="standard")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"task-review-eval: refusing to overwrite first-run result: {args.output}")
    version = subprocess.check_output([args.claude, "--version"], text=True).strip()
    records = []
    for fixture in sorted(p for p in args.fixtures.iterdir() if (p / "input.md").is_file()):
        calls = prompt(args.mode, (fixture / "input.md").read_text())
        texts, usages, elapsed = [], [], []
        for index, call in enumerate(calls, 1):
            start = time.monotonic()
            proc = subprocess.run([args.claude, "-p", call, "--output-format", "json", "--no-session-persistence", "--model", args.model], text=True, capture_output=True, check=False)
            elapsed.append(round(time.monotonic() - start, 3))
            if proc.returncode:
                raise SystemExit(f"task-review-eval: {fixture.name} call {index} failed: {proc.stderr.strip()}")
            text, usage = extract(proc.stdout)
            texts.append(text)
            usages.append(usage)
        transcript = args.output.parent / "transcripts" / f"{args.mode}-{fixture.name}.json"
        transcript.parent.mkdir(parents=True, exist_ok=True)
        transcript.write_text(json.dumps({"outputs": texts, "usage": usages}, indent=2) + "\n")
        records.append({"case_id": fixture.name, "first_run": True, "dispatches": len(calls), "outputs": texts, "usage": usages, "elapsed_seconds": elapsed, "transcript": str(transcript)})
    data = {"schema_version": 1, "commit_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "environment": {"model": args.model, "client_version": version, "reasoning": args.reasoning}, "mode": args.mode, "records": records}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
