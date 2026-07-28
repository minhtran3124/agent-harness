#!/usr/bin/env python3
"""Validate and compare versioned skill-prompt evaluation results.

This tool scores recorded observations; it does not call a model.  That separation preserves the
repo's first-run honesty rule and makes policy regressions deterministic in CI.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


VALID_VERDICTS = {"pass", "missed", "false-positive", "blocked", "not-run"}
REQUIRED_KINDS = {"golden", "boundary", "handoff"}


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be an object")
    return data


def corpus_errors(root: Path) -> list[str]:
    manifest_path = root / "evals/skills/prompt-refactor/corpus-manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != 1:
        return ["corpus: schema_version must be 1"]
    registered = set(read_json(root / "harness-manifest.json").get("skills", []))
    entries = manifest.get("skills")
    if not isinstance(entries, list):
        return ["corpus: skills must be a list"]
    by_name = {entry.get("name"): entry for entry in entries if isinstance(entry, dict)}
    errors = [f"corpus: missing skill {name}" for name in sorted(registered - set(by_name))]
    errors += [f"corpus: unknown skill {name}" for name in sorted(set(by_name) - registered)]
    for name in sorted(registered & set(by_name)):
        entry = by_name[name]
        activation_path = root / entry.get("activation", "")
        behavior_path = root / entry.get("behavior", "")
        for label, path in (("activation", activation_path), ("behavior", behavior_path)):
            if not path.is_file():
                errors.append(f"corpus: {name} {label} file missing: {path.relative_to(root)}")
        if not activation_path.is_file() or not behavior_path.is_file():
            continue
        activation = read_json(activation_path).get("cases", [])
        if not isinstance(activation, list):
            errors.append(f"corpus: {name} activation cases must be a list")
            continue
        for index, case in enumerate(activation):
            if not isinstance(case, dict) or case.get("skill") != name or not case.get("id") or not case.get("query"):
                errors.append(f"corpus: {name} activation case {index} is malformed")
        positives = [c for c in activation if c.get("should_trigger") is True]
        negatives = [c for c in activation if c.get("should_trigger") is False]
        for label, cases in (("should-trigger", positives), ("near-miss", negatives)):
            if len(cases) < 8:
                errors.append(f"corpus: {name} needs >=8 {label} activation cases")
            if not any(c.get("split") == "holdout" for c in cases):
                errors.append(f"corpus: {name} {label} cases need a holdout")
        behavior = read_json(behavior_path).get("cases", [])
        if not isinstance(behavior, list):
            errors.append(f"corpus: {name} behavior cases must be a list")
            continue
        for index, case in enumerate(behavior):
            if not isinstance(case, dict) or case.get("skill") != name or not case.get("id") or not case.get("expectation"):
                errors.append(f"corpus: {name} behavior case {index} is malformed")
        kinds = {case.get("kind") for case in behavior}
        missing = REQUIRED_KINDS - kinds
        if missing:
            errors.append(f"corpus: {name} behavior missing kinds: {', '.join(sorted(missing))}")
    e2e_path = root / manifest.get("end_to_end", "")
    if not e2e_path.is_file():
        errors.append("corpus: end-to-end fixture file missing")
    else:
        cases = read_json(e2e_path).get("cases", [])
        required = {"e2e-tiny", "e2e-normal", "e2e-high-risk", "e2e-resume", "e2e-workflow-engine"}
        found = {case.get("id") for case in cases if isinstance(case, dict)}
        missing = required - found
        if missing:
            errors.append(f"corpus: end-to-end cases missing: {', '.join(sorted(missing))}")
    return errors


def result_errors(data: dict, suite: str | None = None) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("result: schema_version must be 1")
    if not data.get("commit_sha"):
        errors.append("result: commit_sha is required")
    env = data.get("environment")
    if not isinstance(env, dict) or not all(env.get(key) for key in ("model", "client_version", "reasoning")):
        errors.append("result: environment needs model, client_version, reasoning")
    records = data.get("records")
    if not isinstance(records, list) or not records:
        return errors + ["result: records must be a non-empty list"]
    for index, record in enumerate(records):
        prefix = f"result[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        if suite and record.get("suite") != suite:
            continue
        if record.get("verdict") not in VALID_VERDICTS:
            errors.append(f"{prefix}: invalid verdict")
        for key in ("case_id", "skill", "suite", "split", "first_run", "observation"):
            if key not in record:
                errors.append(f"{prefix}: missing {key}")
        if "observation" in record and (not isinstance(record["observation"], str) or not record["observation"].strip()):
            errors.append(f"{prefix}: observation must be a non-empty string")
        if record.get("first_run") is not True:
            errors.append(f"{prefix}: first_run must be true")
    return errors


def expected_case_ids(root: Path, suite: str) -> set[str] | None:
    """Return corpus case IDs for suites that have an in-repo canonical corpus."""
    if suite == "review-chain":
        # The review-chain corpus predates this schema and has no record manifest yet.
        return None
    manifest = read_json(root / "evals/skills/prompt-refactor/corpus-manifest.json")
    if suite == "end-to-end":
        cases = read_json(root / manifest["end_to_end"]).get("cases", [])
        return {case["id"] for case in cases if isinstance(case, dict) and case.get("id")}
    case_key = "activation" if suite == "activation" else "behavior"
    ids: set[str] = set()
    for entry in manifest["skills"]:
        cases = read_json(root / entry[case_key]).get("cases", [])
        ids.update(case["id"] for case in cases if isinstance(case, dict) and case.get("id"))
    return ids


def candidate_errors(root: Path, data: dict, suite: str | None) -> list[str]:
    errors = result_errors(data, suite)
    if suite is None:
        return errors
    expected = expected_case_ids(root, suite)
    if expected is None:
        return errors
    records = [record for record in data.get("records", []) if isinstance(record, dict) and record.get("suite") == suite]
    observed = {record.get("case_id") for record in records}
    missing = sorted(expected - observed)
    if missing:
        errors.append(f"candidate: missing {suite} cases: {', '.join(missing)}")
    for record in records:
        if record.get("case_id") in expected and record.get("verdict") != "pass":
            errors.append(
                f"candidate: {suite} case {record.get('case_id')} has non-passing first-run verdict: "
                f"{record.get('verdict')}"
            )
    return errors


def compare(baseline: dict, candidate: dict) -> list[str]:
    errors = result_errors(baseline) + result_errors(candidate)
    for key in ("model", "client_version", "reasoning"):
        if baseline.get("environment", {}).get(key) != candidate.get("environment", {}).get(key):
            errors.append(f"compare: environment mismatch for {key}")
    old = {record.get("case_id"): record for record in baseline.get("records", []) if isinstance(record, dict)}
    new = {record.get("case_id"): record for record in candidate.get("records", []) if isinstance(record, dict)}
    for case_id, before in old.items():
        after = new.get(case_id)
        if after is None:
            errors.append(f"compare: candidate missing case {case_id}")
            continue
        if before.get("verdict") == "pass" and after.get("verdict") != "pass":
            errors.append(f"compare: regression for {case_id}: {before.get('verdict')} -> {after.get('verdict')}")
        if before.get("verdict") != "false-positive" and after.get("verdict") == "false-positive":
            errors.append(f"compare: new false positive for {case_id}")
        if before.get("safety_critical") and after.get("verdict") in {"missed", "not-run"}:
            errors.append(f"compare: safety-critical failure for {case_id}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--validate-corpus", action="store_true")
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("BASELINE", "CANDIDATE"))
    parser.add_argument("--suite", choices=("activation", "behavior", "review-chain", "end-to-end"))
    parser.add_argument("--candidate", action="store_true", help="validate the candidate results file")
    args = parser.parse_args()
    root = args.root.resolve()

    try:
        if args.validate_corpus:
            errors = corpus_errors(root)
        elif args.compare:
            errors = compare(read_json(args.compare[0]), read_json(args.compare[1]))
        elif args.candidate:
            path = root / "evals/skills/prompt-refactor/results/candidate.json"
            errors = candidate_errors(root, read_json(path), args.suite)
        else:
            parser.error("choose --validate-corpus, --compare, or --candidate")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"skill-eval: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"skill-eval: {error}", file=sys.stderr)
        return 1
    print("skill-eval: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
