#!/usr/bin/env python3
"""Evaluator Protocol v1 registry + subprocess adapters.

``runtime/evaluators.json`` maps an evaluator id to a wrapped checker: ``script``
(repo-relative), ``tier``, ``argv_prefix``, ``argv_suffix``, ``description``,
``requires_args`` (true: an empty ``args`` list is reported as ``skipped`` without
spawning).  ``run`` spawns ``python3 <script> <argv_prefix> <args> <argv_suffix>`` with
``cwd=repo_root`` and a closed stdin, and shapes the outcome as a
``runtime/evaluator_result.py`` result: exit 0 -> pass, 1 -> fail, 2 -> error, anything
else (or a spawn failure, reported as exit 127) -> error.  Two refinements: an exit 1
whose stderr carries a Python traceback is a crashed checker, not a verdict, so it is
``error``; a checker that outlives ``timeout_s`` is killed and reported as ``error`` with
exit 124.  ``score`` is always null; every non-empty stderr line, then stdout line,
becomes an ``evidence`` item.  The adapter itself never writes to disk; a wrapped checker
may (``verify-summary-check`` re-executes the SUMMARY's Verify commands).

CLI:
    list [--check] [--repo-root DIR]
                            print ids; with --check exit 1 unless exactly 4 entries
                            each name an existing script under DIR
    run [--repo-root DIR] [--timeout SECONDS] <id> -- <args...>
                            print the JSON result; exit with the wrapped exit code
                            (unknown id -> exit 2; DIR defaults to the repo root)
    A missing or malformed registry exits 2 with one line on stderr.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from evaluator_result import validate

REGISTRY_PATH = Path(__file__).with_name("evaluators.json")


def default_repo_root() -> Path:
    """The repo root the registry's ``script`` paths are relative to.

    A deployed copy lives at ``<repo>/.claude/runtime/``; the repo root is one level
    further out (mirrors ``scripts/verify_summary.py``). In the harness repo
    ``parents[1]`` is already the root.
    """
    self_root = Path(__file__).resolve().parents[1]
    return self_root.parent if self_root.name == ".claude" else self_root


DEFAULT_REPO_ROOT = default_repo_root()
PYTHON = "python3"
EXPECTED_COUNT = 4
STATUS_BY_EXIT = {0: "pass", 1: "fail", 2: "error"}
SPAWN_FAILURE_EXIT = 127
TIMEOUT_EXIT = 124
DEFAULT_TIMEOUT_S = 300
TRACEBACK_MARKER = "Traceback (most recent call last)"
REGISTRY_ERRORS = (OSError, ValueError, KeyError, TypeError)


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _result(evaluator_id, status, exit_code, evidence, argv, duration_ms) -> dict:
    result = {
        "evaluator": evaluator_id,
        "status": status,
        "score": None,
        "evidence": evidence,
        "exit": exit_code,
        "argv": argv,
        "duration_ms": duration_ms,
    }
    errors = validate(result)
    assert errors == [], errors
    return result


def run(
    evaluator_id: str,
    args: list[str],
    *,
    repo_root=DEFAULT_REPO_ROOT,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> dict:
    """Run one registered evaluator; raises KeyError for an unknown id."""
    entry = load_registry()[evaluator_id]
    repo_root = Path(repo_root).resolve()  # a relative root must not also prefix argv
    argv = [
        PYTHON,
        str(repo_root / entry["script"]),
        *entry["argv_prefix"],
        *args,
        *entry["argv_suffix"],
    ]
    if entry.get("requires_args") and not args:
        evidence = [
            {"source": "adapter", "message": "no targets given; nothing evaluated"}
        ]
        return _result(evaluator_id, "skipped", 0, evidence, argv, 0)

    start = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            cwd=repo_root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        exit_code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        exit_code, stdout, stderr = TIMEOUT_EXIT, "", f"timed out after {timeout_s}s"
    except OSError as exc:
        exit_code, stdout, stderr = SPAWN_FAILURE_EXIT, "", f"spawn failed: {exc}"
    duration_ms = int((time.monotonic() - start) * 1000)

    evidence = [
        {"source": source, "message": line}
        for source, text in (("stderr", stderr), ("stdout", stdout))
        for line in text.splitlines()
        if line.strip()
    ]
    status = STATUS_BY_EXIT.get(exit_code, "error")
    if exit_code == 1 and TRACEBACK_MARKER in stderr:
        status = "error"  # a crashed checker is not a verdict
    return _result(evaluator_id, status, exit_code, evidence, argv, duration_ms)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    passthrough: list[str] = []
    if "--" in argv:
        split = argv.index("--")
        argv, passthrough = argv[:split], argv[split + 1 :]

    parser = argparse.ArgumentParser(description="Run a registered evaluator.")
    sub = parser.add_subparsers(dest="command", required=True)
    list_parser = sub.add_parser("list", help="print evaluator ids")
    list_parser.add_argument("--check", action="store_true")
    list_parser.add_argument("--repo-root", default=DEFAULT_REPO_ROOT, metavar="DIR")
    run_parser = sub.add_parser("run", help="run <id> -- <args...>")
    run_parser.add_argument("--repo-root", default=DEFAULT_REPO_ROOT, metavar="DIR")
    run_parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT_S, metavar="SECONDS"
    )
    run_parser.add_argument("evaluator_id")
    args = parser.parse_args(argv)  # argparse exits 2 on CLI misuse

    try:
        return _dispatch(args, passthrough)
    except REGISTRY_ERRORS as exc:
        print(
            f"evaluators: cannot use registry {REGISTRY_PATH}: {exc!r}", file=sys.stderr
        )
        return 2


def _dispatch(args, passthrough: list[str]) -> int:
    registry = load_registry()
    repo_root = Path(args.repo_root)
    if args.command == "list":
        for evaluator_id in registry:
            print(evaluator_id)
        if not args.check:
            return 0
        problems = [
            f"{k}: {v['script']} not found"
            for k, v in registry.items()
            if not (repo_root / v["script"]).is_file()
        ]
        if len(registry) != EXPECTED_COUNT:
            problems.append(f"expected {EXPECTED_COUNT} entries, found {len(registry)}")
        for message in problems:
            print(f"evaluators: {message}", file=sys.stderr)
        return 1 if problems else 0

    if args.evaluator_id not in registry:
        print(
            f"evaluators: unknown evaluator id {args.evaluator_id!r}", file=sys.stderr
        )
        return 2
    result = run(
        args.evaluator_id, passthrough, repo_root=repo_root, timeout_s=args.timeout
    )
    print(json.dumps(result))
    return result["exit"]


if __name__ == "__main__":
    sys.exit(main())
