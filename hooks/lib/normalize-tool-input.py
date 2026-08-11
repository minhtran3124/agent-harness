#!/usr/bin/env python3
"""Normalize Claude/Codex hook JSON into one conservative, path-set contract."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

PATCH_PATH_RE = re.compile(
    r"^\*\*\* (?:Add|Update|Delete) File: (?P<path>.+)$|^\*\*\* Move to: (?P<move>.+)$"
)
PATCH_CONTROL_RE = re.compile(r"^\*\*\* ")
# A patch program is recognised by a `*** Begin Patch` line anywhere, not only at offset 0:
# a single leading newline must not turn an edit into a "shell command with no paths",
# which a path-set consumer would read as a successful empty edit.
PATCH_PROGRAM_RE = re.compile(r"^\*\*\* Begin Patch\s*$", re.MULTILINE)
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")


def _base(runtime: str = "unknown", event: str = "unknown") -> dict[str, Any]:
    return {
        "schema_version": 1,
        "runtime": runtime,
        "event": event,
        "tool_class": "unknown",
        "status": "unknown",
        "paths": [],
        "command": None,
        "prompt": None,
        "outcome": None,
        "diagnostics": [],
    }


def _runtime(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("turn_id"), str):
        return "codex"
    if isinstance(payload.get("session_id"), str):
        return "claude"
    return "unknown"


def _safe_relative(raw: Any, root: Path) -> tuple[str | None, str | None]:
    if not isinstance(raw, str) or not raw.strip():
        return None, "empty-path"
    value = raw.strip()
    if "\x00" in value:
        return None, "nul-path"
    if WINDOWS_ABSOLUTE_RE.match(value):
        return None, "outside-root"
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=False)
        relative = resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return None, "outside-root"
    if not relative.parts or relative == Path("."):
        return None, "repository-root-path"
    return relative.as_posix(), None


def _normalize_paths(values: list[Any], root: Path) -> tuple[list[str], list[str]]:
    paths: set[str] = set()
    diagnostics: list[str] = []
    for value in values:
        normalized, error = _safe_relative(value, root)
        if normalized is not None:
            paths.add(normalized)
        elif error is not None:
            diagnostics.append(f"unsafe-path:{error}")
    return sorted(paths), sorted(set(diagnostics))


def _patch_paths(command: str) -> tuple[list[str], list[str]]:
    values: list[str] = []
    diagnostics: list[str] = []
    lines = command.splitlines()
    if not lines or lines[0].strip() != "*** Begin Patch":
        diagnostics.append("patch-missing-begin")
    if not lines or lines[-1].strip() != "*** End Patch":
        diagnostics.append("patch-missing-end")
    for line in lines:
        match = PATCH_PATH_RE.match(line)
        if match:
            values.append(match.group("path") or match.group("move"))
        elif PATCH_CONTROL_RE.match(line) and line not in {
            "*** Begin Patch",
            "*** End Patch",
            "*** End of File",
        }:
            diagnostics.append("patch-unparsed-control")
    if not values:
        diagnostics.append("patch-no-paths")
    return values, sorted(set(diagnostics))


def normalize(payload: Any, root: Path) -> dict[str, Any]:
    root = root.resolve()
    if not isinstance(payload, dict):
        result = _base()
        result["diagnostics"] = ["payload-not-object"]
        return result

    runtime = _runtime(payload)
    event = payload.get("hook_event_name")
    if not isinstance(event, str) or not event:
        event = "unknown"
    result = _base(runtime, event)
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    response = payload.get("tool_response")
    if isinstance(response, dict):
        outcome: dict[str, Any] = {"present": True}
        for key in ("exit_code", "success", "status"):
            value = response.get(key)
            if isinstance(value, (str, int, bool)) or value is None:
                if key in response:
                    outcome[key] = value
        result["outcome"] = outcome
    elif response is not None:
        result["outcome"] = {"present": True}

    if event == "UserPromptSubmit" or "prompt" in payload:
        result["tool_class"] = "prompt"
        prompt = payload.get("prompt")
        if isinstance(prompt, str) and prompt:
            result["prompt"] = prompt
            result["status"] = "known"
        else:
            result["diagnostics"] = ["prompt-missing"]
        return result

    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str):
        tool_name = ""
    command = tool_input.get("command")

    looks_like_patch = isinstance(command, str) and bool(
        PATCH_PROGRAM_RE.search(command)
    )

    if tool_name in {"Bash", "exec_command"} or (
        not tool_name and isinstance(command, str) and not looks_like_patch
    ):
        result["tool_class"] = "shell"
        if isinstance(command, str) and command:
            result["command"] = command
            result["status"] = "known"
        else:
            result["diagnostics"] = ["command-missing"]
        return result

    file_value = tool_input.get("file_path")
    if file_value is None and isinstance(payload.get("tool_response"), dict):
        file_value = payload["tool_response"].get("filePath")
    is_edit = (
        tool_name in {"apply_patch", "Edit", "Write"}
        or file_value is not None
        or (not tool_name and looks_like_patch)
    )
    if is_edit:
        result["tool_class"] = "edit"
        raw_paths: list[Any] = []
        diagnostics: list[str] = []
        if tool_name == "apply_patch" or (not tool_name and isinstance(command, str)):
            if isinstance(command, str) and command:
                raw_paths, diagnostics = _patch_paths(command)
            else:
                diagnostics.append("command-missing")
        elif file_value is not None:
            raw_paths.append(file_value)
        else:
            diagnostics.append("file-path-missing")
        paths, path_diagnostics = _normalize_paths(raw_paths, root)
        result["paths"] = paths
        result["diagnostics"] = sorted(set(diagnostics + path_diagnostics))
        if paths and not result["diagnostics"]:
            result["status"] = "known"
        elif paths:
            result["status"] = "partial"
        return result

    result["tool_class"] = "other" if tool_name else "unknown"
    result["diagnostics"] = ["unsupported-tool" if tool_name else "tool-missing"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd(),
        type=Path,
    )
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        result = _base()
        result["diagnostics"] = [f"malformed-json:{exc.__class__.__name__}"]
    else:
        result = normalize(payload, args.root)
    json.dump(result, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
