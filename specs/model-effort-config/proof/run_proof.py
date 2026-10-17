#!/usr/bin/env python3
"""SC-22 live proof: a deployed agent `model:` setting reaches Claude Code.

--prepare  create a fresh git repo, write harness-models.json (test-runner -> sonnet), deploy.
(default)  prepare when the proof repo is missing, then run one headless `claude -p` session
           that dispatches test-runner; exit 0 only when a modelUsage key starts claude-sonnet-.

Local only: needs an authenticated `claude`. The model call is live and nondeterministic.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

WORKTREE = Path(__file__).resolve().parents[3]
PROOF_DIR = Path(os.environ.get("TMPDIR") or "/tmp") / "harness-model-effort-proof"
AGENT_FILE = PROOF_DIR / ".claude" / "agents" / "test-runner.md"
MODELS = {"agents": {"test-runner": {"model": "sonnet"}}}
PROMPT = (
    "Use the Agent tool once to dispatch the test-runner subagent with this prompt: "
    "'Reply with the single word ok. Do not run any tools.' "
    "After it returns, reply with the single word done."
)


def agent_has_sonnet() -> bool:
    if not AGENT_FILE.is_file():
        return False
    return any(line.strip() == "model: sonnet" for line in AGENT_FILE.read_text().splitlines())


def prepare() -> float:
    """Create and deploy the proof repo; return the deploy seconds."""
    if PROOF_DIR.exists():
        if agent_has_sonnet():
            print(f"reusing {PROOF_DIR} (test-runner already has model: sonnet)")
            return 0.0
        sys.exit(f"error: {PROOF_DIR} exists but is not a prepared proof repo; remove it and re-run")
    PROOF_DIR.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=PROOF_DIR, check=True)
    (PROOF_DIR / "harness-models.json").write_text(json.dumps(MODELS, indent=2) + "\n")
    start = time.monotonic()
    subprocess.run(
        ["bash", str(WORKTREE / "scripts" / "deploy-harness.sh"), "--target", str(PROOF_DIR)],
        cwd=PROOF_DIR,
        stdin=subprocess.DEVNULL,
        check=True,
    )
    seconds = time.monotonic() - start
    if not agent_has_sonnet():
        sys.exit(f"error: deploy did not write model: sonnet into {AGENT_FILE}")
    print(f"deploy seconds: {seconds:.1f}")
    return seconds


def run() -> int:
    if not PROOF_DIR.exists():
        prepare()
    elif not agent_has_sonnet():
        sys.exit(f"error: {AGENT_FILE} lacks model: sonnet; remove {PROOF_DIR} and re-run")
    start = time.monotonic()
    proc = subprocess.run(
        ["claude", "-p", "--output-format", "json", "--allowedTools", "Agent"],
        cwd=PROOF_DIR,
        input=PROMPT,
        capture_output=True,
        text=True,
    )
    seconds = time.monotonic() - start
    print(f"claude -p seconds: {seconds:.1f}")
    if proc.returncode != 0:
        print(f"claude -p exit {proc.returncode}\nstdout: {proc.stdout}\nstderr: {proc.stderr}")
        return 1
    try:
        keys = sorted(json.loads(proc.stdout).get("modelUsage", {}))
    except (json.JSONDecodeError, AttributeError):
        print(f"error: claude -p output is not a JSON object:\n{proc.stdout}")
        return 1
    print(f"modelUsage keys: {', '.join(keys) or '(none)'}")
    if any(k.startswith("claude-sonnet-") for k in keys):
        print("PASS: test-runner ran on a sonnet model")
        return 0
    print("FAIL: no modelUsage key starts with claude-sonnet-")
    return 1


def main() -> int:
    if sys.argv[1:] == ["--prepare"]:
        prepare()
        return 0
    if sys.argv[1:]:
        sys.exit("usage: run_proof.py [--prepare]")
    return run()


if __name__ == "__main__":
    sys.exit(main())
