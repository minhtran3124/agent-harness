# Critical Patterns

Always read when consuming this knowledge base, regardless of query domain. Keep this file short — entries here are high-leverage learnings that apply across many features.

Add an entry only when the pattern:
1. Has caused non-obvious bugs in multiple modules, OR
2. Documents a non-negotiable project rule that can't be expressed in a linter

## Entries

_(none yet — added by `/compound` when a pattern qualifies)_

<!--
Example entry shape:

## Async context propagation

**Applies to:** any background task spawning
**Rule:** Use `contextvars.copy_context()` when spawning; otherwise request-scoped state (user, tenant, trace_id) is lost.
**Reference:** docs/solutions/async/context-propagation.md
-->
