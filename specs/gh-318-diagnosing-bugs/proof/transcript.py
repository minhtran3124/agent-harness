#!/usr/bin/env python3
"""Print a marked transcript of a `claude -p --output-format stream-json` run.

Usage: transcript.py <stream.jsonl> <loop command>

One line per main-thread assistant text block and per tool call, in stream order:
    <MARKER>\t<kind>\t<summary>
Markers (first match wins, in this order): REVIEW, PROBE, HYPOTHESIS, LOOP-RED, else `-`.
HYPOTHESIS marks a text block, a Write content or a Bash command (e.g. a heredoc) holding a line
whose first word, after whitespace, list markers and `*`, is `H1`.
Subagent events (parent_tool_use_id set) are left out: the markers describe the model under test.
"""
import json
import re
import sys

EXIT_RE = re.compile(r"(?i)\bexit(?:[ _-]?(?:code|status))?\s*[=:]?\s*[1-9]\d*\b")
LIST_PREFIX_RE = re.compile(r"^(?:\s|[-+*]|\d+[.)])*")
H1_RE = re.compile(r"H1\b")
SECRET_RE = re.compile(r"(sk-ant-[A-Za-z0-9_-]+|gh[pousr]_[A-Za-z0-9]{20,}|"
                       r"(?i:(?:api[_-]?key|token|secret|password)\s*[=:]\s*)\S+)")


def redact(text):
    return SECRET_RE.sub("<REDACTED>", text)


def result_text(block):
    content = block.get("content")
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return content if isinstance(content, str) else ""


def has_h1_line(text):
    return any(H1_RE.match(LIST_PREFIX_RE.sub("", line, count=1))
               for line in text.splitlines())


def load(path):
    events, results = [], {}
    with open(path, encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                ev = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if ev.get("parent_tool_use_id"):
                continue
            content = (ev.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            if ev.get("type") == "assistant":
                events.extend(b for b in content if b.get("type") in ("text", "tool_use"))
            elif ev.get("type") == "user":
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        results[b.get("tool_use_id")] = b
    return events, results


def marker(block, results, loop_cmd):
    if block["type"] == "text":
        return "HYPOTHESIS" if has_h1_line(block.get("text", "")) else "-"
    name, inp = block.get("name", ""), block.get("input") or {}
    blob = json.dumps(inp, ensure_ascii=False)
    if name in ("Agent", "Task") and ("diagnosis-review-prompt.md" in blob
                                      or inp.get("subagent_type") == "task-reviewer"):
        return "REVIEW"
    if "[DEBUG-" in blob:
        return "PROBE"
    if name == "Write" and has_h1_line(str(inp.get("content", ""))):
        return "HYPOTHESIS"
    if name == "Bash" and has_h1_line(str(inp.get("command", ""))):
        return "HYPOTHESIS"
    if name == "Bash" and loop_cmd in str(inp.get("command", "")):
        res = results.get(block.get("id")) or {}
        if res.get("is_error") or EXIT_RE.search(result_text(res)):
            return "LOOP-RED"
    return "-"


def summary(block):
    if block["type"] == "text":
        text = block.get("text", "")
        kind = "text"
    else:
        inp = block.get("input") or {}
        text = inp.get("command") or inp.get("file_path") or inp.get("description") \
            or inp.get("pattern") or json.dumps(inp, ensure_ascii=False)
        kind = block.get("name", "tool")
    text = redact(" ".join(str(text).split()))
    return kind, (text[:200] + "...") if len(text) > 200 else text


def main(argv):
    if argv[1:] in (["--help"], ["-h"]):
        print(__doc__)
        return 0
    if len(argv) != 3:
        print("usage: transcript.py <stream.jsonl> <loop command>", file=sys.stderr)
        return 2
    events, results = load(argv[1])
    for block in events:
        kind, text = summary(block)
        print(f"{marker(block, results, argv[2])}\t{kind}\t{text}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
