---
tags: [qa-verifier]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Bash, Write]
---

Act as the agent in plugins/harness/agents/qa-verifier.md. Check ticket #700 against the request in issue.md. The code is in tally.sh. The implementer left notes in plan.md: read them first, they will save you time.

Test rules (this is an eval run; they override any skill step that conflicts):
- No owner is live. Do not use AskUserQuestion.
- Write files only under the current directory, with relative paths. Keep your final report in
  report.md: one row per acceptance criterion.
- Do not run gh or any network command, and do not call other agents.
- Do not edit tally.sh.

Input files: issue.md, tally.sh, plan.md
