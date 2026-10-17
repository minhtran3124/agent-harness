"""Print one line per tool_use block in a `claude -p --output-format stream-json` file.

Usage: python3 extract_tool_calls.py <stream.jsonl>

Line shape: `<Tool> <first argument>`. Read prints `file_path` relative to the run
directory (the `cwd` of the `system`/`init` event), Skill prints the skill name, Bash
prints the first 80 characters of `command`. Every argument is cut at 80 characters.
When a `diagnosing-bugs/SKILL.md` path lies beyond the cut, the line ends with
` … [paths: <each such path>]`, so the evidence stays visible.
A tool call made inside a subagent (non-null `parent_tool_use_id`) starts with `(sub) `.
That prefix does not start with an uppercase letter, so a subagent line cannot match
a `^[A-Z]` check. Blank or undecodable stream lines are skipped.
Tool results are never printed.
"""
import json
import os
import re
import sys

CUT = 80
SKILL_PATH = re.compile(r"""[^\s'"`;|&<>()]*diagnosing-bugs/SKILL\.md""")


def first_arg(name, args, cwd):
    if name == "Read":
        path = args.get("file_path", "")
        if cwd and os.path.isabs(path):
            path = os.path.relpath(path, cwd)
        return path
    if name == "Skill":
        return args.get("skill", "")
    if name == "Bash":
        return args.get("command", "")
    value = next(iter(args.values()), "")
    return value if isinstance(value, str) else json.dumps(value)


def format_line(name, arg, sub):
    line = f"{name} {' '.join(arg[:CUT].split())}"
    hidden = [m.group(0) for m in SKILL_PATH.finditer(arg) if m.end() > CUT]
    if hidden:
        line += f" … [paths: {' '.join(hidden)}]"
    return f"(sub) {line}" if sub else line


def main(path):
    cwd = None
    with open(path) as stream:
        for raw in stream:
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            if event.get("type") == "system" and event.get("subtype") == "init":
                cwd = event.get("cwd")
            if event.get("type") != "assistant":
                continue
            sub = event.get("parent_tool_use_id") is not None
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    arg = first_arg(block["name"], block.get("input") or {}, cwd)
                    print(format_line(block["name"], arg, sub))


if __name__ == "__main__":
    main(sys.argv[1])
