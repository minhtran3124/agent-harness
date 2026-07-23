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
#
# Three checks, in order of how much they can prove:
#   1. unbound-variable (above) — whole file, always runs.
#   2. `bash -n` syntax — per block, on blocks with no placeholder.
#   3. `shellcheck -S error` — per block, same scope, only when shellcheck is installed.
#
# Blocks containing a `<placeholder>` or `[optional]` are ILLUSTRATIVE, not runnable, and are
# skipped by 2 and 3: shellcheck parses `view_plan.py <slug>` as a stdin redirection and reports
# a parse error, which is noise, not signal. Severity is pinned to `error` for the same reason —
# at default severity these doc fragments emit SC2012 ("use find instead of ls", when `ls -1t`
# is exactly what was meant) and SC2046 on a deliberately unquoted `$(git merge-base …)…HEAD`
# range. A gate that fires on correct code teaches people to ignore it.
#
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

import shutil, subprocess, tempfile, os

# A block carrying `<placeholder>` / `[optional]` is documentation, not a runnable script.
PLACEHOLDER = re.compile(r"<[a-z][a-z0-9_.\- ]*>|\[[a-z][a-z0-9_.\-]*\]")
HAS_SHELLCHECK = shutil.which("shellcheck") is not None

runnable = skipped = 0
for p in sorted(pathlib.Path("skills").rglob("*.md")):
    for idx, block in enumerate(FENCE.findall(p.read_text(encoding="utf-8")), 1):
        # strip comment-only lines before deciding: `# see <type>/<slug>` is prose, not a placeholder
        code = "\n".join(l for l in block.splitlines() if not l.strip().startswith("#"))
        if PLACEHOLDER.search(code):
            skipped += 1
            continue
        runnable += 1
        d = tempfile.mkdtemp()
        f = os.path.join(d, "block.sh")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/bash\n" + block)

        r = subprocess.run(["bash", "-n", f], capture_output=True, text=True)
        if r.returncode:
            msg = r.stderr.replace(f, f"{p} #{idx}").strip().splitlines()
            print(f"  ✗ {p} block #{idx}: bash syntax error", file=sys.stderr)
            for line in msg[:3]:
                print(f"      {line}", file=sys.stderr)
            failed = 1

        if HAS_SHELLCHECK:
            r = subprocess.run(
                ["shellcheck", "-S", "error", "-f", "gcc", f], capture_output=True, text=True
            )
            for line in r.stdout.strip().splitlines():
                print(f"  ✗ {p} block #{idx}: {line.split(':', 3)[-1].strip()}", file=sys.stderr)
                failed = 1

if failed:
    print("\n  skill-bash lint: problems in runnable skill blocks.", file=sys.stderr)
    sys.exit(1)

sc = "shellcheck -S error" if HAS_SHELLCHECK else "shellcheck absent — syntax only"
print(
    f"  ✓ skill-bash lint: {checked} doc(s), {runnable} runnable block(s) checked "
    f"({skipped} illustrative skipped); no unbound vars, {sc} clean"
)
PY
