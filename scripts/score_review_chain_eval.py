#!/usr/bin/env python3
"""Deterministically score review-chain eval results against each fixture's truth.json."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ORACLES = ("correctness", "intent", "context-propagation-audit")
JSON_BLOCK = re.compile(r"```json[ \t]*\n(.*?)```", re.DOTALL)


def _check_pattern(pattern, where: str, need_terms: bool) -> list[str]:
    if not isinstance(pattern, dict):
        return [f"{where} must be an object"]
    errors = []
    if not isinstance(pattern.get("file"), str):
        errors.append(f"{where}.file must be a string")
    for key in ("match_any", "and_any"):
        terms = pattern.get(key)
        if not isinstance(terms, list) or not all(isinstance(t, str) and t for t in terms):
            errors.append(f"{where}.{key} must be a list of non-empty strings")
    if need_terms and not pattern.get("match_any"):
        errors.append(f"{where}.match_any must not be empty")
    return errors


def validate_truth(truth) -> list[str]:
    if not isinstance(truth, dict):
        return ["not an object"]
    errors = []
    if truth.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if truth.get("expected_oracle") not in ORACLES:
        errors.append(f"expected_oracle must be one of {', '.join(ORACLES)}")
    for key in ("core", "correctness_clean"):
        if not isinstance(truth.get(key), bool):
            errors.append(f"{key} must be a boolean")
    errors += _check_pattern(truth.get("planted"), "planted", need_terms=True)
    fps = truth.get("false_positives")
    if not isinstance(fps, list):
        errors.append("false_positives must be a list")
    else:
        for i, fp in enumerate(fps):
            errors += _check_pattern(fp, f"false_positives[{i}]", need_terms=False)
    return errors


def check_truth(fixtures: Path) -> list[str]:
    errors = []
    for fixture in sorted(p for p in fixtures.iterdir() if p.is_dir()):
        path = fixture / "truth.json"
        try:
            problems = validate_truth(json.loads(path.read_text()))
        except (OSError, ValueError) as exc:
            problems = [str(exc)]
        errors += [f"{fixture.name}/truth.json: {p}" for p in problems]
    return errors


def normalise_file(name: str) -> str:
    name = re.sub(r":\d+$", "", name.strip())
    return re.sub(r"^(a/|b/|\./)", "", name)


def matches(finding: dict, pattern: dict) -> bool:
    file = normalise_file(str(finding.get("file") or ""))
    want = pattern["file"]
    if want and file != want and not file.endswith("/" + want):
        return False
    text = (str(finding.get("class", "")) + " " + str(finding.get("summary", ""))).lower()
    if not any(t.lower() in text for t in pattern["match_any"]):
        return False
    return not pattern["and_any"] or any(t.lower() in text for t in pattern["and_any"])


def classify(finding: dict, truth: dict) -> str:
    if str(finding.get("class", "")).lower() == "unknown":
        return "other"
    if matches(finding, truth["planted"]):
        return "planted"
    if any(matches(finding, fp) for fp in truth["false_positives"]):
        return "false_positive"
    if truth["correctness_clean"] and finding.get("oracle") == "correctness":
        return "false_positive"
    return "other"


def parse_findings(text: str) -> tuple[list[dict], int]:
    blocks = JSON_BLOCK.findall(text or "")
    if not blocks:
        return [], 0
    try:
        data = json.loads(blocks[-1])
    except ValueError:
        return [], len(blocks)
    if not isinstance(data, list):
        return [], len(blocks)
    return [f for f in data if isinstance(f, dict)], len(blocks)


def _confidence(finding: dict) -> int:
    value = finding.get("confidence")
    return value if isinstance(value, int) else 0


def score_case(text: str, truth: dict) -> dict:
    findings, blocks = parse_findings(text)
    classes = [classify(f, truth) for f in findings]
    planted = [f for f, c in zip(findings, classes) if c == "planted"]
    return {
        "blocks": blocks,
        "findings": findings,
        "classes": classes,
        "caught": bool(planted),
        "confidence": max((_confidence(f) for f in planted), default=None),
        "oracle_match": any(f.get("oracle") == truth["expected_oracle"] for f in planted),
    }


def score(results: dict, fixtures: Path, threshold: int) -> tuple[dict, list[str]]:
    totals = dict.fromkeys(("core", "core_caught", "core_oracle_match", "bonus_caught", "all_caught", "fp", "fp_at_threshold", "other"), 0)
    lines = []
    for name in sorted(results["cases"]):
        truth = json.loads((fixtures / name / "truth.json").read_text())
        case = score_case(results["cases"][name].get("result", ""), truth)
        totals["core"] += truth["core"]
        if case["caught"]:
            totals["all_caught"] += 1
            if truth["core"]:
                totals["core_caught"] += 1
                totals["core_oracle_match"] += case["oracle_match"]
            else:
                totals["bonus_caught"] += 1
        for f, c in zip(case["findings"], case["classes"]):
            if c == "false_positive":
                totals["fp"] += 1
                totals["fp_at_threshold"] += _confidence(f) >= threshold
            elif c == "other":
                totals["other"] += 1
        verdict = "CAUGHT" if case["caught"] else "MISSED"
        per = ", ".join(f"{f.get('oracle')}/{f.get('class')}@{_confidence(f)}={c}" for f, c in zip(case["findings"], case["classes"]))
        lines.append(f"{name} [{'core' if truth['core'] else 'bonus'}]: {verdict} confidence={case['confidence']} "
                     f"oracle_match={case['oracle_match']} blocks={case['blocks']} findings=[{per}]")
    return totals, lines


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-truth", type=Path, metavar="FIXTURES_DIR")
    mode.add_argument("--score", type=Path, metavar="RESULTS_JSON")
    parser.add_argument("--fixtures", type=Path, default=Path("evals/skills/review-chain/fixtures"))
    parser.add_argument("--threshold", type=int, default=75)
    args = parser.parse_args()
    if args.check_truth:
        errors = check_truth(args.check_truth)
        for error in errors:
            print(f"review-chain-eval: {error}", file=sys.stderr)
        if errors:
            return 1
        print("review-chain-eval: truth.json OK")
        return 0
    totals, lines = score(json.loads(args.score.read_text()), args.fixtures, args.threshold)
    for line in lines:
        print(line)
    print(f"core catches: {totals['core_caught']}/{totals['core']} "
          f"(oracle match {totals['core_oracle_match']}/{totals['core']})")
    print(f"bonus catches (non-core, incl. context-propagation-audit): {totals['bonus_caught']}")
    print(f"all catches: {totals['all_caught']}/{len(lines)}")
    print(f"false positives: {totals['fp']} (at or above {args.threshold}: {totals['fp_at_threshold']})")
    print(f"other findings: {totals['other']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
