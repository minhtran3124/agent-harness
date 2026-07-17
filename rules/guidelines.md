# Engineering Guidelines — pointer

This project's **engineering-guidelines profile lives in `techstacks/`** (a project-owned folder).
Agents: read `techstacks/*.md` for code style, error handling, data access, async/perf, testing,
and logging conventions before writing code.

The harness core ships **no** stack-specific guidelines — `techstacks/` is yours to fill (see
`techstacks/README.md`). Behavior that is genuinely stack-agnostic lives in `rules/behavior.md`
(the SoT for all agents), which applies regardless of stack.
