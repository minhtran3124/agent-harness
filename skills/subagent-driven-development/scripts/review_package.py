#!/usr/bin/env python3
"""Write one explicit BASE..HEAD review package for a task or whole branch."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

STE_LINT = Path(__file__).resolve().parents[2] / "asd-ste100" / "scripts" / "ste-lint.py"
SCOPE_QUALIFIERS = Path(__file__).resolve().parents[3] / "scripts" / "check_scope_qualifiers.py"
LINT_TIMEOUT = 60
PROSE_ROOTS = ("skills/", "rules/", "agents/")
# The counts ignore synonym-rotation. Test H3 measured no effect (specs/ste-terminology-evidence/DECISION.md).
DISABLED_RULES = ("synonym-rotation",)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True, errors="surrogateescape")


def lint_hard_count(text: str) -> int:
    """Return the hard count for the text. Raise RuntimeError when the linter fails."""
    if not STE_LINT.is_file():
        raise RuntimeError(f"linter not found: {STE_LINT}")
    run = subprocess.run([sys.executable, str(STE_LINT), "--json", "--disable", ",".join(DISABLED_RULES)],
                         input=text, capture_output=True, text=True, timeout=LINT_TIMEOUT)
    try:
        return int(json.loads(run.stdout)["hard_count"])
    except (ValueError, KeyError, TypeError):
        raise RuntimeError(f"linter exit {run.returncode}, no hard_count in JSON output")


def prose_paths(base: str, head: str) -> list[str]:
    # -z and quotepath=false keep a non-ASCII path unquoted, so the prefix filter sees it.
    # surrogateescape: a file name that is not UTF-8 cannot crash the package.
    names = subprocess.check_output(["git", "-c", "core.quotepath=false", "-c", "diff.relative=false", "diff", "--name-only", "-z", "--no-renames", "--diff-filter=d", f"{base}..{head}"],
                                    text=True, errors="surrogateescape").split("\0")
    return [name for name in names if name.endswith(".md") and name.startswith(PROSE_ROOTS)]


def ste_section(base: str, head: str) -> str:
    """Return the STE lint section for changed prose files. Return an empty string when no prose file changed."""
    paths = prose_paths(base, head)
    if not paths:
        return ""
    lines = []
    try:
        for path in paths:
            at_base = subprocess.run(["git", "cat-file", "-e", f"{base}:{path}"], capture_output=True).returncode == 0
            base_count = lint_hard_count(git("show", f"{base}:{path}")) if at_base else "new"
            lines.append(f"- {path}: base: {base_count}, head: {lint_hard_count(git('show', f'{head}:{path}'))}")
    # A hang, bad output bytes, or a failed git show is a linter failure. The package still exits 0.
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        lines = [f"ste-lint: unavailable ({' '.join(str(exc).split())})"]
    return "\n## STE lint\n\n" + "\n".join(lines) + "\n"


def scope_section(base: str, head: str) -> str:
    """Return the scope-qualifier section for changed prose files. Return an empty string when no prose file changed."""
    if not prose_paths(base, head):
        return ""
    try:
        if not SCOPE_QUALIFIERS.is_file():
            raise RuntimeError(f"module not found: {SCOPE_QUALIFIERS}")
        run = subprocess.run([sys.executable, str(SCOPE_QUALIFIERS), "--base", base, "--head", head],
                             capture_output=True, text=True, timeout=LINT_TIMEOUT)
        if run.returncode != 0:
            raise RuntimeError(f"module exit {run.returncode}: {run.stderr}")
        output = run.stdout.strip()
    # A hang, bad output bytes, or a non-zero exit is a module failure. The package still exits 0.
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        output = f"scope-qualifiers: unavailable ({' '.join(str(exc).split())})"
    return f"\n## Scope qualifiers\n\n{output}\n" if output else ""


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
    payload += ste_section(base, head)
    payload += scope_section(base, head)
    args.output.write_text(payload, encoding="utf-8", errors="backslashreplace")
    args.output.chmod(0o600)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
