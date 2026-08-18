#!/usr/bin/env python3
"""Report whether the prompt-refactor live-evaluation artifacts are ready for comparison."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def expected_ids(root: Path, suite: str) -> set[str]:
    manifest = json.loads((root / "evals/skills/prompt-refactor/corpus-manifest.json").read_text())
    if suite == "end-to-end":
        path = root / manifest["end_to_end"]
        cases = json.loads(path.read_text()).get("cases", [])
        return {case["id"] for case in cases if isinstance(case, dict) and case.get("id")}
    ids: set[str] = set()
    for entry in manifest["skills"]:
        cases = json.loads((root / entry[suite]).read_text()).get("cases", [])
        ids.update(case["id"] for case in cases if isinstance(case, dict) and case.get("id"))
    return ids


def observed_ids(path: Path, suite: str) -> set[str]:
    if not path.is_file():
        return set()
    data = json.loads(path.read_text())
    return {
        record["case_id"]
        for record in data.get("records", [])
        if isinstance(record, dict) and record.get("suite") == suite and record.get("case_id")
    }


def auth_state(claude: str, config_dir: str) -> tuple[bool, str]:
    result = subprocess.run(
        [claude, "auth", "status"],
        text=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "CLAUDE_CONFIG_DIR": config_dir},
        check=False,
    )
    if result.returncode:
        return False, result.stderr.strip() or f"auth status exited {result.returncode}"
    try:
        status = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, "auth status was not valid JSON"
    return bool(status.get("loggedIn")), "logged in" if status.get("loggedIn") else "not logged in"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--baseline", type=Path, default=Path("evals/skills/prompt-refactor/results/baseline.json"))
    parser.add_argument("--candidate", type=Path, default=Path("evals/skills/prompt-refactor/results/candidate.json"))
    parser.add_argument("--config-dir", default=os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude"))
    parser.add_argument("--claude", default="claude")
    parser.add_argument("--skip-auth-check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    baseline = (root / args.baseline).resolve() if not args.baseline.is_absolute() else args.baseline
    candidate = (root / args.candidate).resolve() if not args.candidate.is_absolute() else args.candidate
    report: dict[str, object] = {"ready": True, "auth": {"logged_in": True, "message": "skipped"}}
    if not args.skip_auth_check:
        logged_in, message = auth_state(args.claude, args.config_dir)
        report["auth"] = {"logged_in": logged_in, "message": message}
        report["ready"] = logged_in
    suites: dict[str, object] = {}
    for suite in ("activation", "behavior", "end-to-end"):
        expected = expected_ids(root, suite)
        base_missing = sorted(expected - observed_ids(baseline, suite))
        cand_missing = sorted(expected - observed_ids(candidate, suite))
        suites[suite] = {
            "expected": len(expected),
            "baseline_observed": len(expected) - len(base_missing),
            "candidate_observed": len(expected) - len(cand_missing),
            "baseline_missing": base_missing,
            "candidate_missing": cand_missing,
        }
        if base_missing or cand_missing:
            report["ready"] = False
    report["suites"] = suites
    print(json.dumps(report, indent=2))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
