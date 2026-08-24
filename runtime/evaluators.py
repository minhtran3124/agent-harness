#!/usr/bin/env python3
"""Evaluator Protocol v1 registry + subprocess adapters.

``runtime/evaluators.json`` maps an evaluator id to a wrapped checker: ``script``
(relative to ``INSTALL_ROOT`` -- the harness checkout here, ``<project>/.claude`` when
deployed), ``tier``, ``argv_prefix``, ``argv_suffix``, ``description``, ``requires_args``
(true: an empty ``args`` list is reported as ``skipped`` without spawning).  ``run``
spawns ``python3 <INSTALL_ROOT/script> <argv_prefix> <args> <argv_suffix>`` with
``cwd=repo_root`` (the project root, where relative targets resolve) and a closed stdin,
and shapes the outcome as a ``runtime/evaluator_result.py`` result.

Exit codes.  The JSON ``exit`` (and the process exit) equals the wrapped exit code when
the checker delivered a verdict: 0 -> pass, 1 -> fail, 2 -> error, any other
non-reserved checker exit -> error.  Adapter-classified outcomes use reserved codes
instead:

    3    skipped  (``requires_args`` and no args; nothing spawned)
    124  error    (killed after ``timeout_s``)
    125  error    (crashed: raw exit 1 with a Python traceback on stderr is not a verdict)
    127  error    (spawn failure)

``score`` is always null; every non-empty stderr line, then stdout line, becomes an
``evidence`` item.  Adapter-classified outcomes always carry a ``source: adapter``
evidence item appended last; a wrapped checker exit that collides with a reserved code
is not a verdict and is reported as exit 2 / ``error`` with an ``adapter`` item saying
so.  The
adapter itself never writes to disk; a wrapped checker may (``verify-summary-check``
re-executes the SUMMARY's Verify commands).

CLI:
    list [--check]          print ids; with --check exit 1 unless exactly 4 entries
                            each name an existing script under INSTALL_ROOT
    run [--repo-root DIR] [--timeout SECONDS] <id> -- <args...>
                            print the JSON result; exit with the result's ``exit``
                            (unknown id -> exit 2; DIR is the project root, defaulting
                            to ``default_repo_root()``; SECONDS must be > 0 and finite)
    A missing or malformed registry, or a bad --timeout, exits 2 with one stderr line.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

from evaluator_result import validate

REGISTRY_PATH = Path(__file__).with_name("evaluators.json")
# Where the registry's ``script`` paths resolve: the directory holding this ``runtime/``
# and the harness ``scripts/`` -- the checkout here, ``<project>/.claude`` when deployed.
INSTALL_ROOT = Path(__file__).resolve().parents[1]


def default_repo_root() -> Path:
    """The project root: ``cwd`` for wrapped checkers, where relative targets resolve.

    In the harness repo it is ``INSTALL_ROOT``; a deployed copy lives at
    ``<project>/.claude/runtime/`` so the project root is one level further out
    (mirrors ``scripts/verify_summary.py``).
    """
    return INSTALL_ROOT.parent if INSTALL_ROOT.name == ".claude" else INSTALL_ROOT


DEFAULT_REPO_ROOT = default_repo_root()
PYTHON = "python3"
EXPECTED_COUNT = 4
STATUS_BY_EXIT = {0: "pass", 1: "fail", 2: "error"}
# Reserved adapter exit codes (see the module docstring); never a wrapped verdict.
SKIPPED_EXIT = 3
TIMEOUT_EXIT = 124
CRASH_EXIT = 125
SPAWN_FAILURE_EXIT = 127
RESERVED_EXITS = frozenset({SKIPPED_EXIT, TIMEOUT_EXIT, CRASH_EXIT, SPAWN_FAILURE_EXIT})
DEFAULT_TIMEOUT_S = 300
TRACEBACK_MARKER = "Traceback (most recent call last)"
REGISTRY_ERRORS = (OSError, ValueError, KeyError, TypeError)


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _valid_timeout(timeout_s) -> bool:
    return timeout_s > 0 and not math.isinf(timeout_s)  # nan > 0 is False


def _validate_entry(evaluator_id: str, entry: dict) -> None:
    """Raise KeyError/TypeError (both REGISTRY_ERRORS) for a malformed entry."""
    for key in ("script", "argv_prefix", "argv_suffix"):
        if key not in entry:
            raise KeyError(key)
    if not isinstance(entry["script"], str):
        raise TypeError(f"entry {evaluator_id!r}: script must be a string")
    for key in ("argv_prefix", "argv_suffix"):
        if not isinstance(entry[key], list) or not all(
            isinstance(item, str) for item in entry[key]
        ):
            raise TypeError(f"entry {evaluator_id!r}: {key} must be a list of strings")
    if not isinstance(entry.get("requires_args", False), bool):
        raise TypeError(f"entry {evaluator_id!r}: requires_args must be a boolean")


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
    if not _valid_timeout(timeout_s):
        raise ValueError(f"timeout_s must be > 0 and finite, got {timeout_s!r}")
    entry = load_registry()[evaluator_id]
    repo_root = Path(repo_root).resolve()  # a relative root must not also prefix argv
    argv = [
        PYTHON,
        str(INSTALL_ROOT / entry["script"]),
        *entry["argv_prefix"],
        *args,
        *entry["argv_suffix"],
    ]
    if entry.get("requires_args") and not args:
        evidence = [
            {"source": "adapter", "message": "no targets given; nothing evaluated"}
        ]
        return _result(evaluator_id, "skipped", SKIPPED_EXIT, evidence, argv, 0)

    start = time.monotonic()
    adapter_message = None
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
        exit_code, stdout, stderr = TIMEOUT_EXIT, "", ""
        adapter_message = f"timed out after {timeout_s}s"
    except OSError as exc:
        exit_code, stdout, stderr = SPAWN_FAILURE_EXIT, "", ""
        adapter_message = f"spawn failed: {exc}"
    duration_ms = int((time.monotonic() - start) * 1000)

    evidence = [
        {"source": source, "message": line}
        for source, text in (("stderr", stderr), ("stdout", stdout))
        for line in text.splitlines()
        if line.strip()
    ]
    if exit_code == 1 and TRACEBACK_MARKER in stderr:
        exit_code = CRASH_EXIT  # a crashed checker is not a verdict
        adapter_message = "wrapped checker crashed (raw exit 1)"
    elif adapter_message is None and exit_code in RESERVED_EXITS:
        # A wrapped exit colliding with a reserved code is ambiguous, not a verdict.
        adapter_message = (
            f"wrapped checker exited with reserved code {exit_code}; reported as error"
        )
        exit_code = 2
    if adapter_message is not None:
        evidence.append({"source": "adapter", "message": adapter_message})
    status = STATUS_BY_EXIT.get(exit_code, "error")
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
    run_parser = sub.add_parser("run", help="run <id> -- <args...>")
    run_parser.add_argument("--repo-root", default=DEFAULT_REPO_ROOT, metavar="DIR")
    run_parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT_S, metavar="SECONDS"
    )
    run_parser.add_argument("evaluator_id")
    args = parser.parse_args(argv)  # argparse exits 2 on CLI misuse
    if args.command == "run" and not _valid_timeout(args.timeout):
        print(
            f"evaluators: --timeout must be > 0 and finite, got {args.timeout!r}",
            file=sys.stderr,
        )
        return 2

    # Only registry loading and entry lookup are guarded: a failure inside run() or
    # while printing the result is not a registry error and must not be reported as one.
    try:
        registry = load_registry()
        if args.command == "list":
            return _list(registry, args.check)
        if args.evaluator_id not in registry:
            print(
                f"evaluators: unknown evaluator id {args.evaluator_id!r}",
                file=sys.stderr,
            )
            return 2
        _validate_entry(args.evaluator_id, registry[args.evaluator_id])
    except REGISTRY_ERRORS as exc:
        print(
            f"evaluators: cannot use registry {REGISTRY_PATH}: {exc!r}", file=sys.stderr
        )
        return 2

    result = run(
        args.evaluator_id,
        passthrough,
        repo_root=Path(args.repo_root),
        timeout_s=args.timeout,
    )
    print(json.dumps(result))
    return result["exit"]


def _list(registry: dict, check: bool) -> int:
    for evaluator_id in registry:
        print(evaluator_id)
    if not check:
        return 0
    problems = []
    for evaluator_id, entry in registry.items():
        _validate_entry(evaluator_id, entry)  # KeyError/TypeError -> registry exit 2
        if not (INSTALL_ROOT / entry["script"]).is_file():
            problems.append(f"{evaluator_id}: {entry['script']} not found")
    if len(registry) != EXPECTED_COUNT:
        problems.append(f"expected {EXPECTED_COUNT} entries, found {len(registry)}")
    for message in problems:
        print(f"evaluators: {message}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
