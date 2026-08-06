#!/usr/bin/env python3
"""Write one explicit BASE..HEAD review package for a task or whole branch."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        base, head = git("rev-parse", "--verify", f"{args.base}^{{commit}}").strip(), git("rev-parse", "--verify", f"{args.head}^{{commit}}").strip()
        subprocess.run(["git", "merge-base", "--is-ancestor", base, head], check=True)
    except subprocess.CalledProcessError:
        raise SystemExit("review-package: BASE must be an ancestor of HEAD")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = f"# Review package\n\nBASE_SHA: {base}\nHEAD_SHA: {head}\n\n## Commits\n\n{git('log', '--format=%H %s', f'{base}..{head}')}\n## Diff stat\n\n{git('diff', '--stat', f'{base}..{head}')}\n## Diff\n\n```diff\n{git('diff', '-U10', f'{base}..{head}')}\n```\n"
    args.output.write_text(payload, encoding="utf-8")
    args.output.chmod(0o600)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
