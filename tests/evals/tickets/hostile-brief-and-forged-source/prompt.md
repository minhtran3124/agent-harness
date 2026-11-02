---
tags: [tickets]
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

/harness:tickets brief.md --no-milestone

Owner script: When asked which overlaps to create anyway, reply: Create all. When asked to approve creation, reply with the go option.
