#!/usr/bin/env python3
"""Run the test-runner agent once per fixture on one model and record raw results.

Each fixture's `repo/` is copied to a fresh temp dir; the agent gets the body of
`agents/test-runner.md` as its system prompt, the role's read/run tools (no Edit/Write,
as in the binding), and the fixture's `task.md` as the dispatch message. The runner
records the final report, the Bash commands the agent ran, and whether any repo file
changed (the role must never edit code or tests).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TOOLS = "Bash,Read,Glob,Grep"
IGNORED_PARTS = {"__pycache__", ".pytest_cache"}
# Kept out of the agent's environment so the missing-env fixture fails the same way everywhere.
SCRUBBED_ENV = ("BILLING_API_TOKEN",)


def agent_body(path: Path) -> str:
    """The agent file minus its frontmatter: what a dispatched subagent runs under."""
    text = path.read_text()
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            return text[end + 5:].lstrip()
    return text


def snapshot(root: Path) -> dict[str, str]:
    files = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.is_file() and not IGNORED_PARTS.intersection(rel.parts):
            files[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def integrity(before: dict[str, str], after: dict[str, str]) -> dict:
    changed = sorted(p for p in before.keys() & after.keys() if before[p] != after[p])
    return {"changed": changed, "added": sorted(after.keys() - before.keys()),
            "removed": sorted(before.keys() - after.keys())}


def parse_stream(raw: str) -> tuple[dict, list[str]]:
    """(final result event, Bash commands run) from stream-json output."""
    result, commands = {}, []
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "result":
            result = event
        elif event.get("type") == "assistant":
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Bash":
                    commands.append(str((block.get("input") or {}).get("command", "")))
    return result, commands


def run_case(args, fixture: Path, system_prompt: str, env: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(fixture / "repo", repo)
        before = snapshot(repo)
        cmd = [args.claude, "-p", (fixture / "task.md").read_text(), "--model", args.model,
               "--system-prompt", system_prompt, "--tools", TOOLS, "--allowedTools", TOOLS,
               "--permission-mode", "dontAsk", "--strict-mcp-config", "--setting-sources", "project",
               "--no-session-persistence", "--output-format", "stream-json", "--verbose"]
        start = time.monotonic()
        try:
            proc = subprocess.run(cmd, cwd=repo, env=env, text=True, capture_output=True,
                                  check=False, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            return {"rc": "timeout", "elapsed": round(time.monotonic() - start, 3), "result": "",
                    "commands": [], "usage": {}, "integrity": integrity(before, snapshot(repo))}
        elapsed = round(time.monotonic() - start, 3)
        result, commands = parse_stream(proc.stdout)
        record = {"rc": proc.returncode, "elapsed": elapsed, "result": result.get("result", ""),
                  "commands": commands, "usage": result.get("usage", {}),
                  "cost_usd": result.get("total_cost_usd"), "num_turns": result.get("num_turns"),
                  "integrity": integrity(before, snapshot(repo))}
        if proc.returncode:
            record["stderr"] = proc.stderr[-2000:]
        return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, default=Path("evals/agents/test-runner/fixtures"))
    parser.add_argument("--agent", type=Path, default=Path("agents/test-runner.md"))
    parser.add_argument("--claude", default="claude")
    parser.add_argument("--python", default=sys.executable,
                        help="interpreter with pytest; its directory is put first on the agent's PATH")
    parser.add_argument("--timeout", type=float, default=300.0, help="seconds per case (default 300)")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"test-runner-eval: refusing to overwrite existing result: {args.output}")
    claude = shutil.which(args.claude)
    if not claude:
        raise SystemExit(f"test-runner-eval: cannot run {args.claude}: not found")
    args.claude = os.path.abspath(claude)
    env = {k: v for k, v in os.environ.items() if k not in SCRUBBED_ENV}
    env["PATH"] = os.path.dirname(os.path.abspath(args.python)) + os.pathsep + env.get("PATH", "")
    version = subprocess.run([args.claude, "--version"], text=True, capture_output=True, check=False).stdout.strip()
    system_prompt = agent_body(args.agent)
    record = {"schema_version": 1, "model": args.model, "client": version or "unknown",
              "agent_sha256": hashlib.sha256(args.agent.read_bytes()).hexdigest(), "cases": {}}
    for fixture in sorted(p for p in args.fixtures.iterdir() if (p / "task.md").is_file()):
        case = run_case(args, fixture, system_prompt, env)
        record["cases"][fixture.name] = case
        print(f"{fixture.name}: rc={case['rc']} elapsed={case['elapsed']}s", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
