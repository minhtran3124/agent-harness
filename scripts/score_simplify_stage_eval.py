#!/usr/bin/env python3
"""Score `/simplify` shadow evidence with safety before cleanup value."""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


RUNNER_PATH = Path(__file__).with_name("run_simplify_stage_eval.py")
RUNNER_SPEC = importlib.util.spec_from_file_location(
    "_simplify_stage_eval_runner",
    RUNNER_PATH,
)
if not RUNNER_SPEC or not RUNNER_SPEC.loader:
    raise RuntimeError(f"unable to load {RUNNER_PATH}")
RUNNER = importlib.util.module_from_spec(RUNNER_SPEC)
sys.modules[RUNNER_SPEC.name] = RUNNER
RUNNER_SPEC.loader.exec_module(RUNNER)


@dataclass(frozen=True)
class ScoreReport:
    quality_pass: bool
    value_evaluated: bool
    value_pass: bool | None
    baseline_value_score: int | None
    value_score: int | None
    minimum_value_score: int | None
    errors: list[str]


class ScoreError(ValueError):
    """Invalid truth or collection evidence."""


def _load_truths(fixtures: Path) -> dict[str, dict[str, Any]]:
    truths: dict[str, dict[str, Any]] = {}
    for path in sorted(fixtures.glob("*/truth.json")):
        try:
            truth = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ScoreError(f"invalid truth file {path}: {exc}") from exc
        case_id = path.parent.name
        if truth.get("schema_version") != 1:
            raise ScoreError(f"{case_id}: truth schema_version must be 1")
        safe = truth.get("safe_outcomes")
        if (
            not isinstance(safe, list)
            or not safe
            or any(item not in {"changed", "no_op"} for item in safe)
        ):
            raise ScoreError(f"{case_id}: safe_outcomes is invalid")
        allowed = truth.get("allowed_changed_paths")
        if not isinstance(allowed, list) or any(
            not isinstance(item, str) or not item for item in allowed
        ):
            raise ScoreError(f"{case_id}: allowed_changed_paths is invalid")
        if not isinstance(truth.get("value_opportunity"), bool):
            raise ScoreError(f"{case_id}: value_opportunity must be boolean")
        minimum_removed = truth.get("minimum_removed_lines")
        if not isinstance(minimum_removed, int) or minimum_removed < 0:
            raise ScoreError(f"{case_id}: minimum_removed_lines must be non-negative")
        truths[case_id] = truth
    if not truths:
        raise ScoreError(f"no truth files found under {fixtures}")
    return truths


def _records(collection: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    raw_records = collection.get("records")
    if not isinstance(raw_records, list):
        return {}, ["records must be a list"]
    records: dict[str, dict[str, Any]] = {}
    for record in raw_records:
        if not isinstance(record, dict):
            errors.append("record must be an object")
            continue
        case_id = record.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            errors.append("record has invalid case_id")
        elif case_id in records:
            errors.append(f"duplicate case_id: {case_id}")
        else:
            records[case_id] = record
    return records, errors


def _all_checks_pass(record: dict[str, Any], field: str) -> bool:
    checks = record.get(field)
    return (
        isinstance(checks, list)
        and bool(checks)
        and all(
            isinstance(check, dict) and check.get("returncode") == 0 for check in checks
        )
    )


def _path_allowed(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _value_score(
    records: dict[str, dict[str, Any]],
    truths: dict[str, dict[str, Any]],
) -> int:
    score = 0
    for case_id, truth in truths.items():
        if not truth["value_opportunity"]:
            continue
        record = records[case_id]
        stats = record.get("diff_stats", {})
        removed = stats.get("simplify_removed_lines", 0)
        if (
            record.get("outcome") == "changed"
            and isinstance(removed, int)
            and removed >= truth["minimum_removed_lines"]
        ):
            score += 1
    return score


def score_collections(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    fixtures: Path,
    *,
    initial_errors: list[str] | None = None,
) -> ScoreReport:
    errors = list(initial_errors or [])
    for label, collection in (("baseline", baseline), ("candidate", candidate)):
        try:
            RUNNER.validate_result(collection)
        except ValueError as exc:
            errors.append(f"{label}: collection schema invalid: {exc}")
    try:
        truths = _load_truths(fixtures)
    except ScoreError as exc:
        return ScoreReport(False, False, None, None, None, None, errors + [str(exc)])
    baseline_records, baseline_errors = _records(baseline)
    candidate_records, candidate_errors = _records(candidate)
    errors.extend(f"baseline: {item}" for item in baseline_errors)
    errors.extend(f"candidate: {item}" for item in candidate_errors)
    truth_cases = set(truths)
    if set(baseline_records) != truth_cases:
        errors.append(
            "baseline case collections differ from truth corpus: "
            f"expected {sorted(truth_cases)}, got {sorted(baseline_records)}"
        )
    if set(candidate_records) != truth_cases:
        errors.append(
            "candidate case collections differ from truth corpus: "
            f"expected {sorted(truth_cases)}, got {sorted(candidate_records)}"
        )
    if baseline.get("mode") != "advisory":
        errors.append("baseline mode must be advisory")
    if candidate.get("mode") != "candidate":
        errors.append("candidate mode must be candidate")
    if baseline.get("source_commit_sha") != candidate.get("source_commit_sha"):
        errors.append("source commit mismatch")
    source_root = RUNNER_PATH.resolve().parent.parent
    shared_source_sha = baseline.get("source_commit_sha")
    source_commit_result = subprocess.run(
        ["git", "cat-file", "-e", f"{shared_source_sha}^{{commit}}"],
        cwd=source_root,
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=True,
        check=False,
    )
    source_ancestry_result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", str(shared_source_sha), "HEAD"],
        cwd=source_root,
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=True,
        check=False,
    )
    if source_commit_result.returncode or source_ancestry_result.returncode:
        errors.append(
            "collection source commit is missing or not an ancestor of current HEAD"
        )
    try:
        current_input_digest = RUNNER.evaluation_input_digest(fixtures)
    except RUNNER.CollectionError as exc:
        errors.append(f"current evaluation inputs invalid: {exc}")
        current_input_digest = None
    baseline_digest = baseline.get("input_digest")
    candidate_digest = candidate.get("input_digest")
    if baseline_digest != candidate_digest:
        errors.append("baseline/candidate evaluation input digest mismatch")
    if current_input_digest is not None and (
        baseline_digest != current_input_digest
        or candidate_digest != current_input_digest
    ):
        errors.append("evaluation input digest is stale against current inputs")
    for key in ("client_version", "expected_client_version", "model"):
        old = baseline.get("environment", {}).get(key)
        new = candidate.get("environment", {}).get(key)
        if not isinstance(old, str) or not old or old != new:
            errors.append(f"environment mismatch for {key}")

    for label, records in (
        ("baseline", baseline_records),
        ("candidate", candidate_records),
    ):
        for case_id, record in records.items():
            fixture = fixtures / case_id
            if fixture.is_dir():
                try:
                    actual_digest = RUNNER._fixture_digest(fixture)
                except RUNNER.CollectionError as exc:
                    errors.append(f"{case_id}: public fixture invalid: {exc}")
                    continue
                if record.get("fixture_digest") != actual_digest:
                    errors.append(f"{label} {case_id}: public fixture digest mismatch")
                try:
                    manifest = RUNNER._load_manifest(fixture)
                except RUNNER.CollectionError as exc:
                    errors.append(f"{case_id}: public fixture manifest invalid: {exc}")
                    continue
                replacements = {
                    "{worktree}": record.get("worktree"),
                    "{fixture}": str(fixture),
                }
                for field, manifest_field in (
                    ("verification", "verification_commands"),
                    ("final_review", "final_review_commands"),
                ):
                    expected_commands = [
                        [replacements.get(part, part) for part in command]
                        for command in manifest[manifest_field]
                    ]
                    actual_commands = [
                        item.get("command")
                        for item in record.get(field, [])
                        if isinstance(item, dict)
                    ]
                    if actual_commands != expected_commands:
                        errors.append(
                            f"{label} {case_id}: {field} commands contradict manifest"
                        )

    if not errors:
        for case_id, truth in truths.items():
            record = candidate_records[case_id]
            outcome = record.get("outcome")
            if outcome not in truth["safe_outcomes"]:
                errors.append(f"{case_id}: unsafe outcome {outcome}")
            claude = record.get("claude", {})
            if claude.get("invocations") != 1:
                errors.append(f"{case_id}: candidate must invoke simplify exactly once")
            if claude.get("returncode") != 0:
                errors.append(f"{case_id}: simplify invocation failed")
            if not _all_checks_pass(record, "verification"):
                errors.append(f"{case_id}: verification failed")
            if not _all_checks_pass(record, "final_review"):
                errors.append(f"{case_id}: final review failed")
            changed_files = record.get("changed_files")
            if not isinstance(changed_files, list):
                errors.append(f"{case_id}: changed_files must be a list")
            else:
                for path in changed_files:
                    if not isinstance(path, str) or not _path_allowed(
                        path, truth["allowed_changed_paths"]
                    ):
                        errors.append(f"{case_id}: changed path is not allowed: {path}")

    if errors:
        return ScoreReport(False, False, None, None, None, None, errors)

    baseline_score = _value_score(baseline_records, truths)
    candidate_score = _value_score(candidate_records, truths)
    scoring_path = fixtures / "scoring.json"
    opportunities = sum(1 for truth in truths.values() if truth["value_opportunity"])
    minimum = opportunities
    if scoring_path.is_file():
        try:
            scoring = json.loads(scoring_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return ScoreReport(
                False,
                False,
                None,
                None,
                None,
                None,
                [f"invalid scoring.json: {exc}"],
            )
        configured = scoring.get("minimum_value_score")
        if (
            not isinstance(configured, int)
            or configured < 1
            or configured > opportunities
        ):
            return ScoreReport(
                False,
                False,
                None,
                None,
                None,
                None,
                ["minimum_value_score is outside the value-opportunity corpus"],
            )
        minimum = configured
    value_pass = candidate_score >= minimum and candidate_score > baseline_score
    value_errors = []
    if not value_pass:
        value_errors.append(
            "value gate failed: "
            f"baseline={baseline_score}, candidate={candidate_score}, minimum={minimum}"
        )
    return ScoreReport(
        True,
        True,
        value_pass,
        baseline_score,
        candidate_score,
        minimum,
        value_errors,
    )


def _sha256(path: Path) -> str:
    return RUNNER.sha256_file(path)


def artifact_errors(collection: dict[str, Any], collection_path: Path) -> list[str]:
    errors: list[str] = []
    root = collection_path.parent.resolve()
    records = collection.get("records")
    if not isinstance(records, list):
        return ["collection records must be a list"]
    for record in records:
        # Match _records: report a non-object rather than crashing on .get().
        # artifact_errors runs before score_collections, so an AttributeError
        # here escaped main() as a traceback instead of the structured report.
        if not isinstance(record, dict):
            errors.append("record must be an object")
            continue
        case_id = record.get("case_id", "<unknown>")
        artifacts = record.get("artifacts")
        if not isinstance(artifacts, dict):
            errors.append(f"{case_id}: artifacts are missing")
            continue
        for label in (
            "pre_diff",
            "simplify_diff",
            "post_diff",
            "transcript",
            "checks",
            "history_bundle",
        ):
            descriptor = artifacts.get(label)
            if not isinstance(descriptor, dict):
                errors.append(f"{case_id}: {label} artifact is missing")
                continue
            relative = descriptor.get("path")
            expected = descriptor.get("sha256")
            if not isinstance(relative, str):
                errors.append(f"{case_id}: {label} path is invalid")
                continue
            path = (root / relative).resolve()
            try:
                path.relative_to(root)
            except ValueError:
                errors.append(f"{case_id}: {label} escapes the result directory")
                continue
            if not path.is_file():
                errors.append(f"{case_id}: {label} artifact does not exist")
            elif not isinstance(expected, str) or _sha256(path) != expected:
                errors.append(f"{case_id}: {label} artifact hash mismatch")
        if any(error.startswith(f"{case_id}:") for error in errors):
            continue
        try:
            errors.extend(
                _crosscheck_record_artifacts(
                    record,
                    root,
                )
            )
        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
            RUNNER.CollectionError,
        ) as exc:
            errors.append(f"{case_id}: artifact cross-check failed: {exc}")
    return errors


def _git_output(repo: Path, *arguments: str) -> bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise ValueError(
            f"git {' '.join(arguments)} failed: "
            f"{completed.stderr.decode(errors='replace').strip()}"
        )
    return completed.stdout


def _numstat(repo: Path, pre_sha: str, post_sha: str) -> dict[str, int]:
    added = 0
    removed = 0
    for line in _git_output(repo, "diff", "--numstat", pre_sha, post_sha).splitlines():
        parts = line.split(b"\t", 2)
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            added += int(parts[0])
            removed += int(parts[1])
    return {
        "simplify_added_lines": added,
        "simplify_removed_lines": removed,
    }


def _crosscheck_record_artifacts(
    record: dict[str, Any],
    root: Path,
) -> list[str]:
    case_id = record["case_id"]
    artifacts = record["artifacts"]
    paths = {
        label: (root / descriptor["path"]).resolve()
        for label, descriptor in artifacts.items()
    }
    errors: list[str] = []
    transcript = json.loads(paths["transcript"].read_text(encoding="utf-8"))
    claude = record["claude"]
    for key in (
        "returncode",
        "elapsed_seconds",
        "result",
        "usage",
        "observed_skill_invocations",
        "skill_tool_evidence",
    ):
        if transcript.get(key) != claude.get(key):
            errors.append(f"{case_id}: transcript contradicts claude.{key}")
    raw_result, raw_usage, raw_skills, raw_evidence = RUNNER._parse_claude_stream(
        transcript.get("stdout", "")
    )
    if claude["invocations"] == 1:
        for label, raw_value, claimed in (
            ("result", raw_result, claude["result"]),
            ("usage", raw_usage, claude["usage"]),
            (
                "observed_skill_invocations",
                raw_skills,
                claude["observed_skill_invocations"],
            ),
            (
                "skill_tool_evidence",
                raw_evidence[0] if len(raw_evidence) == 1 else raw_evidence,
                claude["skill_tool_evidence"],
            ),
        ):
            if raw_value != claimed:
                errors.append(
                    f"{case_id}: raw Claude stream contradicts claude.{label}"
                )
    elif raw_result or raw_usage or raw_skills or transcript.get("stdout"):
        errors.append(f"{case_id}: advisory transcript contains Claude stream output")

    checks = json.loads(paths["checks"].read_text(encoding="utf-8"))
    if checks.get("case_id") != case_id:
        errors.append(f"{case_id}: checks artifact has wrong case_id")
    for field in ("verification", "final_review"):
        if checks.get(field) != record.get(field):
            errors.append(f"{case_id}: checks artifact contradicts {field}")

    with tempfile.TemporaryDirectory(prefix=f"simplify-score-{case_id}-") as temp:
        clone = Path(temp) / "repo"
        completed = subprocess.run(
            ["git", "clone", "-q", str(paths["history_bundle"]), str(clone)],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        )
        if completed.returncode:
            raise ValueError(
                "history bundle cannot be cloned: "
                + completed.stderr.decode(errors="replace").strip()
            )
        base_sha = record["base_sha"]
        pre_sha = record["pre_sha"]
        post_sha = record["post_sha"]
        actual_head = _git_output(clone, "rev-parse", "HEAD").decode().strip()
        if actual_head != post_sha:
            errors.append(f"{case_id}: bundle HEAD contradicts post_sha")
        for older, newer, label in (
            (base_sha, pre_sha, "base/pre"),
            (pre_sha, post_sha, "pre/post"),
        ):
            ancestry = subprocess.run(
                ["git", "merge-base", "--is-ancestor", older, newer],
                cwd=clone,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                check=False,
            )
            if ancestry.returncode:
                errors.append(f"{case_id}: bundle does not preserve {label} ancestry")
        expected_patches = {
            "pre_diff": _git_output(clone, "diff", "--binary", base_sha, pre_sha),
            "simplify_diff": _git_output(
                clone,
                "diff",
                "--binary",
                "--find-renames",
                pre_sha,
                post_sha,
                "--",
            ),
            "post_diff": _git_output(clone, "diff", "--binary", base_sha, post_sha),
        }
        for label, expected in expected_patches.items():
            if paths[label].read_bytes() != expected:
                errors.append(f"{case_id}: {label} contradicts history bundle")
        changed_files = (
            _git_output(clone, "diff", "--name-only", pre_sha, post_sha)
            .decode("utf-8")
            .splitlines()
            if pre_sha != post_sha
            else []
        )
        if sorted(changed_files) != record["changed_files"]:
            errors.append(f"{case_id}: changed_files contradict history bundle")
        if _numstat(clone, pre_sha, post_sha) != record["diff_stats"]:
            errors.append(f"{case_id}: diff_stats contradict history bundle")
        actual_outcome = "changed" if pre_sha != post_sha else "no_op"
        if actual_outcome != record["outcome"]:
            errors.append(f"{case_id}: outcome contradicts history bundle")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compare", nargs=2, type=Path, required=True)
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path("evals/skills/simplify-stage/fixtures"),
    )
    parser.add_argument("--quality-gate", action="store_true")
    parser.add_argument("--value-gate", action="store_true")
    args = parser.parse_args()
    try:
        baseline = json.loads(args.compare[0].read_text(encoding="utf-8"))
        candidate = json.loads(args.compare[1].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"simplify-stage-score: {exc}", file=sys.stderr)
        return 1
    integrity = artifact_errors(baseline, args.compare[0])
    integrity.extend(artifact_errors(candidate, args.compare[1]))
    report = score_collections(
        baseline,
        candidate,
        args.fixtures,
        initial_errors=integrity,
    )
    print(json.dumps(asdict(report), indent=2))
    if args.quality_gate and not report.quality_pass:
        return 1
    if args.value_gate and report.value_pass is not True:
        return 1
    if not args.quality_gate and not args.value_gate:
        return 0 if report.quality_pass and report.value_pass else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
