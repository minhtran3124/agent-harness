#!/usr/bin/env python3
"""Validate the Codex packaging decision and its executable evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


REQUIRED_METADATA = {
    "decision",
    "fallback",
    "cli_version",
    "matrix",
    "hybrid_evidence",
    "direct_evidence",
    "runtime_execution",
    "fallback_trigger",
}
REQUIRED_SECTIONS = {
    "Ownership boundary",
    "Executable evidence",
    "Unresolved gaps",
    "Fallback trigger",
}
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
PRIVATE_PATH_RE = re.compile(
    r"(?:^|[\s\"'])(?:/Users/|/home/|/root/|[A-Za-z]:[\\/]Users[\\/])"
)


def _relative_path(value: Any, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label} must be a non-empty relative path")
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:[\\/]", value):
        errors.append(f"{label} must stay inside the repository")
        return None
    return value


def _front_matter(text: str, errors: list[str]) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        errors.append("decision must start with YAML-style front matter")
        return {}
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return metadata
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            errors.append(f"invalid front-matter line: {line!r}")
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    errors.append("decision front matter is not closed")
    return metadata


def _load_json(path: Path, label: str, errors: list[str]) -> Any | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        errors.append(f"{label} not found: {path}")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label} is not valid readable JSON: {exc}")
    return None


def _private_strings(value: Any, prefix: str) -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            errors.extend(_private_strings(child, f"{prefix}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_private_strings(child, f"{prefix}[{index}]"))
    elif isinstance(value, str) and (
        value.startswith(("/", "file://"))
        or WINDOWS_ABSOLUTE_RE.match(value)
        or PRIVATE_PATH_RE.search(value)
    ):
        errors.append(f"{prefix} contains a private or absolute path")
    return errors


def _validate_evidence(
    payload: Any,
    *,
    candidate: str,
    cli_version: str,
    label: str,
    errors: list[str],
) -> None:
    if not isinstance(payload, dict):
        errors.append(f"{label} must be a JSON object")
        return
    if payload.get("schema_version") != 1:
        errors.append(f"{label}.schema_version must be 1")
    if payload.get("runtime") != "codex":
        errors.append(f"{label}.runtime must be codex")
    if payload.get("cli_version") != cli_version:
        errors.append(f"{label}.cli_version must match the decision")
    if payload.get("candidate") != candidate:
        errors.append(f"{label}.candidate must be {candidate}")
    if payload.get("capture") != "isolated-local-packaging-probe":
        errors.append(f"{label}.capture has unsupported provenance")
    if payload.get("config_hash") != "not-applicable":
        errors.append(f"{label}.config_hash must be not-applicable")
    if not isinstance(payload.get("captured_at"), str):
        errors.append(f"{label}.captured_at must be present")
    result = payload.get("result")
    if not isinstance(result, dict):
        errors.append(f"{label}.result must be an object")
        return
    checks = result.get("checks")
    if not isinstance(checks, dict) or not checks:
        errors.append(f"{label}.result.checks must be non-empty")
    elif any(not isinstance(value, bool) for value in checks.values()):
        errors.append(f"{label} contains a non-boolean check")
    passed = result.get("passed")
    status = result.get("status")
    if not isinstance(passed, bool):
        errors.append(f"{label}.result.passed must be boolean")
    elif passed:
        if (
            status != "observed"
            or not isinstance(checks, dict)
            or not all(checks.values())
        ):
            errors.append(
                f"{label} passing result must be observed with all checks true"
            )
    else:
        if status != "unknown":
            errors.append(f"{label} non-passing result must have unknown status")
        if isinstance(checks, dict) and checks and all(checks.values()):
            errors.append(f"{label} non-passing result must identify a failed check")
        if not isinstance(result.get("owner"), str) or not result.get("owner"):
            errors.append(f"{label} non-passing result must name an owner")
        if not isinstance(result.get("exit_condition"), str) or not result.get(
            "exit_condition"
        ):
            errors.append(f"{label} non-passing result must define an exit condition")
    if result.get("runtime_execution_observed") is not False:
        errors.append(f"{label} must not overclaim runtime execution")
    errors.extend(_private_strings(payload, label))


def validate_decision(decision_path: Path, *, root: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = decision_path.read_text()
    except (OSError, UnicodeDecodeError) as exc:
        return [f"decision is not readable: {exc}"]
    metadata = _front_matter(text, errors)
    for key in sorted(REQUIRED_METADATA - metadata.keys()):
        errors.append(f"decision metadata missing {key}")
    if metadata.get("decision") not in {"hybrid", "direct"}:
        errors.append("decision must be hybrid or direct")
    if metadata.get("fallback") not in {"hybrid", "direct"}:
        errors.append("fallback must be hybrid or direct")
    if metadata.get("decision") == metadata.get("fallback"):
        errors.append("decision and fallback must differ")
    cli_version = metadata.get("cli_version", "")
    if not VERSION_RE.fullmatch(cli_version):
        errors.append("cli_version must be semantic x.y.z")
    if metadata.get("runtime_execution") != "not-observed":
        errors.append("runtime_execution must remain not-observed for this probe")
    if len(metadata.get("fallback_trigger", "")) < 20:
        errors.append("fallback_trigger must be concrete and non-empty")
    for section in sorted(REQUIRED_SECTIONS):
        if f"## {section}" not in text:
            errors.append(f"decision missing section: {section}")

    evidence: dict[str, Any] = {}
    evidence_paths: dict[str, str] = {}
    for candidate in ("hybrid", "direct"):
        key = f"{candidate}_evidence"
        relative = _relative_path(metadata.get(key), key, errors)
        if relative is None:
            continue
        evidence_paths[candidate] = relative
        payload = _load_json(root / relative, key, errors)
        evidence[candidate] = payload
        _validate_evidence(
            payload,
            candidate=candidate,
            cli_version=cli_version,
            label=key,
            errors=errors,
        )

    selected = metadata.get("decision")
    selected_payload = evidence.get(selected)
    selected_result = (
        selected_payload.get("result") if isinstance(selected_payload, dict) else None
    )
    if not isinstance(selected_result, dict) or not (
        selected_result.get("passed") is True
        and selected_result.get("status") == "observed"
    ):
        errors.append(
            "selected packaging candidate must have an observed passing result"
        )

    matrix_relative = _relative_path(metadata.get("matrix"), "matrix", errors)
    if matrix_relative is not None:
        matrix = _load_json(root / matrix_relative, "matrix", errors)
        rows = matrix.get("capabilities", []) if isinstance(matrix, dict) else []
        packaging = [row for row in rows if row.get("id") == "packaging.plugins"]
        if len(packaging) != 1:
            errors.append("matrix must contain exactly one packaging.plugins row")
        else:
            row = packaging[0]
            if (
                row.get("status") != "advisory"
                or row.get("evidence_level") != "observed"
            ):
                errors.append(
                    "matrix packaging.plugins must remain advisory with observed lifecycle evidence"
                )
            if (
                selected in evidence_paths
                and row.get("evidence_path") != evidence_paths[selected]
            ):
                errors.append(
                    "matrix packaging.plugins does not point at selected evidence"
                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decision", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    decision = args.decision if args.decision.is_absolute() else root / args.decision
    errors = validate_decision(decision, root=root)
    if errors:
        for error in errors:
            print(f"codex-packaging: {error}", file=sys.stderr)
        print(f"codex-packaging: {len(errors)} problem(s)", file=sys.stderr)
        return 1
    print(f"codex-packaging: {args.decision} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
