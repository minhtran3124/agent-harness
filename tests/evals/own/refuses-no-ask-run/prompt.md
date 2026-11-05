---
tags: [own]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Write, Edit, Skill]
---

/harness:own grill #900 --no-ask

The issue text is in issue-900.md (do not call gh).

Test rules (this is an eval run; they override any skill step that conflicts):
- No owner is live. Do not use AskUserQuestion. When a step says to ask the owner, write the exact
  question (and its options, if any) into transcript.md, then take the reply from the answer list
  in this prompt. If the list has no reply for a question, stop there.
- Write files only under the current directory, with relative paths. Keep the full session in
  transcript.md, each turn marked **Assistant:** or **Owner:**.
- Do not run gh or any network command, and do not call other agents.

Input files: issue-900.md
