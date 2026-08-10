#!/usr/bin/env python3
"""Validate the versioned Codex capability/evidence contract.

The checker intentionally uses only the Python standard library.  Documentation is
traceability, captured fixtures are provenance, and an unknown capability is valid
only when it is owned and has a concrete exit condition.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse


TOP_LEVEL_FIELDS = {
    "schema_version",
    "runtime",
    "matrix_version",
    "cli_version",
    "evidence_root",
    "supported_platforms",
    "capabilities",
}
CAPABILITY_FIELDS = {
    "id",
    "area",
    "support_target",
    "load_bearing",
    "status",
    "evidence_level",
    "platforms",
    "source",
    "config",
    "evidence_path",
    "owner",
    "exit_condition",
}
FIXTURE_FIELDS = {
    "schema_version",
    "runtime",
    "cli_version",
    "platform",
    "captured_at",
    "config_hash",
    "capture",
    "result",
}
ALLOWED_AREAS = {"agents", "config", "hooks", "packaging", "platform", "tools"}
ALLOWED_TARGETS = {"required", "advisory", "deferred"}
ALLOWED_STATUSES = {"supported", "advisory", "unsupported", "unknown"}
ALLOWED_EVIDENCE = {"observed", "documented", "unknown"}
ALLOWED_SOURCE_KINDS = {
    "captured-fixture",
    "official-documentation",
    "unavailable",
}
ALLOWED_CONFIG_SCOPES = {"effective", "not-applicable", "unknown"}
# A fixture's `capture` names how it was produced.  The first group is emitted verbatim
# by scripts/capture_codex_capabilities.sh; `transcribed-isolated-live-probe` is the only
# label a human may write by hand, and it means the fixture was transcribed from an
# earlier observed run rather than re-derived by the capture tool.  Keeping the vocabulary
# closed is what stops a hand-authored file from wearing a captured label.
ALLOWED_CAPTURES = {
    "local-cli-non-model",
    "local-dependency-probe",
    "controlled-project-config",
    "isolated-local-benchmark",
    "isolated-live-model-probe",
    "live-model-probe-not-observed",
    "transcribed-isolated-live-probe",
}
OFFICIAL_DOC_HOSTS = {
    "developers.openai.com",
    "learn.chatgpt.com",
    "platform.openai.com",
}
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
ID_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
PLATFORM_RE = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
PRIVATE_PATH_RE = re.compile(
    r"(?:^|[\s\"'])(?:/Users/|/home/|/root/|[A-Za-z]:[\\/]Users[\\/])"
)


def _parse_date(value: Any, label: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{label} must be an ISO date string")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label} must be YYYY-MM-DD")
        return None


def _relative_repo_path(value: Any, label: str, errors: list[str]) -> str | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label} must be a non-empty relative path")
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or WINDOWS_ABSOLUTE_RE.match(value):
        errors.append(f"{label} must be relative and contain no private path")
        return None
    if ".." in path.parts:
        errors.append(f"{label} must not traverse outside the repository")
        return None
    return value


def _private_strings(value: Any, prefix: str = "fixture") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            errors.extend(_private_strings(child, f"{prefix}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_private_strings(child, f"{prefix}[{index}]"))
    elif isinstance(value, str):
        parsed = urlparse(value)
        is_url = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        if not is_url and (
            value.startswith("/")
            or WINDOWS_ABSOLUTE_RE.match(value)
            or PRIVATE_PATH_RE.search(value)
            or value.startswith("file://")
        ):
            errors.append(f"{prefix} contains a private or absolute path")
    return errors


def _load_json(path: Path, label: str, errors: list[str]) -> Any | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        errors.append(f"{label} not found: {path}")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"{label} is not valid readable JSON: {exc}")
    return None


def _validate_source(
    source: Any,
    label: str,
    *,
    today: date,
    errors: list[str],
) -> str | None:
    if not isinstance(source, dict):
        errors.append(f"{label}.source must be an object")
        return None
    missing = {"kind", "reference", "checked_at", "expires_at"} - source.keys()
    for field in sorted(missing):
        errors.append(f"{label}.source missing {field}")
    kind = source.get("kind")
    if kind not in ALLOWED_SOURCE_KINDS:
        errors.append(f"{label}.source.kind unsupported: {kind!r}")
    reference = source.get("reference")
    if not isinstance(reference, str) or not reference.strip():
        errors.append(f"{label}.source.reference must be non-empty")
    if kind == "official-documentation" and isinstance(reference, str):
        parsed = urlparse(reference)
        if parsed.scheme != "https" or parsed.hostname not in OFFICIAL_DOC_HOSTS:
            errors.append(
                f"{label}.source.reference must use an official OpenAI docs host"
            )
    checked = _parse_date(
        source.get("checked_at"), f"{label}.source.checked_at", errors
    )
    expires = _parse_date(
        source.get("expires_at"), f"{label}.source.expires_at", errors
    )
    if checked and expires and expires < checked:
        errors.append(f"{label}.source expires before it was checked")
    if expires and today > expires:
        errors.append(f"{label}.source expired on {expires.isoformat()}")
    return kind if isinstance(kind, str) else None


def _validate_config(config: Any, label: str, errors: list[str]) -> None:
    if not isinstance(config, dict):
        errors.append(f"{label}.config must be an object")
        return
    missing = {"scope", "sha256"} - config.keys()
    for field in sorted(missing):
        errors.append(f"{label}.config missing {field}")
    scope = config.get("scope")
    digest = config.get("sha256")
    if scope not in ALLOWED_CONFIG_SCOPES:
        errors.append(f"{label}.config.scope unsupported: {scope!r}")
    if scope == "effective":
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"{label}.config.sha256 must be 64 lowercase hex characters")
    elif digest is not None:
        errors.append(f"{label}.config.sha256 must be null when scope is {scope!r}")


def _validate_fixture(
    fixture_path: Path,
    label: str,
    *,
    matrix: dict[str, Any],
    capability: dict[str, Any],
    errors: list[str],
) -> None:
    payload = _load_json(fixture_path, f"{label}.evidence_path", errors)
    if not isinstance(payload, dict):
        if payload is not None:
            errors.append(f"{label}.evidence fixture must be a JSON object")
        return
    for field in sorted(FIXTURE_FIELDS - payload.keys()):
        errors.append(f"{label}.evidence fixture missing {field}")
    if payload.get("schema_version") != 1:
        errors.append(f"{label}.evidence fixture schema_version must be 1")
    if payload.get("runtime") != matrix.get("runtime"):
        errors.append(f"{label}.evidence fixture runtime does not match matrix")
    if payload.get("cli_version") != matrix.get("cli_version"):
        errors.append(f"{label}.evidence fixture cli_version does not match matrix")
    if payload.get("platform") not in capability.get("platforms", []):
        errors.append(
            f"{label}.evidence fixture platform is not declared by the capability"
        )
    if payload.get("capture") not in ALLOWED_CAPTURES:
        errors.append(
            f"{label}.evidence fixture capture unsupported: {payload.get('capture')!r}"
        )
    result = payload.get("result")
    if not isinstance(result, dict) or result.get("status") != "observed":
        errors.append(f"{label}.evidence fixture result.status must be 'observed'")
    config = capability.get("config")
    if isinstance(config, dict):
        expected_hash = (
            f"sha256:{config.get('sha256')}"
            if config.get("scope") == "effective"
            else config.get("scope")
        )
        if payload.get("config_hash") != expected_hash:
            errors.append(
                f"{label}.evidence fixture config_hash does not match capability"
            )
    errors.extend(_private_strings(payload, f"{label}.evidence fixture"))


def validate_matrix(
    matrix_path: Path,
    *,
    root: Path,
    today: date | None = None,
    require_evidence: bool = False,
) -> list[str]:
    """Return all validation errors; an empty list means the matrix is valid."""

    errors: list[str] = []
    today = today or date.today()
    matrix = _load_json(matrix_path, "capability matrix", errors)
    if not isinstance(matrix, dict):
        if matrix is not None:
            errors.append("capability matrix must be a JSON object")
        return errors

    for field in sorted(TOP_LEVEL_FIELDS - matrix.keys()):
        errors.append(f"matrix missing {field}")
    if matrix.get("schema_version") != 1:
        errors.append("matrix schema_version must be 1")
    if matrix.get("runtime") != "codex":
        errors.append("matrix runtime must be 'codex'")
    cli_version = matrix.get("cli_version")
    if not isinstance(cli_version, str) or not VERSION_RE.fullmatch(cli_version):
        errors.append("matrix cli_version must be a semantic x.y.z version")
        cli_version = "invalid"
    _parse_date(matrix.get("matrix_version"), "matrix.matrix_version", errors)

    expected_root = f"specs/codex-support/evidence/codex-{cli_version}"
    evidence_root = _relative_repo_path(
        matrix.get("evidence_root"), "matrix.evidence_root", errors
    )
    if evidence_root is not None and evidence_root != expected_root:
        errors.append(f"matrix.evidence_root must be {expected_root!r}")

    supported_platforms = matrix.get("supported_platforms")
    if not isinstance(supported_platforms, list) or not supported_platforms:
        errors.append("matrix.supported_platforms must be a non-empty list")
    elif any(
        not isinstance(platform, str) or not PLATFORM_RE.fullmatch(platform)
        for platform in supported_platforms
    ):
        errors.append("matrix.supported_platforms contains an invalid platform label")

    capabilities = matrix.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        errors.append("matrix.capabilities must be a non-empty list")
        return errors

    seen: set[str] = set()
    for index, capability in enumerate(capabilities):
        label = f"capabilities[{index}]"
        if not isinstance(capability, dict):
            errors.append(f"{label} must be an object")
            continue
        for field in sorted(CAPABILITY_FIELDS - capability.keys()):
            errors.append(f"{label} missing {field}")

        capability_id = capability.get("id")
        if not isinstance(capability_id, str) or not ID_RE.fullmatch(capability_id):
            errors.append(f"{label}.id is invalid")
        elif capability_id in seen:
            errors.append(f"{label}.id duplicate: {capability_id}")
        else:
            seen.add(capability_id)
            label = f"capability {capability_id}"

        area = capability.get("area")
        if area not in ALLOWED_AREAS:
            errors.append(f"{label}.area unsupported: {area!r}")
        target = capability.get("support_target")
        if target not in ALLOWED_TARGETS:
            errors.append(f"{label}.support_target unsupported: {target!r}")
        if not isinstance(capability.get("load_bearing"), bool):
            errors.append(f"{label}.load_bearing must be boolean")
        status = capability.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{label}.status unsupported: {status!r}")
        evidence_level = capability.get("evidence_level")
        if evidence_level not in ALLOWED_EVIDENCE:
            errors.append(f"{label}.evidence_level unsupported: {evidence_level!r}")

        platforms = capability.get("platforms")
        if not isinstance(platforms, list) or not platforms:
            errors.append(f"{label}.platforms must be a non-empty list")
        elif any(
            not isinstance(platform, str) or not PLATFORM_RE.fullmatch(platform)
            for platform in platforms
        ):
            errors.append(f"{label}.platforms contains an invalid label")

        source_kind = _validate_source(
            capability.get("source"), label, today=today, errors=errors
        )
        _validate_config(capability.get("config"), label, errors)

        owner = capability.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            errors.append(f"{label}.owner must be non-empty")
        exit_condition = capability.get("exit_condition")
        evidence_path = capability.get("evidence_path")

        if evidence_level == "unknown":
            if status != "unknown":
                errors.append(
                    f"{label}: unknown evidence cannot claim status {status!r}"
                )
            if source_kind != "unavailable":
                errors.append(
                    f"{label}: unknown evidence requires source.kind 'unavailable'"
                )
            if not isinstance(exit_condition, str) or not exit_condition.strip():
                errors.append(
                    f"{label}.exit_condition must own how the unknown will close"
                )
            if evidence_path is not None:
                errors.append(
                    f"{label}.evidence_path must be null for unknown evidence"
                )
        else:
            if exit_condition is not None:
                errors.append(
                    f"{label}.exit_condition must be null unless evidence is unknown"
                )
            if evidence_level == "documented":
                if source_kind != "official-documentation":
                    errors.append(
                        f"{label}: documented evidence requires official documentation"
                    )
                if evidence_path is not None:
                    errors.append(
                        f"{label}.evidence_path must be null for documented evidence"
                    )
            if evidence_level == "observed":
                if source_kind != "captured-fixture":
                    errors.append(
                        f"{label}: observed evidence requires a captured fixture source"
                    )
                relative = _relative_repo_path(
                    evidence_path, f"{label}.evidence_path", errors
                )
                if relative is not None:
                    expected_prefix = f"{expected_root}/"
                    if not relative.startswith(expected_prefix):
                        errors.append(
                            f"{label}.evidence_path must be version-pinned under {expected_prefix}"
                        )
                    else:
                        _validate_fixture(
                            root / relative,
                            label,
                            matrix=matrix,
                            capability=capability,
                            errors=errors,
                        )

        if (
            require_evidence
            and capability.get("load_bearing") is True
            and evidence_level == "documented"
        ):
            errors.append(
                f"{label}: load-bearing documented claim needs observed evidence or explicit unknown"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("--require-evidence", action="store_true")
    parser.add_argument("--today", type=date.fromisoformat, default=None)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    matrix_path = args.matrix
    if not matrix_path.is_absolute():
        matrix_path = repo_root / matrix_path
    errors = validate_matrix(
        matrix_path,
        root=repo_root,
        today=args.today,
        require_evidence=args.require_evidence,
    )
    if errors:
        for error in errors:
            print(f"codex-capabilities: {error}", file=sys.stderr)
        print(f"codex-capabilities: {len(errors)} problem(s)", file=sys.stderr)
        return 1
    print(f"codex-capabilities: {args.matrix} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
