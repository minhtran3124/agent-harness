#!/usr/bin/env python3
"""Deterministically score review-chain eval results against each fixture's truth.json."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

ORACLES = ("correctness", "intent", "context-propagation-audit")
# The opening fence (3+ backticks, optionally inside a `>` blockquote) is anchored to a line start so an
# inline mention of "```json" in prose does not open a block; the closing fence is the first run of at
# least as many backticks after the content, wherever it sits on its line.
JSON_BLOCK = re.compile(r"^[ \t]*(>[ \t]*)?(`{3,})json[^\n]*\n(.*?)\2", re.MULTILINE | re.DOTALL | re.IGNORECASE)
QUOTE_PREFIX = re.compile(r"^[ \t]*>[ \t]?", re.MULTILINE)
HUNK = re.compile(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")
FIXTURE_FILES = ("truth.json", "intent.md", "diff.patch")
DIFF_GIT = re.compile(r"^diff --git a/(\S+) b/(\S+)")
DIFF_OLD = re.compile(r"^--- (?:a/)?(\S+)")
DIFF_NEW = re.compile(r"^\+\+\+ (?:b/)?(\S+)")
NUMBER = re.compile(r"[+-]?\d+(?:\.\d+)?")
TOKEN_KEYS = (("input", "input_tokens"), ("output", "output_tokens"),
              ("cache creation", "cache_creation_input_tokens"), ("cache read", "cache_read_input_tokens"))


def _check_pattern(pattern, where: str, need_file: bool) -> list[str]:
    """need_file marks the planted pattern: it needs a file and at least one and_any term."""
    if not isinstance(pattern, dict):
        return [f"{where} must be an object"]
    errors = []
    if not isinstance(pattern.get("file"), str):
        errors.append(f"{where}.file must be a string")
    elif need_file and not pattern["file"]:
        errors.append(f"{where}.file must not be empty")
    for key in ("match_any", "and_any"):
        terms = pattern.get(key)
        if not isinstance(terms, list) or not all(isinstance(t, str) and t for t in terms):
            errors.append(f"{where}.{key} must be a list of non-empty strings")
    if isinstance(pattern.get("match_any"), list) and not pattern["match_any"]:
        errors.append(f"{where}.match_any must not be empty")
    if need_file and isinstance(pattern.get("and_any"), list) and not pattern["and_any"]:
        errors.append(f"{where}.and_any must not be empty")
    return errors


def validate_truth(truth) -> list[str]:
    if not isinstance(truth, dict):
        return ["not an object"]
    errors = []
    version = truth.get("schema_version")
    if type(version) is not int or version != 1:
        errors.append("schema_version must be the integer 1")
    if truth.get("expected_oracle") not in ORACLES:
        errors.append(f"expected_oracle must be one of {', '.join(ORACLES)}")
    for key in ("core", "correctness_clean"):
        if not isinstance(truth.get(key), bool):
            errors.append(f"{key} must be a boolean")
    errors += _check_pattern(truth.get("planted"), "planted", need_file=True)
    fps = truth.get("false_positives")
    if not isinstance(fps, list):
        errors.append("false_positives must be a list")
    else:
        for i, fp in enumerate(fps):
            errors += _check_pattern(fp, f"false_positives[{i}]", need_file=False)
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


def diff_paths(diff: str) -> set[str]:
    """Every file path named in a unified diff's headers (a/ and b/ prefixes stripped).

    `diff --git` lines always count. An adjacent `---`/`+++` pair counts only outside a hunk: a hunk
    opens at `@@ -a,b +c,d @@` and closes once its b old and d new lines are consumed (or at the next
    `diff --git`), so body lines that happen to start with `---` or `+++` are never read as headers.
    """
    paths: set[str] = set()
    lines = diff.splitlines()
    old_left = new_left = 0
    for i, line in enumerate(lines):
        git = DIFF_GIT.match(line)
        if git:
            paths.update(git.groups())
            old_left = new_left = 0
            continue
        if old_left > 0 or new_left > 0:
            if line.startswith("-"):
                old_left -= 1
            elif line.startswith("+"):
                new_left -= 1
            elif not line.startswith("\\"):
                old_left -= 1
                new_left -= 1
            continue
        hunk = HUNK.match(line)
        if hunk:
            old_left, new_left = (int(n) if n is not None else 1 for n in hunk.groups())
            continue
        old = DIFF_OLD.match(line)
        new = DIFF_NEW.match(lines[i + 1]) if old and i + 1 < len(lines) else None
        if old and new:
            paths.update((old.group(1), new.group(1)))
    return {p for p in paths if p != "/dev/null"}


def _path_matches(path: str, want: str) -> bool:
    return path == want or path.endswith("/" + want)


def _planted_in_diff(fixture: Path, truth: dict) -> list[str]:
    want = truth["planted"]["file"]
    try:
        paths = diff_paths((fixture / "diff.patch").read_text())
    except (OSError, UnicodeDecodeError) as exc:
        return [f"planted.file cannot be checked: diff.patch unreadable ({exc})"]
    if not any(_path_matches(p, want) for p in paths):
        return [f"planted.file {want} does not appear in diff.patch"]
    return []


def _missing_files(path: Path) -> list[str]:
    return [name for name in FIXTURE_FILES if not (path / name).is_file()]


def _is_fixture(path: Path) -> bool:
    """One predicate for both modes: a directory holding any fixture file is a fixture."""
    return len(_missing_files(path)) < len(FIXTURE_FILES)


def check_truth(fixtures: Path) -> list[str]:
    errors = []
    for fixture in filter(_is_fixture, _fixture_dirs(fixtures)):
        missing = _missing_files(fixture)
        if "truth.json" in missing:
            errors.append(f"{fixture.name}: missing truth.json (every fixture needs an answer key)")
            continue
        if missing:
            errors.append(f"{fixture.name}: missing {', '.join(missing)}")
        truth, problems = _truth_problems(fixture / "truth.json")
        if truth is not None and "diff.patch" not in missing:
            problems = _planted_in_diff(fixture, truth)
        errors += [f"{fixture.name}/truth.json: {p}" for p in problems]
    return errors


def normalise_file(name: str) -> str:
    name = re.sub(r":\d+$", "", name.strip())
    return re.sub(r"^(a/|b/|\./)", "", name)


def matches(finding: dict, pattern: dict) -> bool:
    file = normalise_file(str(finding.get("file") or ""))
    want = pattern["file"]
    if want and not _path_matches(file, want):
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


def unknown_bucket(finding: dict, truth: dict) -> str | None:
    """Reporting-only sub-bucket of an `unknown` finding (it stays `other` for catch and FP counts)."""
    if str(finding.get("class", "")).lower() != "unknown":
        return None
    if matches(finding, truth["planted"]):
        return "unknown_planted"
    if truth["correctness_clean"] and finding.get("oracle") == "correctness":
        return "unknown_clean_correctness"
    return None


def parse_findings(text: str) -> tuple[list[dict] | None, int]:
    """Findings from the last fenced json block that parses as a list.

    None (unparseable) when the reply mentions "```json" anywhere but no block parses as a list, so a
    fence the regex cannot open is never silently scored as zero findings.
    """
    text = text or ""
    blocks = []
    for quote, _fence, raw in JSON_BLOCK.findall(text):
        blocks.append(QUOTE_PREFIX.sub("", raw) if quote else raw)
    for raw in reversed(blocks):
        try:
            data = json.loads(raw)
        except ValueError:
            continue
        if isinstance(data, list):
            return [f for f in data if isinstance(f, dict)], len(blocks)
    return (None if blocks or "```json" in text.lower() else []), len(blocks)


def coerce_confidence(value) -> tuple[int | float, bool]:
    """(confidence clamped to 0-100, ok); a bool, non-finite or non-numeric value is (0, False).

    A string counts only as a plain decimal (`[+-]?digits[.digits]`), so "inf", "1e2" or "1_0" are rejected.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return 0, False
    if isinstance(value, str) and not NUMBER.fullmatch(value.strip()):
        return 0, False
    try:
        number = float(value)
    except OverflowError:
        return 0, False
    if not math.isfinite(number):
        return 0, False
    number = min(100.0, max(0.0, number))
    return (int(number) if number.is_integer() else number), True


def _confidence(finding: dict) -> int | float:
    return coerce_confidence(finding.get("confidence"))[0]


def score_case(text: str, truth: dict) -> dict:
    findings, blocks = parse_findings(text)
    unparseable = findings is None
    findings = findings or []
    classes = [classify(f, truth) for f in findings]
    planted = [f for f, c in zip(findings, classes) if c == "planted"]
    return {
        "blocks": blocks,
        "unparseable": unparseable,
        "findings": findings,
        "classes": classes,
        "buckets": [unknown_bucket(f, truth) for f in findings],
        "caught": bool(planted),
        "confidence": max((_confidence(f) for f in planted), default=None),
        "oracle_match": any(f.get("oracle") == truth["expected_oracle"] for f in planted),
    }


def case_error(entry) -> str | None:
    """Why a run's record cannot be scored (non-zero rc, or no output), else None."""
    if not isinstance(entry, dict):
        return "no output"
    rc = entry.get("rc")
    if rc == "skipped":
        return f"skipped: {entry.get('reason') or 'no reason recorded'}"
    if rc is not None and rc != 0:
        return f"rc={rc}"
    text = entry.get("result")
    if not isinstance(text, str) or not text.strip():
        return "no output"
    return None


def _int_tokens(value) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def token_totals(cases: dict) -> dict:
    """Per-arm token sums over every recorded case (errored ones included: they were paid for)."""
    sums = dict.fromkeys((label for label, _ in TOKEN_KEYS), 0)
    for entry in cases.values():
        usage = entry.get("usage") if isinstance(entry, dict) else None
        if isinstance(usage, dict):
            for label, key in TOKEN_KEYS:
                sums[label] += _int_tokens(usage.get(key))
    return sums


def score(results: dict, fixtures: Path, threshold: int, warnings: list[str] | None = None) -> tuple[dict, list[str]]:
    warnings = [] if warnings is None else warnings
    totals = dict.fromkeys(("core", "core_caught", "core_oracle_match", "bonus_caught", "all_caught", "fp", "fp_at_threshold",
                            "other", "unknown_planted", "unknown_clean_correctness", "errored", "core_errored",
                            "unparseable", "core_unparseable", "not_run", "core_not_run", "tokens"), 0)
    lines = []
    cases = results.get("cases") if isinstance(results, dict) else None
    if not isinstance(cases, dict):
        raise EvalError("results file has no \"cases\" object")
    dirs = [p for p in _fixture_dirs(fixtures) if _is_fixture(p)]
    if not dirs:
        raise EvalError(f"no fixtures found under {fixtures}")
    scored = [p for p in dirs if not _missing_files(p)]
    for p in dirs:
        if p not in scored:
            warnings.append(f"fixture {p.name} is incomplete (missing {', '.join(_missing_files(p))}); not scored")
    names = {p.name for p in scored}
    for name in sorted(set(cases) - names):
        warnings.append(f"result case {name} has no matching fixture; ignored")
    for fixture in scored:
        name = fixture.name
        truth = load_truth(fixture)
        kind = "core" if truth["core"] else "bonus"
        ran = name in cases
        entry = cases.get(name)
        if not ran:
            totals["not_run"] += 1
            totals["core_not_run"] += truth["core"]
            warnings.append(f"fixture {name} has no result (not run); excluded from totals")
            lines.append(f"{name} [{kind}]: MISSED (not run) excluded from totals")
            continue
        error = case_error(entry)
        if error:
            totals["errored"] += 1
            totals["core_errored"] += truth["core"]
            warnings.append(f"fixture {name} errored ({error}); excluded from totals")
            lines.append(f"{name} [{kind}]: ERROR ({error}) excluded from totals")
            continue
        text = entry.get("result", "")
        case = score_case(text if isinstance(text, str) else "", truth)
        if case["unparseable"]:
            totals["unparseable"] += 1
            totals["core_unparseable"] += truth["core"]
            warnings.append(f"fixture {name} is unparseable ({case['blocks']} json block(s), none a JSON array); "
                            "excluded from totals")
            lines.append(f"{name} [{kind}]: UNPARSEABLE blocks={case['blocks']} excluded from totals")
            continue
        totals["core"] += truth["core"]
        if case["caught"]:
            totals["all_caught"] += 1
            if truth["core"]:
                totals["core_caught"] += 1
                totals["core_oracle_match"] += case["oracle_match"]
            else:
                totals["bonus_caught"] += 1
        labels = []
        for f, c, bucket in zip(case["findings"], case["classes"], case["buckets"]):
            value, ok = coerce_confidence(f.get("confidence"))
            if not ok:
                warnings.append(f"fixture {name}: confidence {f.get('confidence')!r} is not a number; treated as 0")
            if c == "false_positive":
                totals["fp"] += 1
                totals["fp_at_threshold"] += value >= threshold
            elif c == "other":
                totals["other"] += 1
            if bucket:
                totals[bucket] += 1
            labels.append(f"{f.get('oracle')}/{f.get('class')}@{value}={c}" + (f"({bucket})" if bucket else ""))
        verdict = "CAUGHT" if case["caught"] else "MISSED"
        lines.append(f"{name} [{kind}]: {verdict} confidence={case['confidence']} "
                     f"oracle_match={case['oracle_match']} blocks={case['blocks']} findings=[{', '.join(labels)}]")
    totals["tokens"] = sum(token_totals(cases).values())
    return totals, lines


def _excluded_suffix(errored: int, unparseable: int, not_run: int) -> str:
    parts = [f"{n} {label}" for n, label in ((errored, "errored"), (unparseable, "unparseable"), (not_run, "not run")) if n]
    return f" ({', '.join(parts)})" if parts else ""


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
        warnings: list[str] = []
        totals, lines = score(results, args.fixtures, args.threshold, warnings)
    except EvalError as exc:
        print(f"review-chain-eval: {exc}", file=sys.stderr)
        return 1
    for warning in warnings:
        print(f"review-chain-eval: warning: {warning}", file=sys.stderr)
    for line in lines:
        print(line)
    excluded = totals["errored"] + totals["unparseable"] + totals["not_run"]
    print(f"core catches: {totals['core_caught']}/{totals['core']}"
          f"{_excluded_suffix(totals['core_errored'], totals['core_unparseable'], totals['core_not_run'])} "
          f"(oracle match {totals['core_oracle_match']}/{totals['core']})")
    print(f"bonus catches (non-core, incl. context-propagation-audit): {totals['bonus_caught']}")
    print(f"all catches: {totals['all_caught']}/{len(lines) - excluded}"
          f"{_excluded_suffix(totals['errored'], totals['unparseable'], totals['not_run'])}")
    print(f"false positives: {totals['fp']} (at or above {args.threshold}: {totals['fp_at_threshold']})")
    print(f"other findings: {totals['other']}")
    print(f"unknown findings (counted in other): unknown_planted={totals['unknown_planted']}, "
          f"unknown_clean_correctness={totals['unknown_clean_correctness']}")
    sums = token_totals(results["cases"])
    print(f"tokens: {totals['tokens']} ({', '.join(f'{k} {v}' for k, v in sums.items())}) "
          f"over {len(results['cases'])} cases")
    if excluded == len(lines):
        print(f"review-chain-eval: no fixture could be scored ({totals['errored']} errored, "
              f"{totals['unparseable']} unparseable, {totals['not_run']} not run of {len(lines)})", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
