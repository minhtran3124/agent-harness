#!/usr/bin/env python3
"""Run a test command in a temporary detached worktree at a given commit.

Usage:

    python3 scripts/run_at_commit.py <rev> -- <arg>...

Exit codes:
  the test command's own exit code;
  128+n  the test command was killed by signal n;
  124    the test command ran past TIMEOUT_SECONDS and was killed;
  125    a failure of this helper (no `--`, empty command, unknown rev,
         a `git worktree` error, or a command that cannot start).

The repo is resolved from the current directory, never from this file's
location, so the helper also works when deployed under `.claude/scripts/`.
"""

import os
import shutil
import signal
import subprocess
import sys
import tempfile

TIMEOUT_SECONDS = 50


class HelperError(Exception):
    pass


def _git(*args, cwd=None):
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        raise HelperError(f"git {args[0]} failed: {detail[-1] if detail else result.returncode}")
    return result.stdout.strip()


def _run(command, cwd):
    try:
        proc = subprocess.Popen(command, cwd=cwd, start_new_session=True)
    except OSError as exc:
        raise HelperError(f"cannot start {command[0]!r}: {exc}") from exc
    try:
        code = proc.wait(timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        return 124
    return 128 - code if code < 0 else code


def main(argv):
    try:
        if "--" not in argv:
            raise HelperError("usage: run_at_commit.py <rev> -- <arg>...")
        sep = argv.index("--")
        if sep != 1:
            raise HelperError("usage: run_at_commit.py <rev> -- <arg>...")
        command = argv[sep + 1 :]
        if not command:
            raise HelperError("empty command after --")
        top = _git("rev-parse", "--show-toplevel")
        try:
            commit = _git("rev-parse", "--verify", "--quiet", f"{argv[0]}^{{commit}}", cwd=top)
        except HelperError:
            raise HelperError(f"unknown commit {argv[0]!r}") from None
        _git("worktree", "prune", cwd=top)
        tmp = tempfile.mkdtemp(prefix="run_at_commit-")
        try:
            _git("worktree", "add", "--detach", tmp, commit, cwd=top)
            return _run(command, tmp)
        finally:
            subprocess.run(
                ["git", "worktree", "remove", "--force", tmp],
                cwd=top,
                capture_output=True,
            )
            if os.path.exists(tmp):
                shutil.rmtree(tmp, ignore_errors=True)
    except HelperError as exc:
        print(f"run_at_commit: {exc}", file=sys.stderr)
        return 125


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
