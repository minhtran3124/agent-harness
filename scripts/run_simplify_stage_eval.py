#!/usr/bin/env python3
"""Collect immutable `/simplify` shadow-eval evidence in disposable worktrees.

The runner deliberately never opens fixture ``truth.json`` files. Those files are
reserved for the separate scorer so expected answers cannot leak into collection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, NamedTuple, Sequence


HEX_SHA = re.compile(r"^[0-9a-f]{40}$")
CLIENT_VERSION = re.compile(r"\b(\d+\.\d+\.\d+)\b")


class CollectionError(RuntimeError):
    """A collection contract or orchestration failure."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_immutable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content)
    except FileExistsError as exc:
        raise CollectionError(
            f"refusing to overwrite first-run artifact: {path}"
        ) from exc


def _write_bytes_immutable(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(content)
    except FileExistsError as exc:
        raise CollectionError(
            f"refusing to overwrite first-run artifact: {path}"
        ) from exc


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=True,
        check=False,
    )


def _git(cwd: Path, *arguments: str, check: bool = True) -> str:
    completed = _run(["git", *arguments], cwd=cwd)
    if check and completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise CollectionError(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout


def _copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise CollectionError(f"fixture tree is missing: {source}")
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        target = destination / relative
        if path.is_symlink():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(os.readlink(path))
        elif path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def _fixture_digest(fixture: Path) -> str:
    """Hash collection inputs while intentionally excluding scorer-only truth."""
    digest = hashlib.sha256()
    inputs = [fixture / "fixture.json"]
    for dirname in ("base", "candidate"):
        root = fixture / dirname
        inputs.extend(path for path in root.rglob("*") if path.is_file())
    for path in sorted(inputs):
        if not path.is_file() and not path.is_symlink():
            raise CollectionError(f"fixture input is missing: {path}")
        digest.update(str(path.relative_to(fixture)).encode())
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(b"symlink\0")
            digest.update(os.readlink(path).encode())
        else:
            digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def evaluation_input_digest(fixtures: Path) -> str:
    """Bind executable eval code, schema, and public fixture inputs."""
    source_root = Path(__file__).resolve().parent.parent
    inputs: list[tuple[str, Path]] = [
        ("scripts/run_simplify_stage_eval.py", Path(__file__).resolve()),
        (
            "scripts/score_simplify_stage_eval.py",
            Path(__file__).with_name("score_simplify_stage_eval.py").resolve(),
        ),
        (
            "evals/skills/simplify-stage/schema.json",
            (
                source_root / "evals" / "skills" / "simplify-stage" / "schema.json"
            ).resolve(),
        ),
    ]
    scoring = fixtures / "scoring.json"
    if scoring.is_file():
        inputs.append(("fixtures/scoring.json", scoring))
    for fixture in sorted(
        path
        for path in fixtures.iterdir()
        if path.is_dir() and (path / "fixture.json").is_file()
    ):
        inputs.append(
            (f"fixtures/{fixture.name}/fixture.json", fixture / "fixture.json")
        )
        for dirname in ("base", "candidate"):
            root = fixture / dirname
            for path in sorted(root.rglob("*")):
                if path.is_file() or path.is_symlink():
                    inputs.append(
                        (
                            f"fixtures/{fixture.name}/{dirname}/"
                            f"{path.relative_to(root).as_posix()}",
                            path,
                        )
                    )
    digest = hashlib.sha256()
    for label, path in inputs:
        if not path.is_file() and not path.is_symlink():
            raise CollectionError(f"evaluation input is missing: {label}")
        digest.update(label.encode())
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(b"symlink\0")
            digest.update(os.readlink(path).encode())
        else:
            digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _load_manifest(fixture: Path) -> dict[str, Any]:
    path = fixture / "fixture.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CollectionError(f"invalid fixture manifest {path}: {exc}") from exc
    if manifest.get("schema_version") != 1:
        raise CollectionError(f"{path}: schema_version must be 1")
    if manifest.get("case_id") != fixture.name:
        raise CollectionError(f"{path}: case_id must match directory name")
    for field in ("verification_commands", "final_review_commands"):
        commands = manifest.get(field)
        if not isinstance(commands, list) or not commands:
            raise CollectionError(f"{path}: {field} must be a non-empty command list")
        if any(
            not isinstance(command, list)
            or not command
            or any(not isinstance(part, str) or not part for part in command)
            for command in commands
        ):
            raise CollectionError(f"{path}: {field} contains an invalid command")
    remove_paths = manifest.get("remove_paths", [])
    if not isinstance(remove_paths, list) or any(
        not isinstance(path, str) or not path for path in remove_paths
    ):
        raise CollectionError(f"{path}: remove_paths must contain relative paths")
    for remove_path in remove_paths:
        validate_remove_path(remove_path)
    return manifest


def validate_remove_path(raw: str) -> PurePosixPath:
    if (
        not raw
        or raw == "."
        or "\\" in raw
        or "\0" in raw
        or raw.startswith("/")
        or raw.endswith("/")
    ):
        raise CollectionError(f"unsafe remove_path: {raw!r}")
    path = PurePosixPath(raw)
    if path.is_absolute() or path.as_posix() != raw:
        raise CollectionError(f"remove_path must be canonical and relative: {raw!r}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise CollectionError(f"remove_path contains traversal: {raw!r}")
    return path


def _remove_fixture_path(worktree: Path, raw: str) -> None:
    relative = validate_remove_path(raw)
    target = worktree.joinpath(*relative.parts)
    if target.is_symlink():
        target.unlink()
        return
    root = worktree.resolve()
    resolved = target.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise CollectionError(f"remove_path escapes worktree: {raw!r}") from exc
    if target.is_dir():
        shutil.rmtree(target)
    elif target.exists():
        target.unlink()


class HeadState(NamedTuple):
    resolved: str
    symbolic: str
    git_pointer: bytes


def capture_head_state(worktree: Path) -> HeadState:
    resolved = _git(worktree, "rev-parse", "HEAD").strip()
    symbolic_result = _run(["git", "symbolic-ref", "-q", "HEAD"], cwd=worktree)
    if symbolic_result.returncode not in {0, 1}:
        raise CollectionError(
            f"unable to resolve symbolic HEAD: {symbolic_result.stderr}"
        )
    git_marker = worktree / ".git"
    pointer = git_marker.read_bytes() if git_marker.is_file() else b""
    return HeadState(resolved, symbolic_result.stdout.strip(), pointer)


def assert_head_unchanged(worktree: Path, expected: HeadState) -> None:
    actual = capture_head_state(worktree)
    if actual.resolved != expected.resolved:
        raise CollectionError(
            f"resolved HEAD moved: expected {expected.resolved}, got {actual.resolved}"
        )
    if actual.symbolic != expected.symbolic:
        raise CollectionError(
            f"symbolic HEAD moved: expected {expected.symbolic!r}, "
            f"got {actual.symbolic!r}"
        )
    if actual.git_pointer != expected.git_pointer:
        raise CollectionError("worktree .git pointer changed")


def _parse_claude_stream(
    raw: str,
) -> tuple[str, dict[str, Any], list[str], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    for number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CollectionError(
                f"invalid Claude stream-json event at line {number}: {exc}"
            ) from exc
        if not isinstance(event, dict):
            raise CollectionError(f"Claude stream event {number} is not an object")
        events.append(event)
    result_text = ""
    usage: dict[str, Any] = {}
    skill_names: list[str] = []
    skill_uses: list[tuple[str, str]] = []
    tool_results: dict[str, list[bool]] = {}
    for event in events:
        if event.get("type") == "result":
            result = event.get("result")
            event_usage = event.get("usage")
            result_text = result if isinstance(result, str) else result_text
            usage = event_usage if isinstance(event_usage, dict) else usage
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result":
                result_id = block.get("tool_use_id")
                if isinstance(result_id, str):
                    tool_results.setdefault(result_id, []).append(
                        block.get("is_error") is True
                    )
                continue
            if event.get("type") != "assistant" or block.get("type") != "tool_use":
                continue
            tool_id = block.get("id")
            if not isinstance(tool_id, str) or not tool_id:
                tool_id = "<invalid>"
            if block.get("name") != "Skill":
                continue
            tool_input = block.get("input")
            skill = tool_input.get("skill") if isinstance(tool_input, dict) else None
            normalized_skill = skill if isinstance(skill, str) else "<invalid>"
            skill_names.append(normalized_skill)
            skill_uses.append((tool_id, normalized_skill))
    evidence: list[dict[str, Any]] = []
    for tool_id, skill in skill_uses:
        results = tool_results.get(tool_id, [])
        if len(results) != 1:
            status = "missing" if not results else "duplicate"
        elif results[0]:
            status = "error"
        else:
            status = "success"
        evidence.append(
            {
                "tool_use_id": tool_id,
                "skill": skill,
                "result_count": len(results),
                "result_status": status,
            }
        )
    return result_text, usage, skill_names, evidence


def _sandbox_quote(path: Path) -> str:
    return json.dumps(str(path.resolve()))


def _claude_scratch_root() -> Path:
    return Path(f"/tmp/claude-{os.getuid()}")


def _sandbox_profile(
    *,
    worktree: Path,
    git_dir: Path,
    git_common_dir: Path,
    runtime: Path,
    client: Path,
    source_root: Path,
    fixture: Path,
    output_parent: Path,
) -> str:
    home = Path.home()
    auth_roots = [client.parent]
    claude_scratch_root = _claude_scratch_root()
    protected_roots = {
        source_root.resolve(),
        fixture.resolve(),
        output_parent.resolve(),
    }
    allowed_roots = {
        worktree.resolve(),
        git_dir.resolve(),
        git_common_dir.resolve(),
        runtime.resolve(),
        client.parent.resolve(),
        claude_scratch_root.resolve(),
        *(path.resolve() for path in auth_roots if path.exists()),
    }
    system_read_roots = {
        Path("/System/Library"),
        Path("/System/Cryptexes"),
        Path("/System/Volumes/Preboot/Cryptexes"),
        Path("/usr"),
        Path("/bin"),
        Path("/sbin"),
        Path("/Library"),
        Path("/private/etc"),
        Path("/private/var/db"),
        Path("/private/var/run"),
        Path("/dev"),
    }
    for protected in protected_roots:
        for allowed in allowed_roots:
            if (
                protected == allowed
                or protected in allowed.parents
                or allowed in protected.parents
            ):
                raise CollectionError(
                    "sandbox protected/allowed roots overlap: "
                    f"protected={protected}, allowed={allowed}"
                )

    def aliases(path: Path) -> set[Path]:
        resolved = path.resolve()
        values = {resolved}
        if str(resolved).startswith(("/Users/", "/private/")):
            values.add(Path("/System/Volumes/Data") / str(resolved).lstrip("/"))
        return values

    protected_filters = " ".join(
        f"(subpath {_sandbox_quote(alias)})"
        for root in protected_roots
        for alias in aliases(root)
    )
    home_exception_paths = {
        alias for path in auth_roots if path.exists() for alias in aliases(path)
    }
    home_exceptions = " ".join(
        (
            f"(literal {_sandbox_quote(path)})"
            if path.is_file()
            else f"(subpath {_sandbox_quote(path)})"
        )
        for path in home_exception_paths
    )
    home_filters = " ".join(
        f"(subpath {_sandbox_quote(path)})" for path in aliases(home)
    )
    readable_roots = {
        alias
        for root in allowed_roots | system_read_roots
        if root.exists()
        for alias in aliases(root)
    }
    read_exceptions = " ".join(
        f"(require-not (subpath {_sandbox_quote(path)}))" for path in readable_roots
    )
    safe_devices = {
        Path("/dev/null"),
        Path("/dev/zero"),
        Path("/dev/urandom"),
        Path("/dev/random"),
        Path("/dev/tty"),
    }
    write_exceptions = (
        " ".join(
            f"(require-not (subpath {_sandbox_quote(path)}))"
            for path in (
                worktree,
                runtime,
                claude_scratch_root,
                git_dir,
                git_common_dir,
            )
        )
        + " "
        + " ".join(
            f"(require-not (literal {_sandbox_quote(path)}))" for path in safe_devices
        )
    )
    return (
        "(version 1)\n"
        "(allow default)\n"
        "(allow file-read-metadata)\n"
        f"(deny file-read* (require-any {protected_filters}))\n"
        "(deny file-read-data (require-all "
        "(vnode-type REGULAR-FILE) "
        f"{read_exceptions}))\n"
        "(deny file-read* (require-all "
        f"(require-any {home_filters}) "
        f"(require-not (require-any {home_exceptions}))))\n"
        f"(deny file-write* (require-all {write_exceptions}))\n"
        f"(deny file-write* (literal {_sandbox_quote(worktree / '.git')}))\n"
    )


def _resolve_auth_environment() -> dict[str, str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return {"ANTHROPIC_API_KEY": api_key}
    oauth_token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if oauth_token:
        return {"CLAUDE_CODE_OAUTH_TOKEN": oauth_token}
    if sys.platform != "darwin":
        raise CollectionError(
            "candidate collection requires ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN"
        )
    security = subprocess.Popen(
        [
            "/usr/bin/security",
            "find-generic-password",
            "-s",
            "Claude Code-credentials",
            "-w",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert security.stdout is not None
    plutil = subprocess.Popen(
        [
            "/usr/bin/plutil",
            "-extract",
            "claudeAiOauth.accessToken",
            "raw",
            "-o",
            "-",
            "-",
        ],
        stdin=security.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    security.stdout.close()
    token_bytes, _ = plutil.communicate()
    security_returncode = security.wait()
    if security_returncode or plutil.returncode:
        raise CollectionError("unable to extract Claude OAuth access token")
    token = token_bytes.decode("utf-8", errors="strict").strip()
    if not token:
        raise CollectionError("Claude OAuth access token is empty")
    return {"CLAUDE_CODE_OAUTH_TOKEN": token}


def _sandbox_environment(
    runtime: Path,
    client: Path,
    auth_environment: dict[str, str],
) -> dict[str, str]:
    allowed_keys = {
        "LANG",
        "LC_ALL",
        "USER",
        "LOGNAME",
        "HOME",
    }
    env = {key: value for key, value in os.environ.items() if key in allowed_keys}
    env.update(auth_environment)
    system_path = ["/usr/bin", "/bin", "/usr/sbin", "/sbin", str(client.parent)]
    env.update(
        {
            "PATH": os.pathsep.join(system_path),
            "TMPDIR": str(runtime),
            "XDG_CACHE_HOME": str(runtime / "cache"),
            "CLAUDE_CONFIG_DIR": str(runtime / "claude-config"),
            "NO_COLOR": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }
    )
    return env


def _commands(
    commands: list[list[str]],
    *,
    worktree: Path,
    fixture: Path,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    replacements = {
        "{worktree}": str(worktree),
        "{fixture}": str(fixture),
    }
    for raw_command in commands:
        command = [replacements.get(part, part) for part in raw_command]
        started = time.monotonic()
        completed = _run(command, cwd=worktree)
        results.append(
            {
                "command": command,
                "returncode": completed.returncode,
                "elapsed_seconds": round(time.monotonic() - started, 6),
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
    return results


def _diff_stats(worktree: Path, pre_sha: str, post_sha: str) -> dict[str, int]:
    if pre_sha == post_sha:
        return {"simplify_added_lines": 0, "simplify_removed_lines": 0}
    added = 0
    removed = 0
    for line in _git(worktree, "diff", "--numstat", pre_sha, post_sha).splitlines():
        parts = line.split("\t", 2)
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            added += int(parts[0])
            removed += int(parts[1])
    return {
        "simplify_added_lines": added,
        "simplify_removed_lines": removed,
    }


def _artifact(
    *,
    output_parent: Path,
    path: Path,
    content: str | bytes,
) -> dict[str, str]:
    if isinstance(content, bytes):
        _write_bytes_immutable(path, content)
    else:
        _write_immutable(path, content)
    return {
        "path": str(path.relative_to(output_parent)),
        "sha256": sha256_file(path),
    }


def _collect_case(
    *,
    fixture: Path,
    output_parent: Path,
    run_id: str,
    mode: str,
    claude: str,
    model: str,
    source_root: Path,
    auth_environment: dict[str, str],
) -> dict[str, Any]:
    manifest = _load_manifest(fixture)
    case_id = manifest["case_id"]
    with tempfile.TemporaryDirectory(prefix=f"simplify-eval-{case_id}-") as temp:
        temp_root = Path(temp)
        seed = temp_root / "seed"
        worktree = temp_root / "worktree"
        seed.mkdir()
        _git(seed, "init", "-q", "-b", "main")
        _git(seed, "config", "user.name", "Simplify Eval")
        _git(seed, "config", "user.email", "simplify-eval@example.invalid")
        _git(seed, "config", "commit.gpgsign", "false")
        _copy_tree(fixture / "base", seed)
        _git(seed, "add", "-A")
        _git(seed, "commit", "-q", "-m", "fixture base")
        base_sha = _git(seed, "rev-parse", "HEAD").strip()
        _git(seed, "worktree", "add", "-q", "-b", f"fixture-{case_id}", str(worktree))

        for relative in manifest.get("remove_paths", []):
            _remove_fixture_path(worktree, relative)
        _copy_tree(fixture / "candidate", worktree)
        _git(worktree, "add", "-A")
        if _git(worktree, "status", "--porcelain").strip():
            _git(worktree, "commit", "-q", "-m", "fixture candidate")
        pre_sha = _git(worktree, "rev-parse", "HEAD").strip()
        head_state = capture_head_state(worktree)
        pre_patch = _git(worktree, "diff", "--binary", base_sha, pre_sha)

        prompt = (
            "Use Claude Code's bundled Skill tool to invoke `simplify` exactly once. "
            "Inspect the cumulative branch diff at the explicit target "
            f"{base_sha}..{pre_sha}. Apply only behavior-preserving cleanup in this "
            "isolated worktree that is unambiguous and low-risk. For a reuse/DRY "
            "consolidation, apply it only when the duplicated code encodes a real "
            "shared rule or nontrivial computation that could drift out of sync if "
            "left duplicated; skip it when the reuse target is just a trivial "
            "one-line delegation to a builtin/stdlib call with no rule of its own, "
            "since coupling to it would not reduce real complexity. When in doubt, "
            "leave the code as-is. Do not commit, and return a concise outcome "
            "summary. Do not search outside this repository."
        )
        claude_command = [
            claude,
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--no-session-persistence",
            "--safe-mode",
            "--model",
            model,
            "--dangerously-skip-permissions",
        ]
        transcript_path = output_parent / "transcripts" / run_id / f"{case_id}.json"
        transcript_artifact: dict[str, str] | None = None
        if mode == "candidate":
            sandbox = shutil.which("sandbox-exec")
            if not sandbox:
                raise CollectionError(
                    "candidate collection requires macOS sandbox-exec; "
                    "no safe filesystem sandbox is available"
                )
            resolved_client = Path(shutil.which(claude) or claude).resolve()
            if not resolved_client.is_file():
                raise CollectionError(f"Claude client is not a file: {resolved_client}")
            claude_command[0] = str(resolved_client)
            runtime = temp_root / "runtime"
            runtime.mkdir()
            (runtime / "claude-config").mkdir()
            _claude_scratch_root().mkdir(parents=True, exist_ok=True)
            git_dir_text = _git(worktree, "rev-parse", "--git-dir").strip()
            git_dir = Path(git_dir_text)
            if not git_dir.is_absolute():
                git_dir = (worktree / git_dir).resolve()
            git_common_dir_text = _git(
                worktree, "rev-parse", "--git-common-dir"
            ).strip()
            git_common_dir = Path(git_common_dir_text)
            if not git_common_dir.is_absolute():
                git_common_dir = (worktree / git_common_dir).resolve()
            profile = runtime / "sandbox.sb"
            profile.write_text(
                _sandbox_profile(
                    worktree=worktree,
                    git_dir=git_dir,
                    git_common_dir=git_common_dir,
                    runtime=runtime,
                    client=resolved_client,
                    source_root=source_root,
                    fixture=fixture.parent,
                    output_parent=output_parent,
                ),
                encoding="utf-8",
            )
            sandboxed_command = [sandbox, "-f", str(profile), *claude_command]
            sandbox_env = _sandbox_environment(
                runtime,
                resolved_client,
                auth_environment,
            )
            auth_check = _run(
                [
                    sandbox,
                    "-f",
                    str(profile),
                    str(resolved_client),
                    "--safe-mode",
                    "auth",
                    "status",
                    "--json",
                ],
                cwd=worktree,
                env=sandbox_env,
            )
            try:
                auth_status = json.loads(auth_check.stdout)
            except json.JSONDecodeError:
                auth_status = {}
            if (
                auth_check.returncode
                or not isinstance(auth_status, dict)
                or auth_status.get("loggedIn") is not True
            ):
                raise CollectionError(
                    f"{case_id}: Claude auth preflight failed inside sandbox "
                    f"(returncode={auth_check.returncode})"
                )
            started = time.monotonic()
            completed = _run(
                sandboxed_command,
                cwd=worktree,
                env=sandbox_env,
            )
            elapsed = round(time.monotonic() - started, 6)
            (
                result_text,
                usage,
                observed_skills,
                skill_evidence,
            ) = _parse_claude_stream(completed.stdout)
            successful_skill = skill_evidence[0] if len(skill_evidence) == 1 else None
            claude_result = {
                "invocations": 1,
                "command": [part for part in sandboxed_command if part != prompt],
                "returncode": completed.returncode,
                "elapsed_seconds": elapsed,
                "result": result_text,
                "usage": usage,
                "observed_skill_invocations": observed_skills,
                "skill_tool_evidence": successful_skill,
            }
            transcript_payload = {
                "case_id": case_id,
                "command": sandboxed_command,
                "cwd": str(worktree),
                "returncode": completed.returncode,
                "elapsed_seconds": elapsed,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "result": result_text,
                "usage": usage,
                "observed_skill_invocations": observed_skills,
                "skill_tool_evidence": (
                    successful_skill
                    if successful_skill is not None
                    else {"observations": skill_evidence}
                ),
            }
            transcript_artifact = _artifact(
                output_parent=output_parent,
                path=transcript_path,
                content=json.dumps(transcript_payload, indent=2) + "\n",
            )
            if observed_skills != ["simplify"]:
                raise CollectionError(
                    f"{case_id}: expected exactly one bundled simplify Skill tool-use; "
                    f"observed {observed_skills}; returncode={completed.returncode}; "
                    f"stderr={completed.stderr.strip()!r}"
                )
            if (
                successful_skill is None
                or successful_skill["result_count"] != 1
                or successful_skill["result_status"] != "success"
            ):
                raise CollectionError(
                    f"{case_id}: simplify Skill tool-use requires exactly one "
                    "matching successful tool_result; "
                    f"observed {skill_evidence}"
                )
            assert_head_unchanged(worktree, head_state)
        else:
            claude_result = {
                "invocations": 0,
                "command": [],
                "returncode": 0,
                "elapsed_seconds": 0.0,
                "result": "advisory baseline: simplify not invoked",
                "usage": {},
                "observed_skill_invocations": [],
                "skill_tool_evidence": None,
            }
            transcript_payload = {
                "case_id": case_id,
                "command": [],
                "cwd": str(worktree),
                "returncode": 0,
                "elapsed_seconds": 0.0,
                "stdout": "",
                "stderr": "",
                "result": "advisory baseline: simplify not invoked",
                "usage": {},
                "observed_skill_invocations": [],
                "skill_tool_evidence": None,
            }

        _git(worktree, "add", "-A")
        simplify_patch = _git(
            worktree,
            "diff",
            "--cached",
            "--binary",
            "--find-renames",
            pre_sha,
            "--",
        )
        if _git(worktree, "status", "--porcelain").strip():
            _git(worktree, "commit", "-q", "-m", "captured simplify mutation")
            post_sha = _git(worktree, "rev-parse", "HEAD").strip()
            outcome = "changed"
        else:
            post_sha = pre_sha
            outcome = "no_op"
        post_patch = _git(worktree, "diff", "--binary", base_sha, post_sha)
        changed_files = (
            _git(worktree, "diff", "--name-only", pre_sha, post_sha).splitlines()
            if post_sha != pre_sha
            else []
        )

        verification = _commands(
            manifest["verification_commands"],
            worktree=worktree,
            fixture=fixture,
        )
        final_review = _commands(
            manifest["final_review_commands"],
            worktree=worktree,
            fixture=fixture,
        )
        artifact_base = output_parent / "artifacts" / run_id / case_id
        artifact_base.mkdir(parents=True, exist_ok=False)
        if transcript_artifact is None:
            transcript_artifact = _artifact(
                output_parent=output_parent,
                path=transcript_path,
                content=json.dumps(transcript_payload, indent=2) + "\n",
            )
        bundle_path = artifact_base / "history.bundle"
        bundle_result = _run(
            ["git", "bundle", "create", str(bundle_path), "HEAD"],
            cwd=worktree,
        )
        if bundle_result.returncode:
            raise CollectionError(
                f"{case_id}: unable to create history bundle: "
                f"{bundle_result.stderr.strip()}"
            )
        artifacts = {
            "pre_diff": _artifact(
                output_parent=output_parent,
                path=artifact_base / "pre.patch",
                content=pre_patch,
            ),
            "simplify_diff": _artifact(
                output_parent=output_parent,
                path=artifact_base / "simplify.patch",
                content=simplify_patch,
            ),
            "post_diff": _artifact(
                output_parent=output_parent,
                path=artifact_base / "post.patch",
                content=post_patch,
            ),
            "transcript": transcript_artifact,
            "checks": _artifact(
                output_parent=output_parent,
                path=artifact_base / "checks.json",
                content=json.dumps(
                    {
                        "case_id": case_id,
                        "verification": verification,
                        "final_review": final_review,
                    },
                    indent=2,
                )
                + "\n",
            ),
            "history_bundle": {
                "path": str(bundle_path.relative_to(output_parent)),
                "sha256": sha256_file(bundle_path),
            },
        }
        return {
            "case_id": case_id,
            "fixture_digest": _fixture_digest(fixture),
            "worktree": str(worktree),
            "base_sha": base_sha,
            "pre_sha": pre_sha,
            "post_sha": post_sha,
            "outcome": outcome,
            "changed_files": sorted(changed_files),
            "diff_stats": _diff_stats(worktree, pre_sha, post_sha),
            "claude": claude_result,
            "verification": verification,
            "final_review": final_review,
            "artifacts": artifacts,
        }


def validate_result(result: dict[str, Any]) -> None:
    """Validate the collection shape without a third-party schema dependency."""
    if result.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    if result.get("mode") not in {"advisory", "candidate"}:
        raise ValueError("mode must be advisory or candidate")
    collected_at = result.get("collected_at")
    if not isinstance(collected_at, str):
        raise ValueError("collected_at must be a date-time string")
    try:
        datetime.fromisoformat(collected_at)
    except ValueError as exc:
        raise ValueError("collected_at must be an ISO date-time") from exc
    if not HEX_SHA.fullmatch(str(result.get("source_commit_sha", ""))):
        raise ValueError("source_commit_sha must be a full lowercase SHA")
    if not re.fullmatch(r"[0-9a-f]{64}", str(result.get("input_digest", ""))):
        raise ValueError("input_digest must be SHA-256")
    environment = result.get("environment")
    if not isinstance(environment, dict):
        raise ValueError("environment must be an object")
    for key in ("client_version", "expected_client_version", "model"):
        if not isinstance(environment.get(key), str) or not environment[key]:
            raise ValueError(f"environment.{key} must be a non-empty string")
    for key in ("client_version", "expected_client_version"):
        if not re.fullmatch(r"\d+\.\d+\.\d+", environment[key]):
            raise ValueError(f"environment.{key} must be a semantic version")
    records = result.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("record must be an object")
        case_id = record.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in seen:
            raise ValueError("record case_id must be unique and non-empty")
        seen.add(case_id)
        if not re.fullmatch(r"[0-9a-f]{64}", str(record.get("fixture_digest", ""))):
            raise ValueError(f"{case_id}.fixture_digest must be SHA-256")
        if not isinstance(record.get("worktree"), str) or not record["worktree"]:
            raise ValueError(f"{case_id}.worktree must be non-empty")
        for field in ("base_sha", "pre_sha", "post_sha"):
            if not HEX_SHA.fullmatch(str(record.get(field, ""))):
                raise ValueError(f"{case_id}.{field} must be a full lowercase SHA")
        if record.get("outcome") not in {"changed", "no_op"}:
            raise ValueError(f"{case_id}.outcome is invalid")
        changed_files = record.get("changed_files")
        if (
            not isinstance(changed_files, list)
            or any(not isinstance(path, str) or not path for path in changed_files)
            or len(changed_files) != len(set(changed_files))
        ):
            raise ValueError(f"{case_id}.changed_files must be a list")
        if record["outcome"] == "no_op" and (
            record["pre_sha"] != record["post_sha"] or changed_files
        ):
            raise ValueError(f"{case_id}: no_op contradicts SHAs or changed_files")
        if record["outcome"] == "changed" and (
            record["pre_sha"] == record["post_sha"] or not changed_files
        ):
            raise ValueError(f"{case_id}: changed contradicts SHAs or changed_files")
        stats = record.get("diff_stats")
        if not isinstance(stats, dict) or any(
            not isinstance(stats.get(key), int) or stats[key] < 0
            for key in ("simplify_added_lines", "simplify_removed_lines")
        ):
            raise ValueError(f"{case_id}.diff_stats is invalid")
        claude = record.get("claude")
        if not isinstance(claude, dict):
            raise ValueError(f"{case_id}.claude must be an object")
        required_invocations = 1 if result["mode"] == "candidate" else 0
        expected_skills = ["simplify"] if result["mode"] == "candidate" else []
        evidence = claude.get("skill_tool_evidence")
        evidence_valid = (
            isinstance(evidence, dict)
            and isinstance(evidence.get("tool_use_id"), str)
            and bool(evidence["tool_use_id"])
            and evidence.get("skill") == "simplify"
            and evidence.get("result_count") == 1
            and evidence.get("result_status") == "success"
        )
        if (
            claude.get("invocations") != required_invocations
            or claude.get("observed_skill_invocations") != expected_skills
            or (
                not evidence_valid
                if result["mode"] == "candidate"
                else evidence is not None
            )
            or not isinstance(claude.get("returncode"), int)
            or not isinstance(claude.get("elapsed_seconds"), (int, float))
            or claude["elapsed_seconds"] < 0
            or not isinstance(claude.get("command"), list)
            or not isinstance(claude.get("result"), str)
            or not isinstance(claude.get("usage"), dict)
        ):
            raise ValueError(f"{case_id}.claude is invalid")
        for field in ("verification", "final_review"):
            checks = record.get(field)
            if not isinstance(checks, list) or not checks:
                raise ValueError(f"{case_id}.{field} must be a non-empty list")
            if any(
                not isinstance(item, dict)
                or not isinstance(item.get("command"), list)
                or not item["command"]
                or not isinstance(item.get("returncode"), int)
                or not isinstance(item.get("elapsed_seconds"), (int, float))
                or item["elapsed_seconds"] < 0
                or not isinstance(item.get("stdout"), str)
                or not isinstance(item.get("stderr"), str)
                for item in checks
            ):
                raise ValueError(f"{case_id}.{field} has an invalid returncode")
        artifacts = record.get("artifacts")
        if not isinstance(artifacts, dict) or set(artifacts) != {
            "pre_diff",
            "simplify_diff",
            "post_diff",
            "transcript",
            "checks",
            "history_bundle",
        }:
            raise ValueError(f"{case_id}.artifacts is incomplete")
        for artifact in artifacts.values():
            if not isinstance(artifact.get("path"), str) or not re.fullmatch(
                r"[0-9a-f]{64}", str(artifact.get("sha256", ""))
            ):
                raise ValueError(f"{case_id} has an invalid artifact descriptor")


def collect(
    *,
    mode: str,
    fixtures: Path,
    output: Path,
    claude: str,
    expected_client_version: str,
    model: str,
    source_commit: str,
) -> dict[str, Any]:
    fixtures = fixtures.resolve()
    output = output.resolve()
    if os.sep in claude or (os.altsep and os.altsep in claude):
        claude = str(Path(claude).resolve())
    if output.exists():
        raise CollectionError(f"refusing to overwrite first-run result: {output}")
    if not HEX_SHA.fullmatch(source_commit):
        raise CollectionError("--source-commit must be a full lowercase SHA")
    source_result = _run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path.cwd(),
    )
    if source_result.returncode:
        raise CollectionError("runner must execute from a Git source checkout")
    source_root = Path(source_result.stdout.strip()).resolve()
    resolved_source = _run(
        ["git", "rev-parse", f"{source_commit}^{{commit}}"],
        cwd=source_root,
    )
    current_head = _git(source_root, "rev-parse", "HEAD").strip()
    if (
        resolved_source.returncode
        or resolved_source.stdout.strip() != source_commit
        or current_head != source_commit
    ):
        raise CollectionError(
            "source commit must resolve to a commit and equal source checkout HEAD"
        )
    version_result = _run([claude, "--version"], cwd=Path.cwd())
    if version_result.returncode:
        raise CollectionError(
            f"unable to query Claude Code version: {version_result.stderr.strip()}"
        )
    match = CLIENT_VERSION.search(version_result.stdout)
    if not match:
        raise CollectionError("unable to parse Claude Code client version")
    client_version = match.group(1)
    if client_version != expected_client_version:
        raise CollectionError(
            "client version mismatch: "
            f"expected {expected_client_version}, got {client_version}"
        )
    fixture_dirs = sorted(
        path
        for path in fixtures.iterdir()
        if path.is_dir() and (path / "fixture.json").is_file()
    )
    if not fixture_dirs:
        raise CollectionError(f"no fixtures found under {fixtures}")
    input_digest = evaluation_input_digest(fixtures)
    run_id = re.sub(r"[^a-zA-Z0-9_.-]+", "-", output.stem)
    artifact_root = output.parent / "artifacts" / run_id
    transcript_root = output.parent / "transcripts" / run_id
    for root in (artifact_root, transcript_root):
        if root.exists():
            raise CollectionError(f"refusing to overwrite first-run artifacts: {root}")
    auth_environment = _resolve_auth_environment() if mode == "candidate" else {}
    records = [
        _collect_case(
            fixture=fixture,
            output_parent=output.parent,
            run_id=run_id,
            mode=mode,
            claude=claude,
            model=model,
            source_root=source_root,
            auth_environment=auth_environment,
        )
        for fixture in fixture_dirs
    ]
    result = {
        "schema_version": 1,
        "mode": mode,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source_commit_sha": source_commit,
        "input_digest": input_digest,
        "environment": {
            "client_version": client_version,
            "expected_client_version": expected_client_version,
            "model": model,
        },
        "records": records,
    }
    validate_result(result)
    _write_immutable(output, json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("advisory", "candidate"), required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--claude", default="claude")
    parser.add_argument("--expected-client-version", required=True)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--source-commit")
    args = parser.parse_args()
    try:
        source_commit = args.source_commit
        if source_commit is None:
            source_commit = _git(Path.cwd(), "rev-parse", "HEAD").strip()
        collect(
            mode=args.mode,
            fixtures=args.fixtures,
            output=args.output,
            claude=args.claude,
            expected_client_version=args.expected_client_version,
            model=args.model,
            source_commit=source_commit,
        )
    except (CollectionError, OSError, ValueError) as exc:
        print(f"simplify-stage-eval: {exc}", file=sys.stderr)
        return 1
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
