#!/usr/bin/env python3
"""Persist and validate sanitized Codex runtime-mode diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

MODES = {"enforced", "advisory", "unsupported"}
EVIDENCE_ID_RE = re.compile(r"^codex-mode-[0-9a-f]{16}$")
REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
STATE_RELATIVE = Path(".harness-state/codex-runtime.json")
FINGERPRINT_KEYS = ("install_hash", "config_hash", "cli_version", "trust_hash")


class RuntimeModeError(ValueError):
    """Raised when runtime-mode state is malformed or unsafe."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def hash_json(value: Any) -> str:
    return _digest(_canonical(value))


def _hash_files(rows: list[tuple[str, Path]]) -> str:
    digest = hashlib.sha256()
    for label, path in sorted(rows):
        digest.update(label.encode())
        digest.update(b"\0")
        if path.is_file():
            digest.update(path.read_bytes())
        else:
            digest.update(b"<missing>")
        digest.update(b"\0")
    return digest.hexdigest()


def install_hash(root: Path) -> str:
    """Hash only harness-owned install state, never unrelated project files."""
    root = root.resolve()
    state = root / ".codex/.agent-harness"
    manifest_path = state / "deployment-manifest.json"
    rows = [("deployment-manifest.json", manifest_path)]
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError):
            manifest = {}
        project_files = manifest.get("project_files", {})
        if isinstance(project_files, dict):
            for relative in project_files:
                path = Path(relative)
                if not path.is_absolute() and ".." not in path.parts:
                    rows.append((f"project/{path.as_posix()}", root / path))
    marketplace = state / "marketplace"
    if marketplace.is_dir():
        for path in marketplace.rglob("*"):
            if path.is_file() and not path.is_symlink():
                rows.append(
                    (
                        "marketplace/" + path.relative_to(marketplace).as_posix(),
                        path,
                    )
                )
    return _hash_files(rows)


def config_hash(root: Path, codex_home: Path | None = None) -> str:
    rows = [("project-config", root.resolve() / ".codex/config.toml")]
    if codex_home is not None:
        rows.append(("user-config", codex_home.resolve() / "config.toml"))
    return _hash_files(rows)


def make_fingerprint(
    root: Path,
    *,
    cli_version: str,
    trust: Any,
    codex_home: Path | None = None,
) -> dict[str, str]:
    return {
        "install_hash": install_hash(root),
        "config_hash": config_hash(root, codex_home),
        "cli_version": cli_version,
        "trust_hash": hash_json(trust),
    }


def _validate_fingerprint(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != set(FINGERPRINT_KEYS):
        raise RuntimeModeError("input_fingerprint must contain the four stable keys")
    if not all(isinstance(value[key], str) and value[key] for key in FINGERPRINT_KEYS):
        raise RuntimeModeError("input_fingerprint values must be non-empty strings")
    return {key: value[key] for key in FINGERPRINT_KEYS}


def make_record(
    *,
    mode: str,
    reason_codes: list[str],
    fingerprint: dict[str, str],
    observed_at: str,
    evidence_expires_at: str | None,
    diagnostic_summary: dict[str, str],
) -> dict[str, Any]:
    if mode not in MODES:
        raise RuntimeModeError(f"unknown runtime mode: {mode}")
    reasons = sorted(set(reason_codes))
    if any(not REASON_RE.fullmatch(reason) for reason in reasons):
        raise RuntimeModeError("reason codes must use the stable uppercase vocabulary")
    fingerprint = _validate_fingerprint(fingerprint)
    summary = dict(sorted(diagnostic_summary.items()))
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in summary.items()):
        raise RuntimeModeError("diagnostic_summary must contain strings only")
    identity = {
        "mode": mode,
        "reason_codes": reasons,
        "input_fingerprint": fingerprint,
        "observed_at": observed_at,
        "evidence_expires_at": evidence_expires_at,
        "diagnostic_summary": summary,
    }
    return {
        "schema_version": 1,
        "runtime": "codex",
        **identity,
        "evidence_id": f"codex-mode-{hash_json(identity)[:16]}",
        "valid": True,
    }


def validate_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise RuntimeModeError("runtime-mode record must be an object")
    if record.get("schema_version") != 1 or record.get("runtime") != "codex":
        raise RuntimeModeError("unsupported runtime-mode record")
    if record.get("mode") not in MODES:
        raise RuntimeModeError("runtime-mode record has an invalid mode")
    evidence_id = record.get("evidence_id")
    if not isinstance(evidence_id, str) or not EVIDENCE_ID_RE.fullmatch(evidence_id):
        raise RuntimeModeError("runtime-mode record has an invalid evidence id")
    reasons = record.get("reason_codes")
    if not isinstance(reasons, list) or any(
        not isinstance(reason, str) or not REASON_RE.fullmatch(reason)
        for reason in reasons
    ):
        raise RuntimeModeError("runtime-mode record has invalid reason codes")
    if reasons != sorted(set(reasons)):
        raise RuntimeModeError("runtime-mode reason codes must be sorted and unique")
    fingerprint = _validate_fingerprint(record.get("input_fingerprint"))
    observed_at = record.get("observed_at")
    expires_at = record.get("evidence_expires_at")
    if not isinstance(observed_at, str) or not observed_at:
        raise RuntimeModeError("runtime-mode record has an invalid observation date")
    if expires_at is not None and (not isinstance(expires_at, str) or not expires_at):
        raise RuntimeModeError("runtime-mode record has an invalid expiry date")
    summary = record.get("diagnostic_summary")
    if not isinstance(summary, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in summary.items()
    ):
        raise RuntimeModeError("runtime-mode record has an invalid diagnostic summary")
    identity = {
        "mode": record["mode"],
        "reason_codes": reasons,
        "input_fingerprint": fingerprint,
        "observed_at": observed_at,
        "evidence_expires_at": expires_at,
        "diagnostic_summary": summary,
    }
    if evidence_id != f"codex-mode-{hash_json(identity)[:16]}":
        raise RuntimeModeError("runtime-mode evidence id does not match its contents")
    if record.get("valid") is not True:
        raise RuntimeModeError("persisted runtime-mode records must be valid diagnoses")
    return record


def state_path(root: Path) -> Path:
    return root.resolve() / STATE_RELATIVE


def persist_record(root: Path, record: dict[str, Any]) -> Path:
    validate_record(record)
    destination = state_path(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile("w", dir=destination.parent, delete=False) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    os.replace(temporary, destination)
    return destination


def load_record(root: Path) -> dict[str, Any] | None:
    path = state_path(root)
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text())
        return validate_record(value)
    except (OSError, json.JSONDecodeError, RuntimeModeError):
        return None


def invalidate_if_changed(
    record: dict[str, Any], current_fingerprint: dict[str, str]
) -> dict[str, Any]:
    validate_record(record)
    current = _validate_fingerprint(current_fingerprint)
    changed = [
        key
        for key in FINGERPRINT_KEYS
        if record["input_fingerprint"][key] != current[key]
    ]
    if not changed:
        return record
    reasons = sorted(set(record["reason_codes"]) | {"STATE_INVALIDATED"})
    return {
        **record,
        "mode": "advisory",
        "reason_codes": reasons,
        "valid": False,
        "invalidated_by": changed,
    }


def local_fingerprint_for_record(root: Path, record: dict[str, Any]) -> dict[str, str]:
    """Refresh observable file hashes without pretending to re-diagnose CLI/trust."""
    cached = _validate_fingerprint(record["input_fingerprint"])
    return {
        **cached,
        "install_hash": install_hash(root),
        "config_hash": config_hash(root),
    }


def context_line(root: Path, limit: int = 500) -> str:
    record = load_record(root)
    if record is None:
        return ""
    effective = invalidate_if_changed(record, local_fingerprint_for_record(root, record))
    reasons = ",".join(effective["reason_codes"][:6]) or "none"
    text = (
        f"[codex runtime] mode={effective['mode']} evidence={effective['evidence_id']} "
        f"reasons={reasons}; cached outside-hook diagnosis — run "
        "scripts/codex_harness_doctor.py to refresh"
    )
    return text[:limit]


def update_summary_metadata(path: Path, mode: str, evidence_id: str) -> None:
    if mode not in MODES or not EVIDENCE_ID_RE.fullmatch(evidence_id):
        raise RuntimeModeError("invalid SUMMARY runtime metadata")
    text = path.read_text()
    rows = {
        "Runtime-mode": mode,
        "Runtime-evidence-id": evidence_id,
    }
    for field, value in rows.items():
        pattern = re.compile(rf"^{re.escape(field)}:\s*.*$", re.MULTILINE)
        replacement = f"{field}: {value}"
        if pattern.search(text):
            text = pattern.sub(replacement, text, count=1)
        else:
            anchor = re.search(r"^Input-type:.*$", text, re.MULTILINE)
            if anchor:
                text = text[: anchor.end()] + "\n" + replacement + text[anchor.end() :]
            else:
                text = replacement + "\n" + text
    path.write_text(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    context = sub.add_parser("context")
    context.add_argument("--root", type=Path, default=Path.cwd())
    context.add_argument("--limit", type=int, default=500)
    args = parser.parse_args(argv)
    if args.command == "context":
        line = context_line(args.root, max(1, min(args.limit, 1000)))
        if line:
            print(line)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
