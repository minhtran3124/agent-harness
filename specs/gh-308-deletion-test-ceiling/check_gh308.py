#!/usr/bin/env python3
"""Spec-local checks for gh-308. Each subcommand prints one line per failure and exits 1 on any
failure, 0 otherwise.

Usage: check_gh308.py budget [<skill>] | qualifiers | backlog | ratchet

Verifies:
- budget: each skill's SKILL.md word count is at most 540, or it is below its count at BASE and
  its qualifiers file has a `## Kept long on purpose` heading with at least one `- ` bullet.
- qualifiers: every condition word that `scripts/check_scope_qualifiers.py` lists for the three
  skills has a `kept:` line whose cited text occurs verbatim in the skill's SKILL.md or
  references/ at HEAD.
- backlog: both `ste-rewrite-drops-scope-qualifiers` backlog rows end in `| done |`.
- ratchet: per skill, the summed STE hard count of SKILL.md plus references/*.md in the working
  tree is at most its sum at BASE, and `scripts/ste-baseline.json` changed only keys under the
  three skills.
Does not verify: that a cited "kept" line keeps the condition's meaning or scope, that the kept
long sentences are truly needed, or that a trim keeps agent behavior. It reads the qualifier
script's word list, so a scope split that keeps the word is not seen (its known limit).
"""
import json
import subprocess
import sys
from pathlib import Path

BASE = "cc366fd"
SKILLS = ("session-retro", "feature-intake", "finishing-a-development-branch")
BUDGET = 540
SPEC = "specs/gh-308-deletion-test-ceiling"
BACKLOG = "docs/harness-experimental/improvement-backlog.md"
BACKLOG_ID = "ste-rewrite-drops-scope-qualifiers"
LINT = "skills/asd-ste100/scripts/ste-lint.py"


def run(*args: str, stdin: str | None = None) -> str:
    return subprocess.run(args, cwd=ROOT, input=stdin, capture_output=True, text=True,
                          check=True).stdout


ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                           text=True, check=True).stdout.strip())


def git_files(ref: str, prefix: str) -> list[str]:
    """Paths under `prefix` at `ref` (empty when none exist)."""
    return [p for p in run("git", "ls-tree", "-r", "--name-only", ref, "--", prefix).splitlines() if p]


def qualifiers_file(skill: str) -> Path:
    return ROOT / SPEC / f"qualifiers-{skill}.md"


def has_kept_long(skill: str) -> bool:
    path = qualifiers_file(skill)
    if not path.is_file():
        return False
    in_section = False
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            in_section = line.strip() == "## Kept long on purpose"
        elif in_section and line.startswith("- "):
            return True
    return False


def budget(args: list[str]) -> list[str]:
    skills = args or list(SKILLS)
    fails = []
    for skill in skills:
        if skill not in SKILLS:
            fails.append(f"budget: unknown skill {skill}")
            continue
        words = len((ROOT / "skills" / skill / "SKILL.md").read_text().split())
        if words <= BUDGET:
            continue
        base = len(run("git", "show", f"{BASE}:skills/{skill}/SKILL.md").split())
        if words < base and has_kept_long(skill):
            continue
        fails.append(f"budget: skills/{skill}/SKILL.md has {words} words (budget {BUDGET}, "
                     f"{BASE} count {base}); no shortfall exit")
    return fails


def kept_entries(skill: str) -> dict[tuple[str, str, str], str]:
    """Map (file, line, word) to cited text from `- <file>:<line> "<word>" kept: `...`` lines."""
    path = qualifiers_file(skill)
    entries = {}
    if not path.is_file():
        return entries
    for line in path.read_text().splitlines():
        if not line.startswith("- ") or '" kept:' not in line:
            continue
        head, _, tail = line[2:].partition(" kept:")
        loc, _, word = head.partition(' "')
        file, _, num = loc.rpartition(":")
        first, last = tail.find("`"), tail.rfind("`")
        if not file or not word.endswith('"') or first == -1 or last <= first:
            continue
        entries[(file, num, word[:-1])] = tail[first + 1:last]
    return entries


def head_text(skill: str) -> list[str]:
    prefix = f"skills/{skill}/"
    paths = [p for p in git_files("HEAD", prefix)
             if p == prefix + "SKILL.md" or p.startswith(prefix + "references/")]
    return [run("git", "show", f"HEAD:{p}") for p in paths]


def qualifiers(_: list[str]) -> list[str]:
    out = run(sys.executable, "scripts/check_scope_qualifiers.py", "--base", BASE, "--head", "HEAD")
    fails = []
    texts = {}
    entries = {}
    for line in out.splitlines():
        if line.startswith("scope-qualifiers: unavailable"):
            fails.append(f"qualifiers: {line}")
            continue
        if not line.startswith("- ") or line == "- none":
            continue
        loc, _, rest = line[2:].partition(": dropped \"")
        word = rest.partition('"')[0]
        file, _, num = loc.rpartition(":")
        skill = next((s for s in SKILLS if file.startswith(f"skills/{s}/")), None)
        if skill is None:
            continue
        if skill not in entries:
            entries[skill] = kept_entries(skill)
            texts[skill] = head_text(skill)
        cited = entries[skill].get((file, num, word))
        if cited is None:
            fails.append(f"qualifiers: no kept line for {file}:{num} \"{word}\" in "
                         f"{SPEC}/qualifiers-{skill}.md")
        elif not any(cited in text for text in texts[skill]):
            fails.append(f"qualifiers: {file}:{num} \"{word}\" cited text not found at HEAD: {cited}")
    return fails


def backlog(_: list[str]) -> list[str]:
    rows = [line for line in (ROOT / BACKLOG).read_text().splitlines() if BACKLOG_ID in line]
    if len(rows) != 2:
        return [f"backlog: expected 2 {BACKLOG_ID} rows, found {len(rows)}"]
    return [f"backlog: row not done: {row[:100]}" for row in rows
            if not row.rstrip().endswith("| done |")]


def hard_count(text: str) -> int:
    # ste-lint exits 1 whenever hard_count > 0, so read the JSON, not the exit code.
    proc = subprocess.run([sys.executable, LINT, "--json", "--disable", "synonym-rotation"],
                          cwd=ROOT, input=text, capture_output=True, text=True)
    return json.loads(proc.stdout)["hard_count"]


def ratchet(_: list[str]) -> list[str]:
    fails = []
    for skill in SKILLS:
        prefix = f"skills/{skill}/"
        base_paths = [p for p in git_files(BASE, prefix) if p == prefix + "SKILL.md"
                      or (p.startswith(prefix + "references/") and p.count("/") == 3
                          and p.endswith(".md"))]
        base_sum = sum(hard_count(run("git", "show", f"{BASE}:{p}")) for p in base_paths)
        skill_dir = ROOT / "skills" / skill
        tree_paths = [skill_dir / "SKILL.md", *sorted((skill_dir / "references").glob("*.md"))]
        tree_sum = sum(hard_count(p.read_text()) for p in tree_paths if p.is_file())
        if tree_sum > base_sum:
            fails.append(f"ratchet: {prefix} hard count {tree_sum} > {BASE} sum {base_sum}")
    base = json.loads(run("git", "show", f"{BASE}:scripts/ste-baseline.json"))
    tree = json.loads((ROOT / "scripts" / "ste-baseline.json").read_text())
    allowed = tuple(f"skills/{s}/" for s in SKILLS)
    for key in sorted(set(base) | set(tree)):
        if base.get(key, None) != tree.get(key, None) and not key.startswith(allowed):
            fails.append(f"ratchet: scripts/ste-baseline.json changed outside the three skills: {key}")
    return fails


COMMANDS = {"budget": budget, "qualifiers": qualifiers, "backlog": backlog, "ratchet": ratchet}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"usage: check_gh308.py {{{'|'.join(COMMANDS)}}} [<skill>]", file=sys.stderr)
        return 2
    fails = COMMANDS[sys.argv[1]](sys.argv[2:])
    for line in fails:
        print(line)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
