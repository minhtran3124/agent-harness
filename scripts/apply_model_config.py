#!/usr/bin/env python3
"""Apply harness-models.json model/effort settings to deployed agent and skill frontmatter.

Writes only `<claude-dir>/agents/<role>.md` and `<claude-dir>/skills/<name>/SKILL.md` for the
roles and skills named in the defaults snapshot. It never writes any settings file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

USER_FILE = "harness-models.json"
MODEL_ALIASES = {"opus", "sonnet", "haiku", "fable", "inherit"}
MODEL_ID = re.compile(r"^claude-[a-z0-9.-]+$")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
REVIEW_ROLES = {"reviewer", "task-reviewer"}
REVIEW_EFFORT_FLOOR = "medium"
FIELDS = ("model", "effort")
ANCHORS = ("description", "tools", "model")
ENV_OVERRIDES = (
    "CLAUDE_CODE_EFFORT_LEVEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL_FORCE",
)


class SnapshotError(ValueError):
    """Raised when the defaults snapshot is missing or unreadable."""


def load_snapshot(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"cannot read defaults snapshot {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SnapshotError(f"defaults snapshot {path} is not a JSON object")
    for kind in ("agents", "skills"):
        entries = data.get(kind, {})
        if not isinstance(entries, dict) or not all(
            isinstance(entry, dict) for entry in entries.values()
        ):
            raise SnapshotError(f"defaults snapshot {path}: {kind} is malformed")
    return data


def validate_user(data, snapshot: dict) -> list[str]:
    if not isinstance(data, dict):
        return [f"{USER_FILE} must contain a JSON object"]
    errors = []
    for key in data:
        if key not in ("schema_version", "agents", "skills"):
            errors.append(f"unknown top-level key {key!r}")
    if "schema_version" in data:
        version = data["schema_version"]
        if type(version) is not int or version != 1:
            errors.append(f"unsupported schema_version {version!r}")
    for kind, label in (("agents", "role"), ("skills", "skill")):
        entries = data.get(kind, {})
        if not isinstance(entries, dict):
            errors.append(f"{kind} must be an object")
            continue
        for name, entry in entries.items():
            where = f"{kind}.{name}"
            if name not in snapshot.get(kind, {}):
                errors.append(f"{where}: unknown {label} {name!r}")
                continue
            if not isinstance(entry, dict):
                errors.append(f"{where}: entry must be an object")
                continue
            for field, value in entry.items():
                if field not in FIELDS:
                    errors.append(
                        f"{where}: unknown key {field!r} (allowed: model, effort)"
                    )
                elif not isinstance(value, str):
                    errors.append(
                        f"{where}.{field}: value must be a string, got {value!r}"
                    )
                elif field == "model" and not (
                    value in MODEL_ALIASES or MODEL_ID.match(value)
                ):
                    errors.append(f"{where}.model: invalid model {value!r}")
                elif field == "effort" and value not in EFFORTS:
                    errors.append(
                        f"{where}.effort: invalid effort {value!r} (allowed: {', '.join(EFFORTS)})"
                    )
    return errors


def merge(snapshot: dict, user: dict) -> list[tuple[str, dict, frozenset]]:
    """Return (target, effective values, fields the user file sets) per role and skill."""
    rows = []
    for kind in ("agents", "skills"):
        overrides = user.get(kind, {})
        for name in sorted(snapshot.get(kind, {})):
            values = {f: snapshot[kind][name].get(f) for f in FIELDS}
            entry = overrides.get(name, {})
            values.update({f: entry[f] for f in FIELDS if f in entry})
            target = (
                f"agents/{name}.md" if kind == "agents" else f"skills/{name}/SKILL.md"
            )
            rows.append((target, values, frozenset(f for f in FIELDS if f in entry)))
    return rows


def floor_errors(rows: list[tuple[str, dict, frozenset]]) -> list[str]:
    errors = []
    for target, values, _ in rows:
        role = (
            target[len("agents/") : -len(".md")]
            if target.startswith("agents/")
            else None
        )
        effort = values.get("effort")
        if (
            role in REVIEW_ROLES
            and effort in EFFORTS
            and EFFORTS.index(effort) < EFFORTS.index(REVIEW_EFFORT_FLOOR)
        ):
            errors.append(
                f"agents.{role}.effort: {effort!r} is below the review floor "
                f"{REVIEW_EFFORT_FLOOR!r}"
            )
    return errors


def load(args) -> tuple[list[tuple[str, dict, bool]], list[str]]:
    """Load and validate everything. Raises SnapshotError; returns (rows, errors)."""
    snapshot = load_snapshot(args.defaults)
    user_path = args.project_root / USER_FILE
    user = {}
    if user_path.exists():
        try:
            user = json.loads(user_path.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return [], [f"{USER_FILE}: cannot read or parse: {exc}"]
        errors = validate_user(user, snapshot)
        if errors:
            return [], errors
    rows = merge(snapshot, user)
    return rows, floor_errors(rows)


def rewrite(text: str, values: dict) -> str:
    """Set or delete the model/effort frontmatter lines; keep every other byte."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ValueError("missing frontmatter")
    end = next(
        (i for i in range(1, len(lines)) if lines[i].rstrip("\r\n") == "---"), None
    )
    if end is None:
        raise ValueError("unclosed frontmatter")

    def key_of(line: str) -> str | None:
        return None if line[:1].isspace() else line.split(":", 1)[0].strip()

    for field in FIELDS:
        value = values.get(field)
        found = [i for i in range(1, end) if key_of(lines[i]) == field]
        if value is None:
            for i in reversed(found):
                del lines[i]
                end -= 1
        elif found:
            line = lines[found[0]]
            eol = line[len(line.rstrip("\r\n")) :]
            lines[found[0]] = f"{field}: {value}{eol}"
        else:
            anchors = [i for i in range(1, end) if key_of(lines[i]) in ANCHORS]
            pos = anchors[-1] + 1 if anchors else end
            while pos < end and lines[pos][:1].isspace():
                pos += 1
            lines.insert(pos, f"{field}: {value}\n")
            end += 1
    return "".join(lines)


def write_atomic(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(text.encode("utf-8"))
        os.chmod(tmp, path.stat().st_mode & 0o7777)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def apply(claude_dir: Path, rows) -> dict:
    """Plan every write, then write. Returns a result report."""
    result = {"written": [], "missing": [], "errors": [], "failed": None}
    plan = []
    for target, values, _ in rows:
        path = claude_dir / target
        if not path.is_file():
            result["missing"].append(target)
            continue
        try:
            text = path.read_bytes().decode("utf-8")
            new = rewrite(text, values)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            result["errors"].append(f"{target}: {exc}")
            continue
        if new != text:
            plan.append((target, path, new))
    if result["errors"]:
        return result
    for target, path, new in plan:
        try:
            write_atomic(path, new)
        except OSError as exc:
            result["failed"] = f"{target}: {exc}"
            break
        result["written"].append(target)
    return result


def show(rows) -> None:
    print(
        f"{'target':<40} {'model':<20} {'model-source':<20} {'effort':<8} effort-source"
    )
    for target, values, user_fields in rows:
        if not any(values.values()):
            continue
        model_source, effort_source = (
            USER_FILE if f in user_fields else "default" for f in ("model", "effort")
        )
        model = values.get("model") or "-"
        effort = values.get("effort") or "-"
        print(
            f"{target:<40} {model:<20} {model_source:<20} {effort:<8} {effort_source}"
        )
    for name in ENV_OVERRIDES:
        if os.environ.get(name):
            print(f"warning: {name} is set; it overrides the configured values")


def hook_output(line: str, reload_skills: bool = False) -> None:
    output = {"hookEventName": "SessionStart", "additionalContext": line}
    if reload_skills:
        output["reloadSkills"] = True
    print(json.dumps({"hookSpecificOutput": output}, separators=(",", ":")))


def run_hook(args) -> int:
    try:
        source = json.loads(sys.stdin.read()).get("source")
    except (ValueError, AttributeError):
        return 0
    if source not in ("startup", "clear"):
        return 0
    try:
        rows, errors = load(args)
    except SnapshotError:
        return 0
    if errors:
        hook_output(
            f"harness-models: {USER_FILE} is invalid, so the last applied values stay "
            f"({'; '.join(errors)}). Run /harness-models check."
        )
        return 0
    result = apply(args.claude_dir, rows)
    reload_skills = any(t.startswith("skills/") for t in result["written"])
    if result["errors"]:
        hook_output(
            f"harness-models: nothing applied ({'; '.join(result['errors'])}). "
            "Run /harness-models check."
        )
    elif result["failed"]:
        hook_output(
            f"harness-models: partial apply, {len(result['written'])} file(s) written, "
            f"failed {result['failed']}. Run /harness-models apply.",
            reload_skills,
        )
    elif result["written"]:
        hook_output(
            f"harness-models: applied model/effort to {len(result['written'])} file(s).",
            reload_skills,
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    for name in ("show", "check", "apply", "hook"):
        mode.add_argument(f"--{name}", dest="mode", action="store_const", const=name)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--claude-dir", type=Path)
    parser.add_argument("--defaults", type=Path)
    args = parser.parse_args(argv)
    args.mode = args.mode or "show"
    args.claude_dir = args.claude_dir or args.project_root / ".claude"
    args.defaults = args.defaults or args.claude_dir / "harness-models.defaults.json"

    if args.mode == "hook":
        try:
            return run_hook(args)
        except Exception as exc:  # noqa: BLE001 - the hook never blocks a session
            hook_output(
                f"harness-models: hook error ({exc}). Run /harness-models check."
            )
            return 0

    try:
        rows, errors = load(args)
    except SnapshotError as exc:
        print(f"error: {exc}")
        return 1
    for error in errors:
        print(f"error: {error}")
    if errors:
        return 1
    if args.mode == "show":
        show(rows)
        return 0
    if args.mode == "check":
        print(f"ok: {USER_FILE} is valid")
        return 0

    result = apply(args.claude_dir, rows)
    for target in result["missing"]:
        print(f"missing target {target}")
    for error in result["errors"]:
        print(f"error: {error}")
    for target in result["written"]:
        print(f"wrote {target}")
    if result["errors"]:
        return 1
    if result["failed"]:
        print(f"failed {result['failed']}")
        print(
            f"partial apply: {len(result['written'])} file(s) written; fix the cause and re-run"
        )
        return 1
    print(f"{len(result['written'])} file(s) written")
    if result["written"]:
        print("Skill changes apply at the next invocation of that skill.")
        print("Agent changes apply from the next session in headless runs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
