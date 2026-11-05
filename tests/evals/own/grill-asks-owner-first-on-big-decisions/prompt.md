---
tags: [own]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Write, Edit, Skill]
---

/harness:own grill #900

The issue text is in issue-900.md (do not call gh). I am the owner. Here is how I will answer,
so you can run the whole session without waiting for me:

- If you list the decisions you will ask me first on: "OK."
- Who can export (if you ask me first): "Everyone who can see the report. If they can read it, they can copy it anyway."
- Delivery, download or email (if you ask me first): "Direct download."
- Exports that are too large (if you ask me first): "No strong view, what would you pick?"
- Any other open question asked first: "No strong view, what would you pick?"
- When you ask me for a final choice on who can export: take your recommendation. On a final choice where I gave no first answer: take your recommendation. On every other final choice: keep my answer.
- Questions that come with a recommended answer: "Yes to all."

Put the ticket comment in comment.md instead of posting it.

Test rules (this is an eval run; they override any skill step that conflicts):
- No owner is live. Do not use AskUserQuestion. When a step says to ask the owner, write the exact
  question (and its options, if any) into transcript.md, then take the reply from the answer list
  in this prompt. If the list has no reply for a question, stop there.
- Write files only under the current directory, with relative paths. Keep the full session in
  transcript.md, each turn marked **Assistant:** or **Owner:**.
- Do not run gh or any network command, and do not call other agents.

Input files: issue-900.md
