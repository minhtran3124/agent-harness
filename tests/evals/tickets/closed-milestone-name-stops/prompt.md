---
tags: [tickets]
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill]
---

/harness:tickets brief.md --milestone Search

Owner script: If told the milestone is closed, reply nothing further: the run ends there.
