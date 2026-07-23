#!/bin/bash
# Lint the runnable bash in skills/**/*.md: every referenced shell variable must be assigned
# in the same document, or be a known environment variable.
#
# Why this exists (PR #158, Codex P1): trimming `using-git-worktrees` deleted the section that
# assigned `path=...` while a later step still ran
# `deploy-harness.sh --target "$path"`. Every route into that step reached it with `path`
# unset, so the command expanded to `--target ""` and `deploy-harness.sh` aborted
# (`${2:?--target needs a path}`) — a fresh worktree silently got no `.claude/`, i.e. no hooks
# and no skills. Three independent review oracles missed it because they read the skill as
# policy prose; the binding is code. This lint reads it as code.
#
# Scope: `bash`/`sh` fenced blocks in skills/**/*.md, treated as ONE document per file (a skill
# is read top to bottom, so an assignment in an earlier block covers a later reference).
# Usage: bash scripts/lint-skill-bash.sh [--root DIR]
set -u
ROOT="."
[ "${1:-}" = "--root" ] && ROOT="${2:?--root needs a dir}"
cd "$ROOT" || exit 1

command -v python3 >/dev/null 2>&1 || { echo "  skip — no python3"; exit 0; }

python3 - <<'PY'
import re, sys, pathlib

# Variables a skill may legitimately reference without assigning: the environment it runs in.
ENV_OK = {
    # shell / posix
    "PATH", "HOME", "PWD", "OLDPWD", "USER", "SHELL", "TMPDIR", "EDITOR", "LANG", "TERM",
    "IFS", "PS1", "RANDOM", "SECONDS", "LINENO", "BASH_SOURCE", "FUNCNAME", "OSTYPE",
    # display detection (writing-plans auto-view)
    "DISPLAY", "WAYLAND_DISPLAY",
    # harness-provided
    "CLAUDE_PROJECT_DIR", "ARGUMENTS", "HARNESS_SHARED_BRANCHES", "BRANCH_ISOLATION_REASON",
    "RISK_WARN_CATEGORIES", "RISK_CORROBORATION_STRICT", "REQUIRE_VERIFY",
    "BLAST_RADIUS_STRICT", "SESSION_KNOWLEDGE_DIR", "AUTO_TEST_CMD", "AUTO_TEST_PATTERN",
    "FULL_ARTIFACTS",
    # common CI
    "CI", "GITHUB_TOKEN", "GH_TOKEN",
}

FENCE = re.compile(r"```(?:bash|sh)\n(.*?)```", re.S)
REF = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)")
ASSIGN = re.compile(r"^\s*(?:export\s+|local\s+|declare\s+(?:-\w+\s+)?)?([A-Za-z_][A-Za-z0-9_]*)=", re.M)
FOR = re.compile(r"\bfor\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\b")
READ = re.compile(r"\bread\s+(?:-\w+\s+)*([A-Za-z_][A-Za-z0-9_]*)")

failed = 0
checked = 0
for p in sorted(pathlib.Path("skills").rglob("*.md")):
    blocks = FENCE.findall(p.read_text(encoding="utf-8"))
    if not blocks:
        continue
    checked += 1
    body = "\n".join(blocks)
    bound = set(ASSIGN.findall(body)) | set(FOR.findall(body)) | set(READ.findall(body)) | ENV_OK
    for m in REF.finditer(body):
        name = m.group(1)
        if name in bound:
            continue
        line = body[: m.start()].count("\n") + 1
        print(
            f"  ✗ {p}: `${name}` is referenced in a bash block but never assigned "
            f"(block-line {line}). Assign it, derive it inline, or add it to ENV_OK in "
            f"scripts/lint-skill-bash.sh if it is genuinely environmental.",
            file=sys.stderr,
        )
        failed = 1
        bound.add(name)   # report each name once per file

if failed:
    print("\n  skill-bash lint: unbound variable(s) in runnable skill blocks.", file=sys.stderr)
    sys.exit(1)
print(f"  ✓ skill-bash lint: {checked} skill doc(s) with bash blocks, no unbound variables")
PY
