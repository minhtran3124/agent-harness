"""Print one line per tool_use block in a `claude -p --output-format stream-json` file.

Usage: python3 extract_tool_calls.py <stream.jsonl>

Line shape: `<Tool> <first argument>`. Read prints `file_path` relative to the run
directory (the `cwd` of the `system`/`init` event), Skill prints the skill name, Bash
prints the first 80 characters of `command`. Tool results are never printed.
"""
import json
import os
import sys


def first_arg(name, args, cwd):
    if name == "Read":
        path = args.get("file_path", "")
        if cwd and os.path.isabs(path):
            path = os.path.relpath(path, cwd)
        return path
    if name == "Skill":
        return args.get("skill", "")
    if name == "Bash":
        return args.get("command", "")[:80]
    value = next(iter(args.values()), "")
    return value if isinstance(value, str) else json.dumps(value)


def main(path):
    cwd = None
    with open(path) as stream:
        for raw in stream:
            event = json.loads(raw)
            if event.get("type") == "system" and event.get("subtype") == "init":
                cwd = event.get("cwd")
            if event.get("type") != "assistant":
                continue
            for block in event["message"].get("content", []):
                if block.get("type") == "tool_use":
                    arg = first_arg(block["name"], block.get("input") or {}, cwd)
                    print(f"{block['name']} {' '.join(arg[:80].split())}")


if __name__ == "__main__":
    main(sys.argv[1])
