#!/usr/bin/env python3
"""Deterministically score test-runner eval results against each fixture's truth.json.

A case passes when the report's verdict, failing-test set, failure count and required
mentions all match the answer key, no passing test is reported as failed, the agent ran
pytest itself, and no repo file changed. Diagnosis mentions are scored separately: they
measure explanation quality, not correctness of the report.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

# Anything that is not a letter may sit between the heading and the verdict (bold, emoji, spaces).
VERDICT = re.compile(r"Test Results:[^A-Za-z]*(PASSED|FAILED)", re.IGNORECASE)
COUNT = re.compile(r"^\W*(Failed|Errors)\W*:?\s*\**\s*(\d+)", re.IGNORECASE | re.MULTILINE)
FAILURES = re.compile(r"^#+\s*Failures\b(.*?)(?=^#+\s*Summary\b|\Z)", re.IGNORECASE | re.MULTILINE | re.DOTALL)
PYTEST = re.compile(r"\bpytest\b")
# A line in the Failures section that says the test passed is not a claim that it failed.
PASS_MARK = re.compile(r"\u2705|\bpass(?:ed|es|ing)?\b", re.IGNORECASE)


def load_truths(fixtures: Path) -> dict[str, dict]:
    return {p.parent.name: json.loads(p.read_text()) for p in sorted(fixtures.glob("*/truth.json"))}


def failures_region(text: str) -> str | None:
    match = FAILURES.search(text)
    return match.group(1) if match else None


def mentioned(text: str, group: list[str]) -> bool:
    return any(term.lower() in text.lower() for term in group)


def failed_plus_errors(text: str) -> int:
    """Sum of the report's `Failed:` and `Errors:` lines (first of each; absent counts 0)."""
    seen: dict[str, int] = {}
    for label, number in COUNT.findall(text):
        seen.setdefault(label.lower(), int(number))
    return sum(seen.values())


def score_case(entry: dict, truth: dict) -> dict:
    text = entry.get("result") or ""
    verdict = VERDICT.search(text)
    region = failures_region(text)
    failing_text = region if region is not None else text
    found = [name for name in truth["failing"] if name in failing_text]
    claim_lines = [line for line in (region or "").splitlines() if not PASS_MARK.search(line)]
    false_failures = [name for name in truth["passing"]
                      if any(re.search(rf"\b{re.escape(name)}\b", line) for line in claim_lines)]
    touched = entry.get("integrity") or {}
    edits = sum(len(touched.get(k, [])) for k in ("changed", "added", "removed"))
    checks = {
        "verdict": bool(verdict) and verdict.group(1).upper() == truth["verdict"],
        "recall": len(found) == len(truth["failing"]),
        "no_false_failures": not false_failures,
        "count": failed_plus_errors(text) in truth["failed_plus_errors"],
        "required": all(mentioned(text, g) for g in truth["required"]),
        "ran_pytest": any(PYTEST.search(c) for c in entry.get("commands") or []),
        "no_edits": edits == 0,
    }
    return {"pass": all(checks.values()), "checks": checks, "found": found, "false_failures": false_failures,
            "diagnosis": all(mentioned(text, g) for g in truth["diagnosis"]) if truth["diagnosis"] else None,
            "edits": edits}


def score(results: dict, truths: dict[str, dict]) -> dict:
    cases = results.get("cases") or {}
    scored, errored = {}, []
    for name, truth in truths.items():
        entry = cases.get(name)
        if not isinstance(entry, dict) or entry.get("rc") != 0:
            errored.append(name)
            continue
        scored[name] = score_case(entry, truth)
    diagnosed = [c["diagnosis"] for c in scored.values() if c["diagnosis"] is not None]
    usage = [c.get("usage") or {} for c in cases.values() if isinstance(c, dict)]
    return {
        "model": results.get("model"),
        "cases": scored,
        "errored": errored,
        "passed": sum(c["pass"] for c in scored.values()),
        "total": len(truths),
        "check_failures": {k: sum(not c["checks"][k] for c in scored.values())
                           for k in next(iter(scored.values()))["checks"]} if scored else {},
        "diagnosis": f"{sum(diagnosed)}/{len(diagnosed)}",
        "median_elapsed": statistics.median([c["elapsed"] for c in cases.values() if isinstance(c, dict)]) if cases else None,
        "output_tokens": sum(u.get("output_tokens", 0) or 0 for u in usage),
        "cost_usd": round(sum(c.get("cost_usd") or 0 for c in cases.values() if isinstance(c, dict)), 5),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path, nargs="+")
    parser.add_argument("--fixtures", type=Path, default=Path("evals/agents/test-runner/fixtures"))
    args = parser.parse_args()
    truths = load_truths(args.fixtures)
    if not truths:
        print(f"test-runner-eval: no truth.json under {args.fixtures}", file=sys.stderr)
        return 1
    for path in args.results:
        summary = score(json.loads(path.read_text()), truths)
        print(f"== {path.name} ({summary['model']})")
        for name, case in summary["cases"].items():
            failed = [k for k, ok in case["checks"].items() if not ok]
            print(f"  {name}: {'PASS' if case['pass'] else 'FAIL ' + ','.join(failed)} diagnosis={case['diagnosis']}")
        for name in summary["errored"]:
            print(f"  {name}: ERROR (no result)")
        print(f"  cases passed: {summary['passed']}/{summary['total']}  check failures: {summary['check_failures']}")
        print(f"  diagnosis: {summary['diagnosis']}  median elapsed: {summary['median_elapsed']}s  "
              f"output tokens: {summary['output_tokens']}  cost: ${summary['cost_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
