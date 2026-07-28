#!/usr/bin/env python3
"""Run a corpus suite through the raw-response capture helper, case by case.

Each invocation has stdin closed and its own transcript path. A failed case is logged and does
not prevent later cases from running; this makes a batch a transport convenience, not a grading
step. A human or a separate scorer must still assign verdicts.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def cases(root: Path, suite: str) -> list[dict[str, str]]:
    manifest = json.loads((root / "evals/skills/prompt-refactor/corpus-manifest.json").read_text())
    if suite not in {"activation", "behavior"}:
        raise ValueError("batch runner currently supports activation and behavior")
    found: list[dict[str, str]] = []
    for entry in manifest["skills"]:
        path = root / entry[suite]
        for case in json.loads(path.read_text()).get("cases", []):
            prompt = case.get("prompt") or case.get("query") or case.get("expectation")
            found.append({"id": case["id"], "skill": case["skill"], "prompt": prompt})
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--suite", choices=("activation", "behavior"), required=True)
    parser.add_argument("--cwd", type=Path, required=True)
    parser.add_argument("--transcripts", type=Path, required=True)
    parser.add_argument("--summaries", type=Path, required=True)
    parser.add_argument("--config-dir", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    capture = root / "scripts/capture_skill_eval.py"
    failures: list[str] = []
    args.transcripts.mkdir(parents=True, exist_ok=True)
    args.summaries.mkdir(parents=True, exist_ok=True)
    try:
        suite_cases = cases(root, args.suite)
        for case in suite_cases:
            prompt = f"/{case['skill']}\n\n{case['prompt']}\n\nState the concrete required workflow action and key safety gate. Do not make changes. Answer in at most 120 words."
            result = subprocess.run(
                [
                    sys.executable,
                    str(capture),
                    "--cwd",
                    str(args.cwd),
                    "--output",
                    str(args.transcripts / f"{case['id']}.json"),
                    "--prompt",
                    prompt,
                ],
                cwd=root,
                stdin=subprocess.DEVNULL,
                text=True,
                capture_output=True,
                env={**__import__("os").environ, "CLAUDE_CONFIG_DIR": args.config_dir},
            )
            (args.summaries / f"{case['id']}.json").write_text(result.stdout + result.stderr, encoding="utf-8")
            if result.returncode:
                failures.append(case["id"])
        report = {"suite": args.suite, "total": len(suite_cases), "captured": len(suite_cases) - len(failures), "failures": failures}
        (args.summaries / "batch-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report))
        return 1 if failures else 0
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"skill-eval-batch: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
