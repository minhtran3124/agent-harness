#!/usr/bin/env python3
"""Run the two-oracle blind reviewer once per review-chain fixture and record raw results."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
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


def fail(message: str) -> int:
    print(f"review-chain-eval: {message}", file=sys.stderr)
    return 1


def client_version(claude: str) -> str:
    """The client's --version line, or "unknown" (with a warning) when it fails or prints nothing."""
    proc = subprocess.run([claude, "--version"], text=True, capture_output=True, check=False)
    version = proc.stdout.strip()
    if proc.returncode != 0 or not version:
        print(f"review-chain-eval: warning: {claude} --version exited {proc.returncode} with "
              f"{'no output' if not version else 'output ' + repr(version)}; recording client as unknown", file=sys.stderr)
        return "unknown"
    return version


def review(args, call: str) -> tuple[int | str, float, str, dict]:
    with tempfile.TemporaryDirectory() as empty:
        start = time.monotonic()
        try:
            proc = subprocess.run([args.claude, "-p", call, "--tools", "", "--model", args.model, "--effort", args.effort,
                                   "--output-format", "json"], cwd=empty, text=True, capture_output=True, check=False,
                                  timeout=args.timeout)
        except subprocess.TimeoutExpired:
            return "timeout", round(time.monotonic() - start, 3), "", {}
        elapsed = round(time.monotonic() - start, 3)
    result, usage = extract(proc.stdout)
    return proc.returncode, elapsed, result, usage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, default=Path("evals/skills/review-chain/fixtures"))
    parser.add_argument("--claude", default="claude")
    parser.add_argument("--timeout", type=float, default=600.0, help="seconds per review call (default 600)")
    args = parser.parse_args()
    partial = args.output.with_name(args.output.name + ".partial")
    if args.output.exists():
        return fail(f"refusing to overwrite existing result: {args.output}")
    if partial.exists():
        return fail(f"refusing to overwrite partial result of an earlier run: {partial}")
    if not args.fixtures.is_dir():
        return fail(f"fixtures directory not found: {args.fixtures}")
    fixtures = args.fixtures.resolve()
    try:
        client = client_version(args.claude)
    except OSError as exc:
        return fail(f"cannot run {args.claude}: {exc.strerror or exc}")
    record = {"model": args.model, "effort": args.effort, "client": client, "cases": {}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for fixture in sorted(p for p in fixtures.iterdir() if p.is_dir()):
        absent = [n for n in ("intent.md", "diff.patch") if not (fixture / n).is_file()]
        if absent:
            print(f"review-chain-eval: skipping {fixture.name}: missing {', '.join(absent)}")
            continue
        try:
            call = build_prompt((fixture / "intent.md").read_text(), (fixture / "diff.patch").read_text())
        except (OSError, UnicodeDecodeError) as exc:
            print(f"review-chain-eval: skipping {fixture.name}: cannot read fixture ({exc})")
            continue
        rc, elapsed, result, usage = review(args, call)
        record["cases"][fixture.name] = {"rc": rc, "elapsed": elapsed, "result": result, "usage": usage}
        partial.write_text(json.dumps(record, indent=2) + "\n")
        print(f"{fixture.name}: rc={rc} elapsed={elapsed}s")
    try:
        with args.output.open("x") as out:
            out.write(json.dumps(record, indent=2) + "\n")
    except FileExistsError:
        if not partial.exists():
            partial.write_text(json.dumps(record, indent=2) + "\n")
        return fail(f"{args.output} appeared during the run; not overwritten, results kept in {partial}")
    partial.unlink(missing_ok=True)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
