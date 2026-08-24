#!/usr/bin/env python3
"""Evaluator Protocol v1 result schema + validator.

A result is the outcome of one evaluator invocation, shaped by
``runtime/evaluator-result.schema.json`` (draft-07 keywords, informational only: this
module is the validator; no JSON-Schema library is used).  Field naming is seeded from
``templates/REVIEW-RECEIPT.template.json``: its ``result`` (``pass|fail``) is ``status``
here, widened to ``pass|fail|error|skipped``.

Required keys: evaluator (str), status (enum), score (number or null), evidence (list of
``{"source": str, "message": str}``), exit (int).  Optional: argv (list of str),
duration_ms (int).  Unknown keys are ignored.

CLI exit codes: 0 valid, 1 invalid (one message per violation on stdout), 2 bad
invocation (no flag, unreadable path, or a file that is not JSON).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("evaluator-result.schema.json")

REQUIRED_KEYS = ("evaluator", "status", "score", "evidence", "exit")
STATUSES = ("pass", "fail", "error", "skipped")


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_number_or_null(v) -> bool:
    return v is None or (isinstance(v, (int, float)) and not isinstance(v, bool))


def _is_str_list(v) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def _check_evidence(items) -> list[str]:
    if not isinstance(items, list):
        return ["evidence: expected an array"]
    errors = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"evidence[{i}]: expected an object")
            continue
        for key in ("source", "message"):
            if key not in item:
                errors.append(f"evidence[{i}]: missing required key: {key}")
            elif not isinstance(item[key], str):
                errors.append(f"evidence[{i}].{key}: expected a string")
    return errors


def validate(obj) -> list[str]:
    """Return one message per violation; an empty list means ``obj`` is a valid result."""
    if not isinstance(obj, dict):
        return ["result: expected a JSON object"]
    errors = [f"missing required key: {k}" for k in REQUIRED_KEYS if k not in obj]
    if "evaluator" in obj and not isinstance(obj["evaluator"], str):
        errors.append("evaluator: expected a string")
    if "status" in obj and obj["status"] not in STATUSES:
        status, allowed = obj["status"], "|".join(STATUSES)
        errors.append(f"status: {status!r} is not one of {allowed}")
    if "score" in obj and not _is_number_or_null(obj["score"]):
        errors.append("score: expected a number or null")
    if "evidence" in obj:
        errors.extend(_check_evidence(obj["evidence"]))
    if "exit" in obj and not _is_int(obj["exit"]):
        errors.append("exit: expected an integer")
    if "argv" in obj and not _is_str_list(obj["argv"]):
        errors.append("argv: expected an array of strings")
    if "duration_ms" in obj and not _is_int(obj["duration_ms"]):
        errors.append("duration_ms: expected an integer")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate an evaluator result JSON.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--self-check",
        action="store_true",
        help="load the schema file and print its required key names",
    )
    group.add_argument("--validate", metavar="PATH", help="validate a JSON result file")
    args = parser.parse_args(argv)  # argparse exits 2 on CLI misuse

    if args.self_check:
        try:
            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            required = list(schema["required"])  # non-iterable -> TypeError -> exit 2
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(
                f"evaluator_result: cannot load {SCHEMA_PATH}: {exc}", file=sys.stderr
            )
            return 2
        if required != list(REQUIRED_KEYS):
            print(
                f"evaluator_result: schema required {required} != REQUIRED_KEYS",
                file=sys.stderr,
            )
            return 1
        print("\n".join(required))
        return 0

    try:
        obj = json.loads(Path(args.validate).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"evaluator_result: cannot read {args.validate}: {exc}", file=sys.stderr)
        return 2
    errors = validate(obj)
    for message in errors:
        print(message)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
