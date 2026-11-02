---
tags: [tickets]
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

/harness:tickets brief.md --milestone "Search Q4"

Owner script: When asked to approve creation, reply with the go option.
