#!/usr/bin/env python3
"""Spec-local checks for gh-309. Each subcommand prints one line per failure and exits 1 on any
failure, 0 otherwise.

Usage: check_gh309.py anchors | qualifiers | blindrun | scope | --selftest

Verifies:
- anchors (SC-1): step 2 of `## Flow` in skills/brainstorming/SKILL.md (working tree) holds the
  seven anchor phrases (case-insensitive), the sentence holding `evasive` names `decision`, the
  visual-artifact sentence is present verbatim, and step 2 holds no `;`.
- qualifiers (SC-4): the qualifiers file exists with its `Source:` header, has `replaced:` lines
  for "any" and "still", and has a `kept:`/`replaced:` line for every condition word that
  `scripts/check_scope_qualifiers.py --base BASE --head HEAD` lists under skills/brainstorming/.
  Each cited text occurs in SKILL.md at HEAD (whitespace collapsed).
- blindrun (SC-5): blind-run.md has at least one `## Run <n>` section, every earlier section has a
  `Result: pass|fail` line, and the last section has the four headings, `Decisions: <n>` with
  10 <= n <= 13, `Rounds: <n>` with n <= 3, two or more `#### Round ` lines under
  `### Transcript`, `Result: pass`, and scoring rows (a)-(d) whose result cell is `pass`.
- scope (SC-6): `git diff --name-only BASE..HEAD -- skills/` lists only
  skills/brainstorming/SKILL.md.
Does not verify: that the step 2 prose means what the anchors suggest, that a cited `kept:` or
`replaced:` text keeps the condition's meaning, or that the blind run was truly blind or scored
honestly. --selftest covers anchors, blindrun and the any/still half of qualifiers with fixture
strings. scope and the script half of qualifiers need a git history and are not self-tested.
"""
import re
import subprocess
import sys
from pathlib import Path

BASE = "996f50d"
SPEC = "specs/gh-309-grilling-rounds"
SKILL = "skills/brainstorming/SKILL.md"
QUALIFIERS = f"{SPEC}/qualifiers-brainstorming.md"
BLIND_RUN = f"{SPEC}/blind-run.md"
ANCHORS = ("design tree", "frontier", "numbered round", "recommended answer",
           "never ask the user for a fact", "record the recommended answer as an assumption",
           "shared understanding")
VISUAL = ("Use a visual artifact only when seeing the answer is materially clearer than "
          "reading it.")
SOURCE = "Source: python3 scripts/check_scope_qualifiers.py"
FIXED_WORDS = ("any", "still")


def run(*args: str) -> str:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=True).stdout


ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                           text=True, check=True).stdout.strip())


def collapse(text: str) -> str:
    return " ".join(text.split())


def step2(skill_text: str) -> str | None:
    """Step 2 of `## Flow`, lines joined and whitespace collapsed; None when not found."""
    lines, in_flow, start = skill_text.splitlines(), False, None
    for i, line in enumerate(lines):
        if line.startswith("## "):
            if start is not None:
                return None
            in_flow = line.strip() == "## Flow"
        elif in_flow and start is None and line.startswith("2. "):
            start = i
        elif in_flow and start is not None and line.startswith("3. "):
            return collapse(" ".join(lines[start:i]))
    return None


def check_anchors(skill_text: str) -> list[str]:
    step = step2(skill_text)
    if step is None:
        return ["anchors: step 2 (`2. ` to `3. ` inside `## Flow`) not found"]
    low = step.lower()
    fails = [f"anchors: step 2 lacks \"{a}\"" for a in ANCHORS if a not in low]
    evasive = [s for s in re.split(r"(?<=[.!?])\s+", step) if "evasive" in s.lower()]
    if not evasive:
        fails.append("anchors: step 2 has no sentence holding \"evasive\"")
    fails += [f"anchors: sentence holding \"evasive\" lacks \"decision\": {s}"
              for s in evasive if "decision" not in s.lower()]
    if VISUAL not in step:
        fails.append(f"anchors: step 2 lacks the sentence: {VISUAL}")
    if ";" in step:
        fails.append("anchors: step 2 holds a \";\"")
    return fails


def entries(qual_text: str) -> dict[tuple[str, str], tuple[str, str]]:
    """Map (line, word) to (verb, cited text) from `- SKILL:<n> "<word>" kept|replaced: <text>`."""
    found = {}
    pattern = re.compile(r'^- ' + re.escape(SKILL) + r':(\d+) "([^"]+)" (kept|replaced): (.+)$')
    for line in qual_text.splitlines():
        m = pattern.match(line.strip())
        if not m:
            continue
        text = m.group(4).strip()
        if len(text) > 1 and text.startswith("`") and text.endswith("`"):
            text = text[1:-1]
        found[(m.group(1), m.group(2))] = (m.group(3), collapse(text))
    return found


def check_fixed(skill_text: str, qual_text: str) -> list[str]:
    """Source header plus `replaced:` lines for "any" and "still" whose text occurs in skill_text."""
    fails = []
    if not any(line.startswith(SOURCE) for line in qual_text.splitlines()):
        fails.append(f"qualifiers: {QUALIFIERS} lacks a line starting with `{SOURCE}`")
    skill = collapse(skill_text)
    found = entries(qual_text)
    for word in FIXED_WORDS:
        cited = [text for (_, w), (verb, text) in found.items() if w == word and verb == "replaced"]
        if not cited:
            fails.append(f"qualifiers: no replaced line for \"{word}\" in {QUALIFIERS}")
        fails += [f"qualifiers: \"{word}\" cited text not found at HEAD: {t}"
                  for t in cited if t not in skill]
    return fails


def qualifiers() -> list[str]:
    path = ROOT / QUALIFIERS
    if not path.is_file():
        return [f"qualifiers: {QUALIFIERS} is missing"]
    qual_text = path.read_text()
    skill_text = run("git", "show", f"HEAD:{SKILL}")
    fails = check_fixed(skill_text, qual_text)
    skill, found = collapse(skill_text), entries(qual_text)
    out = run(sys.executable, "scripts/check_scope_qualifiers.py", "--base", BASE, "--head", "HEAD")
    for line in out.splitlines():
        if line.startswith("scope-qualifiers: unavailable"):
            fails.append(f"qualifiers: {line}")
            continue
        if not line.startswith("- ") or line == "- none":
            continue
        loc, _, rest = line[2:].partition(": dropped \"")
        word = rest.partition('"')[0]
        file, _, num = loc.rpartition(":")
        if not file.startswith("skills/brainstorming/"):
            continue
        entry = found.get((num, word)) if file == SKILL else None
        if entry is None:
            fails.append(f"qualifiers: no kept/replaced line for {file}:{num} \"{word}\" "
                         f"in {QUALIFIERS}")
        elif entry[1] not in skill:
            fails.append(f"qualifiers: {file}:{num} \"{word}\" cited text not found at HEAD: "
                         f"{entry[1]}")
    return fails


def check_blindrun(text: str) -> list[str]:
    sections, current = [], None
    for line in text.splitlines():
        if re.match(r"^## Run \d+\b", line):
            current = []
            sections.append(current)
        elif line.startswith("## "):
            current = None
        elif current is not None:
            current.append(line.rstrip())
    if not sections:
        return ["blindrun: no `## Run <n>` section"]
    fails = [f"blindrun: run section {i} lacks a `Result: pass|fail` line"
             for i, sec in enumerate(sections[:-1], 1)
             if not any(re.fullmatch(r"Result: (pass|fail)", l) for l in sec)]
    last = sections[-1]
    for heading in ("### Design question", "### Answer key", "### Transcript", "### Scoring"):
        if heading not in last:
            fails.append(f"blindrun: last run lacks `{heading}`")
    decisions = [int(m.group(1)) for l in last if (m := re.fullmatch(r"Decisions: (\d+)", l))]
    if not any(10 <= n <= 13 for n in decisions):
        fails.append(f"blindrun: last run lacks `Decisions: <n>` with 10 <= n <= 13 (found {decisions})")
    rounds = [int(m.group(1)) for l in last if (m := re.fullmatch(r"Rounds: (\d+)", l))]
    if not any(n <= 3 for n in rounds):
        fails.append(f"blindrun: last run lacks `Rounds: <n>` with n <= 3 (found {rounds})")
    sub = None
    transcript_rounds = 0
    scoring = {}
    for line in last:
        if line.startswith("### "):
            sub = line
        elif sub == "### Transcript" and line.startswith("#### Round "):
            transcript_rounds += 1
        elif sub == "### Scoring" and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            m = re.match(r"\(([a-d])\)", cells[0])
            if m:
                scoring[m.group(1)] = cells[-1]
    if transcript_rounds < 2:
        fails.append(f"blindrun: last run has {transcript_rounds} `#### Round ` lines under "
                     "`### Transcript` (need 2)")
    if "Result: pass" not in last:
        fails.append("blindrun: last run lacks `Result: pass`")
    for row in "abcd":
        if scoring.get(row) != "pass":
            fails.append(f"blindrun: scoring row ({row}) result is {scoring.get(row)!r}, not 'pass'")
    return fails


def anchors() -> list[str]:
    return check_anchors((ROOT / SKILL).read_text())


def blindrun() -> list[str]:
    path = ROOT / BLIND_RUN
    if not path.is_file():
        return [f"blindrun: {BLIND_RUN} is missing"]
    return check_blindrun(path.read_text())


def scope() -> list[str]:
    out = run("git", "diff", "--name-only", f"{BASE}..HEAD", "--", "skills/")
    return [f"scope: changed outside {SKILL}: {p}" for p in out.splitlines() if p and p != SKILL]


GOOD_SKILL = f"""# Brainstorming

## Flow

1. Inspect the project.
2. Walk the design tree one numbered round at a time. Ask from the frontier.
   Give a recommended answer with each question. Never ask the user for a fact the code holds.
   If an answer is evasive twice, name the decision and record the recommended answer as an
   assumption. Stop at shared understanding. {VISUAL}
3. Present approaches.

## Next
"""
BAD_SKILL = GOOD_SKILL.replace("evasive twice, name the decision", "evasive twice; name the gap")
GOOD_QUAL = f"""{SOURCE} --base {BASE} --head HEAD
- {SKILL}:8 "any" replaced: `Stop at shared understanding.`
- {SKILL}:6 "still" replaced: Give a recommended answer with each question.
"""
BAD_QUAL = GOOD_QUAL.replace("Give a recommended", "Offer a recommended")
GOOD_RUN = """# Blind run

## Run 1

Result: fail

## Run 2

### Design question
Q

### Answer key
Decisions: 11

### Transcript
#### Round 1
#### Round 2
Rounds: 2

### Scoring
| Criterion | Evidence | Result |
|---|---|---|
| (a) all decisions | x | pass |
| (b) rounds | x | pass |
| (c) no fact asked | x | pass |
| (d) assumptions | x | pass |

Result: pass
"""
BAD_RUN = GOOD_RUN.replace("Decisions: 11", "Decisions: 14").replace("| (c) no fact asked | x | pass |",
                                                                   "| (c) no fact asked | x | fail |")


def selftest() -> int:
    cases = [
        ("anchors good", check_anchors(GOOD_SKILL), False),
        ("anchors bad", check_anchors(BAD_SKILL), True),
        ("qualifiers good", check_fixed(GOOD_SKILL, GOOD_QUAL), False),
        ("qualifiers bad", check_fixed(GOOD_SKILL, BAD_QUAL), True),
        ("blindrun good", check_blindrun(GOOD_RUN), False),
        ("blindrun bad", check_blindrun(BAD_RUN), True),
    ]
    wrong = 0
    for name, fails, expect_fail in cases:
        if bool(fails) != expect_fail:
            wrong += 1
            print(f"selftest: {name}: expected {'failures' if expect_fail else 'none'}, got {fails}")
    return 1 if wrong else 0


COMMANDS = {"anchors": anchors, "qualifiers": qualifiers, "blindrun": blindrun, "scope": scope}


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        return selftest()
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(f"usage: check_gh309.py {{{'|'.join(COMMANDS)}|--selftest}}", file=sys.stderr)
        return 2
    fails = COMMANDS[sys.argv[1]]()
    for line in fails:
        print(line)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
