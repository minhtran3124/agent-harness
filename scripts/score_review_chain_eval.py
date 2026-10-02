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


class EvalError(Exception):
    """A one-line, user-facing input problem; main() prints it and exits 1."""


def _fixture_dirs(fixtures: Path) -> list[Path]:
    if not fixtures.is_dir():
        raise EvalError(f"fixtures directory not found: {fixtures}")
    return sorted(p for p in fixtures.iterdir() if p.is_dir())


def _truth_problems(path: Path) -> tuple[dict | None, list[str]]:
    try:
        truth = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        return None, [str(exc)]
    problems = validate_truth(truth)
    return (None if problems else truth), problems


def load_truth(fixture: Path) -> dict:
    truth, problems = _truth_problems(fixture / "truth.json")
    if problems:
        raise EvalError(f"{fixture.name}/truth.json: {problems[0]}")
    return truth


def check_truth(fixtures: Path) -> list[str]:
    errors = []
    for fixture in _fixture_dirs(fixtures):
        _, problems = _truth_problems(fixture / "truth.json")
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


def case_error(entry) -> str | None:
    """Why a run's record cannot be scored (non-zero rc, or no output), else None."""
    if not isinstance(entry, dict):
        return "no output"
    rc = entry.get("rc")
    if rc is not None and rc != 0:
        return f"rc={rc}"
    text = entry.get("result")
    if not isinstance(text, str) or not text.strip():
        return "no output"
    return None


def score(results: dict, fixtures: Path, threshold: int) -> tuple[dict, list[str]]:
    totals = dict.fromkeys(("core", "core_caught", "core_oracle_match", "bonus_caught", "all_caught", "fp", "fp_at_threshold",
                            "other", "errored", "core_errored"), 0)
    lines = []
    cases = results.get("cases") if isinstance(results, dict) else None
    if not isinstance(cases, dict):
        raise EvalError("results file has no \"cases\" object")
    for fixture in (p for p in _fixture_dirs(fixtures) if (p / "truth.json").is_file()):
        name = fixture.name
        truth = load_truth(fixture)
        ran = name in cases
        entry = cases.get(name)
        error = case_error(entry) if ran else None
        if error:
            totals["errored"] += 1
            totals["core_errored"] += truth["core"]
            lines.append(f"{name} [{'core' if truth['core'] else 'bonus'}]: ERROR ({error}) excluded from totals")
            continue
        text = entry.get("result", "") if isinstance(entry, dict) else ""
        case = score_case(text if isinstance(text, str) else "", truth)
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
        verdict = "CAUGHT" if case["caught"] else "MISSED" if ran else "MISSED (not run)"
        per = ", ".join(f"{f.get('oracle')}/{f.get('class')}@{_confidence(f)}={c}" for f, c in zip(case["findings"], case["classes"]))
        lines.append(f"{name} [{'core' if truth['core'] else 'bonus'}]: {verdict} confidence={case['confidence']} "
                     f"oracle_match={case['oracle_match']} blocks={case['blocks']} findings=[{per}]")
    return totals, lines


def _errored_suffix(count: int) -> str:
    return f" ({count} errored)" if count else ""


def _scored_fixture_names(fixtures: Path) -> list[str]:
    return [p.name for p in _fixture_dirs(fixtures) if (p / "truth.json").is_file()]


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check-truth", type=Path, metavar="FIXTURES_DIR")
    mode.add_argument("--score", type=Path, metavar="RESULTS_JSON")
    parser.add_argument("--fixtures", type=Path, default=Path("evals/skills/review-chain/fixtures"))
    parser.add_argument("--threshold", type=int, default=75)
    args = parser.parse_args()
    try:
        if args.check_truth:
            errors = check_truth(args.check_truth)
            for error in errors:
                print(f"review-chain-eval: {error}", file=sys.stderr)
            if errors:
                return 1
            print("review-chain-eval: truth.json OK")
            return 0
        try:
            results = json.loads(args.score.read_text())
        except (OSError, ValueError) as exc:
            raise EvalError(f"{args.score}: {exc}") from None
        totals, lines = score(results, args.fixtures, args.threshold)
    except EvalError as exc:
        print(f"review-chain-eval: {exc}", file=sys.stderr)
        return 1
    for name in sorted(set(_scored_fixture_names(args.fixtures)) - set(results["cases"])):
        print(f"review-chain-eval: warning: fixture {name} has no result (not run); scored as MISSED", file=sys.stderr)
    for name in _scored_fixture_names(args.fixtures):
        error = case_error(results["cases"][name]) if name in results["cases"] else None
        if error:
            print(f"review-chain-eval: warning: fixture {name} errored ({error}); excluded from totals", file=sys.stderr)
    for line in lines:
        print(line)
    print(f"core catches: {totals['core_caught']}/{totals['core']}{_errored_suffix(totals['core_errored'])} "
          f"(oracle match {totals['core_oracle_match']}/{totals['core']})")
    print(f"bonus catches (non-core, incl. context-propagation-audit): {totals['bonus_caught']}")
    print(f"all catches: {totals['all_caught']}/{len(lines) - totals['errored']}{_errored_suffix(totals['errored'])}")
    print(f"false positives: {totals['fp']} (at or above {args.threshold}: {totals['fp_at_threshold']})")
    print(f"other findings: {totals['other']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
