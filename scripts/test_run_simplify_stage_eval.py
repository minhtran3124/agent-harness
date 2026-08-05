from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


SCRIPT = Path(__file__).with_name("run_simplify_stage_eval.py")
SPEC = importlib.util.spec_from_file_location("run_simplify_stage_eval", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_fixture(root: Path, *, failing_checks: bool = False) -> Path:
    fixture = root / "fixtures" / "reuse-helper"
    (fixture / "base").mkdir(parents=True)
    (fixture / "candidate").mkdir()
    (fixture / "base" / "app.py").write_text(
        "def total(values):\n    return sum(values)\n",
        encoding="utf-8",
    )
    (fixture / "candidate" / "app.py").write_text(
        "def total(values):\n"
        "    copied = [value for value in values]\n"
        "    return sum(copied)\n",
        encoding="utf-8",
    )
    expected = "99" if failing_checks else "6"
    manifest = {
        "schema_version": 1,
        "case_id": "reuse-helper",
        "verification_commands": [
            [
                sys.executable,
                "-c",
                (f"import app; assert app.total([1, 2, 3]) == {expected}"),
            ]
        ],
        "final_review_commands": [
            [sys.executable, "-c", "import app; assert callable(app.total)"]
        ],
    }
    (fixture / "fixture.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    # Deliberately invalid JSON and secret-bearing: collection must never read it.
    (fixture / "truth.json").write_text(
        "SECRET_TRUTH_MUST_NOT_REACH_CLAUDE {",
        encoding="utf-8",
    )
    return fixture


def _sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def _fake_claude_sh(
    *,
    version: str,
    skill_names: tuple[str, ...],
    attempts: list[str],
    readable: list[str],
    forbidden_write: Path | None,
    forbidden_exec: Path | None,
    tool_results: tuple[tuple[str, bool], ...],
    auth_logged_in: bool,
) -> str:
    """A POSIX-sh fake Claude client.

    Deliberately NOT a `#!/usr/bin/python3` script: on macOS that path is the
    Xcode stub, which shells out to `xcrun` and dlopens libxcrun from
    /Applications/Xcode*.app. The Seatbelt profile does not grant /Applications
    (correctly — the real Node client never needs Xcode), so the stub dies before
    emitting anything and every candidate test fails with an opaque
    "auth preflight failed (returncode=1)". /bin/sh is a real binary under an
    already-allowed read root, so it runs wherever the sandbox runs.

    Trade-off: sh sets PWD/OLDPWD itself, so those two cannot be checked here.
    The Python flavor keeps that assertion — see
    test_python_client_env_is_fully_scrubbed.
    """
    lines = [
        "#!/bin/sh",
        'for arg in "$@"; do',
        '  [ "$arg" = "--version" ] && { printf %s\\\\n '
        + _sh_quote(f"{version} (Claude Code)")
        + "; exit 0; }",
        "done",
        'case " $* " in',
        '  *\\ auth\\ *) case " $* " in *\\ status\\ *) printf %s\\\\n '
        + _sh_quote(
            json.dumps(
                {"loggedIn": auth_logged_in, "authMethod": "oauth_token"},
            )
        )
        + "; exit 0;; esac;;",
        "esac",
        # sh recreates PWD/OLDPWD, so only the env vars it does not synthesize
        # are checkable from a shell client.
        "for key in PYTHONPATH VIRTUAL_ENV GIT_DIR; do",
        '  eval "value=\\${$key-}"',
        '  [ -n "$value" ] && { echo "unscrubbed path env: $key" >&2; exit 1; }',
        "done",
    ]
    for path in attempts:
        lines.append(
            f"if cat {_sh_quote(path)} >/dev/null 2>&1; then "
            f'echo "sandbox allowed forbidden read: {path}" >&2; exit 1; fi'
        )
    for path in readable:
        lines.append(
            f"if ! head -c 1 {_sh_quote(path)} >/dev/null 2>&1; then "
            f'echo "sandbox denied an allowed read: {path}" >&2; exit 1; fi'
        )
    if forbidden_write:
        lines.append(
            f"if echo escaped > {_sh_quote(str(forbidden_write))} 2>/dev/null; then "
            'echo "sandbox allowed forbidden write" >&2; exit 1; fi'
        )
    if forbidden_exec:
        lines.append(
            f"if {_sh_quote(str(forbidden_exec))} -h >/dev/null 2>&1 </dev/null; then "
            'echo "sandbox allowed forbidden process-exec" >&2; exit 1; fi'
        )
    # Same mutation the Python flavor performs: collapse the copied-list helper
    # into a direct sum, line for line.
    lines += [
        "sed -e '/^    copied = \\[value for value in values\\]$/d' "
        "-e 's/^    return sum(copied)$/    return sum(values)/' "
        "app.py > app.py.tmp && mv app.py.tmp app.py",
    ]
    for index, skill in enumerate(skill_names):
        payload = json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": f"skill-{index}",
                            "name": "Skill",
                            "input": {"skill": skill},
                        }
                    ]
                },
            }
        )
        lines.append("printf %s\\\\n " + _sh_quote(payload))
    for tool_id, is_error in tool_results:
        payload = json.dumps(
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "is_error": is_error,
                            "content": "done",
                        }
                    ]
                },
            }
        )
        lines.append("printf %s\\\\n " + _sh_quote(payload))
    lines.append(
        "printf %s\\\\n "
        + _sh_quote(
            json.dumps(
                {
                    "type": "result",
                    "result": "simplified",
                    "usage": {"input_tokens": 5, "output_tokens": 7},
                }
            )
        )
    )
    return "\n".join(lines) + "\n"


def write_fake_claude(
    root: Path,
    *,
    version: str = "2.1.220",
    skill_names: tuple[str, ...] = ("simplify",),
    forbidden_reads: tuple[Path, ...] = (),
    allowed_reads: tuple[Path, ...] = (),
    forbidden_write: Path | None = None,
    forbidden_exec: Path | None = None,
    tool_results: tuple[tuple[str, bool], ...] | None = None,
    auth_logged_in: bool = True,
    flavor: str = "sh",
) -> Path:
    fake = root / "fake-claude"
    attempts = [str(path) for path in forbidden_reads]
    readable = [str(path) for path in allowed_reads]
    if tool_results is None:
        tool_results = tuple(
            (f"skill-{index}", False) for index, _ in enumerate(skill_names)
        )
    if flavor == "sh":
        fake.write_text(
            _fake_claude_sh(
                version=version,
                skill_names=skill_names,
                attempts=attempts,
                readable=readable,
                forbidden_write=forbidden_write,
                forbidden_exec=forbidden_exec,
                tool_results=tool_results,
                auth_logged_in=auth_logged_in,
            ),
            encoding="utf-8",
        )
        fake.chmod(0o755)
        return fake
    fake.write_text(
        "#!/usr/bin/python3\n"
        "import json, os, pathlib, subprocess, sys\n"
        "if '--version' in sys.argv:\n"
        f"    print('{version} (Claude Code)')\n"
        "    raise SystemExit(0)\n"
        "if 'auth' in sys.argv and 'status' in sys.argv:\n"
        f"    print(json.dumps({{'loggedIn': {auth_logged_in!r}, "
        f"'authMethod': 'oauth_token'}}))\n"
        "    raise SystemExit(0)\n"
        "for forbidden_key in ('PWD', 'OLDPWD', 'PYTHONPATH', 'VIRTUAL_ENV', 'GIT_DIR'):\n"
        "    if forbidden_key in os.environ:\n"
        "        raise SystemExit('unscrubbed path env: ' + forbidden_key)\n"
        f"for forbidden in {attempts!r}:\n"
        "    try:\n"
        "        pathlib.Path(forbidden).read_bytes()\n"
        "    except (OSError, PermissionError):\n"
        "        pass\n"
        "    else:\n"
        "        raise SystemExit('sandbox allowed forbidden read: ' + forbidden)\n"
        f"for readable in {readable!r}:\n"
        "    with pathlib.Path(readable).open('rb') as handle:\n"
        "        handle.read(1)\n"
        + (
            f"try:\n    pathlib.Path({str(forbidden_write)!r}).write_text('escaped')\n"
            "except (OSError, PermissionError):\n    pass\n"
            "else:\n    raise SystemExit('sandbox allowed forbidden write')\n"
            if forbidden_write
            else ""
        )
        + (
            f"try:\n    subprocess.run([{str(forbidden_exec)!r}, '-h'], "
            "stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, "
            "stderr=subprocess.DEVNULL, check=False)\n"
            "except (OSError, PermissionError):\n    pass\n"
            "else:\n    raise SystemExit('sandbox allowed forbidden process-exec')\n"
            if forbidden_exec
            else ""
        )
        + "path = pathlib.Path.cwd() / 'app.py'\n"
        "text = path.read_text()\n"
        "path.write_text(text.replace("
        '"    copied = [value for value in values]\\n'
        '    return sum(copied)\\n", '
        '"    return sum(values)\\n"))\n'
        f"for index, skill in enumerate({skill_names!r}):\n"
        "    print(json.dumps({'type': 'assistant', 'message': {'content': "
        "[{'type': 'tool_use', 'id': 'skill-' + str(index), 'name': 'Skill', "
        "'input': {'skill': skill}}]}}))\n"
        f"for tool_id, is_error in {tool_results!r}:\n"
        "    print(json.dumps({'type': 'user', 'message': {'content': "
        "[{'type': 'tool_result', 'tool_use_id': tool_id, "
        "'is_error': is_error, 'content': 'done'}]}}))\n"
        "print(json.dumps({'type': 'result', 'result': 'simplified', "
        "'usage': {'input_tokens': 5, 'output_tokens': 7}}))\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    return fake


def invoke(
    fixtures: Path,
    output: Path,
    fake_claude: Path,
    *,
    expected_version: str = "2.1.220",
    source_commit: str | None = None,
) -> subprocess.CompletedProcess[str]:
    # Candidate collection is macOS-only by design: the runner refuses to run
    # without Seatbelt rather than fall back to an unsandboxed client
    # ("candidate collection requires macOS sandbox-exec"). Asserting success on
    # a platform the code deliberately does not support is a test bug, so gate
    # here — the single choke point every candidate test funnels through, which
    # cannot drift as tests are added. Same precedent as the genuine-Seatbelt
    # probe below.
    if sys.platform != "darwin" or not shutil.which("sandbox-exec"):
        pytest.skip("candidate collection requires macOS sandbox-exec")
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--mode",
            "candidate",
            "--fixtures",
            str(fixtures),
            "--output",
            str(output),
            "--claude",
            str(fake_claude),
            "--expected-client-version",
            expected_version,
            "--source-commit",
            source_commit or source_sha(),
        ],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "CLAUDE_CODE_OAUTH_TOKEN": "test-oauth-token"},
    )


def source_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=SCRIPT.parent.parent,
        text=True,
    ).strip()


def artifact_path(output: Path, artifact: dict[str, str]) -> Path:
    return output.parent / artifact["path"]


def test_candidate_isolated_collection_hides_truth_and_captures_evidence(tmp_path):
    fixture = write_fixture(tmp_path)
    fake_root = tmp_path / "client"
    fake_root.mkdir()
    forbidden_output = tmp_path / "results" / "escaped"
    fake = write_fake_claude(
        fake_root,
        forbidden_reads=(
            fixture / "truth.json",
            SCRIPT.parent.parent / "CLAUDE.md",
            Path.home() / ".claude.json",
            Path.home() / ".claude" / "settings.json",
            Path.home() / "Library" / "Keychains" / "metadata.keychain-db",
            Path.home() / "Library" / "Keychains" / "login.keychain-db",
            Path("/System/Volumes/Data")
            / str(Path.home() / ".claude.json").lstrip("/"),
            Path("/System/Volumes/Data")
            / str(Path.home() / "Library" / "Keychains" / "login.keychain-db").lstrip(
                "/"
            ),
        ),
        forbidden_write=forbidden_output,
    )
    original = (fixture / "candidate" / "app.py").read_text(encoding="utf-8")
    output = tmp_path / "results" / "candidate.json"

    completed = invoke(fixture.parent, output, fake)

    assert completed.returncode == 0, completed.stderr
    result = json.loads(output.read_text(encoding="utf-8"))
    MODULE.validate_result(result)
    record = result["records"][0]
    assert record["outcome"] == "changed"
    assert record["changed_files"] == ["app.py"]
    assert record["claude"]["returncode"] == 0
    assert record["claude"]["observed_skill_invocations"] == ["simplify"]
    assert record["claude"]["skill_tool_evidence"]["result_status"] == "success"
    assert "--safe-mode" in record["claude"]["command"]
    assert "--bare" not in record["claude"]["command"]
    assert record["claude"]["usage"]["input_tokens"] == 5
    assert record["verification"][0]["returncode"] == 0
    assert record["final_review"][0]["returncode"] == 0
    assert record["base_sha"] != record["pre_sha"]
    assert record["pre_sha"] != record["post_sha"]
    assert not Path(record["worktree"]).exists()

    assert (fixture / "candidate" / "app.py").read_text(encoding="utf-8") == original
    captured = output.read_text(encoding="utf-8")
    for artifact in record["artifacts"].values():
        artifact_bytes = artifact_path(output, artifact).read_bytes()
        captured += artifact_bytes.decode("utf-8", errors="ignore")
        assert MODULE.sha256_file(artifact_path(output, artifact)) == artifact["sha256"]
    assert "SECRET_TRUTH_MUST_NOT_REACH_CLAUDE" not in captured
    assert not forbidden_output.exists()


def test_first_run_artifacts_are_never_overwritten(tmp_path):
    fixture = write_fixture(tmp_path)
    client = tmp_path / "client"
    client.mkdir()
    fake = write_fake_claude(client)
    output = tmp_path / "results" / "candidate.json"
    first = invoke(fixture.parent, output, fake)
    assert first.returncode == 0, first.stderr
    before = {
        path: path.read_bytes() for path in output.parent.rglob("*") if path.is_file()
    }

    second = invoke(fixture.parent, output, fake)

    assert second.returncode != 0
    assert "refusing to overwrite" in second.stderr
    assert before == {
        path: path.read_bytes() for path in output.parent.rglob("*") if path.is_file()
    }


def test_client_version_pin_fails_before_collection(tmp_path):
    fixture = write_fixture(tmp_path)
    fake = write_fake_claude(tmp_path, version="2.1.219")
    output = tmp_path / "results" / "candidate.json"

    completed = invoke(
        fixture.parent,
        output,
        fake,
        expected_version="2.1.220",
    )

    assert completed.returncode != 0
    assert "client version mismatch" in completed.stderr
    assert not output.exists()


def test_runner_records_failed_checks_for_quality_scorer(tmp_path):
    fixture = write_fixture(tmp_path, failing_checks=True)
    client = tmp_path / "client"
    client.mkdir()
    fake = write_fake_claude(client)
    output = tmp_path / "results" / "candidate.json"

    completed = invoke(fixture.parent, output, fake)

    assert completed.returncode == 0, completed.stderr
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["records"][0]["verification"][0]["returncode"] != 0


def test_advisory_mode_does_not_invoke_simplify(tmp_path):
    fixture = write_fixture(tmp_path)
    fake = write_fake_claude(tmp_path)
    output = tmp_path / "results" / "baseline.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--mode",
            "advisory",
            "--fixtures",
            str(fixture.parent),
            "--output",
            str(output),
            "--claude",
            str(fake),
            "--expected-client-version",
            "2.1.220",
            "--source-commit",
            source_sha(),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    record = json.loads(output.read_text(encoding="utf-8"))["records"][0]
    assert record["outcome"] == "no_op"
    assert record["claude"]["invocations"] == 0
    assert record["pre_sha"] == record["post_sha"]


def test_relative_output_and_fixtures_resolve_from_caller_cwd(tmp_path):
    write_fixture(tmp_path)
    client = tmp_path / "client"
    client.mkdir()
    write_fake_claude(client)
    caller = tmp_path / "caller"
    caller.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=caller, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=caller, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=caller,
        check=True,
    )
    (caller / "source.txt").write_text("source\n", encoding="utf-8")
    subprocess.run(["git", "add", "source.txt"], cwd=caller, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "source"], cwd=caller, check=True)
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=caller,
        text=True,
    ).strip()

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--mode",
            "advisory",
            "--fixtures",
            "../fixtures",
            "--output",
            "results/baseline.json",
            "--claude",
            "../client/fake-claude",
            "--expected-client-version",
            "2.1.220",
            "--source-commit",
            source_commit,
        ],
        cwd=caller,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    output = caller / "results" / "baseline.json"
    result = json.loads(output.read_text(encoding="utf-8"))
    for artifact in result["records"][0]["artifacts"].values():
        assert not Path(artifact["path"]).is_absolute()
        assert (output.parent / artifact["path"]).is_file()


def test_candidate_rejects_zero_multiple_or_wrong_skill_tool_use(tmp_path):
    for index, names in enumerate(((), ("simplify", "simplify"), ("review",))):
        case_root = tmp_path / str(index)
        fixture = write_fixture(case_root)
        client = case_root / "client"
        client.mkdir()
        fake = write_fake_claude(client, skill_names=names)

        completed = invoke(
            fixture.parent,
            case_root / "results" / "candidate.json",
            fake,
        )

        assert completed.returncode != 0
        assert "exactly one bundled simplify Skill tool-use" in completed.stderr


def test_candidate_rejects_missing_error_mismatched_or_duplicate_skill_result(
    tmp_path,
):
    result_sets = (
        (),
        (("other-tool", False),),
        (("skill-0", True),),
        (("skill-0", False), ("skill-0", False)),
    )
    for index, results in enumerate(result_sets):
        case_root = tmp_path / str(index)
        fixture = write_fixture(case_root)
        client = case_root / "client"
        client.mkdir()
        fake = write_fake_claude(client, tool_results=results)

        completed = invoke(
            fixture.parent,
            case_root / "results" / "candidate.json",
            fake,
        )

        assert completed.returncode != 0
        assert "matching successful tool_result" in completed.stderr


def test_source_commit_must_resolve_and_equal_source_head(tmp_path):
    fixture = write_fixture(tmp_path)
    fake = write_fake_claude(tmp_path, version="2.1.220")
    output = tmp_path / "results" / "candidate.json"

    completed = invoke(
        fixture.parent,
        output,
        fake,
        source_commit="0" * 40,
    )

    assert completed.returncode != 0
    assert "source commit" in completed.stderr
    assert not output.exists()


def test_auth_environment_is_token_only_and_drops_cloud_credentials(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oauth-test")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "must-not-pass")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/must/not/pass")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert MODULE._resolve_auth_environment() == {
        "CLAUDE_CODE_OAUTH_TOKEN": "oauth-test"
    }


def test_sandbox_profile_allows_git_common_dir_and_safe_devices(tmp_path):
    worktree = tmp_path / "worktree"
    git_dir = tmp_path / "git-dir"
    git_common_dir = tmp_path / "git-common-dir"
    runtime = tmp_path / "runtime"
    fixture_root = tmp_path / "fixtures"
    output_parent = tmp_path / "results"
    client = tmp_path / "client" / "fake-claude"
    client.parent.mkdir()
    client.touch()
    for path in (
        worktree,
        git_dir,
        git_common_dir,
        runtime,
        fixture_root,
        output_parent,
    ):
        path.mkdir()

    profile = MODULE._sandbox_profile(
        worktree=worktree,
        git_dir=git_dir,
        git_common_dir=git_common_dir,
        runtime=runtime,
        client=client,
        source_root=SCRIPT.parent.parent,
        fixture=fixture_root,
        output_parent=output_parent,
    )

    write_deny_clause = profile.splitlines()[-2]
    assert "file-write*" in write_deny_clause
    assert f"(require-not (subpath {MODULE._sandbox_quote(git_dir)}))" in (
        write_deny_clause
    )
    assert f"(require-not (subpath {MODULE._sandbox_quote(git_common_dir)}))" in (
        write_deny_clause
    )
    for device in ("/dev/null", "/dev/zero", "/dev/urandom", "/dev/random", "/dev/tty"):
        assert (
            f"(require-not (literal {MODULE._sandbox_quote(Path(device))}))"
            in write_deny_clause
        )


def test_sandbox_profile_allows_writes_and_reads_under_claude_scratch_root(tmp_path):
    worktree = tmp_path / "worktree"
    git_dir = tmp_path / "git-dir"
    git_common_dir = tmp_path / "git-common-dir"
    runtime = tmp_path / "runtime"
    fixture_root = tmp_path / "fixtures"
    output_parent = tmp_path / "results"
    client = tmp_path / "client" / "fake-claude"
    client.parent.mkdir()
    client.touch()
    for path in (
        worktree,
        git_dir,
        git_common_dir,
        runtime,
        fixture_root,
        output_parent,
    ):
        path.mkdir()

    scratch_root = MODULE._claude_scratch_root()
    assert str(scratch_root) == f"/tmp/claude-{os.getuid()}"

    profile = MODULE._sandbox_profile(
        worktree=worktree,
        git_dir=git_dir,
        git_common_dir=git_common_dir,
        runtime=runtime,
        client=client,
        source_root=SCRIPT.parent.parent,
        fixture=fixture_root,
        output_parent=output_parent,
    )

    assert MODULE._sandbox_quote(scratch_root.resolve()) in profile
    write_deny_clause = profile.splitlines()[-2]
    assert "file-write*" in write_deny_clause
    assert MODULE._sandbox_quote(scratch_root.resolve()) in write_deny_clause


def test_sandbox_environment_redirects_claude_config_dir_under_runtime(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    client = tmp_path / "client" / "fake-claude"
    client.parent.mkdir()
    client.touch()

    environment = MODULE._sandbox_environment(runtime, client, {})

    assert environment["CLAUDE_CONFIG_DIR"] == str(runtime / "claude-config")


def test_failed_sandbox_auth_preflight_creates_no_run_artifacts(tmp_path):
    fixture = write_fixture(tmp_path)
    client = tmp_path / "client"
    client.mkdir()
    fake = write_fake_claude(client, auth_logged_in=False)
    output = tmp_path / "results" / "candidate.json"

    completed = invoke(fixture.parent, output, fake)

    assert completed.returncode != 0
    assert "auth preflight failed inside sandbox" in completed.stderr
    assert not output.exists()
    assert not (output.parent / "artifacts").exists()
    assert not (output.parent / "transcripts").exists()


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="probes macOS-only content roots (/private/tmp, /Users/Shared, /Volumes)",
)
def test_sandbox_denies_unrelated_content_roots(tmp_path):
    # Guarded at test level, not via invoke(): the /private/tmp sentinel assertion
    # below runs before invoke() is ever called, so it fails on Linux (where the
    # probe roots do not exist) before the shared skip can fire.
    sentinels: list[Path] = []
    temp_dirs: list[tempfile.TemporaryDirectory[str]] = []
    try:
        for root in (Path("/private/tmp"), Path("/Users/Shared"), Path("/Volumes")):
            if not root.is_dir() or not os.access(root, os.W_OK):
                continue
            temporary = tempfile.TemporaryDirectory(
                prefix="simplify-read-probe-",
                dir=root,
            )
            temp_dirs.append(temporary)
            sentinel = Path(temporary.name) / "secret"
            sentinel.write_text("must stay unreadable", encoding="utf-8")
            sentinels.append(sentinel)
        assert any(str(path).startswith("/private/tmp/") for path in sentinels)
        fixture = write_fixture(tmp_path)
        client = tmp_path / "client"
        client.mkdir()
        fake = write_fake_claude(client, forbidden_reads=tuple(sentinels))

        completed = invoke(
            fixture.parent,
            tmp_path / "results" / "candidate.json",
            fake,
        )

        assert completed.returncode == 0, completed.stderr
    finally:
        for temporary in reversed(temp_dirs):
            temporary.cleanup()


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="genuine Seatbelt and Keychain probe requires macOS",
)
def test_real_safe_mode_auth_succeeds_but_security_cannot_read_keychain(tmp_path):
    sandbox = shutil.which("sandbox-exec")
    claude = shutil.which("claude")
    if not sandbox or not claude:
        pytest.skip("sandbox-exec or Claude client is unavailable")
    client = Path(claude).resolve()
    worktree = tmp_path / "worktree"
    git_dir = tmp_path / "git-dir"
    git_common_dir = tmp_path / "git-common-dir"
    runtime = tmp_path / "runtime"
    fixture_root = tmp_path / "fixtures"
    output_parent = tmp_path / "results"
    for path in (
        worktree,
        git_dir,
        git_common_dir,
        runtime,
        fixture_root,
        output_parent,
    ):
        path.mkdir()
    profile = runtime / "sandbox.sb"
    profile.write_text(
        MODULE._sandbox_profile(
            worktree=worktree,
            git_dir=git_dir,
            git_common_dir=git_common_dir,
            runtime=runtime,
            client=client,
            source_root=SCRIPT.parent.parent,
            fixture=fixture_root,
            output_parent=output_parent,
        ),
        encoding="utf-8",
    )
    auth_environment = MODULE._resolve_auth_environment()
    environment = MODULE._sandbox_environment(
        runtime,
        client,
        auth_environment,
    )

    auth = subprocess.run(
        [
            sandbox,
            "-f",
            str(profile),
            str(client),
            "--safe-mode",
            "auth",
            "status",
            "--json",
        ],
        cwd=worktree,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert auth.returncode == 0, auth.stderr
    auth_status = json.loads(auth.stdout)
    assert auth_status["loggedIn"] is True
    if "CLAUDE_CODE_OAUTH_TOKEN" in auth_environment:
        assert auth_status["authMethod"] == "oauth_token"

    security = subprocess.run(
        [
            sandbox,
            "-f",
            str(profile),
            "/usr/bin/security",
            "find-generic-password",
            "-s",
            "Claude Code-credentials",
            "-w",
        ],
        cwd=worktree,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    assert security.returncode == 44


def test_remove_paths_reject_traversal_backslash_and_absolute_paths(tmp_path):
    for raw in (
        "../outside",
        "nested/../../outside",
        "nested\\outside",
        "/outside",
        ".",
    ):
        try:
            MODULE.validate_remove_path(raw)
        except MODULE.CollectionError:
            pass
        else:
            raise AssertionError(f"unsafe remove path accepted: {raw}")
    assert MODULE.validate_remove_path("nested/old.py").as_posix() == "nested/old.py"


def test_head_guard_rejects_resolved_and_symbolic_movement(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=repo,
        check=True,
    )
    (repo / "file").write_text("one", encoding="utf-8")
    subprocess.run(["git", "add", "file"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "one"], cwd=repo, check=True)
    state = MODULE.capture_head_state(repo)
    subprocess.run(["git", "checkout", "-q", "--detach"], cwd=repo, check=True)
    try:
        MODULE.assert_head_unchanged(repo, state)
    except MODULE.CollectionError as exc:
        assert "symbolic HEAD moved" in str(exc)
    else:
        raise AssertionError("detaching HEAD at the same SHA must be rejected")


def test_remove_path_unlinks_symlink_without_following_target(tmp_path):
    worktree = tmp_path / "worktree"
    outside = tmp_path / "outside"
    worktree.mkdir()
    outside.mkdir()
    sentinel = outside / "keep"
    sentinel.write_text("safe", encoding="utf-8")
    (worktree / "linked").symlink_to(outside, target_is_directory=True)

    MODULE._remove_fixture_path(worktree, "linked")

    assert not (worktree / "linked").exists()
    assert sentinel.read_text(encoding="utf-8") == "safe"


def test_cached_patch_captures_untracked_deleted_rename_and_binary(tmp_path):
    fixture = write_fixture(tmp_path)
    (fixture / "base" / "old.txt").write_text("delete me\n", encoding="utf-8")
    client = tmp_path / "client"
    client.mkdir()
    fake = client / "fake-claude"
    # POSIX sh for the same reason as the shared fixture: #!/usr/bin/python3 is
    # the Xcode stub on macOS runners and dies under Seatbelt. This one is
    # hand-rolled rather than using write_fake_claude because it exercises a
    # bespoke set of worktree mutations (rename, delete, new file, binary).
    fake.write_text(
        "#!/bin/sh\n"
        'for arg in "$@"; do\n'
        '  [ "$arg" = "--version" ] && { echo "2.1.220 (Claude Code)"; exit 0; }\n'
        "done\n"
        'case " $* " in\n'
        '  *\\ auth\\ *) case " $* " in *\\ status\\ *) '
        + "printf %s\\\\n "
        + _sh_quote(json.dumps({"loggedIn": True, "authMethod": "oauth_token"}))
        + "; exit 0;; esac;;\n"
        "esac\n"
        "mv app.py renamed.py\n"
        "rm -f old.txt\n"
        "printf 'new file\\n' > new.txt\n"
        # 256 bytes, 0x00-0xFF — the same binary payload the Python fake wrote.
        "awk 'BEGIN{for(i=0;i<256;i++)printf \"%c\", i}' > binary.bin\n"
        + "printf %s\\\\n "
        + _sh_quote(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "one",
                                "name": "Skill",
                                "input": {"skill": "simplify"},
                            }
                        ]
                    },
                }
            )
        )
        + "\n"
        + "printf %s\\\\n "
        + _sh_quote(
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "one",
                                "is_error": False,
                                "content": "done",
                            }
                        ]
                    },
                }
            )
        )
        + "\n"
        + "printf %s\\\\n "
        + _sh_quote(json.dumps({"type": "result", "result": "done", "usage": {}}))
        + "\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    output = tmp_path / "results" / "candidate.json"

    completed = invoke(fixture.parent, output, fake)

    assert completed.returncode == 0, completed.stderr
    record = json.loads(output.read_text(encoding="utf-8"))["records"][0]
    patch = artifact_path(output, record["artifacts"]["simplify_diff"]).read_text(
        encoding="utf-8"
    )
    assert "new file mode" in patch
    assert "deleted file mode" in patch
    assert "rename from app.py" in patch
    assert "rename to renamed.py" in patch
    assert "GIT binary patch" in patch
    assert record["changed_files"] == [
        "binary.bin",
        "new.txt",
        "old.txt",
        "renamed.py",
    ]


@pytest.mark.skipif(
    sys.platform != "darwin" or bool(os.environ.get("CI")),
    reason=(
        "the Python fake client's #!/usr/bin/python3 is the Xcode stub, which "
        "needs xcrun/libxcrun under /Applications — correctly denied by the "
        "Seatbelt profile. Runs on macOS dev machines where /usr/bin/python3 "
        "resolves to Command Line Tools under the allowed /Library root."
    ),
)
def test_python_client_env_is_fully_scrubbed(tmp_path):
    # The sh fake cannot assert PWD/OLDPWD scrubbing because sh synthesizes both
    # itself. This test keeps that half of the guarantee honest by running the
    # Python flavor, which reads the inherited environment verbatim.
    fixture = write_fixture(tmp_path)
    client = tmp_path / "client"
    client.mkdir()
    fake = write_fake_claude(client, flavor="python")
    completed = invoke(
        fixture.parent,
        tmp_path / "results" / "candidate.json",
        fake,
    )
    assert completed.returncode == 0, completed.stderr
    assert "unscrubbed path env" not in completed.stderr
