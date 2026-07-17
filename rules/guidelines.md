# Engineering Guidelines (Active Profile)

This file is the **active engineering-guidelines profile** for this project.

Stack-specific guidelines live in `templates/stacks/<stack>/guidelines.md` and are generated
in `templates/stacks/<stack>/`. Copy the appropriate profile here when setting up a project.

---

## Code Style

Naming conventions, type annotations, and code organization — fill per stack.

## Layer Discipline

Define the layer boundary (entry → orchestration → logic → data → storage).
Each layer has one responsibility; do not leak concerns across boundaries.

## Error Handling

- Guard clauses first — handle errors at function top with early returns.
- Use a shared error/exception factory; avoid ad-hoc error construction at call sites.
- Log errors with context: include the component name and the error value.

## Data Access

- Route all persistence through the data-access layer; no ad-hoc queries in higher layers.
- Background code must use an isolated session, not the request-scoped one.

## Async I/O & Performance

- Never block the primary execution thread — all I/O must be non-blocking.
- Use a cache layer for frequently read data; invalidate on write.

## Testing

- Always test: happy path, error/edge cases, boundary conditions.
- Unit tests must not hit real external systems; use mocks or fakes for I/O.
- Coverage target: fill per stack (80% is a common baseline).

## Logging

- Use a module-scoped logger (one per file).
- Prefix log messages with component context: `[SERVICE_NAME]`, `[HANDLER]`, etc.
- Never log sensitive data (tokens, passwords, full request bodies in production).
