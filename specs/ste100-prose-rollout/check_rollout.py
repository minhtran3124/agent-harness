#!/usr/bin/env python3
"""Phase 3 rollout checker for the ASD-STE100 prose rewrite (SC-7, SC-8, SC-9, SC-12).

Usage:
  check_rollout.py --sum-below <n>
  check_rollout.py --frontmatter <ref>
  check_rollout.py --verdicts
  check_rollout.py --task-scope <task id> <base>
  check_rollout.py --selftest
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
SPEC = "specs/ste100-prose-rollout/"
IGNORED_PREFIXES = (SPEC, ".harness-state/")
SCOPE_COUNT = 43


def parse_scope(design_text: str) -> list[str]:
    """Unique backticked paths in the second cell of the Phase B rows `| B1 |` ... `| B9 |`."""
    paths: list[str] = []
    for line in design_text.splitlines():
        if not re.match(r"^\|\s*B[1-9]\s*\|", line):
            continue
        cell = line.split("|")[2]
        for path in re.findall(r"`([^`]+)`", cell):
            if path not in paths:
                paths.append(path)
    return paths


def frontmatter(text: str) -> str | None:
    """The leading `---` YAML block (delimiters included), or None when the file has none.
    Raises ValueError when the leading block has no closing `---`."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            return "".join(lines[: i + 1])
    raise ValueError("leading `---` block is not closed")


def unfenced(text: str) -> list[str]:
    """The lines of text outside fenced code blocks (``` or ~~~)."""
    out, fence = [], None
    for line in text.splitlines():
        m = re.match(r"^\s*(```|~~~)", line)
        if fence is None and m:
            fence = m.group(1)
        elif fence is not None and m and m.group(1) == fence:
            fence = None
        elif fence is None:
            out.append(line)
    return out


def section(text: str, heading: str) -> list[str] | None:
    """Lines under `<heading>` (whole heading, or heading plus a space and more) up to the next
    `#` heading of any level, or None when the heading is absent. Fenced code blocks are skipped."""
    lines = unfenced(text)
    for i, line in enumerate(lines):
        if line.rstrip() == heading or line.startswith(heading + " "):
            body = []
            for nxt in lines[i + 1 :]:
                if re.match(r"^#{1,6}\s", nxt):
                    break
                body.append(nxt)
            return body
    return None


def check_verdicts(summary_text: str, scope: list[str]) -> list[str]:
    rows = section(summary_text, "### Meaning verdicts")
    if rows is None:
        return ["SUMMARY.md has no `### Meaning verdicts` section"]
    verdicts: dict[str, list[str]] = {}
    for line in rows:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.strip().startswith("|") or len(cells) < 3:
            continue
        path = cells[0].strip("`")
        if path == "File" or set(path) <= set("-: "):
            continue
        verdicts.setdefault(path, []).append(cells[2].strip("`").lower())
    errors = []
    for path in scope:
        got = verdicts.get(path, [])
        if len(got) != 1:
            errors.append(f"{path}: expected exactly one verdict row, found {len(got)}")
        elif got[0] not in ("pass", "fail"):
            errors.append(f"{path}: verdict {got[0]!r} is not `pass` or `fail`")
    for path in sorted(set(verdicts) - set(scope)):
        errors.append(f"{path}: verdict row for a file outside the 43-file scope")
    deviations = section(summary_text, "### Deviations") or []
    for path in scope:
        if verdicts.get(path) == ["fail"] and not any(
            path in line and re.search(r"\b(fail|restored)\b", line, re.I) for line in deviations
        ):
            errors.append(
                f"{path}: verdict `fail` but no `### Deviations` line names it with `fail` or `restored`"
            )
    return errors


def parse_porcelain_z(out: str) -> list[str]:
    """Paths from `git status --porcelain -z --no-renames`: NUL-separated `XY <path>` entries."""
    return [entry[3:] for entry in out.split("\0") if entry]


def parse_name_only_z(out: str) -> list[str]:
    """Paths from `git diff -z --name-only --no-renames`: NUL-separated paths."""
    return [p for p in out.split("\0") if p]


def parse_files(plan_text: str, task_id: str) -> list[str] | None:
    """The `- **Files:**` list of `### Task <task_id>` in PLAN.md, or None when absent."""
    for line in section(plan_text, f"### Task {task_id}") or []:
        m = re.match(r"^- \*\*Files:\*\*\s*(.*)$", line.strip())
        if m:
            return [p.strip().strip("`") for p in m.group(1).split(",") if p.strip()]
    return None


def out_of_scope(changed: list[str], allowed: list[str]) -> list[str]:
    return sorted(
        {p for p in changed if p not in allowed and not p.startswith(IGNORED_PREFIXES)}
    )


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout


def load_scope() -> list[str]:
    scope = parse_scope((REPO / SPEC / "design.md").read_text(encoding="utf-8"))
    if len(scope) != SCOPE_COUNT:
        sys.exit(f"FAIL: design.md Phase B table lists {len(scope)} paths, expected {SCOPE_COUNT}")
    return scope


def cmd_sum_below(limit: int) -> list[str]:
    baseline = json.loads((REPO / "scripts/ste-baseline.json").read_text(encoding="utf-8"))
    scope = load_scope()
    missing = [p for p in scope if p not in baseline]
    if missing:
        return [f"{p}: no entry in scripts/ste-baseline.json" for p in missing]
    total = sum(baseline[p] for p in scope)
    print(f"sum of {SCOPE_COUNT} baseline entries = {total} (limit: below {limit})")
    return [] if total < limit else [f"sum {total} is not below {limit}"]


def cmd_frontmatter(ref: str) -> list[str]:
    errors = []
    for path in load_scope():
        try:
            old = git("show", f"{ref}:{path}")
        except subprocess.CalledProcessError:
            errors.append(f"{path}: not found at {ref}")
            continue
        new = (REPO / path).read_text(encoding="utf-8")
        try:
            if frontmatter(old) != frontmatter(new):
                errors.append(f"{path}: YAML frontmatter differs from {ref}")
        except ValueError as exc:
            errors.append(f"{path}: {exc} (at {ref} or on disk)")
    return errors


def cmd_verdicts() -> list[str]:
    summary = (REPO / SPEC / "SUMMARY.md").read_text(encoding="utf-8")
    return check_verdicts(summary, load_scope())


def cmd_task_scope(task_id: str, base: str) -> list[str]:
    allowed = parse_files((REPO / SPEC / "PLAN.md").read_text(encoding="utf-8"), task_id)
    if allowed is None:
        return [f"PLAN.md has no `- **Files:**` line for Task {task_id}"]
    committed = parse_name_only_z(git("diff", "-z", "--name-only", "--no-renames", f"{base}..HEAD"))
    dirty = parse_porcelain_z(git("status", "--porcelain", "-z", "--no-renames", "-uall"))
    return [f"{p}: changed but not in Task {task_id} Files" for p in out_of_scope(committed + dirty, allowed)]


def selftest() -> list[str]:
    errors: list[str] = []

    def expect(name: str, got, want) -> None:
        if got != want:
            errors.append(f"{name}: got {got!r}, want {want!r}")

    design = (
        "| Batch | Files |\n|---|---|\n"
        "| B1 | `rules/a.md`, `rules/b.md` |\n"
        "| B2 | `agents/c.md`, `rules/a.md` |\n"
        "| B10 | `x.md` |\n"
        "| A1 | `not/me.md` |\n"
    )
    expect("scope parse", parse_scope(design), ["rules/a.md", "rules/b.md", "agents/c.md"])
    expect("scope count != 43", len(parse_scope(design)) != SCOPE_COUNT, True)
    big = "\n".join(f"| B{1 + i % 9} | `f{i}.md` |" for i in range(SCOPE_COUNT))
    expect("scope count == 43", len(parse_scope(big)), SCOPE_COUNT)

    baseline = {"rules/a.md": 5, "rules/b.md": 7, "agents/c.md": 0, "other.md": 99}
    expect("sum", sum(baseline[p] for p in parse_scope(design)), 12)

    fm = "---\nname: x\ndescription: y\n---\n"
    expect("frontmatter present", frontmatter(fm + "# Body\n"), fm)
    expect("frontmatter equal", frontmatter(fm + "old body\n") == frontmatter(fm + "new body\n"), True)
    expect("frontmatter different", frontmatter(fm) == frontmatter(fm.replace("y", "z")), False)
    expect("frontmatter absent", frontmatter("# Title\n---\nx\n---\n"), None)
    try:
        frontmatter("---\nname: x\n")
        errors.append("frontmatter unclosed: no ValueError raised")
    except ValueError:
        pass
    expect("frontmatter absent vs present", frontmatter("# T\n") == frontmatter(fm), False)

    scope = ["rules/a.md", "rules/b.md"]
    head = "### Meaning verdicts\n\n| File | Task | Verdict | Note |\n| --- | --- | --- | --- |\n"
    good = (
        head + "| `rules/a.md` | 2.1 | pass | ok |\n| rules/b.md | 2.1 | fail | lost a hedge |\n"
        "\n### Deviations\n\n- rules/b.md restored to BASE after two failed rounds\n"
    )
    expect("verdicts complete", check_verdicts(good, scope), [])
    expect("verdicts section missing", len(check_verdicts("### Deviations\n- none\n", scope)), 1)
    expect("verdicts row missing", len(check_verdicts(head + "| rules/a.md | 2.1 | pass | |\n", scope)), 1)
    dup = good.replace("| rules/b.md |", "| rules/a.md | 2.1 | pass | |\n| rules/b.md |")
    expect("verdicts duplicate row", len(check_verdicts(dup, scope)), 1)
    bad_word = good.replace("| fail |", "| maybe |")
    expect("verdicts bad value", len(check_verdicts(bad_word, scope)), 1)
    no_dev = good.replace("- rules/b.md restored", "- something else")
    expect("fail without deviation", len(check_verdicts(no_dev, scope)), 1)
    split = good.replace("- rules/b.md restored to BASE after two failed rounds", "- rules/b.md\n- restored to BASE")
    expect("fail path and keyword on different lines", len(check_verdicts(split, scope)), 1)
    no_word = good.replace("restored to BASE after two failed rounds", "edited in Task 2.1")
    expect("fail deviation line without fail/restored", len(check_verdicts(no_word, scope)), 1)
    fenced = "```\n### Meaning verdicts\n| rules/a.md | 2.1 | pass | |\n```\n"
    expect("verdicts heading inside fence ignored", len(check_verdicts(fenced, scope)), 1)
    expect(
        "section stops at #### and skips fenced lines",
        section("### A\nx\n```\n### B\ny\n```\nz\n#### C\nw\n", "### A"),
        ["x", "z"],
    )

    porcelain = " M rules/a.md\0?? dir with space/new \"q\".md\0 D old.md\0"
    expect(
        "porcelain -z quoted/space path",
        parse_porcelain_z(porcelain),
        ["rules/a.md", 'dir with space/new "q".md', "old.md"],
    )

    renamed = "rules/old.md\0" + SPEC + "moved.md\0"
    expect("diff --no-renames lists both paths", parse_name_only_z(renamed), ["rules/old.md", SPEC + "moved.md"])
    expect("renamed source flagged", out_of_scope(parse_name_only_z(renamed), []), ["rules/old.md"])

    plan = (
        "### Task 2.1 — Rewrite B1 (wave 6)\n\n"
        "- **Files:** rules/a.md, `rules/b.md`, scripts/ste-baseline.json\n- **Action:** x\n\n"
        "### Task 2.10 — Other\n\n- **Files:** z.md\n"
    )
    files = parse_files(plan, "2.1")
    expect("files parse", files, ["rules/a.md", "rules/b.md", "scripts/ste-baseline.json"])
    expect("files parse no prefix clash", parse_files(plan, "2.10"), ["z.md"])
    expect("files parse absent", parse_files(plan, "9.9"), None)
    changed = ["rules/a.md", SPEC + "SUMMARY.md", ".harness-state/sdd/x.md", "rules/c.md"]
    expect("scope check", out_of_scope(changed, files), ["rules/c.md"])
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--sum-below", type=int, metavar="N")
    mode.add_argument("--frontmatter", metavar="REF")
    mode.add_argument("--verdicts", action="store_true")
    mode.add_argument("--task-scope", nargs=2, metavar=("TASK_ID", "BASE"))
    mode.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        errors = selftest()
    elif args.sum_below is not None:
        errors = cmd_sum_below(args.sum_below)
    elif args.frontmatter:
        errors = cmd_frontmatter(args.frontmatter)
    elif args.verdicts:
        errors = cmd_verdicts()
    else:
        errors = cmd_task_scope(*args.task_scope)
    for e in errors:
        print(f"FAIL: {e}", file=sys.stderr)
    if not errors:
        print("OK")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
