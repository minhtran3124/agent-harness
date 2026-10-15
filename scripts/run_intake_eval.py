#!/usr/bin/env python3
"""Run the feature-intake classifier eval once per fixture, hardened (playbook Play 8).

Each fixture's `eval.json` pins a `from` commit and a `may_change` glob list. Per fixture the
agent runs headless in a scratch worktree at `from`, with `evals/` removed and the harness
config of the branch under test deployed into it. Any file changed outside `may_change`, or any
repo ref created, deleted or moved, marks the fixture `stray`. The scorer and answer keys are
copied out before the first fixture runs, and the copy does the scoring.

Usage:
  run_intake_eval.py --model M --output-dir DIR [--fixtures DIR] [--claude PATH]
                     [--deploy-script PATH] [--timeout S] [--only NAME] [--strict]
  run_intake_eval.py --check-fixtures [--fixtures DIR]
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from run_test_runner_eval import IGNORED_PARTS, integrity

DEFAULT_FIXTURES = "evals/workflow/intake-classifier/fixtures"
DEFAULT_DEPLOY = "scripts/deploy-harness.sh"
SCORER = "scripts/score_intake_eval.py"
TOOLS = "Bash,Read,Glob,Grep,Write,Edit,Skill"
CLIENT_FLAGS = ["--setting-sources", "project", "--permission-mode", "dontAsk",
                "--allowedTools", TOOLS, "--no-session-persistence", "--output-format", "json"]
PROMPT = ("Classify the change request below with the feature-intake skill. Do not implement it. "
          "End your reply with the intake header lines `Lane:`, `Confidence:`, `Reason:`, "
          "`Flags:` and `Escalate:`.\n\n---\n\n")
SHA_RE = re.compile(r"[0-9a-f]{40}")


def git(*args: str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=check)


def repo_root() -> Path:
    """The repo the current directory is in — never this script's own location."""
    return Path(git("rev-parse", "--show-toplevel").stdout.strip())


def load_meta(fixture_dir: Path) -> dict:
    name = fixture_dir.name
    path = fixture_dir / "eval.json"
    try:
        meta = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise ValueError(f"{name}: cannot read eval.json: {exc}") from None
    if not isinstance(meta, dict):
        raise ValueError(f"{name}: eval.json is not an object")
    sha = meta.get("from")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise ValueError(f"{name}: 'from' is not a 40-character lowercase hex sha: {sha!r}")
    if git("rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}", check=False).returncode:
        raise ValueError(f"{name}: 'from' does not resolve to a commit: {sha}")
    may_change = meta.get("may_change")
    if not isinstance(may_change, list) or not all(isinstance(g, str) for g in may_change):
        raise ValueError(f"{name}: 'may_change' is not a list of strings")
    return {"from": sha, "may_change": may_change}


def fixture_dirs(fixtures: Path) -> list[Path]:
    return sorted(p for p in fixtures.iterdir() if (p / "request.md").is_file())


def copy_scorer(root: Path, fixtures: Path) -> Path:
    """Copy the scorer and the answer keys out of the repo before any fixture runs."""
    copy = Path(tempfile.mkdtemp(prefix="intake-eval-scorer-"))
    shutil.copy2(root / SCORER, copy / "score_intake_eval.py")
    shutil.copytree(fixtures, copy / "fixtures")
    return copy


def snapshot(root: Path) -> dict[str, str]:
    files = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if rel.parts[0] == ".git" or IGNORED_PARTS.intersection(rel.parts) or not path.is_file():
            continue
        files[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def refs(root: Path) -> dict[str, str]:
    out = git("for-each-ref", "--format=%(refname) %(objectname)", cwd=root).stdout
    return dict(line.split(" ", 1) for line in out.splitlines() if line)


def stray_paths(before: dict, after: dict, refs_before: dict, refs_after: dict,
                may_change: list[str]) -> list[str]:
    diff = integrity(before, after)
    touched = diff["changed"] + diff["added"] + diff["removed"]
    stray = [p for p in touched if not any(fnmatch.fnmatchcase(p, g) for g in may_change)]
    stray += [f"ref:{r}" for r in refs_before.keys() | refs_after.keys()
              if refs_before.get(r) != refs_after.get(r)]
    return sorted(stray)


def build_cmd(args, prompt: str) -> list[str]:
    cmd = [args.claude, "-p", prompt, "--model", args.model, *CLIENT_FLAGS]
    if "--bare" in cmd:
        raise ValueError("the client must load the harness config: --bare is not allowed")
    return cmd


def as_text(data) -> str:
    if isinstance(data, bytes):
        return data.decode(errors="replace")
    return data or ""


def run_fixture(args, root: Path, fixture: Path, meta: dict) -> dict:
    name = fixture.name
    tmp = Path(tempfile.mkdtemp(prefix="intake-eval-wt-"))
    wt = tmp / "wt"
    try:
        git("worktree", "add", "--detach", str(wt), meta["from"], cwd=root)
        shutil.rmtree(wt / "evals", ignore_errors=True)
        subprocess.run(["bash", str(args.deploy_script), "--target", str(wt)], cwd=root,
                       text=True, capture_output=True, check=True)
        before, refs_before = snapshot(wt), refs(root)
        cmd = build_cmd(args, PROMPT + (fixture / "request.md").read_text())
        start = time.monotonic()
        try:
            proc = subprocess.run(cmd, cwd=wt, text=True, capture_output=True, check=False,
                                  timeout=args.timeout)
            rc, raw = proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired as exc:
            rc, raw = "timeout", as_text(exc.stdout) + as_text(exc.stderr)
        elapsed = round(time.monotonic() - start, 3)
        stray = stray_paths(before, snapshot(wt), refs_before, refs(root), meta["may_change"])
    finally:
        git("worktree", "remove", "--force", str(wt), cwd=root, check=False)
        shutil.rmtree(tmp, ignore_errors=True)
        git("worktree", "prune", cwd=root, check=False)

    result = None
    if rc == 0:
        try:
            result = json.loads(proc.stdout).get("result")
        except (ValueError, AttributeError):
            result = None
    if stray:
        status = "stray"
    elif rc == "timeout":
        status = "timeout"
    elif rc != 0 or not isinstance(result, str):
        status = "client-error"
    else:
        status = "ok"
    if status == "ok":
        (args.output_dir / f"{name}.md").write_text(result)
    else:
        (args.output_dir / f"{name}.raw.txt").write_text(raw)
    return {"from": meta["from"], "may_change": meta["may_change"], "rc": rc,
            "elapsed": elapsed, "stray": stray, "status": status}


def check_fixtures(fixtures: Path) -> int:
    for fixture in fixture_dirs(fixtures):
        try:
            meta = load_meta(fixture)
        except ValueError as exc:
            print(f"INVALID {exc}")
            return 1
        print(f"ok {fixture.name}: from={meta['from']} may_change={len(meta['may_change'])}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check-fixtures", action="store_true",
                        help="validate every fixture's eval.json and exit")
    parser.add_argument("--model")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--fixtures", type=Path, default=Path(DEFAULT_FIXTURES))
    parser.add_argument("--claude", default="claude")
    parser.add_argument("--deploy-script", type=Path, default=Path(DEFAULT_DEPLOY))
    parser.add_argument("--timeout", type=float, default=600.0, help="seconds per fixture (default 600)")
    parser.add_argument("--only", metavar="NAME", help="run only this fixture")
    parser.add_argument("--strict", action="store_true", help="pass --strict to the scorer")
    args = parser.parse_args(argv)

    root = repo_root()
    fixtures = root / args.fixtures
    if args.check_fixtures:
        return check_fixtures(fixtures)
    if not args.model or not args.output_dir:
        parser.error("--model and --output-dir are required unless --check-fixtures")
    args.output_dir = (root / args.output_dir).resolve()
    if args.output_dir.exists():
        raise SystemExit(f"intake-eval: refusing to overwrite existing output: {args.output_dir}")
    claude = shutil.which(args.claude)
    if not claude:
        raise SystemExit(f"intake-eval: cannot run {args.claude}: not found")
    args.claude = os.path.abspath(claude)
    args.deploy_script = root / args.deploy_script

    selected = [f for f in fixture_dirs(fixtures) if args.only in (None, f.name)]
    if not selected:
        raise SystemExit(f"intake-eval: no fixture to run under {fixtures}")
    metas = {f.name: load_meta(f) for f in selected}
    version = subprocess.run([args.claude, "--version"], text=True, capture_output=True,
                             check=False).stdout.strip()
    head = git("rev-parse", "HEAD", cwd=root).stdout.strip()
    args.output_dir.mkdir(parents=True)

    copy = copy_scorer(root, fixtures)
    try:
        record = {"schema_version": 1, "model": args.model, "client": version or "unknown",
                  "head": head, "fixtures": {}}
        for fixture in selected:
            case = run_fixture(args, root, fixture, metas[fixture.name])
            record["fixtures"][fixture.name] = case
            print(f"{fixture.name}: status={case['status']} rc={case['rc']} "
                  f"elapsed={case['elapsed']}s", flush=True)
        (args.output_dir / "run.json").write_text(json.dumps(record, indent=2) + "\n")
        score = [sys.executable, str(copy / "score_intake_eval.py"), "--run", str(args.output_dir),
                 "--fixtures", str(copy / "fixtures")] + (["--strict"] if args.strict else [])
        scored = subprocess.run(score, text=True, capture_output=True, check=False)
        (args.output_dir / "scorecard.txt").write_text(scored.stdout)
        sys.stderr.write(scored.stderr)
    finally:
        shutil.rmtree(copy, ignore_errors=True)
    print(args.output_dir / "scorecard.txt")
    failed = any(c["status"] != "ok" for c in record["fixtures"].values())
    return 1 if failed or scored.returncode else 0


if __name__ == "__main__":
    raise SystemExit(main())
